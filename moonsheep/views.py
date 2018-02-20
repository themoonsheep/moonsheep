import dpath.util
import json
import pbclient
import re

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.http.request import QueryDict
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView, TemplateView

from requests.exceptions import ConnectionError

from .exceptions import (
    PresenterNotDefined, TaskSourceNotDefined, NoTasksLeft, TaskMustSetTemplate
)
from .forms import NewTaskForm
from .models import Task
from .register import base_task, initial_task
from .settings import (
    RANDOM_SOURCE, PYBOSSA_SOURCE, TASK_SOURCE,
    PYBOSSA_BASE_URL, PYBOSSA_PROJECT_ID
)
from .tasks import AbstractTask


class TaskView(FormView):
    task = None
    form_class = None
    error_message = None
    error_template = None

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
            self.initialize_task_data()
        except NoTasksLeft:
            self.error_message = 'Broker returned no tasks'
            self.error_template = 'error-messages/no-tasks.html'
            self.task = None
            self.template_name = 'views/message.html'
        except ImproperlyConfigured:
            self.error_message = 'Improperly configured PyBossa'
            self.error_template = 'error-messages/improperly-configured.html'
            self.task = None
            self.template_name = 'views/message.html'
        except PresenterNotDefined:
            self.error_message = 'Presenter not defined'
            self.error_template = 'error-messages/presenter-not-defined.html'
            self.task = None
            self.template_name = 'views/message.html'

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
            project_id=request.POST['_project_id'],
            task_id=request.POST['_task_id']
        )

        self.initialize_task_data()
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
        context.update({
            'project_id': PYBOSSA_PROJECT_ID,
            'pybossa_url': PYBOSSA_BASE_URL
        })
        if self.task:
            context['task'] = self.task
            try:
                context['presenter'] = self.task.get_presenter()
            except TypeError:
                raise PresenterNotDefined
        else:
            context.update({
                'error': True,
                'message': self.error_message,
                'template': self.error_template
            })
        return context

    def initialize_task_data(self):
        # Template showing a task: presenter and the form, can be overridden by setting task_template in your Task
        # By default it uses moonsheep/templates/task.html

        # Overriding template
        if hasattr(self.task, 'template_name'):
            self.template_name = self.task.template_name

        self.form_class = getattr(self.task, 'task_form', None)

        if not self.template_name:
            raise TaskMustSetTemplate(self.task.__class__)

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

    def _get_task(self, project_id=None, task_id=None):
        if task_id:
            if TASK_SOURCE == RANDOM_SOURCE:
                task_data = self.get_random_mocked_task_data(task_id)
            elif TASK_SOURCE == PYBOSSA_SOURCE:
                task_data = pbclient.get_task(
                    project_id=project_id,
                    task_id=task_id
                )[0]
            else:
                raise TaskSourceNotDefined
        else:
            task_data = self._get_new_task()
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
            defined_tasks = base_task.registry

            if not defined_tasks:
                raise NotImplementedError(
                    "You haven't defined any tasks or forgot to add in urls.py folllowing line: from .tasks import *"
                    + "# Keep it to make Moonsheep aware of defined tasks")

            # Rotate tasks one after another
            TaskView.__mocked_task_counter += 1
            if TaskView.__mocked_task_counter >= len(defined_tasks):
                TaskView.__mocked_task_counter = 0
            task = defined_tasks[TaskView.__mocked_task_counter]()
            task_type = task.full_klass_name()

        default_params = {
            'info': {
                "url": "https://nazk.gov.ua/sites/default/files/docs/2017/3/3_kv/2/Agrarna_partija/3%20%EA%E2%E0%F0%F2%E0%EB%202017%20%D6%C0%20%C0%CF%D3%20%97%20%E7%E0%F2%E5%F0%F2%E8%E9.pdf",
                "type": task_type,
            },
            'id': task_type,
            'project_id': 'https://i.imgflip.com/hkimf.jpg'
        }

        if not task:
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
        try:
            return pbclient.get_new_task(PYBOSSA_PROJECT_ID)
        except ConnectionError:
            raise ImproperlyConfigured(
                "Please check if PyBossa is running and properly set. Current settings: PYBOSSA_URL = {0}, "
                "PYBOSSA_PROJECT_ID = {1}".format(PYBOSSA_BASE_URL, PYBOSSA_PROJECT_ID)
            )

    def _send_task(self, data):
        """
        Mechanism responsible for sending tasks. Points to PyBossa API taskrun and sends data from form.
        """
        if TASK_SOURCE == RANDOM_SOURCE:
            # In development let's take a shortcut straight to verification
            taskruns_list = [data]
            self.task.verify_and_save(taskruns_list)
            return
        elif TASK_SOURCE == PYBOSSA_SOURCE:
            self.send_pybossa_task(data)
        else:
            raise TaskSourceNotDefined()

    def send_pybossa_task(self, data):
        user_ip = self.request.META.get(
            'HTTP_X_FORWARDED_FOR', self.request.META.get('REMOTE_ADDR')
        ).split(',')[-1].strip()
        return pbclient.create_taskrun(
            project_id=PYBOSSA_PROJECT_ID,
            task_id=self.task.id,
            info=data,
            # external_uid=user_ip
        )


