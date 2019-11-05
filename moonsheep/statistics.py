from moonsheep import models


def update_parents_progress(task: models.Task):
    if task.parent_id:
        pass
        # TODO update parent total progress #138
        # ( average(subtasks progress) * average_number_of_subtasks(configured in task) + own_progress ) / (average_number_of_subtasks(configured in task) + 1)
        # own_progress of parent == 1
    else:
        # it must be a doc-descendant task
        # TODO update doc progress  #138
        pass
