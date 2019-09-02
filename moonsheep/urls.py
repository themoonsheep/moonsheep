"""moonsheep URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.urls import path
from django.views.generic import TemplateView

from .views import NewTaskFormView, TaskListView, ManualVerificationView, DocumentListView

urlpatterns = [
    path('', TemplateView.as_view(template_name='moonsheep/campaign.html'), name='ms-admin'),  # TODO cleaner namespace here instead of ms-admin url name
    path('documents', DocumentListView.as_view(), name='documents'),
    path('documents/import-http', TemplateView.as_view(template_name='moonsheep/documents.html'), name='documents-import-http'),
    path('old', TemplateView.as_view(template_name = 'views/admin.html')),
    url(r'^new-task/$', NewTaskFormView.as_view(), name='ms-new-task'),
    url(r'^tasks/$', TaskListView.as_view(), name='ms-tasks'),
    url(r'^manual-verification/$', ManualVerificationView.as_view(), name='ms-manual-verification'),
]
