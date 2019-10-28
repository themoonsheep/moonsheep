from abc import abstractmethod
from typing import Sequence

from django.http import HttpResponseBadRequest, HttpResponseRedirect, QueryDict
from django.urls import reverse
from django.views.generic.base import TemplateView

from moonsheep.models import Task
from moonsheep.plugins import PluginError, Interface
from moonsheep.registry import TASK_TYPES
from moonsheep.settings import MOONSHEEP


class DocumentSaver:
    def __init__(self, tasks_to_create):
        self.tasks_to_create = tasks_to_create

    def add_documents(self, urls) -> None:
        """
        Allow to add documents in batches

        :param urls: Urls to be added
        """

        for url in urls:
            # Create domain object based on document
            model = MOONSHEEP['DOCUMENT_MODEL']

            # TODO can we create/insert many at once?
            # We expect that the DOCUMENT_MODEL should have url field
            d = model.objects.create({'url': url})

            # Create needed tasks
            for t in self.tasks_to_create:
                Task.objects.create({
                    'type': t,
                    'params': {
                        'url': url
                    },
                    'priority': 1.0,  # TODO compute when setting https://github.com/themoonsheep/moonsheep/issues/50
                })


class IDocumentImporter(Interface):
    @abstractmethod
    def import_documents(self, params: QueryDict, doc_saver: DocumentSaver) -> Sequence[str]:
        pass


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

        # TODO doc_saver
        importer.import_documents(request.POST, DocumentSaver(tasks_to_create))
        # TODO error handling
        # TODO progress screen

        # TODO flash message was successful
        return HttpResponseRedirect(reverse('documents'))

        # request.POST
        # if form.is_valid():
        #     # <process form cleaned data>
        #     return HttpResponseRedirect('/success/')
        #
        # return render(request, self.template_name, {'form': form})
