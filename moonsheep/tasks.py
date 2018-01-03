import importlib
import pbclient

from .verifiers import MIN_CONFIDENCE, DEFAULT_DICT_VERIFIER


class AbstractTask(object):
    N_ANSWERS = 1

    def __init__(self, **kwargs):
        info = kwargs.get('info')
        self.url = None
        self.data = None

        self.task_form = None
        self.task_form_template = None

        self.project_id = kwargs.get('project_id')
        self.id = kwargs.get('id')
        self.verified = False
        if info:
            self.url = info.get('url')
            self.data = info.get('info')

            # to override templates
            if 'task_form' in info:
                self.task_form = AbstractTask.klass_from_name(info.get('task_form'))
            if 'task_form_template' in info:
                self.task_form_template = info.get('task_form_template')
            # if type == "pybossa_task"

    def get_presenter(self):
        """
        Choosing how to render document to transcribe.

        The default behaviour is to check:
        1. Known url templates for YouTube, Vimeo, etc.
        2. Url file extension

        :return: {
            'template': 'presenters/fancy.html',
            'url': url,
            'other_presenter_option': 'width: 110px'
        }
        """
        # ^(https?\:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$
        # http://(www\.)?vimeo\.com/(\d+)
        url = getattr(self, 'url')
        return {
            'template': 'presenters/pdf.html',
            'url': url
        }

    def verify_and_save(self, taskruns_list):
        """
        This method is called by webhook with required amount of taskruns per task.
        It crosschecks users' answers (the taskruns) and if they match -
        their confidence is greater than MIN_CONFIDENCE, then data is verified and can be saved to database
        otherwise... I don't know yet (will be invoked again or called "dirty data" - to be checked by moderator)
        :type taskruns_list: list
        :param taskruns_list: list containing taskrun dictionaries
        :rtype: bool
        :return: True if verified otherwise False
        """
        crosschecked, confidence = self.cross_check(taskruns_list)
        self.verified = confidence >= MIN_CONFIDENCE
        if self.verified:
            # save verified data
            self.save_verified_data(crosschecked)
            # create new tasks
            self.after_save(crosschecked)
            # pbclient.delete_task(self.id)
            return True
        else:
            # TODO: do something here
            return False

    def cross_check(self, entries: list) -> (dict, float):
        """
        Cross check all entries recursively
        :param entries: Entries for a given task
        :return (dict, float): (results, confidence)
        """

        verifier = DEFAULT_DICT_VERIFIER(self, '')
        return verifier(entries)

    def save_verified_data(self, verified_data: dict):
        """
        To implement in derived classes
        :param verified_data:
        :return:
        """
        raise NotImplementedError("Task {}.{} should define save_verified_data method"
                                  .format(self.__class__.__module__, self.__class__.__name__))

    def after_save(self, verified_data):
        """
        This method is invoked right after save_verified_data.
        If user wants to do some actions afterwards, i.e. create new task, it should be done in
        method after_save in derived class.
        :type verified_data: dict
        :param verified_data: dictionary containing verified and saved fields from form
        """
        pass

    def create_new_task(self, task, info):
        """
        Helper method for creating new task.
        It has proposed structure
        :param task:
        :param info:
        :return: created task
        """
        # TODO: 'type' is now reserved key in task params
        # TODO: maybe we should reserve '_type' ?
        info['type'] = ".".join([task.__module__, task.__name__])
        return pbclient.create_task(self.project_id, info, self.N_ANSWERS)

    @staticmethod
    def klass_from_name(name):
        parts = name.split('.')
        module_name, class_name = '.'.join(parts[:-1]), parts[-1]
        try:
            module_path = importlib.import_module(module_name)
            klass = getattr(module_path, class_name)
        except (ImportError, AttributeError) as e:
            raise Exception("Couldn't import class {}".format(name)) from e
        return klass

    @staticmethod
    def create_task_instance(task_type, **kwargs):
        """
        Create relevant task instance.

        :param task_type: full reference to task class, ie. 'app.task.MyTaskClass'
        :param kwargs: task parameters
        :return: Task object
        """

        klass = AbstractTask.klass_from_name(task_type)
        return klass(**kwargs)

    @staticmethod
    def verify_task(project_id, task_id):
        task_data = pbclient.get_task(project_id=project_id, task_id=task_id)

        taskruns = pbclient.find_taskruns(project_id=project_id, task_id=task_id)
        taskruns_list = [taskrun.data['info'] for taskrun in taskruns]

        task = AbstractTask.create_task_instance(task_data[0]['info']['type'], **task_data[0])
        task.verify_and_save(taskruns_list)

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
