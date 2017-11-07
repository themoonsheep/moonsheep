import json
import importlib
import random
import urllib.request

from django.conf import settings
from django.views.generic import TemplateView

from .exceptions import PresenterNotDefined


class TaskView(TemplateView):
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
        task = self._get_task()
        context.update({
            'task': task,
            'presenter': self.get_presenter(task.url)
        })
        return context

    def _get_task(self):
        """
        Mechanism responsible for getting tasks. Points to PyBossa API and collects task.
        Task structure contains type, url and metadata that might be displayed in template.

        :rtype: AbstractTask
        :return: user's implementation of AbstractTask object
        """
        if settings.MOONSHEEP_TASK_SOURCE == 'random':
            task = self.get_random_mocked_task()
        elif settings.MOONSHEEP_TASK_SOURCE == 'pybossa':
            task = self.get_pybossa_task()
        else:
            task = self.get_random_mocked_task()
        parts = task['type'].split('.')
        url = task['url']
        module_path, class_name = importlib.import_module('.'.join(parts[:-1])), parts[-1]
        del task['type'], task['url']
        return getattr(module_path, class_name)(url, **task)

    def get_random_mocked_task(self):
        tasks = [
            {
                "url": "https://epf.org.pl/pl/wp-content/themes/epf/images/logo-epanstwo.png",
                "party": "",
                "type": "opora.tasks.FindTableTask",
                "page": "",
                "record_id": ""
            },
            {
                "url": "https://epf.org.pl/pl/wp-content/themes/epf/images/logo-epanstwo.png",
                "party": "1",
                "type": "opora.tasks.GetTransactionIdsTask",
                "page": "1",
                "record_id": ""
            },
            {
                "url": "https://epf.org.pl/pl/wp-content/themes/epf/images/logo-epanstwo.png",
                "party": "1",
                "type": "opora.tasks.GetTransactionTask",
                "page": "1",
                "record_id": "1"
            }
        ]
        return random.choice(tasks)

    def get_pybossa_task(self):
        """
        Method for obtaining task structure from distant source, i.e. PyBossa

        :rtype: dict
        :return: task structure
        """
        url = settings.PYBOSSA_URL + "/api/project/" + str(settings.PYBOSSA_PROJECT_ID) + "/newtask"
        r = urllib.request.urlopen(url)
        result = json.loads(r.read().decode(r.info().get_param('charset') or 'utf-8'))
        return result['info']

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
        return 1
