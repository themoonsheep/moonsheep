import logging
import pbclient

from .models import klass_from_name, name_from_klass
from .verifiers import MIN_CONFIDENCE, DEFAULT_DICT_VERIFIER
from .settings import (
    TASK_SOURCE, RANDOM_SOURCE, REDUNDANCY
)

logger = logging.getLogger(__name__)


class AbstractTask(object):
    N_ANSWERS = REDUNDANCY
    verbose_name = None
    url = None
    data = {}

    def __init__(self, **kwargs):
        info = kwargs.get('info')

        self.project_id = kwargs.get('project_id')
        self.id = kwargs.get('id')
        self.verified = False
        if info:
            self.url = info.get('url')
            self.data = info.get('info', {})

            # to override templates
            if 'task_form' in info:
                self.task_form = klass_from_name(info.get('task_form'))
            if 'template_name' in info:
                self.template_name = info.get('template_name')
            # if type == "pybossa_task"

    def __str__(self):
        return self.full_klass_name()

    @classmethod
    def full_klass_name(cls):
        return name_from_klass(cls)

    def display(self):
        return self.verbose_name if self.verbose_name else self.full_klass_name()

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
        raise NotImplementedError(
            "Task {}.{} should define save_verified_data method".format(
                self.__class__.__module__,
                self.__class__.__name__
            )
        )

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
        info.update({
            'type': task.__name__(),
            'parent_task': self.__name__()
        })

        if TASK_SOURCE == RANDOM_SOURCE:
            logger.info("Skipping task creation because TASK_SOURCE is set to random: " + repr(info))
        else:
            return pbclient.create_task(self.project_id, info, self.N_ANSWERS)

    @staticmethod
    def create_task_instance(task_type, **kwargs):
        """
        Create relevant task instance.

        :param task_type: full reference to task class, ie. 'app.task.MyTaskClass'
        :param kwargs: task parameters
        :return: Task object
        """

        klass = klass_from_name(task_type)
        return klass(**kwargs)

    @staticmethod
    def verify_task(project_id, task_id):
        task_data = pbclient.get_task(project_id=project_id, task_id=task_id)

        taskruns = pbclient.find_taskruns(project_id=project_id, task_id=task_id)
        taskruns_list = [taskrun.data['info'] for taskrun in taskruns]

        task = AbstractTask.create_task_instance(task_data[0]['info']['type'], **task_data[0])
        task.verify_and_save(taskruns_list)
