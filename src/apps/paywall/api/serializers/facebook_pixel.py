from rest_framework import serializers
from apps.paywall.models import Plan, Campaign
from datetime import datetime


class FacebookPixelSerializer(serializers.Serializer):
    """Serialize FacebookPixel."""
    subscription_id = serializers.CharField(
        max_length=200
    )
    event_name = serializers.CharField(
        max_length=200,
        required=False,
    )
    subscription_value = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
    )
    currency = serializers.CharField(
        max_length=200,
        required=False,
    )
    is_subscriber = serializers.BooleanField(
        required=False,
    )
