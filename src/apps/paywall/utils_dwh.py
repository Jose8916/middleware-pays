from datetime import datetime

from apps.paywall.models import Payment, Operation, PaymentTracking, Subscription
from django.utils.timezone import get_default_timezone
from sentry_sdk import capture_event, capture_exception


class UsersSubscription(object):

    def __init__(self, subscription):
        try:
            self.payment = Payment.objects.filter(subscription=subscription).last()
        except Exception as e:
            capture_event(
                {
                    'message': 'error opteniendo el payment',
                    'extra': {
                        'error': e,
                        'operacion': subscription,
                    }
                }
            )
            self.payment = ''
        except SystemExit as e:
            capture_event(
                {
                    'message': 'error opteniendo el payment - systemExit',
                    'extra': {
                        'error': e,
                        'operacion': subscription,
                    }
                }
            )
            self.payment = ''

        try:
            payment_main = Payment.objects.get(subscription=subscription, pa_origin='WEB')
            self.profile = payment_main.payment_profile
        except Exception:
            capture_exception()
            self.profile = ''
        except SystemExit:
            capture_exception()
            self.profile = ''

        try:
            self.product = subscription.plan.product
        except Exception as e:
            capture_event(
                {
                    'message': 'error opteniendo el producto',
                    'extra': {
                        'error': e,
                        'operacion': subscription,
                    }
                }
            )
            self.product = ''
        except SystemExit as e:
            capture_event(
                {
                    'message': 'error opteniendo el producto',
                    'extra': {
                        'error': e,
                        'operacion': subscription,
                    }
                }
            )
            self.product = ''

        try:
            self.subscription = subscription
        except Exception:
            capture_exception()
            self.subscription = ''
        except SystemExit:
            capture_exception()
            self.subscription = ''

        try:
            self.brand = self.subscription.partner
        except Exception:
            capture_exception()
            self.brand = ''
        except SystemExit:
            capture_exception()
            self.brand = ''

    def get_user_name(self):
        try:
            if self.profile.prof_name:
                return self.profile.prof_name
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
            if self.profile.prof_lastname:
                return self.profile.prof_lastname
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_last_name_mother(self):
        try:
            if self.profile.prof_lastname_mother:
                return self.profile.prof_lastname_mother
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_document_type(self):
        try:
            if self.profile.prof_doc_type:
                return self.profile.prof_doc_type
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
            if self.profile.prof_doc_num:
                return self.profile.prof_doc_num
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
            if self.profile.prof_phone:
                return self.profile.prof_phone
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
            return self.local_format(self.subscription.starts_date)
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_subscription_renovation(self):
        try:
            return self.local_format(self.subscription.date_renovation)
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_subscription_annulment(self):
        try:
            return self.local_format(self.subscription.date_anulled)
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_subscription_motive_annulment(self):
        try:
            return self.subscription.motive_anulled
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_plan_name(self):
        try:
            if self.subscription.plan.plan_name:
                return self.subscription.plan.plan_name
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
            if self.brand.partner_name:
                return self.brand.partner_name
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_brand_code(self):
        try:
            if self.brand.partner_code:
                return self.brand.partner_code
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_uuid_arc(self):
        try:
            if self.subscription.arc_user.uuid:
                return self.subscription.arc_user.uuid
            else:
                capture_event(
                    {
                        'message': 'Suscripcion sin uuid',
                        'extra': {
                            'data': self.subscription,
                        }
                    }
                )
                return ''
        except Exception as e:
            capture_event(
                {
                    'message': 'Suscripcion sin uuid - Exception',
                    'extra': {
                        'data': self.subscription,
                        'error': e
                    }
                }
            )
            return ''
        except SystemExit as e:
            capture_event(
                {
                    'message': 'Suscripcion sin uuid - system_exit',
                    'extra': {
                        'data': self.subscription,
                        'error': e
                    }
                }
            )
            return ''

    def get_brand_email(self):
        try:
            if self.profile.portal_email:
                return self.profile.portal_email
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_payment_date_update(self):
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
            if self.subscription.id:
                return self.subscription.id
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
            if self.product.prod_name:
                return self.product.prod_name
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
            if self.subscription.state:
                return self.subscription.state
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
            return self.local_format(self.subscription.last_updated)
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_payment_amount(self):
        try:
            if self.payment.pa_amount:
                return self.payment.pa_amount
            else:
                return ''
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_subscription_id(self):
        try:
            if self.subscription.id:
                return self.subscription.id
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
            if self.subscription.arc_id:
                return self.subscription.arc_id
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
            if self.product and self.product.siebel_code:
                return self.product.siebel_code
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
            if self.product.arc_sku:
                return self.product.arc_sku
            else:
                capture_event(
                    {
                        'message': 'sku vacio',
                        'extra': {
                            'data': self.product,
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
            if self.subscription.plan.arc_pricecode:
                return self.subscription.plan.arc_pricecode
            else:
                return ''
        except Exception as e:
            print(e)
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_subscription_method(self):
        try:
            if self.subscription and self.subscription.data:
                return self.subscription.data['currentPaymentMethod']['paymentPartner']
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_payment_method(self):
        try:
            if self.payment:
                return self.payment.pa_method
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_url_referer(self):
        try:
            payment_tracking = PaymentTracking.objects.get(subscription=self.subscription)
            return payment_tracking.url_referer
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_medio(self):
        try:
            payment_tracking = PaymentTracking.objects.get(subscription=self.subscription)
            return payment_tracking.medium
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def get_device(self):
        try:
            payment_tracking = PaymentTracking.objects.get(subscription=self.subscription)
            return payment_tracking.device
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

    def get_reason_for_cancellation(self):
        """
            obtiene el motivo de cancelacion del usuario.
        """
        try:
            if self.subscription.motive_cancelation:
                return self.subscription.motive_cancelation
            else:
                motive_cancelation = ''
                events_list = self.subscription.data.get('events', '')
                list_events_ordered = sorted(events_list, key=lambda i: i['eventDateUTC'])
                for event in list_events_ordered:
                    if event.get('eventType', '') == 'CANCEL_SUBSCRIPTION' and event.get('details', ''):
                        motive_cancelation = event.get('details', '')
                return motive_cancelation
        except Exception:
            capture_exception()
            return ''
        except SystemExit:
            capture_exception()
            return ''

    def format_user(self):
        return {
            'id': self.get_subscription_id(),
            'subscription_arc_id': self.get_subscription_arc_id(),
            'subscription_created': self.get_subscription_created(),
            'subscription_method': self.get_subscription_method(),
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
            'subscription_date_renovation': self.get_subscription_renovation(),
            'subscription_cancellation_date': self.get_subscription_annulment(),
            'ubigeo': 0,
            'subscription_state': self.subscription_state(),
            'brand_email': self.get_brand_email(),
            'last_updated': self.get_last_update_subcription(),
            'uuid': self.get_uuid_arc(),
            'siebel_entecode': self.get_siebel_entecode(),
            'siebel_delivery': self.get_siebel_delivery(),
            'brand_code': self.get_brand_code(),
            'brand_name': self.get_brand_name(),
            'payment_date_update': self.get_payment_date_update(),
            'payment_amount': self.get_payment_amount(),
            'payment_method': self.get_payment_method(),
            'arc_orden': self.get_arc_orden(),
            'arc_sku': self.get_sku(),  # plan
            'arc_price_code': self.get_price_code(),  # precio
            'url_referer': self.get_url_referer(),
            'medio': self.get_medio(),
            'device': self.get_device(),
            'motive_anulled': self.get_subscription_motive_annulment(),
            'motive_cancelation': self.get_reason_for_cancellation(),
            'low_by_type': self.get_low_by_type()
        }
