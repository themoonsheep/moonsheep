import json
import importlib
import random
import urllib.request, urllib.parse

from django.http import HttpResponse
from django.views import View
from django.views.generic import FormView

from .exceptions import PresenterNotDefined, TaskSourceNotDefined
from .forms import DummyForm
from .moonsheep_settings import (
    RANDOM_SOURCE, PYBOSSA_SOURCE, TASK_SOURCE,
    PYBOSSA_NEW_TASK_URL, PYBOSSA_TASK_RUN_URL
)


class TaskView(FormView):
    template_name = 'task.html'

    def __init__(self, *args, **kwargs):
        # TODO: don't get task for each creation
        self.task = self._get_task()
        self.presenter = self.get_presenter(self.task.url)
        super(TaskView, self).__init__(*args, **kwargs)

    # TODO: update docstring
    def get_context_data(self, **kwargs):
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
            'presenter': self.presenter,
            'task': self.task,
        })
        return context

    def get_form_class(self):
        try:
            return self._get_task().task_form
        except AttributeError:
            # TODO: check if template exists, if not raise exception
            return DummyForm


    def form_valid(self, form):
        # TODO: send data to pybosssa here
        self._send_task(form)
        return super(TaskView, self).form_valid(form)

    def form_invalid(self, form):
        print('invalid form')
        print(form)
        return super(TaskView, self).form_valid(form)

    def get_presenter(self, url):
        """
        Returns presenter based on task data. Default presenter depends on the url MIME Type
        :return:
        """

        # TODO: opening file in order to check mimetype isn't very efficient...
        # with urllib.request.urlopen(url) as response:
        #     info = response.info()
        #     print(info.get_content_type())  # -> text/html
        #     print(info.get_content_maintype())  # -> text
        #     print(info.get_content_subtype())  # -> html

        # try:
        #     return "presenters.{0}".format(mimetype)
        # except:  # DoesNotExist:
        #     raise PresenterNotDefined
        return {
            'template': 'presenters/pdf_presenter.html',
            'url': url
        }

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
            raise TaskSourceNotDefined()

        # task['type'] -> 'app.task.MyTaskClass'
        parts = task['info']['type'].split('.')
        # task url is presenter http source
        module_path, class_name = importlib.import_module('.'.join(parts[:-1])), parts[-1]
        return getattr(module_path, class_name)(task['info']['url'], **task)

    def get_random_mocked_task(self):
        tasks = [
            {
                'info': {
                    "url": "http://sccg.sk/~cernekova/Benesova_Digital%20Image%20Processing%20Lecture%20Objects%20tracking%20&%20motion%20detection.pdf",
                    "party": "",
                    "type": "opora.tasks.FindTableTask",
                    "page": "",
                    "record_id": ""
                }
            },
            {
                'info': {
                    "url": "http://www.cs.stanford.edu/~amirz/index_files/PED12_v2.pdf",
                    "party": "1",
                    "type": "opora.tasks.GetTransactionIdsTask",
                    "page": "1",
                    "record_id": ""
                }
            },
            {
                'info': {
                    "url": "https://epf.org.pl/pl/wp-content/themes/epf/images/logo-epanstwo.png",
                    "party": "1",
                    "type": "opora.tasks.GetTransactionTask",
                    "page": "1",
                    "record_id": "1"
                }
            }
        ]
        return random.choice(tasks)

    def get_pybossa_task(self):
        """
        Method for obtaining task structure from distant source, i.e. PyBossa

        :rtype: dict
        :return: task structure
        """
        url = PYBOSSA_NEW_TASK_URL
        r = urllib.request.urlopen(url)
        return json.loads(r.read().decode(r.info().get_param('charset') or 'utf-8'))

    def _send_task(self, form):
        """
        Mechanism responsible for sending tasks. Points to PyBossa API taskrun and sends data from form.
        """
        if TASK_SOURCE == PYBOSSA_SOURCE:
            return self.send_pybossa_task(form)
        else:
            raise TaskSourceNotDefined()

    def send_pybossa_task(self, form):
        post_data = [
            ('task_id', self.task.id),
            ('project_id', self.task.project_id),
            ('info', form.cleaned_data)
        ]
        url = PYBOSSA_TASK_RUN_URL
        data = urllib.parse.urlencode(json.dumps(post_data)).encode("utf-8")
        req = urllib.request.Request(url, data=data)
        # req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req) as f:
            resp = f.read()


class WebhookTaskRunView(View):
    def get(self, request):
        # empty response so pybossa can set webhook to this endpoint
        return HttpResponse()

    def post(self, request):
        # give a response for request:
        # {
        #   'fired_at':,
        #   'project_short_name': 'project-slug',
        #   'project_id': 1,
        #   'task_id': 1,
        #   'result_id': 1,
        #   'event': 'task_completed'
        # }
        print(request)
