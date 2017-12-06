import collections
import importlib
import inspect
import pbclient

from .verifiers import EqualsVerifier


class AbstractTask(object):
    MIN_CONFIDENCE = 0.5
    N_ANSWERS = 1

    def __init__(self, url, **kwargs):
        self.url = url
        self.kwargs = kwargs
        # TODO: if type == "pybossa_task"
        self.project_id = kwargs.get('project_id')
        self.id = kwargs.get('id')
        self.verified = False

    def get_presenter(self):
        """
        Choosing how to render document to transcribe.

        The default behaviour is to check:
        1. Known url templates for YouTube, Vimeo, etc.
        2. Url file extension

        :return: {
            'template': 'presenters/pdf.html',
            'url': url,
            'other_presenter_option': 'width: 110px'
        }
        """

        return {
            'template': 'presenters/pdf.html',
            'url': self.url
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
        confidence, crosschecked = self.cross_check(taskruns_list)
        self.verified = confidence > self.MIN_CONFIDENCE
        if self.verified:
            # save verified data
            self.save_verified_data(crosschecked)
            # create new tasks
            print(crosschecked)
            self.after_save(crosschecked)
            # pbclient.delete_task(self.id)
            return True
        else:
            # TODO: do something here
            return False

    def cross_check(self, taskruns_list):
        # TODO: to implement verify_data let's copy how django forms do it: django.forms.forms.BaseForm#full_clean
        """
        Verification method for all form fields in regard to answers of other users' (other taskruns).
        It iterates through all taskrun fields and invokes verify_field of AbstractTask.
        If no verify_field method or verifier then calls EqualsVerifier.

        :param taskruns_list: list containing taskrun dictionaries
        :type taskruns_list: list
        :return: dictionary containing tuples of verified fields
        """
        taskruns_dict = collections.defaultdict(list)
        results_dict = {}
        confidences_list = []

        for d in taskruns_list:
            for k, v in d.items():
                taskruns_dict[k].append(v)

        for k, v in taskruns_dict.items():
            verifier = getattr(self, "verify_" + k, EqualsVerifier)
            value, confidence = verifier()(v) if inspect.isclass(verifier) else verifier(v)
            results_dict[k] = value
            confidences_list.append(confidence)

        overall_confidence = self.calculate_confidence(confidences_list)
        return overall_confidence, results_dict

    def calculate_confidence(self, confidences):
        return self.min_input_confidence(confidences)

    def min_input_confidence(self, values_list):
        return min(values_list)

    def max_input_confidence(self, values_list):
        return max(values_list)

    def save_verified_data(self, verified_data):
        """
        To implement in derived classes
        :param verified_data:
        :return:
        """
        raise NotImplementedError

    def after_save(self, verified_data):
        """
        This method is invoked right after save_verified_data.
        If user wants to do some actions afterwards, i.e. create new task, it should be done in
        method after_save in derived class.
        :type verified_data: dict
        :param verified_data: dictionary containing verified and saved fields from form
        """
        raise NotImplementedError

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
    def create_task_instance(task_type, **kwargs):
        """
        Create relevant task instance.

        :param task_type: full reference to task class, ie. 'app.task.MyTaskClass'
        :param kwargs: task parameters
        :return: Task object
        """

        parts = task_type.split('.')

        module_name, class_name = '.'.join(parts[:-1]), parts[-1]
        try:
            module_path = importlib.import_module(module_name)
            klass = getattr(module_path, class_name)
        except (ImportError, AttributeError) as e:
            raise Exception("Couldn't import task {}".format(task_type)) from e

        return klass(kwargs['info']['url'], **kwargs)

    @staticmethod
    def verify_task(project_id, task_id):
        task_data = pbclient.get_task(project_id=project_id, task_id=task_id)
        task = AbstractTask.create_task_instance(task_data[0]['info']['type'], **task_data[0])

        taskruns = pbclient.find_taskruns(project_id=project_id, task_id=task_id)
        taskruns_list = [taskrun.data['info'] for taskrun in taskruns]

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