class AdminView(TemplateView):
    template_name = 'views/admin.html'


class NewTaskFormView(FormView):
    template_name = 'views/new-task.html'
    form_class = NewTaskForm

    def get_success_url(self):
        return reverse('ms-new-task')

    def form_valid(self, form):
        import pbclient
        from moonsheep.settings import PYBOSSA_BASE_URL, PYBOSSA_API_KEY
        pbclient.set('endpoint', PYBOSSA_BASE_URL)
        pbclient.set('api_key', PYBOSSA_API_KEY)
        if not len(initial_task.registry):
            raise ImproperlyConfigured
        for task in initial_task.registry:
            pbclient.create_task(
                project_id=PYBOSSA_PROJECT_ID,
                info={
                    'type': task().full_klass_name(),
                    'url': form.cleaned_data.get('url'),
                },
                n_answers=AbstractTask.N_ANSWERS
            )
        return super(NewTaskFormView, self).form_valid(form)


class TaskListView(TemplateView):
    template_name = 'views/task-list.html'

    def get_context_data(self, **kwargs):
        context = super(TaskListView, self).get_context_data(**kwargs)
        task_types = base_task.registry
        task_types_str = [task().full_klass_name() for task in base_task.registry]
        # TODO: in pybossa always offset 0 limit 100
        pb_tasks = pbclient.get_tasks(project_id=PYBOSSA_PROJECT_ID)
        pb_taskruns = pbclient.get_taskruns(project_id=PYBOSSA_PROJECT_ID)
        # TODO: this is spaghetti design, needs optimization
        tasks = {}
        reports = {}
        for task in pb_tasks:
            new_task = AbstractTask.create_task_instance(task.data['info']['type'], **task.data)
            task_name = new_task.full_klass_name()
            if new_task.url not in reports:
                reports[new_task.url] = dict.fromkeys(task_types_str)
            if reports[new_task.url][task_name] is None:
                reports[new_task.url][task_name] = {}
            if new_task.id not in reports[new_task.url][task_name]:
                reports[new_task.url][task_name][new_task.id] = {
                    'task': None,
                    'taskruns': [],
                }
            tasks[new_task.id] = task_name
            reports[new_task.url][task_name][new_task.id]['task'] = new_task
            reports[new_task.url][task_name][new_task.id]['taskruns'] = []
        for taskrun in pb_taskruns:
            reports[
                taskrun.data['info']['_url']
            ][
                tasks[int(taskrun.data['info']['_task_id'])].__str__()
            ][
                int(taskrun.data['info']['_task_id'])
            ]['taskruns'].\
                append(taskrun.data)
        report_data = []
        transcripted_documents = 0
        verified_tasks = 0
        for url, report in reports.items():
            report_table_data = []
            step = 100 / len(report)
            overall_percentage = 0
            # TODO: this will probably not work with OPORA
            # TODO: "required" should be multiplied by number of tasks
            for task_klass, task_data in report.items():
                if task_data:
                    for task_id, params in task_data.items():
                        completed = len(params['taskruns'])
                        overall_percentage += completed * step
                        required = AbstractTask.N_ANSWERS
                        if completed == required:
                            verified_tasks += 1
                        try:
                            percentage = "{0:.1f}%".format(100 * completed / required)
                        except ZeroDivisionError:
                            required = '?'
                            percentage = '?'
                        report_table_data.append({
                            'task_class': task_klass,
                            'required': required,
                            'completed': completed,
                            'percentage': percentage
                        })
            if verified_tasks == len(report):
                transcripted_documents += 1
            report_table_data.sort(key=lambda k: task_types_str.index(k['task_class']))
            report_data.append({
                'url': url,
                'percentage': "{0:.1f}%".format(overall_percentage),
                'tasks': report_table_data
            })
        context.update({
            'verified_tasks': verified_tasks,
            'transcripted_documents': transcripted_documents,
            'redundancy': AbstractTask.N_ANSWERS,
            'task_types': task_types,
            'reports': report_data
        })
        return context


class ManualVerificationView(TemplateView):
    template_name = 'views/manual-verification.html'

    def get_context_data(self, **kwargs):
        context = super(ManualVerificationView, self).get_context_data(**kwargs)
        context['tasks'] = Task.objects.filter(verified=False)
        print(context['tasks'])
        return context


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
