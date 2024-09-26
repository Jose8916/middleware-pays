from datetime import datetime, timedelta

from django.utils.timezone import get_default_timezone
from apps.paywall.models import Subscription


class Collaborator(object):

    def __init__(self, collaborator):
        self.collaborator = collaborator
        try:
            self.subscription = Subscription.objects.get(
                arc_id=self.collaborator.data.get('subscriptionID', '')
            )
        except Exception:
            self.subscription = ''

        try:
            self.product = self.subscription.plan.product
        except Exception:
            self.product = ''
        except SystemExit:
            self.product = ''

    def get_user_name(self):
        try:
            if self.collaborator.name:
                return self.collaborator.name
            else:
                return ''
        except Exception:
            return ''

    def get_last_name(self):
        try:
            if self.collaborator.lastname:
                return self.collaborator.lastname
            else:
                return ''
        except Exception:
            return ''

    def get_last_name_mother(self):
        try:
            if self.collaborator.lastname_mother:
                return self.collaborator.lastname_mother
            else:
                return ''
        except Exception:
            return ''

    def get_document_type(self):
        try:
            if self.collaborator.doc_type:
                return self.collaborator.doc_type
            else:
                return ''
        except Exception:
            return ''

    def get_document_number(self):
        try:
            if self.collaborator.doc_number:
                return self.collaborator.doc_number
            else:
                return ''
        except Exception:
            return ''

    def get_phone(self):
        try:
            if self.profile.prof_phone:
                return self.profile.prof_phone
            else:
                return ''
        except Exception:
            return ''

    def get_subscription_created(self):
        try:
            if self.subscription.starts_date:
                return self.local_format(self.subscription.starts_date)
            else:
                return ''
        except Exception:
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

    def get_subscription_annulment(self):
        # data.nextEventDateUTC
        try:
            if self.collaborator.date_annulled:
                return self.local_format(self.collaborator.date_annulled)
            else:
                return ''
        except Exception:
            return ''

    def get_payment_date_update(self):
        try:
            if self.payment.last_updated:
                return self.local_format(self.payment.last_updated)
            else:
                return ''
        except Exception:
            return ''

    def get_subscription_motive_annulment(self):
        try:
            if self.subscription.motive_anulled:
                return self.subscription.motive_anulled
            else:
                return ''
        except Exception:
            return ''

    def get_plan_name(self):
        try:
            if self.operation.plan.plan_name:
                return self.operation.plan.plan_name
            else:
                return ''
        except Exception:
            return ''

    def get_siebel_entecode(self):
        try:
            if self.profile.siebel_entecode:
                return self.profile.siebel_entecode
            else:
                return ''
        except Exception:
            return ''

    def get_siebel_delivery(self):
        try:
            if self.operation.siebel_delivery:
                return self.operation.siebel_delivery
            else:
                return ''
        except Exception:
            return ''

    def get_arc_orden(self):
        try:
            if self.payment.arc_order:
                return self.payment.arc_order
            else:
                return ''
        except Exception:
            return ''

    def get_brand_name(self):
        try:
            if self.subscription.partner.partner_name:
                return self.subscription.partner.partner_name
            else:
                return ''
        except Exception:
            return ''

    def get_brand_code(self):
        try:
            if self.subscription.partner.partner_code:
                return self.subscription.partner.partner_code
            else:
                return ''
        except Exception:
            return ''

    def get_uuid_arc(self):
        try:
            if self.collaborator.uuid:
                return self.collaborator.uuid
            else:
                return ''
        except Exception:
            return ''

    def get_brand_email(self):
        try:
            if self.collaborator.email:
                return self.collaborator.email
            else:
                return ''
        except Exception:
            return ''

    def get_subscription(self):
        try:
            if self.subscription.id:
                return self.subscription.id
            else:
                return ''
        except Exception:
            return ''

    def get_product_name(self):
        try:
            if self.product.prod_name:
                return self.product.prod_name
            else:
                return ''
        except Exception:
            return ''

    def subscription_state(self):
        try:
            if self.subscription:
                return self.subscription.state
            else:
                return ''
        except Exception:
            return ''

    def get_last_update_subcription(self):
        try:
            if self.subscription.last_updated:
                return self.subscription.last_updated
            else:
                return ''
        except Exception:
            return ''

    def get_payment_amount(self):
        try:
            if self.payment.pa_amount:
                return self.payment.pa_amount
            else:
                return ''
        except Exception:
            return ''

    def get_subscription_id(self):
        try:
            if self.subscription.id:
                return self.subscription.id
            else:
                return ''
        except Exception:
            return ''

    def get_subscription_arc_id(self):
        try:
            if self.collaborator.data.get('subscriptionID', ''):
                return self.collaborator.data.get('subscriptionID', '')
            else:
                return ''
        except Exception:
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

    def local_format(self, _date):
        if not isinstance(_date, datetime):
            return ''

        _date = _date.astimezone(
            get_default_timezone()
        )

        _date = _date.replace(tzinfo=None)

        return _date

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

    def format_user(self):
        return {
            'arc_orden': '',
            'brand_code': self.get_brand_code(),
            'brand_email': self.get_brand_email(),
            'brand_name': self.get_brand_name(),
            'client_created_on': '',
            'client_doc_num': self.get_document_number(),
            'client_doc_type': self.get_document_type(),
            'client_lastname_father': self.get_last_name(),
            'client_lastname_mother': self.get_last_name_mother(),
            'client_name': self.get_user_name(),
            'client_phone': self.get_phone(),
            'id': self.get_subscription_id(),
            'last_updated': self.get_last_update_subcription(),
            'legal_tyc': 'true',
            'motive_anulled': '',
            'payment_amount': '',
            'payment_date_update': '',
            'plan_code': '',  # no hay codigo en siebel
            'plan_name': 'Digital Colaborador',
            'product_name': 'Plan Colaborador',
            'rate_total': '',
            'siebel_delivery': '',
            'siebel_entecode': '',
            'subscription_arc_id': self.get_subscription_arc_id(),
            'subscription_cancellation_date': self.get_subscription_annulment(),
            'subscription_created': self.get_subscription_created(),
            'subscription_date_renovation': '',
            'subscription_state': self.subscription_state(),
            'ubigeo': 0,
            'uuid': self.get_uuid_arc(),
            'arc_sku': self.get_sku(),  # plan
            'arc_price_code': self.get_price_code(),  # precio
        }
