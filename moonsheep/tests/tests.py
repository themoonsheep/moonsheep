import json
from requests.exceptions import ConnectionError

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models
from django.http.request import QueryDict
from django.test import TestCase as DjangoTestCase, Client, RequestFactory, override_settings
from django.urls import reverse

from unittest import TestCase as UnitTestCase
from unittest.mock import MagicMock, patch, sentinel, call

from moonsheep.exceptions import PresenterNotDefined, TaskMustSetTemplate, NoTasksLeft, TaskSourceNotDefined
from moonsheep.forms import NewTaskForm, MultipleRangeField
from moonsheep.models import ModelMapper
from moonsheep.register import base_task, initial_task
from moonsheep.settings import PYBOSSA_SOURCE, RANDOM_SOURCE
from moonsheep.tasks import AbstractTask
from moonsheep.verifiers import equals, OrderedListVerifier
from moonsheep.views import unpack_post, TaskView, NewTaskFormView, WebhookTaskRunView


# TODO: FIXME
# class PresenterTests(UnitTestCase):
#
#     def get_presenter(self, url):
#         """
#         Choosing how to render document to transcribe.
#
#         The default behaviour is to check:
#         1. Known url templates for YouTube, Vimeo, etc.
#         2. Url file extension
#         """
#
#     def _test_presenter(self, url, template, url_out=None):
#         t = AbstractTask(**{'info': {'url': url}})
#         p = t.get_presenter()
#
#         if url_out is None:
#             url_out = url
#
#         self.assertDictEqual(p, {
#             'template': 'presenters/{}.html'.format(template),
#             'url': url_out
#         })
#
#     def test_youtube(self):
#         self._test_presenter('https://www.youtube.com/watch?v=qEI1_oGPQr0', 'youtube')
#
#     def test_youtube_not_valid(self):
#         t = AbstractTask(**{'info': {'url': 'https://www.youtube.com/'}})
#
#         with self.assertRaises(PresenterNotDefined):
#             t.get_presenter()
#
#     def test_vimeo(self):
#         self._test_presenter('https://vimeo.com/201762745', 'vimeo')
#
#     def test_vimeo_not_valid(self):
#         t = AbstractTask(**{'info': {'url': 'https://vimeo.com/'}})
#
#         with self.assertRaises(PresenterNotDefined):
#             t.get_presenter()
#
#     def test_extension_pdf(self):
#         self._test_presenter('http://domain.pl/document.pdf', 'pdf')
#
#     def test_extension_png(self):
#         self._test_presenter('http://domain.pl/document.png', 'image')
#
#     def test_extension_jpg(self):
#         self._test_presenter('http://domain.pl/document.jpg', 'image')
#
#     def test_extension_jpeg(self):
#         self._test_presenter('http://domain.pl/document.jpeg', 'image')
#
#     def test_missing_presenter(self):
#         t = AbstractTask(**{'info': {'url': 'http://domain.pl/document.whatthehell'}})
#
#         with self.assertRaises(PresenterNotDefined):
#             t.get_presenter()


# TODO test error handling for Tasks with no form and no template

# views.py
PYBOSSA_PROJECT_ID = 1


def setup_view(view, request, *args, **kwargs):
    """
    Mimic as_view() returned callable, but returns view instance.
    args and kwargs are the same you would pass to ``reverse()``
    """
    view.request = request
    view.args = args
    view.kwargs = kwargs
    return view


