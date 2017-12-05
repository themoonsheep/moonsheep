from django.test import TestCase
from unittest import TestCase as UnitTestCase

from .tasks import AbstractTask
from .exceptions import PresenterNotDefined


class PresenterTests(UnitTestCase):

    def get_presenter(self, url):
        """
        Choosing how to render document to transcribe.

        The default behaviour is to check:
        1. Known url templates for YouTube, Vimeo, etc.
        2. Url file extension
        """

    def _test_presenter(self, url, template, url_out=None):
        t = AbstractTask(url)
        p = t.get_presenter()

        if url_out is None:
            url_out = url

        self.assertDictEqual(p, {
            'template': 'presenters/{}.html'.format(template),
            'url': url_out
        })

    def test_youtube(self):
        self._test_presenter('https://www.youtube.com/watch?v=qEI1_oGPQr0', 'youtube')

    def test_youtube_not_valid(self):
        t = AbstractTask('https://www.youtube.com/')

        with self.assertRaises(PresenterNotDefined):
            t.get_presenter()

    def test_vimeo(self):
        self._test_presenter('https://vimeo.com/201762745', 'vimeo')

    def test_vimeo_not_valid(self):
        t = AbstractTask('https://vimeo.com/')

        with self.assertRaises(PresenterNotDefined):
            t.get_presenter()

    def test_extension_pdf(self):
        self._test_presenter('http://domain.pl/document.pdf', 'pdf')

    def test_extension_png(self):
        self._test_presenter('http://domain.pl/document.png', 'image')

    def test_extension_jpg(self):
        self._test_presenter('http://domain.pl/document.jpg', 'image')

    def test_extension_jpeg(self):
        self._test_presenter('http://domain.pl/document.jpeg', 'image')

    def test_missing_presenter(self):
        t = AbstractTask('http://domain.pl/document.whatthehell')

        with self.assertRaises(PresenterNotDefined):
            t.get_presenter()
