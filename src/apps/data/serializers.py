from rest_framework import serializers

from apps.paywall.models import Payment, Subscription


class PaymentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Payment
        exclude = [
            'data',
            'data_loaded',
            'pa_gateway',
            'partner',
            'payment_profile',
            'subscription',
        ]


class SubscriptionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Subscription
        exclude = [
            'data',
            'data_loaded',
        ]
