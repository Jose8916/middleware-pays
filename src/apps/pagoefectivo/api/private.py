from django.conf.urls import url

from .views.pagoefectivo_notification import ApiPagoEfectivoNotificationView
from .views.cip_creation import ApiCIPCreationView

urlpatterns = [
    # SERVERLESS APIs
    url(
        r'^cip_creation/$',
        ApiCIPCreationView.as_view(),
        name='cip_creation'
    ),
    url(
        r'^payment/$',
        ApiPagoEfectivoNotificationView.as_view(),
        name='subscription_start'
    ),

]
