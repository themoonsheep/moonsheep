from decimal import Decimal

import psycopg2
from django.db import connections
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


def stats_documents_verified():
    """
    Shows stats regarding fully verified documents

    :return: dict
    - verified
    - verified_percent
    - total
    - total_progress
    - remaining
    """
    # TODO cache it

    table_name = MOONSHEEP['DOCUMENT_MODEL'].objects.model._meta.db_table

    with connections['default'].connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
        cursor.execute(f"""SELECT 
            COUNT(CASE WHEN progress = 100 THEN 1 END) AS "verified", 
            COUNT("id") AS "total", 
            AVG("progress") AS "total_progress" 
        FROM {table_name}
        """)
        docs = cursor.fetchone()

    docs['verified_percents'] = Decimal(docs['verified']) / docs['total']
    docs['remaining'] = int(docs['total'] - docs['verified'])

    return docs


def stats_users():
    """
    Show user stats

    :return: dict
    - registered
    - participated (at least one entry)
    - entries_total - number of all entries sent
    - active TODO #140
    """
    # TODO cache it

    with connections['default'].connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
        cursor.execute("""
select
	count(id) as registered,
	count(id) FILTER(where entries_count > 0) as participated,
	sum(entries_count) as entries_total
	from (
	select
		u.id as id,
		count(e.id) as "entries_count"
		-- max(e.timestamp)
	from
		"moonsheep_user" u
	left join "moonsheep_entry" e on
		e.user_id = u.id
	where
		u.is_staff = false
	group by u.id) u
""")

        users = cursor.fetchone()

    return users

# TODO
# def stats_users_leaderboards():
#     """
#     Show user leaderboards:
#     - by max entries
#     - by accuracy
#     """
