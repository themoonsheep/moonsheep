import urllib.request

from django.views.generic.edit import FormView

from .exceptions import PresenterNotDefined


class AbstractTask(FormView):
    # task_group
    # PyBossa API
    #: Project.ID that this task is associated with.
    # project_id = Column(Integer, ForeignKey('project.id', ondelete='CASCADE'), nullable=False)

    # quorum = Column(Integer, default=0)

    #: If the task is a calibration task
    # calibration = Column(Integer, default=0)

    #: Priority of the task from 0.0 to 1.0
    # priority_0 = Column(Float, default=0)

    #: Task.info field in JSON with the data for the task.
    # info = Column(JSON)

    #: Number of answers to collect for this task.
    # n_answers = Column(Integer, default=30)

    # level -> digitization stage (task level)
    task_data = None

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
        context = super(AbstractTask, self).get_context_data(**kwargs)
        context['form'] = self._get_task()
        context['presenter'] = self.get_presenter(self.task_data)
        return context

    def _get_task(self):
        """
        Mechanism of getting tasks. Points to PyBossa API and collects task.
        Task structure contains type, url and metadata that might be displayed in template.

        OPORA task responses:
        [
            {
                'type': 'find_pages',
                'url': ''
            },
            {
                'type': 'get_transaction_ids',
                'url': '',
                'page': '10',
                'party': '1 (Party)'
            },
            {
                'type': 'get_transaction',
                'url': '',
                'page': '10',
                'party': '1 (Party)',
                'record_id': '1'
            }
        ]
        :return: task structure
        """
        # TODO: undummy
        task_url = 'pybossa/url'
        with urllib.request.urlopen(task_url) as response:
            return response

    def get_presenter(self, task_data):
        """
        Returns presenter based on task data. Default presenter depends on the url MIME Type
        :return:
        """

        # TODO: opening file to check mymetipe isn't very efficient...
        with urllib.request.urlopen(task_data['url']) as response:
            info = response.info()
            print(info.get_content_type())  # -> text/html
            print(info.get_content_maintype())  # -> text
            print(info.get_content_subtype())  # -> html

        # try:
        #     return "presenters.{0}".format(mimetype)
        # except:  # DoesNotExist:
        #     raise PresenterNotDefined

    # TODO think how to serve this data
    def save_verified_data(self, outcome, confidence, verified_data):
        """

        :param outcome: yes/partly
        :param confidence: tolerance
        :param verified_data:
        :return:
        """
        raise NotImplementedError()

    # TODO to implement verify_data let's copy how django forms do it: django.forms.forms.BaseForm#full_clean


# # Flow 2. Serve form for a given task  (to implement in Moonsheep Controller)
# task_type = 'find_table'
# task = FindTableTask()
# task.get_form() ->
# task.get_presenter(pybossa.task_data)
#
# # Flow 4. Verify task runs of a given task
# # input
# task_type = 'find_table'
# task_runs = []
# # logic
# task = FindTableTask()
# task.full_verify(task_runs) # it generates cl.verified_data or throws some errors
#     try:
#         verified_data = self.verify() # if it's overriden
#
# task.verified_data # aka self.cleaned_data = {}
# task.save_verified_data() # saves to the model


### MOONSHEEP ABOVE
### OPORA BELOW
