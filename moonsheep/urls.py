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

from moonsheep.importers.importers import ImporterView
from .views import ManualVerificationView, DocumentListView, CampaignView

urlpatterns = [
    path('', CampaignView.as_view(), name='ms-admin'),  # TODO cleaner namespace here instead of ms-admin url name? Or? Django docs somewhere said that's the way to prefix apps, check it!
    path('documents', DocumentListView.as_view(), name='documents'),
    path('documents/import/<slug:importer_id>', ImporterView.as_view(), name='importer'),

    path('manual-verification/<int:task_id>', ManualVerificationView.as_view(), name='ms-manual-verification'),
]
