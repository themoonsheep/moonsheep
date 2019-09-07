"""
Support for interfaces that can be implemented by multiple services.

Example: DocumentImporter interface that can allow multiple implementations (HTTP, FTP, S3, ..)

Reusing PyUtilib Component Arcitecture (PCA), which is documented at https://github.com/PyUtilib/pyutilib/blob/master/doc/plugin/pca.pdf
Thanks to CKAN project for highlighting this lib.

Cheatsheet: To implement an interface subclass `Plugin` and use `implements` directive.
Copy method stubs from interface and implement them.

  class HttpDocumentImporter(Plugin):
    implements(IDocumentImporter)
"""

from pyutilib.component.core import *


class IDocumentImporter(Interface):
    def import_document():
        pass

# TODO we need better importing mechanism, should Moonsheep load all /importers /plugins dir?
# especially that relates to custom plugins implemented in projects based on Moonsheep
# for now we go with
from .importers import *
