from decimal import Decimal

from django.db.models import F, Avg, Count

from moonsheep import models
from moonsheep.models import Task
from moonsheep.settings import MOONSHEEP


def update_total_progress(task: models.Task):
    """
    Update total progress of given task and all of its parents

    # TODO in the future this should be run effectively by some backend job regularly #138
    :param task:
    :return:
    """
    from moonsheep.tasks import AbstractTask

    while True:
        # Update total progress of given task
        # total_progress = ( average(subtasks progress) * average_number_of_subtasks(configured in task) + own_progress)
        #                   / (average_number_of_subtasks(configured in task) + 1)

        if task.own_progress < 100:
            # it has not subtasks yet, guess its number
            average_number_of_subtasks = AbstractTask.create_task_instance(task).average_subtasks_count()
            task.total_progress = task.own_progress / (average_number_of_subtasks + 1)
        else:
            # own_progress == 100, so there might be subtasks
            subtasks = Task.objects.filter(parent=task) \
                .aggregate(average_progress=Avg('total_progress'), count=Count('id'))

            task.total_progress = Decimal(
                subtasks['average_progress'] * subtasks['count'] + 100) / (
                                          subtasks['count'] + 1)
        task.save()

        # Update total progress of all of its parents
        if task.parent_id:
            task = task.parent
        else:
            break

    # now it must be a doc-descendant task, so compute progress of a document
    # Progress of a document is an average total progress of all of tasks created on such document.
    doc_progress = Task.objects.filter(doc_id=task.doc_id, parent=None) \
        .aggregate(Avg('total_progress'))['total_progress__avg']

    Document = MOONSHEEP['DOCUMENT_MODEL']
    Document.objects.filter(id=task.doc_id).update(progress=doc_progress)
