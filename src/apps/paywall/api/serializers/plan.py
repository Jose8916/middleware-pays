from rest_framework import serializers
from apps.paywall.models import Plan, Campaign
from datetime import datetime


class PlansSerializer(serializers.ModelSerializer):
    """Serialize Plan."""
    portal_code = serializers.SerializerMethodField('get_portal_code')
    arc_sku = serializers.SerializerMethodField('get_arc_sku')
    portal = serializers.SerializerMethodField('get_portal')
    state_campaign = serializers.SerializerMethodField('get_state_campaign')

    class Meta:
        model = Plan
        fields = ['plan_name', 'arc_pricecode', 'arc_sku', 'portal', 'portal_code', 'state_campaign']

    def get_portal_code(self, obj):
        try:
            return obj.partner.partner_code
        except:
            return ''

    def get_arc_sku(self, obj):
        try:
            return obj.product.arc_sku
        except:
            return ''

    def get_portal(self, obj):
        try:
            return obj.partner.partner_name
        except:
            return ''

    def get_state_campaign(self, obj):
        try:
            obj_campaign = Campaign.objects.filter(
                plans=obj).order_by('id').last()
            return obj_campaign.is_active
        except:
            return False
        #try:
        # campaigns = Campaign.objects.all()
        # for campaign in campaigns:
        #
        #     list_products = campaign.data.get('products', '')
        #     for product in list_products:
        #         if product.get('sku', '') == obj.product.arc_sku:
        #             return campaign.is_active
        # return False
        # except:
        #     return False


class Comment(object):
    def __init__(self, email, content):
        self.email = email
        self.content = content


class CommentSerializer(serializers.Serializer):
    email = serializers.EmailField()
    content = serializers.CharField(max_length=200)

