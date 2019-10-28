"""
Support for interfaces that can be implemented by multiple services.

Example: DocumentImporter interface that can allow multiple implementations (HTTP, FTP, S3, ..)

Reusing PyUtilib Component Arcitecture (PCA), which is documented at https://github.com/PyUtilib/pyutilib/blob/master/doc/plugin/pca.pdf
Thanks to CKAN project for highlighting this lib.
CKAN wraps it up offering:
- dynamic discovery of plugins and entrypoints via
  - https://setuptools.readthedocs.io/en/latest/setuptools.html#dynamic-discovery-of-services-and-plugins
  - https://github.com/ckan/ckan/blob/master/setup.py#L95

Cheatsheet: To implement an interface subclass `Plugin` and use `implements` directive.
Copy method stubs from interface and implement them.

  class HttpDocumentImporter(Plugin):
    implements(IDocumentImporter)
"""
from pyutilib.component.core import Interface as _pca_Interface, ExtensionPoint as PluginImplementations, \
    implements, Plugin, SingletonPlugin, PluginError
from inspect import isclass

__all__ = [
    'PluginImplementations', 'implements', 'Interface',
    'Plugin', 'SingletonPlugin', 'PluginError'
]


# TODO pack it in another file and add MIT license
class Interface(_pca_Interface):
    u'''Base class for custom interfaces.
    Marker base class for extension point interfaces.  This class
    is not intended to be instantiated.  Instead, the declaration
    of subclasses of Interface are recorded, and these
    classes are used to define extension points.
    '''

    @classmethod
    def provided_by(cls, instance):
        u'''Check that the object is an instance of the class that implements
        the interface.
        '''
        return cls.implemented_by(instance.__class__)

    @classmethod
    def implemented_by(cls, other):
        u'''Check whether the class implements the current interface.
        '''
        if not isclass(other):
            raise TypeError(u'Class expected', other)
        try:
            return cls in other._implements
        except AttributeError:
            return False

    @classmethod
    def implementations(cls):
        return PluginImplementations(cls)
