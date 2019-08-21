from random import random

import dpath.util
import json
import re

from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.http.request import QueryDict
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView, TemplateView

from moonsheep.mapper import klass_from_name
from .exceptions import (
    PresenterNotDefined, NoTasksLeft, TaskMustSetTemplate)
from .forms import NewTaskForm
from . import registry
from .settings import MOONSHEEP
from .tasks import AbstractTask
from .models import Task, Entry


class TaskView(FormView):
    task_type = None
    form_class = None
    error_message = None
    error_template = None

    def get(self, request, *args, **kwargs):
        """
        Returns form for this task

        Algorithm:
        1. Get actual (implementing) class name, ie. FindTableTask
        2. Derive template name for it and try to return if exists 'forms/find_table.html'
        3. Otherwise return `forms/FindTableForm`
        4. Otherwise return error suggesting to implement 2 or 3
        :return: path to the template (string) or Django's Form class
        """
        try:
            self.task_type = self._get_new_task()
            self.configure_template_and_form()
        except NoTasksLeft:
            self.error_message = 'Task Chooser returned no tasks'
            self.error_template = 'error-messages/no-tasks.html'
            self.task_type = None
            self.template_name = 'views/message.html'
        except PresenterNotDefined:
            self.error_message = 'Presenter not defined'
            self.error_template = 'error-messages/presenter-not-defined.html'
            self.task_type = None
            self.template_name = 'views/message.html'

        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate a form instance with the passed
        POST variables and then check if it's valid.

        Overrides django.views.generic.edit.ProcessFormView to adapt for a case
        when user hasn't defined form for a given task.
        """
        if '_task_id' not in request.POST:
            raise KeyError('Missing _task_id field. Include moonsheep_token template tag!')

        if '_task_type' not in request.POST:
            return KeyError('Missing _task_type field. Include moonsheep_token template tag!')

        # TODO keep task_id separate
        self.task_type = self._get_task(request.POST['_task_id'])
        self.configure_template_and_form()

        form = self.get_form()

        # no form defined in the task, no field validation then, but we continue
        if form is None:
            data = unpack_post(request.POST)
            # TODO what to do if we have forms defined? is Django nested formset a way to go?
            # Check https://stackoverflow.com/questions/20894629/django-nested-inline-formsets
            # Check https://docs.djangoproject.com/en/2.0/ref/contrib/admin/#django.contrib.admin.InlineModelAdmin
            self._save_entry(data)
            return HttpResponseRedirect(self.get_success_url())

        # there is a task's form defined, validate fields with it
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super(TaskView, self).get_context_data(**kwargs)
        context.update({
            'project_id': 'fake it'  # TODO remove it everywhere
        })
        if self.task_type:
            context['task'] = self.task_type
            try:
                context['presenter'] = self.task_type.get_presenter()
            except TypeError:
                raise PresenterNotDefined
        else:
            context.update({
                'error': True,
                'message': self.error_message,
                'template': self.error_template
            })
        return context

    def configure_template_and_form(self):
        # TODO maybe merge with _get_task (but check if it work for tests)
        # Template showing a task: presenter and the form, can be overridden by setting task_template in your Task
        # By default it uses moonsheep/templates/task.html

        # Overriding template
        if hasattr(self.task_type, 'template_name'):
            self.template_name = self.task_type.template_name

        if not self.template_name:
            raise TaskMustSetTemplate(self.task_type.__class__)

        self.form_class = getattr(self.task_type, 'task_form', None)

    # =====================
    # Override FormView to adapt for a case when user hasn't defined form for a given task
    # and to process form in our own manner

    def get_form_class(self):
        return self.task_type.task_form if hasattr(self.task_type, 'task_form') else None

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view.

        Overrides django.views.generic.edit.FormMixin to adapt for a case
        when user hasn't defined form for a given task.
        """
        if form_class is None:
            form_class = self.get_form_class()

        if form_class is None:
            return None
        return form_class(**self.get_form_kwargs())

    def form_valid(self, form):
        if MOONSHEEP['DEV_ROTATE_TASKS']:
            # Test saving data: let's assume that this entry is all we need for crosscheck
            self.task_type.save_verified_data(form.cleaned_data)
            # create new tasks
            self.task_type.after_save(form.cleaned_data)

        else:
            self._save_entry(self.request.POST['_task_id'], form.cleaned_data)

        return super(TaskView, self).form_valid(form)

    # End of FormView override
    # ========================

    def _get_task(self, task_id) -> AbstractTask:
        if MOONSHEEP['DEV_ROTATE_TASKS']:
            return self.get_random_mocked_task_data(task_id)

        else:
            task = Task.objects.get(task_id)
            return AbstractTask.create_task_instance(task)

    def _get_new_task(self) -> AbstractTask:
        """
        Mechanism responsible for getting tasks to execute.

        :rtype: AbstractTask
        :return: user's implementation of AbstractTask object
        """
        if MOONSHEEP['DEV_ROTATE_TASKS']:
            return self.get_random_mocked_task_data()

        else:
            return AbstractTask.create_task_instance(self.choose_a_task())

    __mocked_task_counter = 0

    # TODO rename after choosing a convention
    def get_random_mocked_task_data(self, task_type: str = None) -> AbstractTask:
        # Make sure that tasks are imported before this code is run, ie. in your project urls.py

        # Allow to test one type definition, by passing it as GET parameter
        # TODO document it
        if task_type is None:
            task_type = self.request.GET.get('task_type', None)

        if task_type is None:
            defined_tasks = registry.TASK_TYPES

            if not defined_tasks:
                raise NotImplementedError(
                    "You haven't defined any tasks or forgot to add in urls.py folllowing line: from .tasks import *"
                    + "# Keep it to make Moonsheep aware of defined tasks")

            # Rotate tasks one after another
            TaskView.__mocked_task_counter += 1
            if TaskView.__mocked_task_counter >= len(defined_tasks):
                TaskView.__mocked_task_counter = 0
            task_type = defined_tasks[TaskView.__mocked_task_counter]

        task_class = klass_from_name(task_type)

        # Developers should provide mocked params for the task
        has_mocked_params = True
        try:
            if not hasattr(task_class, 'mocked_params'):
                has_mocked_params = False
        except TypeError as e:
            has_mocked_params = False

        if not has_mocked_params:
            raise NotImplementedError(
                "Task {} should define '@classproperty def mocked_params(cls) -> dict:'".format(task_type))


        task = AbstractTask.create_task_instance(Task(type=task_type, id=task_type, params=task_class.mocked_params))

        return task

    def choose_a_task(self) -> Task:
        """
        Choose a task to be served to user
        """
        # TODO make it pluggable / create interface for it
        tasks = Task.objects.filter(state=Task.OPEN).order_by('-priority')[:20]

        if not tasks:
            raise NoTasksLeft()

        # choose task at random, so everyone won't get the same task
        # TODO otherwise an "open_count" could help to limit it,
        #  especially where there are a lot of volunteers and long tasks
        return tasks[random.choice()]

    def _save_entry(self, task_id, data) -> None:
        """
        Save entry in the database
        """
        # TODO in #130
        user = None

        Entry(task_id=task_id, user=user, data=data).save()
        # TODO record that a Entry was saved, when crosscheck should happen?

    def _get_user_ip(self):
        return self.request.META.get(
            'HTTP_X_FORWARDED_FOR', self.request.META.get('REMOTE_ADDR')
        ).split(',')[-1].strip()


