from django.core.management.base import BaseCommand, CommandError

from moonsheep.importers.http import HttpDocumentImporter
from moonsheep.importers.importers import import_documents


class Command(BaseCommand):
    help = 'Imports documents published on http server with Index List enabled'

    def add_arguments(self, parser):
        parser.add_argument('paths', type=str, nargs='+', metavar='path', help='Paths to be imported')
        # parser.add_argument('-W', dest='ask_for_password', type=bool, nargs='?', default=False, const=True,
        #   help = 'Ask for password instead of specifying it on the command line')
        parser.add_argument('--host', dest='host', type=str, help="Host to be used if multiple paths are provided")
        parser.add_argument('-f', dest='pattern', type=str,
                            help="*-wildcarded pattern of the file names to be included, ie. -f *.pdf")
        parser.add_argument('--dry-run', dest='dry_run', type=bool, nargs='?', default=False, const=True,
                            help='Dry run to see what would get imported without actually importing it')

    def handle(self, *args, **options):
        host = options['host']
        paths = options['paths']

        # TODO remove; opora docs: https://opora.engnroom.org/filerepo/2016/%d0%86_%d0%9a%d0%92%d0%90%d0%a0%d0%a2%d0%90%d0%9b_%d0%a1%d0%9a%d0%90%d0%9d/
        importer = HttpDocumentImporter("http")
        import_documents(importer, host=host, paths=paths, pattern=options['pattern'], dry_run=options['dry_run'])
