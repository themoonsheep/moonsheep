class AbstractTask(object):
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

    def __init__(self, url, **kwargs):
        self.url = url
        self.kwargs = kwargs

    # TODO to implement verify_data let's copy how django forms do it: django.forms.forms.BaseForm#full_clean
    def verify_data(self):
        raise NotImplementedError()

    # TODO think how to serve this data
    def save_verified_data(self, outcome, confidence, verified_data):
        """

        :param outcome: yes/partly
        :param confidence: tolerance
        :param verified_data:
        :return:
        """
        raise NotImplementedError()


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
