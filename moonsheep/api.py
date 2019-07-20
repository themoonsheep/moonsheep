from rest_framework import routers, serializers, viewsets
from django.apps import apps


class AppApi:
    def __init__(self, app_label):
        self.app_label = app_label
        self.router = routers.DefaultRouter()

        for slug, klazz in apps.get_app_config(app_label).models.items():
            class Meta:
                model = klazz
                fields = '__all__'

            serializer_cls = type(klazz.__name__ + "SeralizerDefault", (serializers.ModelSerializer,), dict(
                Meta=Meta
            ))

            viewset_cls = type(klazz.__name__ + "ViewSetDefault", (viewsets.ModelViewSet,), dict(
                queryset=klazz.objects.all(),
                serializer_class=serializer_cls
            ))

            klazz.objects
            self.router.register(slug, viewset_cls)

    @property
    def urls(self):
        return self.router.urls, 'app-api', 'api-' + self.app_label

