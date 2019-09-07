from pyutilib.component.core import Plugin, implements

from moonsheep.plugins import IDocumentImporter


class HttpDocumentImporter(Plugin):
    implements(IDocumentImporter)

    def import_document():
        pass
