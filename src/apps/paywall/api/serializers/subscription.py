from rest_framework import serializers
from apps.paywall.models import Subscription
from datetime import datetime


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serialize Subscription."""

    class Meta:
        model = Subscription
        fields = [
            'id',
        ]
        # fields = [
        #     'id',
        #     'subscription_arc_id',
        #     'subscription_created',
        #     'subscription_method',
        #     'client_created_on',
        #     'client_name',
        #     'client_lastname_father',
        #     'client_lastname_mother',
        #     'client_doc_type',
        #     'client_doc_num',
        #     'client_phone',
        #     'plan_code',
        #     'plan_name',
        #     'product_name',
        #     'rate_total',
        #     'legal_tyc',
        #     'subscription_date_renovation',
        #     'subscription_cancellation_date',
        #     'motive_anulled',
        #     'ubigeo',
        #     'subscription_state',
        #     'brand_email',
        #     'last_updated',
        #     'uuid',
        #     'siebel_entecode',
        #     'siebel_delivery',
        #     'brand_code',
        #     'brand_name',
        #     'payment_date_update',
        #     'payment_amount',
        #     'payment_method',
        #     'arc_orden',
        #     'arc_sku',
        #     'arc_price_code',
        # ]
