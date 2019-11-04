import re
import urllib
import urllib.parse
from typing import Sequence, List, Pattern

import requests
from django.core.management import BaseCommand
from django.http import QueryDict

from moonsheep.importers.core import IDocumentImporter
from moonsheep.plugins import Plugin, implements


# TODO What a pity we can't base this plugin on ABC form of IDocumentImporter (some metaclass conflicts happen), maybe we should manage plugins and interfaces ourselves?
class HttpDocumentImporter(Plugin):
    # TODO, this should not be singleton, this should be configurable plugin
    implements(IDocumentImporter)

    # View - template
    template_name = "importers/http.html"

    # Default label, may be overridden in settings TODO
    def __str__(self):
        # TODO modify if there are several
        return 'from HTTP listing'

    # TODO won't importers need extra API calls/urls? ie. to load subdirs?

    def __init__(self, name):
        self.name = name

    @staticmethod
    def listdir(html_contents):
        """
        Returns list of entries (files & dir) in a given html file
        :param html_contents:
        :return:
        """
        regexp = r'<a\s+href="([^"]+)"\s*>([^<]+)<'
        return [g[0] for g in re.findall(regexp, html_contents) if not g[1].startswith('..')]

    def find_urls(self, host: str, pattern: str, paths: List[str], log=None) -> List[str]:
        path_queue = [urllib.parse.urljoin(host, path) for path in paths]

        if pattern:
            pattern_re: Pattern = re.compile(pattern.replace('.', '\\.').replace('*', '.*'))

        while path_queue:
            path = path_queue.pop()

            # if directory
            if path.endswith('/'):
                if log:
                    log(f"Downloading {path}")

                response = requests.get(path)
                # TODO test response.status_code
                for entry in HttpDocumentImporter.listdir(response.text):
                    if not (entry.startswith('http://') or entry.startswith('https://')):
                        entry = path + entry

                    if entry.endswith('/'):  # dir
                        path_queue.append(entry)

                    elif not pattern or pattern_re.match(entry):  # file
                        yield entry

            elif not pattern or pattern_re.match(path):
                yield path


# Initialize and activate
# TODO name should be taken from config
h1 = HttpDocumentImporter("http-1")
h1.activate()
