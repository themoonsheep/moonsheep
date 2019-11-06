import datetime
import decimal
import uuid
from unittest import TestCase

from moonsheep.models import JSONField


# TODO make it pass
class JSONFieldTest(TestCase):
    f = JSONField()

    def assertStores(self, value):
        json = self.f.get_db_prep_save({'value': value})
        value_after = self.f.from_db_value(json)['value']

        self.assertEqual(value, value_after)
        self.assertEqual(value.__class__, value_after.__class__)

    def test_datetime_tz(self):
        self.assertStores(datetime.datetime.now(tz=datetime.timezone.utc))

    def test_datetime(self):
        self.assertStores(datetime.datetime.now())

    def test_date(self):
        self.assertStores(datetime.date.today())

    def test_time_tz(self):
        self.assertStores(datetime.time(12, 10, 30, tzinfo=datetime.timezone.utc))

    def test_time(self):
        self.assertStores(datetime.time(12, 10, 30))

    def test_timedelta(self):
        self.assertStores(datetime.timedelta(weeks=40, days=84, hours=23, minutes=50, seconds=600))

    def test_decimal(self):
        self.assertStores(decimal.Decimal('3.14'))

    def test_UUID(self):
        self.assertStores(uuid.UUID('{12345678-1234-5678-1234-567812345678}'))
        self.assertStores(uuid.UUID(bytes='\x12\x34\x56\x66' * 4))