class TaskViewTest(DjangoTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.fake_path = '/'
        self.redirect_path = 'http://redirected.com/'
        self.template_name = 'test-template.html'
        self.task_data = {
            'info': {
                'url': 'http://example.com',
                'template_name': 'task-template.html',
                'task_form': 'myapp.forms.TaskForm'
            }
        }
        self.pybossa_project_id = 1
        self.task_id = 1
        self.post_data = {
            '_project_id': self.pybossa_project_id,
            '_task_id': self.task_id
        }

    @patch('moonsheep.views.TaskView._get_task')
    @patch('moonsheep.views.TaskView.initialize_task_data')
    @patch('moonsheep.views.TaskView.get_context_data')
    def test_get(
            self,
            get_context_data_mock: MagicMock,
            _get_form_class_data_mock: MagicMock,
            _get_task_mock: MagicMock
    ):
        request = self.factory.get(self.fake_path)
        view = TaskView()
        view = setup_view(view, request, **self.task_data)
        view.template_name = self.template_name
        response = view.get(request)
        self.assertEqual(response.status_code, 200)
        _get_task_mock.assert_any_call()
        _get_form_class_data_mock.assert_any_call()
        get_context_data_mock.assert_any_call()

    @patch('moonsheep.views.TaskView._get_task')
    @patch('moonsheep.views.TaskView.initialize_task_data')
    @patch('moonsheep.views.TaskView.get_context_data')
    def test_get_no_tasks(
            self,
            get_context_data_mock: MagicMock,
            _get_form_class_data_mock: MagicMock,
            _get_task_mock: MagicMock
    ):
        _get_task_mock.side_effect = NoTasksLeft
        request = self.factory.get(self.fake_path)
        view = TaskView()
        view = setup_view(view, request, **self.task_data)
        view.task = AbstractTask()
        view.template_name = self.template_name
        response = view.get(request)
        self.assertEqual(view.task, None)
        self.assertEqual(view.error_message, 'Broker returned no tasks')
        self.assertEqual(view.error_template, 'error-messages/no-tasks.html')
        self.assertEqual(response.status_code, 200)
        _get_task_mock.assert_any_call()
        _get_form_class_data_mock.assert_not_called()
        get_context_data_mock.assert_any_call()

    @patch('moonsheep.views.TaskView._get_task')
    @patch('moonsheep.views.TaskView.initialize_task_data')
    @patch('moonsheep.views.TaskView.get_context_data')
    def test_get_improperly_configured(
            self,
            get_context_data_mock: MagicMock,
            _get_form_class_data_mock: MagicMock,
            _get_task_mock: MagicMock
    ):
        _get_task_mock.side_effect = ImproperlyConfigured
        request = self.factory.get(self.fake_path)
        view = TaskView()
        view = setup_view(view, request, **self.task_data)
        view.task = AbstractTask()
        view.template_name = self.template_name
        response = view.get(request)
        self.assertEqual(view.task, None)
        self.assertEqual(view.error_message, 'Improperly configured PyBossa')
        self.assertEqual(view.error_template, 'error-messages/improperly-configured.html')
        self.assertEqual(response.status_code, 200)
        _get_task_mock.assert_any_call()
        _get_form_class_data_mock.assert_not_called()
        get_context_data_mock.assert_any_call()

    @patch('moonsheep.views.TaskView._get_task')
    @patch('moonsheep.views.TaskView.initialize_task_data')
    @patch('moonsheep.views.TaskView.get_context_data')
    def test_get_presenter_not_defined(
            self,
            get_context_data_mock: MagicMock,
            _get_form_class_data_mock: MagicMock,
            _get_task_mock: MagicMock
    ):
        _get_task_mock.side_effect = PresenterNotDefined
        request = self.factory.get(self.fake_path)
        view = TaskView()
        view = setup_view(view, request, **self.task_data)
        view.task = AbstractTask()
        view.template_name = self.template_name
        response = view.get(request)
        self.assertEqual(view.task, None)
        self.assertEqual(view.error_message, 'Presenter not defined')
        self.assertEqual(view.error_template, 'error-messages/presenter-not-defined.html')
        self.assertEqual(response.status_code, 200)
        _get_task_mock.assert_any_call()
        _get_form_class_data_mock.assert_not_called()
        get_context_data_mock.assert_any_call()

    @patch('moonsheep.views.TaskView._get_task')
    @patch('moonsheep.views.TaskView.initialize_task_data')
    @patch('moonsheep.views.TaskView.get_form')
    @patch('moonsheep.views.TaskView.form_valid')
    def test_post(
            self,
            form_valid_mock: MagicMock,
            get_form_mock: MagicMock,
            _get_form_class_data_mock: MagicMock,
            _get_task_mock: MagicMock
    ):
        request = self.factory.post(self.fake_path, self.post_data)
        view = TaskView()
        view = setup_view(view, request, **self.task_data)
        view.post(request)
        _get_task_mock.assert_called_once_with(
            new=False,
            project_id=str(self.post_data.get('_project_id')),
            task_id=str(self.post_data.get('_task_id'))
        )
        _get_form_class_data_mock.assert_any_call()
        get_form_mock.assert_any_call()
        # TODO: FIXME
        # form_valid_mock.assert_called_once_with(get_form_mock)

    # TODO: FIXME
    # @patch('moonsheep.views.TaskView._get_task')
    # @patch('moonsheep.views.TaskView.initialize_task_data')
    # @patch('moonsheep.views.TaskView.get_form')
    # @patch('moonsheep.views.TaskView.form_invalid')
    # def test_post_invalid_form(
    #         self,
    #         form_invalid_mock: MagicMock,
    #         get_form_mock: MagicMock,
    #         _get_form_class_data_mock: MagicMock,
    #         _get_task_mock: MagicMock
    # ):
    #     mock = MagicMock
    #     attrs = {'is_valid': False}
    #     mock.configure_mock(attrs)
    #     get_form_mock.return_value = mock
    #
    #     request = self.factory.post(self.fake_path, self.post_data)
    #     view = TaskView()
    #     view = setup_view(view, request, **self.task_data)
    #     view.post(request)
    #
    #     _get_task_mock.assert_any_call()
    #     _get_form_class_data_mock.assert_any_call()
    #     get_form_mock.assert_any_call()

    @patch('moonsheep.views.TaskView._get_task')
    @patch('moonsheep.views.TaskView.initialize_task_data')
    @patch('moonsheep.views.TaskView.get_form')
    @patch('moonsheep.views.unpack_post')
    @patch('moonsheep.views.TaskView._send_task')
    @patch('moonsheep.views.TaskView.get_success_url')
    def test_post_no_form(
            self,
            get_success_url_mock: MagicMock,
            _send_task_mock: MagicMock,
            unpack_post_mock: MagicMock,
            get_form_mock: MagicMock,
            _get_form_class_data_mock: MagicMock,
            _get_task_mock: MagicMock
    ):
        get_form_mock.return_value = None
        get_success_url_mock.return_value = self.redirect_path
        request = self.factory.post(self.fake_path, self.post_data)
        view = TaskView()
        view = setup_view(view, request, **self.task_data)
        response = view.post(request)
        self.assertEqual(response.status_code, 302)
        get_success_url_mock.assert_any_call()
        # TODO: FIXME
        # _send_task_mock.assert_called_with(unpack_post_mock)
        # TODO: FIXME
        # unpack_post_mock.assert_called_once_with(self.post_data)
        get_form_mock.assert_any_call()
        _get_form_class_data_mock.assert_any_call()
        _get_task_mock.assert_called_with(
            new=False,
            project_id=str(self.post_data.get('_project_id')),
            task_id=str(self.post_data.get('_task_id'))
        )

    def test_post_no_task_id(self):
        del self.post_data['_task_id']
        request = self.factory.post(self.fake_path, self.post_data)
        view = TaskView()
        view = setup_view(view, request, **self.task_data)
        response = view.post(request)
        self.assertEqual(response.status_code, 400)

    def test_post_no_project_id(self):
        del self.post_data['_project_id']
        request = self.factory.post(self.fake_path, self.post_data)
        view = TaskView()
        view = setup_view(view, request, **self.task_data)
        response = view.post(request)
        self.assertEqual(response.status_code, 400)

    @patch('moonsheep.views.TaskView._get_task')
    @patch('moonsheep.views.TaskView.initialize_task_data')
    def test_get_context_data(
            self,
            initialize_task_data_mock: MagicMock,
            _get_task_mock: MagicMock
    ):
        request = self.factory.get(self.fake_path)
        view = TaskView()
        view = setup_view(view, request)
        view.task = AbstractTask()
        context = view.get_context_data()
        self.assertIsInstance(context['task'], AbstractTask)
        self.assertEqual(context['task'], view.task)
        self.assertEqual(context['project_id'], PYBOSSA_PROJECT_ID)
        from moonsheep.settings import PYBOSSA_BASE_URL
        self.assertEqual(context['pybossa_url'], PYBOSSA_BASE_URL)

    @patch('moonsheep.views.TaskView._get_task')
    @patch('moonsheep.views.TaskView.initialize_task_data')
    @patch('moonsheep.tasks.AbstractTask.get_presenter')
    def test_get_context_data_presenter_typeerror(
            self,
            get_presenter_mock: MagicMock,
            initialize_task_data_mock: MagicMock,
            _get_task_mock: MagicMock
    ):
        get_presenter_mock.side_effect = TypeError
        request = self.factory.get(self.fake_path)
        view = TaskView()
        view = setup_view(view, request)
        view.task = AbstractTask()
        with self.assertRaises(PresenterNotDefined):
            view.get_context_data()

    @patch('moonsheep.views.TaskView.initialize_task_data')
    def test_get_context_data_no_task(
            self,
            _get_task_mock: MagicMock
    ):
        request = self.factory.get(self.fake_path)
        view = TaskView()
        view.error_message = 'Sample error message'
        view.error_template = 'Sample error template'
        view = setup_view(view, request)
        context = view.get_context_data()
        self.assertTrue(context['error'])
        self.assertEqual(context['message'], 'Sample error message')
        self.assertEqual(context['template'], 'Sample error template')
        self.assertEqual(context['project_id'], PYBOSSA_PROJECT_ID)
        from moonsheep.settings import PYBOSSA_BASE_URL
        self.assertEqual(context['pybossa_url'], PYBOSSA_BASE_URL)

    @patch('moonsheep.models.klass_from_name')
    def test_initialize_task_data(
            self,
            klass_from_name_mock: MagicMock
    ):
        del self.task_data['info']['task_form']
        request = self.factory.get(self.fake_path)
        view = TaskView()
        view = setup_view(view, request)
        view.task = AbstractTask(**self.task_data)
        view.initialize_task_data()
        # TODO: divide to 2 test cases
        # self.assertEqual(view.template_name, self.task_data.get('info').get('template_name'))
        self.assertEqual(view.template_name, self.task_data.get('info').get('template_name'))
        # klass_from_name_mock.assert_called_once_with(self.task_data.get('info').get('task_form'))

    def test_initialize_task_data_no_template_nor_form(self):
        request = self.factory.get(self.fake_path)
        view = TaskView()
        view = setup_view(view, request)
        self.assertRaises(TaskMustSetTemplate, view.initialize_task_data)

    def test_get_form_class(self):
        # TODO
        pass

    def test_get_form(self):
        pass

    def test_get_form_no_form_class(self):
        pass

    @patch('moonsheep.views.TaskView._get_new_task')
    @patch('moonsheep.tasks.AbstractTask.create_task_instance')
    def test_get_task_new(
            self,
            create_task_instance_mock: MagicMock,
            _get_new_task_mock: MagicMock
    ):
        request = self.factory.get(self.fake_path)
        view = TaskView()
        view = setup_view(view, request)
        view._get_task(new=True)
        _get_new_task_mock.assert_any_call()
        # TODO: FIXME
        # create_task_instance_mock.assert_called_once_with()

    # TODO: FIXME
    # @patch('moonsheep.views.TaskView.get_random_mocked_task_data')
    # @patch('moonsheep.tasks.AbstractTask.create_task_instance')
    # @patch('moonsheep.settings.TASK_SOURCE', RANDOM_SOURCE)
    # def test_get_task_random_source(
    #         self,
    #         create_task_instance_mock: MagicMock,
    #         get_random_mocked_task_data_mock: MagicMock
    # ):
    #     request = self.factory.get(self.fake_path)
    #     view = TaskView()
    #     view = setup_view(view, request)
    #     view._get_task(new=False)
    #     get_random_mocked_task_data_mock.assert_any_call()
    #     # TODO: FIXME
    #     # create_task_instance_mock.assert_called_once_with()

    # # TODO: FIXME
    # @patch('pbclient.get_task')
    # @patch('moonsheep.tasks.AbstractTask.create_task_instance')
    # @override_settings(TASK_SOURCE=PYBOSSA_SOURCE)
    # def test_get_task_old_not_development(
    #         self,
    #         create_task_instance_mock: MagicMock,
    #         get_task_mock: MagicMock
    # ):
    #     request = self.factory.get(self.fake_path)
    #     view = TaskView()
    #     view = setup_view(view, request)
    #     view._get_task(new=False, project_id=self.pybossa_project_id, task_id=self.task_id)
    #     get_task_mock.assert_called_once_with(project_id=self.pybossa_project_id, task_id=self.task_id)
    #     # TODO: FIXME
    #     # create_task_instance_mock.assert_called_once_with()

    def test_form_valid(self):
        pass

    # TODO: FIXME
    # @patch('moonsheep.views.TaskView.get_random_mocked_task_data')
    # @override_settings(MOONSHEEP_TASK_SOURCE=RANDOM_SOURCE)
    # @patch('moonsheep.settings.TASK_SOURCE', RANDOM_SOURCE)
    # def test_get_new_task_random_mocked_task(self, get_random_mocked_task_data_mock: MagicMock):
    #     from moonsheep.views import TaskView
    #     request = self.factory.get(self.fake_path)
    #     view = TaskView()
    #     view = setup_view(view, request)
    #     task = view._get_new_task()
    #     get_random_mocked_task_data_mock.assert_any_call()
    #     # TODO: FIXME
    #     # self.assertEqual(task, get_random_mocked_task_data_mock)

    # TODO: FIXME
    # @patch('moonsheep.views.TaskView.get_random_pybossa_task')
    # @override_settings(TASK_SOURCE=PYBOSSA_SOURCE)
    # @patch('moonsheep.settings.TASK_SOURCE', PYBOSSA_SOURCE)
    # def test_get_new_task_random_pybossa_task(self, get_random_pybossa_task_mock: MagicMock):
    #     from moonsheep.views import TaskView
    #     request = self.factory.get(self.fake_path)
    #     view = TaskView()
    #     view = setup_view(view, request)
    #     task = view._get_new_task()
    #     get_random_pybossa_task_mock.assert_any_call()
    #     # TODO: FIXME
    #     # self.assertEqual(task, get_random_mocked_task_data_mock)

    # TODO: FIXME
    # @override_settings(TASK_SOURCE='error-source')
    # def test_get_new_task_not_defined(self):
    #     from moonsheep.settings import TASK_SOURCE
    #     request = self.factory.get(self.fake_path)
    #     view = TaskView()
    #     view = setup_view(view, request)
    #     with self.assertRaises(TaskSourceNotDefined):
    #         view._get_new_task()

    # TODO: FIXME
    # @patch('moonsheep.views.TaskView.get_random_mocked_task_data')
    # @override_settings(TASK_SOURCE=RANDOM_SOURCE)
    # def test_get_new_task_no_tasks(self, get_random_mocked_task_data_mock: MagicMock):
    #     get_random_mocked_task_data_mock.return_value = None
    #     request = self.factory.get(self.fake_path)
    #     view = TaskView()
    #     view = setup_view(view, request)
    #     with self.assertRaises(NoTasksLeft):
    #         view._get_new_task()

    # TODO: test tasks rotation
    def test_get_random_mocked_task_data(self):
        request = self.factory.get(self.fake_path)
        base_task.register(AbstractTask)
        view = TaskView()
        view = setup_view(view, request)
        task = view.get_random_mocked_task_data()
        self.assertEqual(task, {
            'project_id': 'https://i.imgflip.com/hkimf.jpg',
            'info': {
                'url': 'https://nazk.gov.ua/sites/default/files/docs/2017/3/3_kv/2/Agrarna_partija/3%20%EA%E2%E0%F0%F2%E0%EB%202017%20%D6%C0%20%C0%CF%D3%20%97%20%E7%E0%F2%E5%F0%F2%E8%E9.pdf',
                'type': 'moonsheep.tasks.AbstractTask'
            },
            'id': 'moonsheep.tasks.AbstractTask'
        })
        base_task.clear()

    def test_get_random_mocked_task_data_no_registry(self):
        request = self.factory.get(self.fake_path)
        view = TaskView()
        view = setup_view(view, request)
        with self.assertRaises(NotImplementedError):
            view.get_random_mocked_task_data()

    @patch('pbclient.get_new_task')
    def test_get_random_pybossa_task(self, get_new_task_mock: MagicMock):
        request = self.factory.get(self.fake_path)
        view = TaskView()
        view = setup_view(view, request)
        view.get_random_pybossa_task()
        get_new_task_mock.assert_called_with(PYBOSSA_PROJECT_ID)

    @patch('pbclient.get_new_task')
    def test_get_random_pybossa_task_connection_error(self, get_new_task_mock: MagicMock):
        get_new_task_mock.side_effect = ConnectionError
        request = self.factory.get(self.fake_path)
        view = TaskView()
        view = setup_view(view, request)
        with self.assertRaises(ImproperlyConfigured):
            view.get_random_pybossa_task()

    def test_send_task(self):
        pass

    def test_send_pybossa_task(self):
        pass


@override_settings(ROOT_URLCONF='moonsheep.urls')
class NewTaskFormViewTest(DjangoTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.client = Client()
        self.path = reverse('ms-new-task')
        self.pybossa_project_id = 1
        self.task_id = 1

    def test_get_success_url(self):
        request = self.factory.get(self.path)
        view = NewTaskFormView()
        view.request = request
        success_url = view.get_success_url()
        self.assertEquals(success_url, self.path)

    @patch('pbclient.set')
    @patch('pbclient.create_task')
    def test_form_valid_no_registry(
            self,
            create_task_mock: MagicMock,
            set_mock: MagicMock
    ):
        request = self.factory.get(self.path)
        view = NewTaskFormView()
        view.request = request
        form_data = {
            'url': 'http://byleco.pl'
        }
        form = NewTaskForm(form_data)
        form.full_clean()
        with self.assertRaises(ImproperlyConfigured):
            view.form_valid(form)

    @patch('pbclient.set')
    @patch('pbclient.create_task')
    def test_form_valid(
            self,
            create_task_mock: MagicMock,
            set_mock: MagicMock
    ):
        request = self.factory.get(self.path)
        initial_task.register(AbstractTask)
        view = NewTaskFormView()
        view.request = request
        form_data = {
            'url': 'http://byleco.pl'
        }
        form = NewTaskForm(form_data)
        form.full_clean()
        success_url = view.form_valid(form).url
        self.assertEquals(success_url, self.path)
        initial_task.clear()
        # set_mock.assert_has_calls([call('endpoint', settings.PY)])
        # create_task_mock.assert_any_call({
        #     'project_id': PYBOSSA_PROJECT_ID,
        #     'info': {
        #         'type':
        #     }
        # })

    # def test_form_valid_no_base_tasks(self):


class WebhookTaskRunViewTest(UnitTestCase):
    def test_dispatch(self):
        pass

    def test_get(self):
        pass

    def test_post(self):
        pass


class UnpackPostTest(UnitTestCase):
    """
    It tests moonsheep.views.unpack_post function.

    Unpack items in POST fields that have multiple occurences.

    It handles:
    - multiple fields without brackets, ie. field
    - multiple fields PHP5 style, ie. field[]
    - objects, ie. obj[field1]=val1 obj[field2]=val2
    - multiple rows of several fields, ie. row[0][field1], row[1][field1]
    - hierarchily nested multiples, ie. row[0][entry_id], row[0][entry_options][]

    :param: post QueryDict
    :return: list or dict
    """

    def test_querydict_single(self):
        post = QueryDict('field=val1')
        self.assertEqual(post['field'], 'val1')
        self.assertEqual(post.getlist('field'), ['val1'])
        self.assertDictEqual(post, {
            'field': ['val1']
        })

    def test_querydict_multiple(self):
        post = QueryDict('field=val1&field=val2')

        # simple __get_item__ returns last value
        self.assertEqual(post['field'], 'val2')

        # to get all values one have to use getlist
        self.assertEqual(post.getlist('field'), ['val1', 'val2'])

        # equals takes into account multiple values
        self.assertDictEqual(post, {
            'field': ['val1', 'val2']
        })

        # but QueryDict.dict() don't (it just return the last value)
        self.assertDictEqual(post.dict(), {
            'field': 'val2'
        })

    def test_multiple_wo_brackets(self):
        post = QueryDict('field=val1&field=val2')
        self.assertDictEqual(unpack_post(post), {
            'field': ['val1', 'val2']
        })

    def test_multiple_with_brackets(self):
        post = QueryDict('field[]=val1&field[]=val2')
        self.assertDictEqual(unpack_post(post), {
            'field': ['val1', 'val2']
        })

    def test_single_wo_brackets(self):
        post = QueryDict('field=val1')
        self.assertDictEqual(unpack_post(post), {
            'field': 'val1'
        })

    def test_single_with_brackets(self):
        """
        Where we assume that the developer wanted list
        """
        post = QueryDict('field[]=val1')
        self.assertDictEqual(unpack_post(post), {
            'field': ['val1']
        })

    def test_object(self):
        post = QueryDict('obj[field1]=val1&obj[field2]=val2')
        self.assertDictEqual(unpack_post(post), {
            'obj': {
                'field1': 'val1',
                'field2': 'val2'
            }
        })

    def test_rows(self):
        post = QueryDict('row[0][field1]=val1&row[0][field2]=val2&row[1][field1]=val3')
        self.assertDictEqual(unpack_post(post), {
            'row': [
                {'field1': 'val1', 'field2': 'val2'},
                {'field1': 'val3'}
            ]
        })

    def test_rows_alpha_index(self):
        """
        TODO this test is unstable (once fails, once not)
        :return:
        """
        post = QueryDict('row[0][fld]=0&row[bla][fld]=bla')
        with self.assertRaises(ValueError):
            unpack_post(post)

    def test_rows_missing_index(self):
        """
        For now, we don't throw errors.. Should we?
        """
        post = QueryDict('row[0][fld]=0&row[2][fld]=2')
        self.assertDictEqual(unpack_post(post), {
            'row': [
                {'fld': '0'},
                {'fld': '2'}
            ]
        })

    def test_rows_inverse_order(self):
        post = QueryDict('row[1][field1]=val3&row[0][field1]=val1&row[0][field2]=val2')
        self.assertDictEqual(unpack_post(post), {
            'row': [
                {'field1': 'val1', 'field2': 'val2'},
                {'field1': 'val3'}
            ]
        })

    def test_rows_inverse_order_numcomparison(self):
        """
        to check that 1, 10, 2 are sorted numerically and not alphabetically
        """
        post = QueryDict('&'.join(['row[{}][fld]={}'.format(i, i) for i in range(11, -1, -1)]))
        self.assertDictEqual(unpack_post(post), {
            'row': [
                {'fld': '0'},
                {'fld': '1'},
                {'fld': '2'},
                {'fld': '3'},
                {'fld': '4'},
                {'fld': '5'},
                {'fld': '6'},
                {'fld': '7'},
                {'fld': '8'},
                {'fld': '9'},
                {'fld': '10'},
                {'fld': '11'}
            ]
        })
        pass

    def test_nested_rows_not_numbered(self):
        post = QueryDict('row[0][entry_id]=val1&row[0][entry_options][]=val2&row[0][entry_options][]=val3')
        self.assertDictEqual(unpack_post(post), {
            'row': [{
                'entry_id': 'val1',
                'entry_options': ['val2', 'val3']
            }]
        })

    def test_nested_rows_numbered(self):
        """
        :return:
        """
        post = QueryDict('row[0][entry_id]=val1&row[0][entry_options][0]=val2&row[0][entry_options][1]=val3')
        self.assertDictEqual(unpack_post(post), {
            'row': [{
                'entry_id': 'val1',
                'entry_options': ['val2', 'val3']
            }]
        })


@override_settings(ROOT_URLCONF='moonsheep.urls')
class TaskProcessingTests(DjangoTestCase):
    webhook_url = '/webhooks/task-run/'

    @patch('moonsheep.tasks.AbstractTask.verify_task')
    def test_webhook_exists(self, verify_task_mock: MagicMock):
        client = Client()
        response = client.get(self.webhook_url)

        self.assertEqual(response.status_code, 200)
        verify_task_mock.assert_not_called()

    @patch('moonsheep.tasks.AbstractTask.verify_task')
    def test_webhook_receives(self, verify_task_mock: MagicMock):
        client = Client()
        data = {
            'event': 'task_completed',
            'project_id': "PROJECT_ID",
            'task_id': "TASK_ID",
        }
        response = client.post(self.webhook_url, json.dumps(data), content_type="application/json")

        self.assertEqual(response.status_code, 200)
        verify_task_mock.assert_called_with("PROJECT_ID", "TASK_ID")

    @patch('moonsheep.tasks.AbstractTask.verify_task')
    def test_webhook_receives_missing_data(self, verify_task_mock: MagicMock):
        client = Client()
        data = {
            'event': 'task_completed',
        }
        response = client.post(self.webhook_url, json.dumps(data), content_type="application/json")
        verify_task_mock.assert_not_called()

        self.assertEqual(response.status_code, 400)

    def test_webhook_unrecognized_event(self):
        client = Client()
        data = {
            'event': 'unknown_event',
        }
        response = client.post(self.webhook_url, json.dumps(data), content_type="application/json")

        self.assertEqual(response.status_code, 400)

    def test_webhook_no_payload(self):
        client = Client()
        response = client.post(self.webhook_url)

        self.assertEqual(response.status_code, 400)

    @patch('moonsheep.tasks.AbstractTask.after_save')
    @patch('moonsheep.tasks.AbstractTask.save_verified_data')
    def test_flow_of_verified(self, save_verified_data_mock: MagicMock, after_save_mock: MagicMock):
        verified_data = {'fld': 'val1'}

        task = AbstractTask(info={'url': 'https://bla.pl'})

        # TODO test verification on one input
        task.verify_and_save([verified_data, verified_data])

        save_verified_data_mock.assert_called_with(verified_data)
        after_save_mock.assert_called_with(verified_data)

    # FIXME: this is set by pybossa
    # @patch('moonsheep.tasks.AbstractTask.after_save')
    # @patch('moonsheep.tasks.AbstractTask.save_verified_data')
    # def test_flow_one_input(self, save_verified_data_mock: MagicMock, after_save_mock: MagicMock):
    #     """
    #     One input shouldn't be enough for verification to run successful
    #     In future this may be extended to set a limit
    #     :return:
    #     """
    #     verified_data = {'fld': 'val1'}
    #
    #     task = AbstractTask(info={'url': 'https://bla.pl'})
    #
    #     task.verify_and_save([verified_data])
    #
    #     save_verified_data_mock.assert_not_called_with(verified_data)
    #     after_save_mock.assert_not_called_with(verified_data)

    def test_flow_of_unverified(self):
        """
        TODO
        :return:
        """
        pass

    def test_create_task_instance(self):
        task = AbstractTask.create_task_instance('moonsheep.tasks.AbstractTask', info={'url': 'https://bla.pl'})
        self.assertIsInstance(task, AbstractTask)

    @patch('moonsheep.verifiers.DEFAULT_BASIC_VERIFIER_METHOD')
    def test_verification_default_equals_mock(self, equals_mock: MagicMock):
        verified_dict_data = {'fld': 'val1'}
        task = AbstractTask(info={'url': 'https://bla.pl'})

        equals_mock.return_value = (1, verified_dict_data)

        task.cross_check([verified_dict_data, verified_dict_data])
        equals_mock.assert_called_with(['val1', 'val1'])

    def test_verification_default_equals_true(self):
        verified_dict_data = {'fld': 'val1'}
        task = AbstractTask(info={'url': 'https://bla.pl'})

        (result, confidence) = task.cross_check([verified_dict_data, verified_dict_data])
        self.assertEquals(result, verified_dict_data)

    @patch('moonsheep.tasks.AbstractTask.save_verified_data')
    @patch('moonsheep.tasks.AbstractTask.after_save')
    def test_verification_default_equals_false(self, after_save_mock: MagicMock, save_verified_data_mock: MagicMock):
        task = AbstractTask(info={'url': 'https://bla.pl'})

        decision = task.verify_and_save([{'fld': 'val1'}, {'fld': 'whatever'}])
        self.assertEqual(decision, False)
        after_save_mock.assert_not_called()
        save_verified_data_mock.assert_not_called()

    @patch('moonsheep.verifiers.OrderedListVerifier.__call__')
    def test_verification_default_ordered_list_mock(self, unordered_set_mock: MagicMock):
        verified_list_data = {'items': [1, 2, 3]}
        task = AbstractTask(info={'url': 'https://bla.pl'})

        unordered_set_mock.side_effect = [([1, 2, 3], 1)]
        task.cross_check([verified_list_data, verified_list_data])
        unordered_set_mock.assert_called_with([[1, 2, 3], [1, 2, 3]])

    def test_verification_default_ordered_list_true(self):
        verified_list_data = {'items': [1, 2, 3]}
        task = AbstractTask(info={'url': 'https://bla.pl'})

        (result, confidence) = task.cross_check([verified_list_data, verified_list_data])
        self.assertEquals(result, verified_list_data)

    # TODO: FIXME
    # def test_verification_default_ordered_list_false(self):
    #     task = AbstractTask(info={'url': 'https://bla.pl'})
    #
    #     (result, confidence) = task.cross_check([{'items': [1, 2, 3]}, {'items': [7, 2, 8]}])
    #     self.assertEquals(confidence, 0)
    #     self.assertEquals(result, None)

    def test_verification_default_complex_true(self):
        verified_dict_data = {'cars': [{'model': 'A', 'year': 2011}, {'model': 'B', 'year': 2012}]}
        task = AbstractTask(info={'url': 'https://bla.pl'})

        (result, confidence) = task.cross_check([verified_dict_data, verified_dict_data])

        self.assertEquals(confidence, 1)
        self.assertEquals(result, verified_dict_data)

    @patch('moonsheep.verifiers.DEFAULT_BASIC_VERIFIER_METHOD')
    def test_verification_default_complex(self, equals_mock: MagicMock):
        verified_dict_data = {'cars': [{'model': 'A', 'year': 2011}, {'model': 'B', 'year': 2012}]}
        task = AbstractTask(info={'url': 'https://bla.pl'})

        equals_mock.side_effect = lambda values: (values[0], 1)

        task.cross_check([verified_dict_data, verified_dict_data])
        # equals_mock.assert_not_called_with([verified_dict_data, verified_dict_data])
        calls = [call(['A', 'A']), call([2011, 2011]), call(['B', 'B']), call([2012, 2012])]
        equals_mock.assert_has_calls(calls, any_order=True)


class CustomVerificationTests(UnitTestCase):
    # TODO
    pass


class VerifierEqualsTest(UnitTestCase):
    def test_same_text(self):
        (result, confidence) = equals(['a', 'a', 'a'])

        self.assertEquals(result, 'a')
        self.assertEquals(confidence, 1)

    def test_same_num(self):
        (result, confidence) = equals([2, 2, 2])

        self.assertEquals(result, 2)
        self.assertEquals(confidence, 1)

    def test_outlier(self):
        (result, confidence) = equals(['a', 'a', 'a', 'b'])

        self.assertEquals(result, 'a')
        self.assertGreaterEqual(confidence, 0)
        self.assertLess(confidence, 1)

    def test_no_standing_out(self):
        (result, confidence) = equals(['a', 'b', 'c', 'd'])

        self.assertGreaterEqual(confidence, 0)  # TODO shouldn't confidence be 0 in such case?
        self.assertLess(confidence, 1)
        self.assertIn(result, ['a', 'b', 'c', 'd'])
        # self.assertEquals(result, None)


class VerifierListTest(UnitTestCase):
    def test_all_same_text(self):
        entry = ['val1', 'val2', 'val3', 'val4']
        task = AbstractTask(info={'url': 'https://bla.pl'})
        (result, confidence) = OrderedListVerifier(task, '')([entry, entry, entry])

        self.assertEquals(result, entry)
        self.assertEquals(confidence, 1)

    def test_all_same_num(self):
        entry = [1, 2, 3, 4]
        task = AbstractTask(info={'url': 'https://bla.pl'})
        (result, confidence) = OrderedListVerifier(task, '')([entry, entry, entry])

        self.assertEquals(result, entry)
        self.assertEquals(confidence, 1)

    def test_different_length1(self):
        entry = [1, 2, 3, 4]
        task = AbstractTask(info={'url': 'https://bla.pl'})
        (result, confidence) = OrderedListVerifier(task, '')([entry, entry, entry + [5]])

        self.assertEquals(result, entry)
        self.assertGreaterEqual(confidence, 0)
        self.assertLess(confidence, 1)

    def test_different_length2(self):
        entry = [1, 2, 3, 4]
        task = AbstractTask(info={'url': 'https://bla.pl'})
        (result, confidence) = OrderedListVerifier(task, '')([entry + [5], entry, entry])

        self.assertEquals(result, entry)
        self.assertGreaterEqual(confidence, 0)
        self.assertLess(confidence, 1)

    def test_no_standing_out(self):
        task = AbstractTask(info={'url': 'https://bla.pl'})
        (result, confidence) = OrderedListVerifier(task, '')([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]])

        self.assertLess(confidence, 1)
        self.assertGreaterEqual(confidence, 0)
        # self.assertEquals(result, None)

    def test_ordering(self):
        task = AbstractTask(info={'url': 'https://bla.pl'})
        (result, confidence) = OrderedListVerifier(task, '')([[1, 2, 3, 4], [4, 3, 2, 1]])

        self.assertLess(confidence, 1)
        self.assertGreaterEqual(confidence, 0)
        # self.assertEquals(result, None)


class MultipleRangeFieldTestCase(UnitTestCase):
    def setUp(self):
        self.field = MultipleRangeField()

    def test_clean_single_number(self):
        self.assertEquals(self.field.clean('1'), ['1'])

    def test_clean_comma_separated_numbers(self):
        self.assertEquals(self.field.clean('1,2,4'), ['1', '2', '4'])

    def test_clean_dash_separated_numbers(self):
        self.assertEquals(self.field.clean('1-4'), ['1', '2', '3', '4'])

    def test_clean_various_type_number_ranges(self):
        self.assertEquals(self.field.clean('1-4,5-6'), ['1', '2', '3', '4', '5', '6'])

    def test_clean_comma_separated_numbers_with_prefixes(self):
        self.assertEquals(self.field.clean('abc,abc1'), ['abc', 'abc1'])

    def test_clean_postfix(self):
        self.assertEquals(self.field.clean('5820345SB,5820336SB'), ['5820345SB', '5820336SB'])

    def test_clean_dash_separated_numbers_with_prefixes(self):
        self.assertEquals(self.field.clean('A1-A3'), ['A1', 'A2', 'A3'])

    def test_clean_various_type_ranges(self):
        self.assertEquals(self.field.clean('a1-a2,1-3'), ['a1', 'a2', '1', '2', '3'])

    def test_clean_useless_range(self):
        self.assertEquals(self.field.clean('1-1'), ['1'])

    def test_clean_warning_range(self):
        self.assertEquals(self.field.clean('3-5,4'), ['3', '4', '5'])

    def test_clean_reverse_range_error(self):
        self.assertRaises(ValidationError, self.field.clean, '5-3')

    def test_clean_range_format_error(self):
        self.assertRaises(ValidationError, self.field.clean, '1-3-5')

    def test_clean_prefix_format_error(self):
        self.assertRaises(ValidationError, self.field.clean, 'A1-C3')

    def test_clean_no_number_range_error(self):
        self.assertRaises(ValidationError, self.field.clean, 'ABC-CDE')

    def test_clean_postfix_range_error(self):
        # TODO: is this range acceptable or should cause error?
        # TODO: it happens in Opora, with suffix going down: 5820345SB-5820336SB
        # page 46 on https://nazk.gov.ua/sites/default/files/docs/2017/3/3_kv/2/Agrarna_partija/3%20%EA%E2%E0%F0%F2%E0%EB%202017%20%D6%C0%20%C0%CF%D3%20%97%20%E7%E0%F2%E5%F0%F2%E8%E9.pdf
        self.assertRaises(ValidationError, self.field.clean, '1A-3A')

    def test_clean_spaces(self):
        self.assertEquals(self.field.clean(' 1 -   3'), ['1', '2', '3'])

    def test_clean_wrong_spaces(self):
        self.assertRaises(ValidationError, self.field.clean, '1 1')

    def test_clean_too_many_commas(self):
        self.assertRaises(ValidationError, self.field.clean, ',,')


class ModelMapperTest(UnitTestCase):
    def test_general(self):
        class Dummy(models.Model):
            boolean = models.BooleanField()
            null_boolean = models.NullBooleanField()
            char = models.CharField(max_length=128)
            integer = models.IntegerField(blank=True, null=True)

        data = {
            'boolean': 'on',
            'null_boolean': 'on',
            'char': 'char',
            'integer': '3'
        }
        dummy = ModelMapper(Dummy, data).map().create()

        self.assertIsInstance(dummy, Dummy)
        self.assertEquals(dummy.boolean, True)
        self.assertEquals(dummy.null_boolean, True)
        self.assertEquals(dummy.char, 'char')
        self.assertEquals(dummy.integer, 3)

    def test_empty(self):
        # TODO warning RuntimeWarning: Model 'moonsheep.dummy' was already registered.
        # Reloading models is not advised as it can lead to inconsistencies, most notably with related models.
        # make dummy a proper test model
        class Dummy(models.Model):
            boolean = models.BooleanField()
            null_boolean = models.NullBooleanField()
            char = models.CharField(max_length=128)
            integer = models.IntegerField(blank=True, null=True)

        data = {}
        ModelMapper(Dummy, data).map().create()

    def test_char_filled(self):
        class Dummy(models.Model):
            char = models.CharField(max_length=128)

        dummy = ModelMapper(Dummy, {'char': 'filled'}).map().create()
        self.assertEquals(dummy.char, 'filled')
        self.assertIsInstance(dummy, Dummy)

    def test_char_empty(self):
        class Dummy(models.Model):
            char = models.CharField(max_length=128)

        dummy = ModelMapper(Dummy, {'char': ''}).map().create()
        self.assertEquals(dummy.char, '')
        self.assertIsInstance(dummy, Dummy)

    def test_char_missing(self):
        class Dummy(models.Model):
            char = models.CharField(max_length=128)

        dummy = ModelMapper(Dummy, {}).map().create()
        self.assertEquals(dummy.char, '')
        self.assertIsInstance(dummy, Dummy)

    def test_rename_one(self):
        class Dummy(models.Model):
            char = models.CharField(max_length=128)

        dummy = ModelMapper(Dummy, {'some_param': 'value'}).map_one('char', 'some_param').create()
        self.assertEquals(dummy.char, 'value')
        self.assertIsInstance(dummy, Dummy)

    def test_rename_many(self):
        class Dummy(models.Model):
            char = models.CharField(max_length=128)
            integer = models.IntegerField(blank=True, null=True)

        dummy = ModelMapper(Dummy, {
            'some_param': 'value',
            'other_param': '4'
        }).map(rename={
            'char': 'some_param',
            'integer': 'other_param'
        }).create()

        self.assertEquals(dummy.char, 'value')
        self.assertEquals(dummy.integer, 4)
        self.assertIsInstance(dummy, Dummy)

    def test_overwrite(self):
        class Dummy(models.Model):
            char = models.CharField(max_length=128)

        m = ModelMapper(Dummy, {'char': 'choose other', 'other': 'end-value'})
        m.map_one('char', 'other')

        dummy = m.create()
        self.assertEquals(dummy.char, 'end-value')
        self.assertIsInstance(dummy, Dummy)

    def test_dont_overwrite_if_empty(self):
        class Dummy(models.Model):
            char = models.CharField(max_length=128)

        m = ModelMapper(Dummy, {'char': 'choose other', 'other': ''}).map()
        m.map_one('char', 'other')

        dummy = m.create()
        self.assertEquals(dummy.char, 'choose other')
        self.assertIsInstance(dummy, Dummy)

    def test_create_with_extras(self):
        class Dummy(models.Model):
            char = models.CharField(max_length=128)
            integer = models.IntegerField()

        dummy = ModelMapper(Dummy, {'char': 'value'}).map().create(char='new value', integer=3)
        self.assertEquals(dummy.char, 'new value')
        self.assertEquals(dummy.integer, 3)
        self.assertIsInstance(dummy, Dummy)
