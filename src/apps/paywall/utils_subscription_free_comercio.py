from datetime import datetime, timedelta

from django.utils.timezone import get_default_timezone
from apps.paywall.models import UserOffer, SubscriberPrinted


class UsersSubscriptionFree(object):

    def __init__(self, subscription):
        try:
            self.product = subscription.plan.product
        except Exception:
            self.product = ''
        except SystemExit:
            self.product = ''

        try:
            self.subscription = subscription
        except Exception:
            self.subscription = ''
        except SystemExit:
            self.subscription = ''

        self.brand = subscription.plan.product.partner
        self.profile = self.get_profile(subscription.arc_user)

    def get_profile(self, arc_user):
        try:
            user_offer = UserOffer.objects.filter(arc_user=arc_user, offer='full_subscriber').last()
            if user_offer:
                suscriptor = SubscriberPrinted.objects.get(us_docnumber=user_offer.dni)
                return suscriptor
            else:
                return ''
        except Exception:
            return ''

    def get_user_name(self):
        try:

            if self.profile.us_name:
                return self.profile.us_name
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_last_name(self):
        
        try:
            if self.profile.us_lastname:
                apellidos = self.profile.us_lastname.split(' ')
                return apellidos[0]
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_last_name_mother(self):
        try:
            if self.profile.us_lastname:
                apellidos = self.profile.us_lastname.split(' ')
                return apellidos[1]
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_document_type(self):
        try:
            if self.profile.us_doctype:
                return self.profile.us_doctype
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_document_number(self):
        try:
            if self.profile.cus_docnumber:
                return self.profile.cus_docnumber
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_phone(self):
        try:
            if self.profile.prof_phone:
                return self.profile.prof_phone
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_subscription_created(self):
        try:
            if self.subscription.starts_date:
                return self.local_format(self.subscription.starts_date)
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_subscription_renovation(self):
        try:
            # data.nextEventDateUTC
            if self.subscription.date_renovation:
                return self.local_format(self.subscription.date_renovation)
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_subscription_annulment(self):
        # data.nextEventDateUTC
        try:
            if self.subscription.date_anulled:
                return self.local_format(self.subscription.date_anulled)
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_payment_date_update(self):
        try:
            if self.payment.last_updated:
                return self.local_format(self.payment.last_updated)
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_last_update_subcription(self):
        try:
            if self.subscription.last_updated:
                return self.local_format(self.subscription.last_updated)
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_subscription_motive_annulment(self):
        try:
            if self.subscription.motive_anulled:
                return self.subscription.motive_anulled
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_plan_name(self):
        try:
            if self.subscription.plan.plan_name:
                return self.subscription.plan.plan_name
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_siebel_entecode(self):
        try:
            if self.profile.siebel_entecode:
                return self.profile.siebel_entecode
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_siebel_delivery(self):
        try:
            if self.operation.siebel_delivery:
                return self.operation.siebel_delivery
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_arc_orden(self):
        try:
            if self.payment.arc_order:
                return self.payment.arc_order
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_brand_name(self):
        try:
            if self.brand.partner_name:
                return self.brand.partner_name
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_brand_code(self):
        try:
            if self.brand.partner_code:
                return self.brand.partner_code
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_uuid_arc(self):
        try:
            if self.profile.arc_user.uuid:
                return self.profile.arc_user.uuid
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_brand_email(self):
        try:
            if self.profile.portal_email:
                return self.profile.portal_email
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_subscription(self):
        try:
            if self.subscription.id:
                return self.subscription.id
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_product_name(self):
        try:
            if self.product.prod_name:
                return self.product.prod_name
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def subscription_state(self):
        try:
            if self.subscription.state:
                return self.subscription.state
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_payment_amount(self):
        try:
            if self.payment.pa_amount:
                return self.payment.pa_amount
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_subscription_id(self):
        try:
            if self.subscription.id:
                return self.subscription.id
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_subscription_arc_id(self):
        try:
            if self.subscription.arc_id:
                return self.subscription.arc_id
            else:
                return ''
        except Exception:
            return ''
        except SystemExit:
            return ''

    def get_plan_code(self):
        """
            obtiene el codigo de producto de siebel
            :return:
        """
        try:
            if self.product.siebel_code:
                return self.product.siebel_code
            else:
                return ''
        except Exception as e:
            print(e)
            return ''
        except SystemExit:
            return ''

    def get_sku(self):
        """
            obtiene el sku que es el identificador del Plan.
        """
        try:
            if self.product.arc_sku:
                return self.product.arc_sku
            else:
                return ''
        except Exception as e:
            print(e)
            return ''
        except SystemExit:
            return ''

    def get_price_code(self):
        """
            obtiene el arc_pricecode del Plan.
        """
        try:
            if self.subscription.plan.arc_pricecode:
                return self.subscription.plan.arc_pricecode
            else:
                return ''
        except Exception as e:
            print(e)
            return ''
        except SystemExit:
            return ''

    def local_format(self, _date):
        if not isinstance(_date, datetime):
            return ''

        _date = _date.astimezone(
            get_default_timezone()
        )

        _date = _date.replace(tzinfo=None)

        return _date

    def format_user(self):
        return {
            'id': self.get_subscription_id(),
            'subscription_arc_id': self.get_subscription_arc_id(),
            'subscription_created': self.get_subscription_created(),
            'client_created_on': '',
            'client_name': self.get_user_name(),
            'client_lastname_father': self.get_last_name(),
            'client_lastname_mother': self.get_last_name_mother(),
            'client_doc_type': self.get_document_type(),
            'client_doc_num': self.get_document_number(),
            'client_phone': '',  # self.get_phone(),
            'plan_code': self.get_plan_code(),
            'plan_name': self.get_plan_name(),
            'product_name': self.get_product_name(),
            'rate_total': '',
            'legal_tyc': 'true',
            'subscription_date_renovation': '',
            'subscription_cancellation_date': self.get_subscription_annulment(),  #usuarios terminados
            'motive_anulled': '',
            'ubigeo': 0,
            'subscription_state': self.subscription_state(),
            'brand_email': self.get_brand_email(),
            'last_updated': self.get_last_update_subcription(),
            'uuid': self.get_uuid_arc(),
            'siebel_entecode': '',
            'siebel_delivery': '',
            'brand_code': self.get_brand_code(),
            'brand_name': self.get_brand_name(),
            'payment_date_update': '',
            'payment_amount': 0,
            'arc_orden': '',
            'arc_sku': self.get_sku(),  # plan
            'arc_price_code': self.get_price_code(),  # precio
        }
