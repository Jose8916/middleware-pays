from rest_framework import generics

from django.db.models import Q
from apps.paywall.api.views.pagination import LargeResultsSetPagination, StandardResultsSetPagination
from apps.paywall.models import Subscription
import json


class SubscriptionDwhApiView(generics.ListAPIView):
    # serializer_class = SubscriptionSerializer
    pagination_class = LargeResultsSetPagination
    pagination_class.page_size = 50

    def get_date_range(self, request):
        body = request.body.decode('utf-8')
        received_json_data = json.loads(body)
        date_start = received_json_data.get('date_start', '')
        date_end = received_json_data.get('date_end', '')

        return (
            self.start_date(date_start),
            self.end_date(date_end) + timedelta(days=1)
        )

    def get_queryset(self):
        date_range = self.get_date_range(request=self.request)

        return Subscription.objects.filter(
            Q(created__range=date_range) |
            Q(last_updated__range=date_range)
        )
