import logging
import math
from typing import List, Type

from django.db import transaction
from django.utils.decorators import classproperty

from moonsheep import statistics
from moonsheep.json_field import JSONField
from moonsheep.models import Task, Entry
from moonsheep.settings import MOONSHEEP
from .mapper import klass_from_name
from .verifiers import MIN_CONFIDENCE, DEFAULT_DICT_VERIFIER
from . import registry

logger = logging.getLogger(__name__)


# TODO rename to TaskType? add ABC class?
class AbstractTask(object):
    params: JSONField
    instance: Task

    def __init__(self, instance: Task):
        self.instance = instance
        self.id = instance.id  # TODO attr rather than field
        self.params = instance.params  # TODO attr rather than field

        # per-instance overrides
        if 'task_form' in self.params:
            self.task_form = klass_from_name(self.params.get('task_form'))
        if 'template_name' in self.params:
            self.template_name = self.params.get('template_name')

    @classproperty
    def name(cls):
        return cls.__module__ + '.' + cls.__name__

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
        url = self.instance.params['url']
        return {
            'template': 'presenters/pdf.html',
            'url': url
        }

    def verify_and_save(self, task_id: int) -> bool:
        """
        Called after a new entry was created. It crosschecks users' answers (entries) and if they match data is saved to structured db.

        Entries are considered cross-checked if confidence returned from the checking algorithm is greater than MIN_CONFIDENCE.
        TODO otherwise...I don't know yet (will be invoked again or called "dirty data" - to be checked by moderator)

        Progress of a task (and its parents) is being updated here.

        :param task_id: Identifier of the task
        :return: True if cross-verified otherwise False
        """

        verified = False

        # Do the crosscheck if we have enough entries
        # TODO is task_id needed? we have self.instance.id
        entries = Entry.objects.filter(task_id=task_id)
        entries_count = entries.count()

        if entries_count >= MOONSHEEP['MIN_ENTRIES_TO_CROSSCHECK']:
            # So far we only take real data into account but in the future Verifiers might want also to look at users' "trustworthiness"
            crosschecked, confidence = self.cross_check(list([entry.data for entry in entries]))
            # TODO record somewhere on how many entries the crosscheck was done, update values if new crosscheck comes with higher rank?

            verified = confidence >= MIN_CONFIDENCE  # TODO MIN_CONFIDENCE configurable
            if verified:
                # save verified data
                with transaction.atomic():
                    self.save_verified_data(crosschecked)

                    # create new tasks
                    self.after_save(crosschecked)

                # update progress & state
                self.instance.own_progress = 100
                self.instance.state = Task.CROSSCHECKED

                statistics.update_total_progress(self.instance)

            elif entries_count >= MOONSHEEP['MIN_ENTRIES_TO_MARK_DIRTY']:
                self.instance.state = Task.DIRTY

        # Entry was added so we should update progress if it's not at 100 already
        if self.instance.own_progress != 100:
            self.instance.own_progress = 95 * (
                    1 - math.exp(-2 / MOONSHEEP['MIN_ENTRIES_TO_CROSSCHECK'] * entries_count))

            statistics.update_total_progress(self.instance)

        # Task's state might have changed also, so save that data
        self.instance.save()

        return verified

    def verified_manually(self, task_id: int, entry: Entry):
        """
        Mark task as checked by moderator and save the data
        :param task_id:
        :param entry:
        :return:
        """

        # save verified data
        with transaction.atomic():
            self.save_verified_data(entry.data)

            # create new tasks
            self.after_save(entry.data)

        # update progress & state
        self.instance.own_progress = 100
        self.instance.state = Task.CLOSED_MANUALLY

        statistics.update_total_progress(self.instance)


    def cross_check(self, entries: List[dict]) -> (dict, float):
        """
        Cross check all entries recursively
        :param entries: Entries data for a given task
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
            "Task {}.{} should define save_verified_data method".format(self.__class__.name)
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

    @classmethod
    def create(cls, **properties) -> Task:
        """
        Helper method for creating a new task of given type.

        :param params: Params to initialize the task
        :param parent: Parent task
        :return: created task
        """
        properties.update({
            'type': cls.name,
            'doc_id': properties['parent'].doc_id if 'parent' in properties else None
        })

        return Task.objects.create(**properties)

    # TODO change convention
    @staticmethod
    def create_task_instance(task: Task) -> 'AbstractTask':
        """
        Create relevant task instance.

        :param task: task description from the DB
        :return: Task object
        """

        klass = klass_from_name(task.type)
        return klass(task)

    def average_subtasks_count(self):
        raise NotImplementedError(f"{self.__class__.name} should implement average_subtasks_count()")

    def __repr__(self):
        return "<{} id={} params={}".format(self.__class__.name, self.id, self.params)


def register_task():
    """
    Decorator to register a given task class

    @register_task()
    class TransactionTask(AbstractTask):

    """

    def _task_wrapper(task_class):
        if not task_class:
            raise ValueError('Task Class must be passed to register.')

        registry.register(task_class)

        return task_class

    return _task_wrapper
