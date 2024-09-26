from django.urls import path

from .views import (
    SubsctiptionPrintListView, SubsctiptionPrintDetailView,
    SubsctiptionDigitalListView, SubsctiptionDigitalDetailView,
)


urlpatterns = [
    # API
    path(
        'api/v1/subscriptions/print',
        SubsctiptionPrintListView.as_view(),
        name='subscription_print_list',
    ),
    path(
        'api/v1/subscription-print/<int:subscription_id>/details',
        SubsctiptionPrintDetailView.as_view(),
        name='subscription_print_detail',
    ),
    path(
        'api/v1/subscriptions/digital',
        SubsctiptionDigitalListView.as_view(),
        name='subscription_digital_list',
    ),
    path(
        'api/v1/subscription-digital/<int:subscription_id>/details',
        SubsctiptionDigitalDetailView.as_view(),
        name='subscription_digital_detail',
    ),
]
