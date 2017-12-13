import datetime
import decimal
import json
import pbclient

from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView

from .exceptions import (
    PresenterNotDefined, TaskSourceNotDefined, NoTasksLeft, TaskWithNoTemplateNorForm
)
from .moonsheep_settings import (
    RANDOM_SOURCE, PYBOSSA_SOURCE, TASK_SOURCE,
    PYBOSSA_PROJECT_ID
)
from .tasks import AbstractTask


class Encoder(json.JSONEncoder):
    """Create an encoder subclassing JSON.encoder.
    Make this encoder aware of our classes (e.g. datetime.datetime objects)
    """
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, decimal.Decimal):
            # wanted a simple yield str(o) in the next line,
            # but that would mean a yield on the line with super(...),
            # which wouldn't work (see my comment below), so...
            return (str(obj) for obj in [obj])
        else:
            return json.JSONEncoder.default(self, obj)


class TaskView(FormView):
    # TODO either we should have full template in Moonsheep or have that template in project_template
    template_name = 'task.html'
    form_template_name = None

    def __init__(self, *args, **kwargs):
        # TODO: don't get task for each creation
        self.task = self._get_task()

        # Template showing a task: presenter and the form, can be overridden by setting task_template in your Task
        # By default it uses moonsheep/templates/task.html
        if hasattr(self.task, 'task_template'):
            self.template_name = self.task.task_template

        if hasattr(self.task, 'task_form_template'):
            self.form_template_name = self.task.task_form_template
        if hasattr(self.task, 'task_form'):
            self.form_class = self.task.task_form

        if self.form_class is None and self.form_template_name is None:
            raise TaskWithNoTemplateNorForm(self.task.__class__)

        super(TaskView, self).__init__(*args, **kwargs)

    def get_context_data(self, **kwargs):
        # TODO: update docstring
        """
        Returns form for a this task

        Algorithm:
        1. Get actual (implementing) class name, ie. FindTableTask
        2. Try to return if exists 'forms/find_table.html'
        3. Otherwise return `forms/FindTableForm`
        4. Otherwise return error suggesting to implement 2 or 3
        :return: path to the template (string) or Django's Form class
        """
        context = super(TaskView, self).get_context_data(**kwargs)
        context.update({
            'presenter': self.task.get_presenter(),
            'task': self.task,
        })
        return context

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
        self._send_task(form)
        return super(TaskView, self).form_valid(form)

    def form_invalid(self, form):
        print('invalid form')
        print(form.errors)
        return super(TaskView, self).form_invalid(form)

    def _get_task(self):
        """
        Mechanism responsible for getting tasks. Points to PyBossa API and collects task.
        Task structure contains type, url and metadata that might be displayed in template.

        :rtype: AbstractTask
        :return: user's implementation of AbstractTask object
        """
        if TASK_SOURCE == RANDOM_SOURCE:
            task = self.get_random_mocked_task()
        elif TASK_SOURCE == PYBOSSA_SOURCE:
            task = self.get_pybossa_task()
        else:
            raise TaskSourceNotDefined

        if not task:
            raise NoTasksLeft

        return AbstractTask.create_task_instance(task['info']['type'], **task)

    __mocked_task_counter = 0

    def get_random_mocked_task(self):
        # Make sure that tasks are imported before this code is run, ie. in your project urls.py
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
            }
        }

        task = AbstractTask.create_task_instance(task_type, **default_params)
        # Check if developers don't want to test out tasks with mocked data
        if hasattr(task, 'create_mocked_task') and callable(task.create_mocked_task):
            return task.create_mocked_task(default_params)
        else:
            return default_params

    def get_pybossa_task(self):
        """
        Method for obtaining task structure from distant source, i.e. PyBossa

        :rtype: dict
        :return: task structure
        """
        return pbclient.get_new_task(PYBOSSA_PROJECT_ID)

    def _send_task(self, form):
        """
        Mechanism responsible for sending tasks. Points to PyBossa API taskrun and sends data from form.
        """
        if TASK_SOURCE == PYBOSSA_SOURCE:
            return self.send_pybossa_task(form)
        else:
            raise TaskSourceNotDefined()

    def send_pybossa_task(self, form):
        # data = urllib.parse.urlencode(form.cleaned_data)
        data = form.cleaned_data
        user_ip = self.request.META.get(
            'HTTP_X_FORWARDED_FOR', self.request.META.get('REMOTE_ADDR')
        ).split(',')[-1].strip()
        return pbclient.create_taskrun(PYBOSSA_PROJECT_ID, self.task.id, data, user_ip)


class WebhookTaskRunView(View):
    # TODO: instead of csrf, IP white list
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(WebhookTaskRunView, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        # empty response so pybossa can set webhook to this endpoint
        return HttpResponse()

    def post(self, request):
        """
        give a response for request:
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
        webhook_data = json.loads(request.read().decode('utf-8'))
        if webhook_data['event'] == 'task_completed':
            project_id = webhook_data['project_id']
            task_id = webhook_data['task_id']

            AbstractTask.verify_task(project_id, task_id)

            return HttpResponse("ok")
        return HttpResponseBadRequest()
