import dpath.util
import json
import pbclient
import re

from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.http.request import QueryDict
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView, TemplateView

from .exceptions import (
    PresenterNotDefined, TaskSourceNotDefined, NoTasksLeft, TaskWithNoTemplateNorForm
)
from .settings import (
    RANDOM_SOURCE, PYBOSSA_SOURCE, TASK_SOURCE,
    PYBOSSA_PROJECT_ID, DEVELOPMENT_MODE
)
from .tasks import AbstractTask


class TaskView(FormView):
    # TODO either we should have full template in Moonsheep or have that template in project_template
    template_name = 'task.html'
    form_template_name = None
    task = None
    form_class = None

    def get(self, request, *args, **kwargs):
        """
        Returns form for a this task

        Algorithm:
        1. Get actual (implementing) class name, ie. FindTableTask
        2. Try to return if exists 'forms/find_table.html'
        3. Otherwise return `forms/FindTableForm`
        4. Otherwise return error suggesting to implement 2 or 3
        :return: path to the template (string) or Django's Form class
        """
        try:
            self.task = self._get_task()
            self._get_form_class_data()
        except NoTasksLeft:
            self.task = None

        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate a form instance with the passed
        POST variables and then check if it's valid.

        Overrides django.views.generic.edit.ProcessFormView to adapt for a case
        when user hasn't defined form for a given task.
        """
        if '_task_id' not in request.POST:
            return HttpResponseBadRequest('Missing _task_id field. Include moonsheep_token template tag!')

        if '_project_id' not in request.POST:
            return HttpResponseBadRequest('Missing _project_id field. Include moonsheep_token template tag!')

        self.task = self._get_task(
            new=False,
            project_id=request.POST['_project_id'],
            task_id=request.POST['_task_id']
        )

        self._get_form_class_data()
        form = self.get_form()

        # no form defined in the task
        if form is None:
            data = unpack_post(request.POST)
            # TODO what to do if we have forms defined? is Django nested formset a way to go?
            # Check https://stackoverflow.com/questions/20894629/django-nested-inline-formsets
            # Check https://docs.djangoproject.com/en/2.0/ref/contrib/admin/#django.contrib.admin.InlineModelAdmin
            self._send_task(data)
            return HttpResponseRedirect(self.get_success_url())

        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super(TaskView, self).get_context_data(**kwargs)
        if self.task:
            context['task'] = self.task
            try:
                context['presenter'] = self.task.get_presenter()
            except TypeError:
                pass
        else:
            context.update({
                'error': True,
                'message': 'Broker returned no tasks',
                'template': 'error-messages/no-tasks.html'
            })
        return context

    def _get_form_class_data(self):
        # Template showing a task: presenter and the form, can be overridden by setting task_template in your Task
        # By default it uses moonsheep/templates/task.html

        self.template_name = getattr(self.task, 'task_template', None)

        self.form_template_name = getattr(self.task, 'task_form_template', None)
        self.form_class = getattr(self.task, 'task_form', None)

        # if not self.form_class and not self.form_template_name:
        #     raise TaskWithNoTemplateNorForm(self.task.__class__)

    # =====================
    # Override FormView to adapt for a case when user hasn't defined form for a given task
    # and to process form in our own manner

    def get_form_class(self):
        return self.task.task_form if hasattr(self.task, 'task_form') else None

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view.

        Overrides django.views.generic.edit.FormMixin to adapt for a case
        when user hasn't defined form for a given task.
        """
        if form_class is None:
            form_class = self.get_form_class()

        if form_class is None:
            return None
        return form_class(**self.get_form_kwargs())

    def form_valid(self, form):
        self._send_task(form.cleaned_data)
        return super(TaskView, self).form_valid(form)

    # End of FormView override
    # ========================

    def _get_task(self, new=True, project_id=None, task_id=None):
        if new:
            task_data = self._get_new_task()
        else:
            if DEVELOPMENT_MODE:
                task_data = self.get_random_mocked_task_data(task_id)
            else:
                task_data = pbclient.get_task(
                    project_id=project_id,
                    task_id=task_id
                )[0]

        return AbstractTask.create_task_instance(task_data['info']['type'], **task_data)

    def _get_new_task(self):
        """
        Mechanism responsible for getting tasks. Points to PyBossa API and collects task.
        Task structure contains type, url and metadata that might be displayed in template.

        :rtype: AbstractTask
        :return: user's implementation of AbstractTask object
        """
        if TASK_SOURCE == RANDOM_SOURCE:
            task = self.get_random_mocked_task_data()
        elif TASK_SOURCE == PYBOSSA_SOURCE:
            task = self.get_random_pybossa_task()
        else:
            raise TaskSourceNotDefined

        if not task:
            raise NoTasksLeft

        return task

    __mocked_task_counter = 0

    def get_random_mocked_task_data(self, task_type=None):
        # Make sure that tasks are imported before this code is run, ie. in your project urls.py
        if task_type is None:
            defined_tasks = [
                klass.__module__ + '.' + klass.__qualname__ for klass in globals()['AbstractTask'].__subclasses__()
            ]
            defined_tasks.sort()

            if not defined_tasks:
                raise NotImplementedError(
                    "You haven't defined any tasks or forgot to add in urls.py folllowing line: from .tasks import *"
                    + "# Keep it to make Moonsheep aware of defined tasks")

            # Rotate tasks one after another
            TaskView.__mocked_task_counter += 1
            if TaskView.__mocked_task_counter >= len(defined_tasks):
                TaskView.__mocked_task_counter = 0
            task_type = defined_tasks[TaskView.__mocked_task_counter]

        default_params = {
            'info': {
                "url": "http://sccg.sk/~cernekova/Benesova_Digital%20Image%20Processing%20Lecture%20Objects%20tracking%20&%20motion%20detection.pdf",
                "type": task_type,
            },
            'id': task_type,
            'project_id': 'https://i.imgflip.com/hkimf.jpg'
        }

        task = AbstractTask.create_task_instance(task_type, **default_params)
        # Check if developers don't want to test out tasks with mocked data
        if hasattr(task, 'create_mocked_task') and callable(task.create_mocked_task):
            return task.create_mocked_task(default_params)
        else:
            return default_params

    def get_random_pybossa_task(self):
        """
        Method for obtaining task structure from distant source, i.e. PyBossa

        :rtype: dict
        :return: task structure
        """
        return pbclient.get_new_task(PYBOSSA_PROJECT_ID)

    def _send_task(self, data):
        """
        Mechanism responsible for sending tasks. Points to PyBossa API taskrun and sends data from form.
        """
        if DEVELOPMENT_MODE:
            # In development let's take a shortcut straight to verification
            taskruns_list = [data]
            self.task.verify_and_save(taskruns_list)
            return

        if TASK_SOURCE == PYBOSSA_SOURCE:
            self.send_pybossa_task(data)
        else:
            raise TaskSourceNotDefined()

    def send_pybossa_task(self, data):
        user_ip = self.request.META.get(
            'HTTP_X_FORWARDED_FOR', self.request.META.get('REMOTE_ADDR')
        ).split(',')[-1].strip()
        return pbclient.create_taskrun(PYBOSSA_PROJECT_ID, self.task.id, data, user_ip)


