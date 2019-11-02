from django.core.management.base import BaseCommand, CommandError

from moonsheep.importers.http import HttpDocumentImporter


class Command(BaseCommand):
    help = 'Imports documents published on http server with Index List enabled'

    def add_arguments(self, parser):
        parser.add_argument('paths', type=str, nargs='+', metavar='path', help='Paths to be imported')
#        parser.add_argument('-W', dest='ask_for_password', type=bool, nargs='?', default=False, const=True,
                            help='Ask for password instead of specifying it on the command line')
        parser.add_argument('--host', dest='host', type=str, help="Host to be used if multiple paths are provided")
        parser.add_argument('-f', dest='pattern', type=str,
                            help="*-wildcarded pattern of the file names to be included, ie. -f *.pdf")
        parser.add_argument('--dry-run', dest='dry_run', type=bool, nargs='?', default=False, const=True,
                            help='Dry run to see what would get imported without actually importing it')

    def handle(self, *args, **options):
        host = options['host']
        # TODO if not host
        paths = options['paths']
        # TODO dry_run

        for path in HttpDocumentImporter.find_urls(host=host, paths=paths, pattern=options['pattern']):
            print(f"\t{path}")
            # TODO actually import them into Moonsheep unless dry_run