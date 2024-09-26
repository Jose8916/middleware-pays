import json

from rest_framework.permissions import AllowAny
from rest_framework import generics

from apps.paywall.api.views.pagination import LargeResultsSetPagination, StandardResultsSetPagination
from apps.paywall.models import Plan
from apps.paywall.api.serializers.plan import PlansSerializer


class PlanApiView(generics.ListAPIView):
    serializer_class = PlansSerializer
    pagination_class = LargeResultsSetPagination
    pagination_class.page_size = 50

    def get_queryset(self):
        return Plan.objects.filter(partner__isnull=False, product__isnull=False)
