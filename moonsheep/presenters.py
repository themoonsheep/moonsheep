# -*- coding: utf-8 -*-
from django.views.generic import TemplateView


class PDFPresenter(TemplateView):
    template_name = 'presenters/pdf_presenter.html'


class ImagePresenter(TemplateView):
    template_name = 'presenters/image_presenter.html'


class VideoPresenter(TemplateView):
    template_name = 'presenters/video_presenter.html'
