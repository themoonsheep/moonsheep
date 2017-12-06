import datetime
import json
import pbclient
import random

from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView

from .exceptions import (
    PresenterNotDefined, TaskSourceNotDefined, NoTasksLeft
)
from .forms import DummyForm
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
        else:
            return json.JSONEncoder.default(self, obj)


class TaskView(FormView):
    template_name = 'task.html'

    def __init__(self, *args, **kwargs):
        # TODO: don't get task for each creation
        self.task = self._get_task()
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

    def get_form_class(self):
        try:
            return self.task.task_form
        except AttributeError:
            # TODO: check if template exists, if not raise exception
            return DummyForm

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

    def get_random_mocked_task(self):
        # Make sure that tasks are imported before this code is run, ie. in your project urls.py
        defined_tasks = [
            klass.__module__ + '.' + klass.__qualname__ for klass in globals()['AbstractTask'].__subclasses__()
        ]
        task_type = random.choice(defined_tasks)

        # TODO allow task implementers to override mocked task creation

        return {
            'info': {
                "url": "http://sccg.sk/~cernekova/Benesova_Digital%20Image%20Processing%20Lecture%20Objects%20tracking%20&%20motion%20detection.pdf",
                "type": task_type,
            }
        }

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