class AdminView(TemplateView):
    template_name = 'views/admin.html'


class NewTaskFormView(FormView):
    template_name = 'views/new-task.html'
    form_class = NewTaskForm

    def get_success_url(self):
        return reverse('ms-new-task') # TODO namespace not needed in app, right? remove ms-

    def form_valid(self, form):
        form.cleaned_data.get('url'),
        # TODO implement importing documents

        return super(NewTaskFormView, self).form_valid(form)


class TaskListView(TemplateView):
    template_name = 'views/stats.html'

    def get_context_data(self, **kwargs):
        context = super(TaskListView, self).get_context_data(**kwargs)
        context['tasks'] = registry.TASK_TYPES
        return context


class ManualVerificationView(TemplateView):
    template_name = 'views/manual-verification.html'


class WebhookTaskRunView(View):
    # TODO remove it
    # TODO: instead of csrf exempt, IP white list
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(WebhookTaskRunView, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        # empty response so pybossa can set webhook to this endpoint # TODO
        return HttpResponse(status=200)

    def post(self, request):
        """
        Receive webhooks from other applications.

        Event: PyBossa's task_completed sends following data
        {
          'fired_at':,
          'project_short_name': 'project-slug',
          'project_id': 1,
          'task_id': 1,
          'result_id': 1,
          'event': 'task_completed'
        }
        :param request:
        :return:
        """
        try:
            webhook_data = json.loads(request.read().decode('utf-8'))
        except json.JSONDecodeError:
            return HttpResponseBadRequest()

        if webhook_data.get('event') == 'task_completed':
            project_id = webhook_data.get('project_id')
            task_id = webhook_data.get('task_id')

            if not project_id or not task_id:
                return HttpResponseBadRequest()
            AbstractTask.verify_task(project_id, task_id)
            return HttpResponse("ok")

        return HttpResponseBadRequest()


def unpack_post(post: QueryDict) -> dict:
    """
    Unpack items in POST fields that have multiple occurences.

    It handles:
    - multiple fields without brackets, ie. field
    - multiple fields PHP5 style, ie. field[]
    - objects, ie. obj[field1]=val1 obj[field2]=val2
    - multiple rows of several fields, ie. row[0][field1], row[1][field1]
    - hierarchily nested multiples, ie. row[0][entry_id], row[0][entry_options][]

    Possible TODO, Django does it like this: (we could use Django parsing)
    <input type="hidden" name="acquisition_titles-TOTAL_FORMS" value="3" id="id_acquisition_titles-TOTAL_FORMS" autocomplete="off">
    <input type="hidden" name="acquisition_titles-INITIAL_FORMS" value="0" id="id_acquisition_titles-INITIAL_FORMS">
    <input type="hidden" name="acquisition_titles-MIN_NUM_FORMS" value="0" id="id_acquisition_titles-MIN_NUM_FORMS">
    <input type="hidden" name="acquisition_titles-MAX_NUM_FORMS" value="1000" id="id_acquisition_titles-MAX_NUM_FORMS" autocomplete="off">
    <input type="hidden" name="acquisition_titles-1-id" id="id_acquisition_titles-1-id">
    <input type="hidden" name="acquisition_titles-1-property" id="id_acquisition_titles-1-property">

    :param QueryDict post: POST data
    :return: dictionary representing the object passed in POST
    """

    dpath_separator = '/'
    result = {}
    convert_to_array_paths = set()

    for k in post.keys():
        # analyze field name
        m = re.search(r"^" +
                      "(?P<object>[\w\-_]+)" +
                      "(?P<selectors>(\[[\d\w\-_]+\])*)" +
                      "(?P<trailing_brackets>\[\])?" +
                      "$", k)
        if not m:
            raise Exception("Field name not valid: {}".format(k))

        path = m.group('object')
        if m.group('selectors'):
            for ms in re.finditer(r'\[([\d\w\-_]+)\]', m.group('selectors')):
                # if it is integer then make sure list is created
                idx = ms.group(1)
                if re.match(r'\d+', idx):
                    convert_to_array_paths.add(path)

                path += dpath_separator + idx

        def get_list_or_value(post, key):
            val = post.getlist(key)
            # single element leave single unless developer put brackets
            if len(val) == 1 and not m.group('trailing_brackets'):
                val = val[0]
            return val

        dpath.util.new(result, path, get_list_or_value(post, k), separator=dpath_separator)

    # dpath only works on dicts, but sometimes we want arrays
    # ie. row[0][fld]=0&row[1][fld]=1 results in row { "0": {}, "1": {} } instead of row [ {}, {} ]
    for path_to_d in convert_to_array_paths:
        arr = []
        d = dpath.util.get(result, path_to_d)
        numeric_keys = [int(k_int) for k_int in d.keys()]
        for k_int in sorted(numeric_keys):
            arr.append(d[str(k_int)])

        dpath.util.set(result, path_to_d, arr)

    return result
