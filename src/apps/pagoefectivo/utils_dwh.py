from datetime import datetime

from apps.paywall.models import Payment, Operation, Subscription
from django.utils.timezone import get_default_timezone
from sentry_sdk import capture_event, capture_exception


class UsersPESubscription(object):
    def __init__(self, operation):
        self.operation = operation
        self.cip_obj = operation.cip_obj

    def get_user_name(self):
        try:
            if self.cip_obj.user_name:
                return self.cip_obj.user_name
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_last_name(self):
        try:
            return self.cip_obj.lastname_father
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_last_name_mother(self):
        try:
            return self.cip_obj.lastname_mother
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_document_type(self):
        try:
            if self.cip_obj.user_document_type:
                return self.cip_obj.user_document_type
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_document_number(self):
        try:
            if self.cip_obj.user_document_number:
                return self.cip_obj.user_document_number
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_phone(self):
        try:
            if self.cip_obj.user_phone:
                return self.cip_obj.user_phone
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_subscription_created(self):
        try:
            return self.local_format(self.operation.payment_date)
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_subscription_renovation(self):
        try:
            return self.local_format(self.operation.subscription.date_renovation)
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_subscription_annulment(self):
        try:
            return self.local_format(self.operation.subscription.date_anulled)
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_subscription_motive_annulment(self):
        try:
            return self.cip_obj.subscription.motive_anulled
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_plan_name(self):
        try:
            if self.cip_obj.plan.plan_name:
                return self.cip_obj.plan.plan_name
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_siebel_entecode(self):
        try:
            if self.profile.siebel_entecode:
                return self.profile.siebel_entecode
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_siebel_delivery(self):
        try:
            obj_operation = Operation.objects.get(payment__subscription=self.subscription,
                                                  siebel_delivery__isnull=False)
            if obj_operation:
                return obj_operation.siebel_delivery
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_arc_orden(self):
        try:
            if self.payment.arc_order:
                return self.payment.arc_order
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_brand_name(self):
        try:
            return self.cip_obj.subscription.partner.partner_name
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_brand_code(self):
        try:
            return self.cip_obj.subscription.partner.partner_code
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_uuid_arc(self):
        try:
            if self.cip_obj.arc_user.uuid:
                return self.cip_obj.arc_user.uuid
            else:
                capture_exception()
                return ''
        except Exception as e:
            capture_exception()
        except SystemExit as e:
            capture_exception()
            return ''

    def get_brand_email(self):
        try:
            if self.cip_obj.user_email:
                return self.cip_obj.user_email
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_payment_date_update(self):
        #fecha de pago
        try:
            if self.payment:
                return self.local_format(self.payment.date_payment)
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_subscription(self):
        try:
            if self.operation.subscription.id:
                return self.operation.subscription.id
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_product_name(self):
        try:
            if self.cip_obj.plan.product.prod_name:
                return self.cip_obj.plan.product.prod_name
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def subscription_state(self):
        try:
            if self.cip_obj.subscription.state:
                return self.cip_obj.subscription.state
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_last_update_subcription(self):
        try:
            return self.local_format(self.cip_obj.last_updated)
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_payment_amount(self):
        try:
            if self.operation.amount:
                return self.operation.amount
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_subscription_arc_id(self):
        try:
            if self.cip_obj.subscription.arc_id:
                return self.cip_obj.subscription.arc_id
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_plan_code(self):
        """
            obtiene el codigo de producto de siebel
            :return:
        """
        try:
            if self.cip_obj.plan.product.siebel_code:
                return self.cip_obj.plan.product.siebel_code
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def local_format(self, _date):
        try:
            if not isinstance(_date, datetime):
                return ''

            _date = _date.astimezone(
                get_default_timezone()
            )

            _date = _date.replace(tzinfo=None)

            return _date
        except Exception as e:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_sku(self):
        """
            obtiene el sku que es el identificador del Plan.
        """
        try:
            if self.cip_obj.plan.product.arc_sku:
                return self.cip_obj.plan.product.arc_sku
            else:
                capture_event(
                    {
                        'message': 'sku vacio',
                        'extra': {
                            'data': self.cip_obj.plan.product,
                        }
                    }
                )
                return ''
        except Exception as e:
            print(e)
            capture_event(
                {
                    'message': 'error get sku',
                    'extra': {
                        'error': e,
                        'data': self.product,
                    }
                }
            )
            return ''
        except SystemExit as e:
            capture_event(
                {
                    'message': 'error get sku',
                    'extra': {
                        'error': e,
                        'data': self.product,
                    }
                }
            )
            return ''

    def get_price_code(self):
        """
            obtiene el arc_pricecode del Plan.
        """
        try:
            if self.cip_obj.subscription.plan.arc_pricecode:
                return self.cip_obj.subscription.plan.arc_pricecode
            else:
                return ''
        except Exception as e:
            print(e)
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_url_referer(self):
        try:
            return self.cip_obj.payment_tracking_pe.url_referer
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_medio(self):
        try:
            if self.cip_obj.payment_tracking_pe.medium:
                return self.cip_obj.payment_tracking_pe.medium
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_device(self):
        try:
            return self.cip_obj.payment_tracking_pe.device
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def low_on_request(self):
        try:
            if self.subscription.state == Subscription.ARC_STATE_TERMINATED:
                events_list = self.subscription.data.get('events', '')
                list_events_ordered = sorted(events_list, key=lambda i: i['eventDateUTC'])
                for event in list_events_ordered:
                    if event.get('eventType', '') == 'TERMINATE_SUBSCRIPTION' and previous_event == 'CANCEL_SUBSCRIPTION':
                        return 'low_on_request'
                    previous_event = event.get('eventType', '')
                return ''
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def low_for_lack_of_payment(self):
        try:
            list_suspended = ['SUSPEND_SUBSCRIPTION', 'FAIL_RENEW_SUBSCRIPTION']
            if self.subscription.state == Subscription.ARC_STATE_TERMINATED:
                events_list = self.subscription.data.get('events', '')
                list_events_ordered = sorted(events_list, key=lambda i: i['eventDateUTC'])
                for event in list_events_ordered:
                    if event.get('eventType', '') == 'TERMINATE_SUBSCRIPTION' and previous_event in list_suspended:
                        return 'low_for_lack_of_payment'
                    previous_event = event.get('eventType', '')
                return ''
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def low_for_other_reasons(self):
        try:
            list_exceptions = ['SUSPEND_SUBSCRIPTION', 'FAIL_RENEW_SUBSCRIPTION', 'CANCEL_SUBSCRIPTION']
            if self.subscription.state == Subscription.ARC_STATE_TERMINATED:
                events_list = self.subscription.data.get('events', '')
                list_events_ordered = sorted(events_list, key=lambda i: i['eventDateUTC'])
                for event in list_events_ordered:
                    if event.get('eventType', '') == 'TERMINATE_SUBSCRIPTION' and previous_event not in list_exceptions:
                        return 'low_for_other_reasons'
                    previous_event = event.get('eventType', '')
                return ''
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_low_by_type(self):
        if self.low_on_request():
            return self.low_on_request()
        elif self.low_for_lack_of_payment():
            return self.low_for_lack_of_payment()
        elif self.low_for_other_reasons():
            return self.low_for_other_reasons()
        else:
            return ''

    def get_transaction_code_pag_efect(self):
        try:
            return self.cip_obj.transaction_code_response
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_cip(self):
        try:
            return self.cip_obj.cip
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def format_user(self):
        return {
            'id': '',
            'subscription_arc_id': self.get_subscription_arc_id(),
            'subscription_created': self.get_subscription_created(),
            'subscription_method': 'pago_efectivo',
            'client_created_on': '',
            'client_name': self.get_user_name(),
            'client_lastname_father': self.get_last_name(),
            'client_lastname_mother': self.get_last_name_mother(),
            'client_doc_type': self.get_document_type(),
            'client_doc_num': self.get_document_number(),
            'client_phone': self.get_phone(),
            'plan_code': self.get_plan_code(),
            'plan_name': self.get_plan_name(),
            'product_name': self.get_product_name(),
            'rate_total': '',
            'legal_tyc': '',
            'subscription_date_renovation': '',
            'subscription_cancellation_date': '',
            'ubigeo': 0,
            'subscription_state': self.subscription_state(),
            'brand_email': self.get_brand_email(),
            'last_updated': self.get_last_update_subcription(),
            'uuid': self.get_uuid_arc(),
            'siebel_entecode': self.get_siebel_entecode(),
            'siebel_delivery': self.get_siebel_delivery(),
            'brand_code': self.get_brand_code(),
            'brand_name': self.get_brand_name(),
            'payment_date_update': self.get_subscription_created(),
            'payment_amount': self.get_payment_amount(),
            'payment_method': '',
            'arc_orden': '',
            'arc_sku': self.get_sku(),  # plan
            'arc_price_code': self.get_price_code(),  # precio
            'url_referer': self.get_url_referer(),
            'medio': self.get_medio(),
            'device': self.get_device(),
            'motive_anulled': self.get_subscription_motive_annulment(),
            'motive_cancelation': '',
            'low_by_type': self.get_low_by_type(),
            'transaction_code_pag_efect': self.get_transaction_code_pag_efect(),
            'cip': self.get_cip()
        }
