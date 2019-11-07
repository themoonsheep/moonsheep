from abc import abstractmethod
from typing import Sequence

from django.db import IntegrityError
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.urls import reverse
from django.views.generic.base import TemplateView

from moonsheep.models import Task
from moonsheep.plugins import PluginError, Interface
from moonsheep.registry import TASK_TYPES
from moonsheep.settings import MOONSHEEP


class IDocumentImporter(Interface):
    @abstractmethod
    def find_urls(self, **options) -> Sequence[str]:
        """
        Returns a list of urls to be imported as documents
        :param options: Configuration options dependent on importer
        :return:
        """
        pass


# TODO move it to BaseDocumentImporter once it is created
def import_documents(importer, tasks_to_create=[], **options):
    if not tasks_to_create:
        tasks_to_create = MOONSHEEP['DOCUMENT_INITIAL_TASKS']

    # Create domain object based on document
    model = MOONSHEEP['DOCUMENT_MODEL']
    model_label = model._meta.label

    dry_run = options.pop('dry_run', False)

    # TODO options should be passed here or during importer construction?
    # when do we have an instance of importer, when a class available?
    for url in importer.find_urls(**options):
        print(f"Creating {model_label}[url={url}] with tasks {', '.join(tasks_to_create)}")
        if dry_run:
            continue

        # TODO can we create/insert many at once?
        # We expect that the DOCUMENT_MODEL should have url field
        # TODO one might not want to create object instantly, but only after task is cross-checked
        # in the domain db we rather want to have only filled in data
        # maybe this should be steered by on_document_create hook that might be implemented (and also customized)
        # TODO doc Document should have url field, and no other field should be required on the model
        try:
            d = model.objects.create(**{'url': url})
        except IntegrityError as e:
            if str(e).startswith("UNIQUE constraint failed"):
                print("\tSkipping url as duplicate")
                continue

            raise e

        # Create needed tasks
        for t in tasks_to_create:
            Task.objects.create(**{
                'type': t,
                'params': {
                    'url': url,
                },
                'doc_id': d.id,  # pointer to document object, might be helpful for debugging
                'priority': 1.0,  # TODO compute when setting https://github.com/themoonsheep/moonsheep/issues/50
            })


class ImporterView(TemplateView):
    """
    Shows an importer interface

    Practically that means rendering:
    - a form wrapping up importer's template
    - multiselect with tasks that should be created based on imported documents
    - submit button

    Parameters selected in the form are passed back to importer that can do some extra processing
    and should return list of documents to be imported.
    """

    template_name = "importers/_wrapper.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        importer = self.get_importer()

        context.update({
            'label': str(importer),
            'template_name': importer.template_name,
            'all_tasks': TASK_TYPES,
            'tasks_to_create': MOONSHEEP['DOCUMENT_INITIAL_TASKS'],
        })
        return context

    def get_importer(self) -> IDocumentImporter:
        imp = IDocumentImporter.implementations().service(key=self.kwargs['importer_id'])
        if imp is None:
            raise PluginError("Could not find importer with id '%s'" % self.kwargs['importer_id'])
        return imp

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        importer = self.get_importer()

        tasks_to_create = MOONSHEEP['DOCUMENT_INITIAL_TASKS']
        if not tasks_to_create:
            tasks_to_create = request.POST['tasks_to_create']

        if not tasks_to_create:
            # TODO re-render the form with err message
            raise HttpResponseBadRequest("tasks_to_create should be provided")

        import_documents(importer, tasks_to_create, request.POST)
        # TODO error handling, retry?
        # TODO progress screen

        # TODO flash message was successful
        return HttpResponseRedirect(reverse('documents'))

        # request.POST
        # if form.is_valid():
        #     # <process form cleaned data>
        #     return HttpResponseRedirect('/success/')
        #
        # return render(request, self.template_name, {'form': form})
