import json

from django.core.exceptions import ValidationError
from django.db import models
from django.http.request import QueryDict
from django.test import TestCase as DjangoTestCase, Client, override_settings

from unittest import TestCase as UnitTestCase
from unittest.mock import Mock, MagicMock, patch, sentinel, call

from moonsheep.exceptions import PresenterNotDefined
from moonsheep.forms import MultipleRangeField
from moonsheep.models import ModelMapper
from moonsheep.tasks import AbstractTask
from moonsheep.tests import DummyTask
from moonsheep.verifiers import equals, OrderedListVerifier
from moonsheep.views import unpack_post


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

        # but QuueryDict.dict() don't (it just return the last value)
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
        task = AbstractTask.create_task_instance('moonsheep.tests.DummyTask', info={'url': 'https://bla.pl'})
        self.assertEquals(task.__class__, DummyTask)

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

    def test_single_number(self):
        self.assertEquals(self.field.clean('1'), ['1'])

    def test_comma_separated_numbers(self):
        self.assertEquals(self.field.clean('1,2,4'), ['1', '2', '4'])

    def test_dash_separated_numbers(self):
        self.assertEquals(self.field.clean('1-4'), ['1', '2', '3', '4'])

    def test_various_type_number_ranges(self):
        self.assertEquals(self.field.clean('1-4,5-6'), ['1', '2', '3', '4', '5', '6'])

    def test_comma_separated_numbers_with_prefixes(self):
        self.assertEquals(self.field.clean('abc,abc1'), ['abc', 'abc1'])

    # def test_dash_separated_numbers_with_prefixes(self):
    #     self.assertEquals(self.field.clean('A1-A3'), ['A1', 'A2', 'A3'])

    # def test_various_type_ranges(self):
    #     self.assertEquals(self.field.clean('a1-a2,1-3'), ['a1', 'a2', '1', '2', '3'])

    def test_useless_range(self):
        self.assertEquals(self.field.clean('1-1'), ['1'])

    def test_warning_range(self):
        self.assertEquals(self.field.clean('3-5,4'), ['3', '4', '5'])

    def test_reverse_range_error(self):
        self.assertRaises(ValidationError, self.field.clean, '5-3')

    def test_wrong_range_format_error(self):
        self.assertRaises(ValidationError, self.field.clean, '1-3-5')

    # def test_wrong_prefix_format_error(self):
    #     self.assertRaises(ValidationError, self.field.clean, '1A-1C')

    def test_clean_spaces(self):
        self.assertEquals(self.field.clean(' 1 -   3'), ['1', '2', '3'])

    def test_clean_wrong_spaces(self):
        self.assertRaises(ValidationError, self.field.clean, '1 1')


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
