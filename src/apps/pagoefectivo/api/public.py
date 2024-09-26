"""
from django.conf.urls import url

from .views.cip_creation import ApiCIPCreationView

urlpatterns = [
    # PUBLIC APIs
    url(
        r'^cip_creation/$',
        ApiCIPCreationView.as_view(),
        name='cip_creation'
    ),
]
"""