from django.conf.urls import url

from .views import ApiSiebelCancellationsView


urlpatterns = [
    # API
    url(
        r'^cancellations/$',
        ApiSiebelCancellationsView.as_view(),
        name='api_siebel_cancellations'
    ),
]
