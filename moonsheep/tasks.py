import collections
import inspect
import pbclient

from moonsheep.verifiers import EqualsVerifier


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

    def verify_and_save(self, taskruns_list):
        confidence, crosschecked = self.cross_check(taskruns_list)
        self.verified = confidence > self.MIN_CONFIDENCE
        if self.verified:
            # save verified data
            self.save_verified_data(crosschecked)
            # create new tasks
            self.after_save(crosschecked)
            # pbclient.delete_task(self.id)
        else:
            raise NotImplementedError

    # TODO to implement verify_data let's copy how django forms do it: django.forms.forms.BaseForm#full_clean
    def cross_check(self, taskruns_list):
        """
        Iterates through all taskrun fields and invokes verify_field of AbstractTask.
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
        To implement in derived classes if needed
        :return:
        """
        pass

    def create_new_task(self, task, **info):
        info['task'] = ".".join([task.__module__, task.__name__])
        pbclient.create_task(self.project_id, info, self.N_ANSWERS)


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
