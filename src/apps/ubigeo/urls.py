from django.conf.urls import url
from .views import AddressGetDistrictsView

urlpatterns = [
    url(r'^get-districts/(?P<code>.*)/$',
        AddressGetDistrictsView.as_view(),
        name='payment_address_districts'),
]
