import os
import unittest

from moonsheep.importers import HttpDocumentImporter
from django.core import management

class TestHttpImporter(unittest.TestCase):
    @staticmethod
    def load_file(path: str):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
        with open(path, 'r') as content_file:
            return content_file.read()

    def test_load_dirs(self):
        print(__file__)
        print(os.path.abspath(__file__))
        content = self.load_file('http_listings/index_dirs.html')
        entries = HttpDocumentImporter.listdir(content)

        self.assertIn("http://debian.mirror.ac.za/debian/pool/main/t/t-code/", entries)
        self.assertIn("http://debian.mirror.ac.za/debian/pool/main/t/tzsetup/", entries)
        self.assertIn("http://debian.mirror.ac.za/debian/pool/main/t/tryton-modules-stock-supply-production/", entries)

        self.assertNotIn("http://debian.mirror.ac.za/debian/pool/main/", entries, "Parent dir should not be returned")
        self.assertNotIn("http://debian.mirror.ac.za/debian/pool/main", entries, "Parent dir should not be returned")
        self.assertNotIn("http://debian.mirror.ac.za/debian/pool/main/t/", entries,
                         "Current dir should not be returned")
        self.assertNotIn("http://debian.mirror.ac.za/debian/pool/main/t", entries, "Current dir should not be returned")

    def load_files(self):
        content = self.load_file('http_listings/index_files.html')
        entries = HttpDocumentImporter.listdir(content)

        # Encoded url
        self.assertIn(
            "http://debian.mirror.ac.za/debian/pool/main/t/tasksel/task-albanian-desktop_3.31%2Bdeb8u1_all.deb",
            entries)
        self.assertIn("http://debian.mirror.ac.za/debian/pool/main/t/tasksel/tasksel_3.56_all.deb", entries)

        self.assertNotIn("http://debian.mirror.ac.za/debian/pool/main/t/", entries, "Parent dir should not be returned")
        self.assertNotIn("http://debian.mirror.ac.za/debian/pool/main/t", entries, "Parent dir should not be returned")
        self.assertNotIn("http://debian.mirror.ac.za/debian/pool/main/t/taskel", entries,
                         "Current dir should not be returned")
        self.assertNotIn("http://debian.mirror.ac.za/debian/pool/main/t/taskel", entries,
                         "Current dir should not be returned")


# class TestHttpImporterCommand(unittest.TestCase):
#     # TODO @patch and assert HttpDocumentImporter.find_urls
#     def host_with_multiple_paths(self):
#         management.call_command('moonsheep_import_http', '-W -h http://user@host/root dir1 dir2/file1')
#         # TODO then what?
#
#
#     def one_path(self):
#         management.call_command('moonsheep_import_http', 'http://user@host/root/dir1')
#
#
#     def file_pattern(self):
#         management.call_command('moonsheep_import_http', 'http://user@host/root/dir1 -f *.pdf')



