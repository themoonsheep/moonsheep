import sys

from django.core.management.base import BaseCommand

from moonsheep.exporters import *


class Command(BaseCommand):
    help = 'Exports data'

    def add_arguments(self, parser):
        parser.add_argument('app_label', type=str, metavar='app_label', help='Specify which application\'s data should be exported')
        parser.add_argument('format', type=str, metavar='format', help='Format: xlsx')
        parser.add_argument('-o', dest='output', type=str, help="Save export to output file [if nothing given will output to stdout")

    def handle(self, *args, **options):
        app_label = options['app_label']

        # TODO default label
        # TODO discovery and export in the admin

        fmt = options['format']
        output = options.get('output', None)

        if output is None:
            output = sys.stdout

        exporter_cls = Exporter.implementations().get(fmt, None)
        if exporter_cls is None or fmt == 'appapi':
            raise NotImplementedError(f"There is no '{fmt}' exporter defined")

        exporter_cls(app_label).export(output)