class AdminView(TemplateView):
    template_name = 'views/admin.html'


class NewTaskView(TemplateView):
    template_name = 'views/new-task.html'


class TaskListView(TemplateView):
    template_name = 'views/stats.html'


class ManualVerificationView(TemplateView):
    template_name = 'views/manual-verification.html'


class WebhookTaskRunView(View):
    # TODO: instead of csrf exempt, IP white list
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(WebhookTaskRunView, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        # empty response so pybossa can set webhook to this endpoint
        return HttpResponse(status=200)

    def post(self, request):
        """
        Receive webhooks from other applications.

        Event: PyBossa's task_completed sends following data
        {
          'fired_at':,
          'project_short_name': 'project-slug',
          'project_id': 1,
          'task_id': 1,
          'result_id': 1,
          'event': 'task_completed'
        }
        :param request:
        :return:
        """
        try:
            webhook_data = json.loads(request.read().decode('utf-8'))
        except json.JSONDecodeError:
            return HttpResponseBadRequest()

        if webhook_data.get('event') == 'task_completed':
            project_id = webhook_data.get('project_id')
            task_id = webhook_data.get('task_id')

            if not project_id or not task_id:
                return HttpResponseBadRequest()
            AbstractTask.verify_task(project_id, task_id)
            return HttpResponse("ok")

        return HttpResponseBadRequest()


def unpack_post(post: QueryDict) -> dict:
    """
    Unpack items in POST fields that have multiple occurences.

    It handles:
    - multiple fields without brackets, ie. field
    - multiple fields PHP5 style, ie. field[]
    - objects, ie. obj[field1]=val1 obj[field2]=val2
    - multiple rows of several fields, ie. row[0][field1], row[1][field1]
    - hierarchily nested multiples, ie. row[0][entry_id], row[0][entry_options][]

    Possible TODO, Django does it like this: (we could use Django parsing)
    <input type="hidden" name="acquisition_titles-TOTAL_FORMS" value="3" id="id_acquisition_titles-TOTAL_FORMS" autocomplete="off">
    <input type="hidden" name="acquisition_titles-INITIAL_FORMS" value="0" id="id_acquisition_titles-INITIAL_FORMS">
    <input type="hidden" name="acquisition_titles-MIN_NUM_FORMS" value="0" id="id_acquisition_titles-MIN_NUM_FORMS">
    <input type="hidden" name="acquisition_titles-MAX_NUM_FORMS" value="1000" id="id_acquisition_titles-MAX_NUM_FORMS" autocomplete="off">
    <input type="hidden" name="acquisition_titles-1-id" id="id_acquisition_titles-1-id">
    <input type="hidden" name="acquisition_titles-1-property" id="id_acquisition_titles-1-property">

    :param QueryDict post: POST data
    :return: dictionary representing the object passed in POST
    """

    dpath_separator = '/'
    result = {}
    convert_to_array_paths = set()

    for k in post.keys():
        # analyze field name
        m = re.search(r"^" +
                      "(?P<object>[\w\-_]+)" +
                      "(?P<selectors>(\[[\d\w\-_]+\])*)" +
                      "(?P<trailing_brackets>\[\])?" +
                      "$", k)
        if not m:
            raise Exception("Field name not valid: {}".format(k))

        path = m.group('object')
        if m.group('selectors'):
            for ms in re.finditer(r'\[([\d\w\-_]+)\]', m.group('selectors')):
                # if it is integer then make sure list is created
                idx = ms.group(1)
                if re.match(r'\d+', idx):
                    convert_to_array_paths.add(path)

                path += dpath_separator + idx

        def get_list_or_value(post, key):
            val = post.getlist(key)
            # single element leave single unless developer put brackets
            if len(val) == 1 and not m.group('trailing_brackets'):
                val = val[0]
            return val

        dpath.util.new(result, path, get_list_or_value(post, k), separator=dpath_separator)

    # dpath only works on dicts, but sometimes we want arrays
    # ie. row[0][fld]=0&row[1][fld]=1 results in row { "0": {}, "1": {} } instead of row [ {}, {} ]
    for path_to_d in convert_to_array_paths:
        arr = []
        d = dpath.util.get(result, path_to_d)
        numeric_keys = [int(k_int) for k_int in d.keys()]
        for k_int in sorted(numeric_keys):
            arr.append(d[str(k_int)])

        dpath.util.set(result, path_to_d, arr)

    return result
