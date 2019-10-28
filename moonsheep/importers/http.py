from typing import Sequence

from django.http import QueryDict

from moonsheep.importers.core import IDocumentImporter, DocumentSaver
from moonsheep.plugins import Plugin, implements


# TODO What a pity we can't base this plugin on ABC form of IDocumentImporter (some metaclass conflicts happen), maybe we should manage plugins and interfaces ourselves?
class HttpDocumentImporter(Plugin):
    # TODO, this should not be singleton, this should be configurable plugin
    implements(IDocumentImporter)

    def import_documents(self, params: QueryDict, doc_saver: DocumentSaver) -> Sequence[str]:
        return []

    # View - template
    template_name = "importers/http.html"

    # Default label, may be overridden in settings TODO
    def __str__(self):
        # TODO modify if there are several
        return 'from HTTP listing'

    # TODO won't importers need extra API calls/urls? ie. to load subdirs?

    def __init__(self, name):
        self.name = name


# Initialize and activate
# TODO name should be taken from config
h1 = HttpDocumentImporter("http-1")
h1.activate()
