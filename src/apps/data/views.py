from rest_framework import mixins, routers
from rest_framework.pagination import PageNumberPagination
from rest_framework.viewsets import GenericViewSet

from .serializers import PaymentSerializer, SubscriptionSerializer
from apps.paywall.models import Payment, Subscription


class LargeResultsSetPagination(PageNumberPagination):
    page_size = 1000
    page_size_query_param = 'page_size'
    max_page_size = 10000


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ViewSets define the view behavior.
class PaymentViewSet(mixins.ListModelMixin, GenericViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    pagination_class = StandardResultsSetPagination


# ViewSets define the view behavior.
class SubscriptionViewSet(mixins.ListModelMixin, GenericViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    pagination_class = StandardResultsSetPagination


# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r'payments', PaymentViewSet)
router.register(r'subscriptions', SubscriptionViewSet)
