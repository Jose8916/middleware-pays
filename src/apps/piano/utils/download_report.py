from urllib.parse import urljoin
from datetime import datetime
from django.conf import settings
from apps.piano.constants import LIST_WITHOUT_TRANSACTIONS_RECOGNITION, LIST_EMAIL_SENDER
from apps.paywall.shortcuts import render_send_email
from sentry_sdk import capture_exception, add_breadcrumb, capture_event
import requests
import csv
from django.utils import formats, timezone
from apps.piano.utils_models import (get_or_create_subscription,
                                     get_payment_profile)
from apps.piano.piano_clients import VXClient, PaymentOS, IDClient, Payu
from apps.piano.models import Term, Transaction, PromotionPiano
from apps.paywall.models import Partner
import time


class VXProcess(object):

    def get_list_transactions_report(self, brand, date_from, date_to, time_sleep):
        list_transactions = []
        report_id = VXClient().get_transactions_report(brand, date_from, date_to)
        if report_id:
            export = report_id.get('export', '')
            export_id = export.get('export_id', '')
            if time_sleep:
                time.sleep(time_sleep)
            else:
                time.sleep(90)
            for i in [100, 100, 100, 100, 100, 100]:
                export_csv_link = VXClient().get_export_download(brand, export_id)
                if export_csv_link.get('data', ''):
                    list_transactions = VXClient().get_csv_from_url(export_csv_link.get('data', ''))
                    break
                else:
                    time.sleep(i)
        return list_transactions

    def get_list_recognition_transactions_report(self, brand, date_from, date_to, date_interval, time_sleep):
        list_transactions_recognition = []
        date_from_r = datetime.fromtimestamp(date_from).strftime("%Y-%m-%d")
        date_to_r = datetime.fromtimestamp(date_to).strftime("%Y-%m-%d")
        report_recognition_id = VXClient().get_recognition_transactions_report(
            brand,
            date_from_r,
            date_to_r,
            date_interval
        )
        if report_recognition_id:
            export_id_recognition = report_recognition_id.get('export_id', '')
            if time_sleep:
                time.sleep(time_sleep)
            else:
                time.sleep(90)

            for i in [100, 100, 100, 100, 100, 100]:
                export_csv_link_recognition = VXClient().get_rest_export_download(brand, export_id_recognition)
                if export_csv_link_recognition.get('url', ''):
                    list_transactions_recognition = VXClient().get_csv_from_url_recognition(
                        export_csv_link_recognition.get('url', '')
                    )
                    break
                else:
                    time.sleep(i)
        return list_transactions_recognition

    def get_environments(self):
        return [
            {
                'app_id': settings.PAYMENTSOS_APP_ID_NEW_CUSTOMERS,
                'private_key': settings.PAYMENTSOS_PRIVATE_KEY_NEW_CUSTOMERS
            },
            {
                'app_id': settings.PAYMENTSOS_APP_ID_RENEWAL,
                'private_key': settings.PAYMENTSOS_PRIVATE_KEY_RENEWAL
            }
        ]

    def get_payment_os_data(self, transaction_):
        environments = self.get_environments()
        reconciliation_id = None
        initial_transaction = None

        for env_ in environments:
            detail_payment = PaymentOS().get_payment(
                env_.get('app_id'),
                env_.get('private_key'),
                transaction_.get('external_tx_id')
            )

            try:
                id_paymentos = detail_payment.get('id', '')
            except:
                id_paymentos = ''

            if id_paymentos:
                break

        if id_paymentos:
            related_resources = detail_payment.get('related_resources', '')
            if related_resources:
                charges = related_resources.get('charges', '')[0]
                if charges:
                    reconciliation_id = charges.get('reconciliation_id', '')

            if detail_payment.get('id', '') and env_.get('app_id', '') == settings.PAYMENTSOS_APP_ID_NEW_CUSTOMERS:
                initial_transaction = True
            elif detail_payment.get('id', '') and env_.get('app_id', '') == settings.PAYMENTSOS_APP_ID_RENEWAL:
                initial_transaction = False

        return initial_transaction, reconciliation_id, id_paymentos

    def get_payu_data(self, reconciliation_id):
        transaction_payu = Payu().get_transaction_by_type(
            'ORDER_DETAIL_BY_REFERENCE_CODE',
            'referenceCode',
            reconciliation_id
        )
        try:
            id_transaction = transaction_payu.get('result', {}).get('payload')[0].get('transactions')[0].get('id')
        except:
            id_transaction = ''

        try:
            payu_order_id = transaction_payu.get('result', {}).get('payload')[0].get('id')
        except:
            payu_order_id = ''
        return payu_order_id, id_transaction

    def format_string_to_date(self, date_time_str):
        if date_time_str:
            date_time_obj = datetime.strptime(date_time_str, '%m/%d/%Y')
            tz = timezone.get_current_timezone()
            return date_time_obj.astimezone(tz)
        else:
            return None

    def save_term(self, dict_term):
        try:
            term = Term.objects.get(term_id=dict_term.get('term_id'))
        except:
            term = Term(
                plan_name=dict_term.get('name'),
                plan_description=dict_term.get('description'),
                term_id=dict_term.get('term_id'),
                app_id=dict_term.get('aid'),
                data=dict_term
            )
            term = term.save()
        return term

    def save_subscription_promotion(self, uid, brand, subscription):
        list_conversions = VXClient().get_conversion(uid, brand)
        for conversion in list_conversions.get('conversions'):
            if conversion.get('promo_code', ''):
                if conversion.get('subscription').get('subscription_id') == subscription.subscription_id:
                    promotion = PromotionPiano(
                        promotion_id=conversion.get('promo_code').get('promotion_id'),
                        subscription=subscription,
                        promo_code_id=conversion.get('promo_code').get('promo_code_id')
                    )
                    promotion.save()

    def report_save_transactions(self, list_transactions, list_transactions_recognition, brand):
        list_payment_not_found = []
        try:
            partner = Partner.objects.get(partner_code=brand)
        except Exception:
            partner = None
        if partner:
            from_email = '{name_sender} <{direction_sender}>'.format(
                name_sender=partner.partner_name,
                direction_sender=partner.transactional_sender
            )
        else:
            from_email = None

        if not list_transactions or not list_transactions_recognition:
            render_send_email(
                template_name='mailings/error.html',
                subject=('[Test]' if settings.ENVIRONMENT == 'test' else '[Production]') + ' Carga de pagos',
                to_emails=LIST_EMAIL_SENDER,
                from_email=from_email,
                context={
                    'error': 'Error no cargo los pagos para el ' + brand
                }
            )

        for transaction_ in list_transactions:
            if not Transaction.objects.filter(external_tx_id=transaction_.get('external_tx_id')).exists():
                print(f"Cargando transaccion: {transaction_.get('external_tx_id')}")
                access_from = access_to = ''
                amount = None
                match_tx_id = False

                for transaction_recognition in list_transactions_recognition:
                    if transaction_recognition.get('external_tx_id') == transaction_.get('external_tx_id'):
                        access_from = transaction_recognition.get('access_from')
                        access_to = transaction_recognition.get('access_to')
                        payment_date = transaction_recognition.get('payment_date')
                        amount = int(transaction_recognition.get('amount').split(".")[0])
                        match_tx_id = True
                        break

                if match_tx_id or transaction_.get('external_tx_id') in LIST_WITHOUT_TRANSACTIONS_RECOGNITION:
                    subscription_obj = get_or_create_subscription(transaction_.get('subscription_id'), brand)
                    payment_ = VXClient().get_payment(
                        user_payment_id=transaction_.get('user_payment_id'),
                        brand=brand
                    )
                    obj = Transaction(
                        external_tx_id=transaction_.get('external_tx_id'),
                        tx_type=transaction_.get('tx_type'),
                        status=transaction_.get('status'),
                        term_name=transaction_.get('term_name'),
                        term_identifier=transaction_.get('term_id'),
                        subscription_id_str=transaction_.get('subscription_id'),
                        user_id=transaction_.get('user_id'),
                        amount=amount,
                        access_from=access_from,
                        access_to=access_to,
                        access_from_date=self.format_string_to_date(access_from),
                        payment_date=self.format_string_to_date(payment_date),
                        payment_source_type=transaction_.get('payment_source_type'),
                        subscription=subscription_obj,
                        report_data=transaction_.get('report_data'),
                        original_price=payment_.get('payment', {}).get('original_price', '')
                    )
                    initial_transaction, reconciliation_id, id_paymentos = VXProcess().get_payment_os_data(transaction_)
                    if reconciliation_id and id_paymentos:
                        payu_order_id, id_transaction = VXProcess().get_payu_data(reconciliation_id)
                        if payu_order_id and id_transaction:
                            obj.initial_transaction = initial_transaction
                            obj.reconciliation_id = reconciliation_id
                            obj.id_transaction_paymentos = id_paymentos
                            obj.payu_transaction_id = id_transaction
                            obj.payu_order_id = payu_order_id
                            obj.payment_profile = get_payment_profile(transaction_.get('user_id'), brand, subscription_obj)

                            response_term = VXClient().get_term(brand, transaction_.get('term_id'))
                            obj.term = self.save_term(response_term.get('term'))
                            obj.save()
                            subscription_obj.term = self.save_term(response_term.get('term'))
                            subscription_obj.save()
                            self.save_subscription_promotion(transaction_.get('user_id'), brand, subscription_obj)
                        else:
                            print('no se logro obtener el payu_order_id o id_transaction de ' + str(transaction_.get('external_tx_id')))
                            if settings.ENVIRONMENT != 'test':
                                render_send_email(
                                    template_name='mailings/error.html',
                                    subject=('[Test]' if settings.ENVIRONMENT == 'test' else '[Production]') + ' Carga de pagos',
                                    to_emails=LIST_EMAIL_SENDER,
                                    from_email=from_email,
                                    context={
                                        'error': 'no se logro obtener el payu_order_id o id_transaction de ' + str(
                                            transaction_.get('external_tx_id')),
                                    }
                                )

                    else:
                        print('external_tx_id no existe en paymentOS: ' + str(transaction_.get('external_tx_id')))
                        render_send_email(
                            template_name='mailings/error.html',
                            subject=('[Test]' if settings.ENVIRONMENT == 'test' else '[Production]') + ' Carga de pagos',
                            to_emails=LIST_EMAIL_SENDER,
                            from_email=from_email,
                            context={
                                'error': 'external_tx_id no existe en paymentOS: ' + str(transaction_.get('external_tx_id'))
                            }
                        )
                else:
                    list_payment_not_found.append(transaction_.get('external_tx_id'))
                    print('No fue encontrado: ' + transaction_.get('external_tx_id'))

        if len(list_payment_not_found) > 10:
            render_send_email(
                template_name='mailings/error.html',
                subject=('[Test]' if settings.ENVIRONMENT == 'test' else '[Production]') + ' Carga de pagos',
                to_emails=LIST_EMAIL_SENDER,
                from_email=from_email,
                context={
                    'error': 'No fue encontrado: ' + str(list_payment_not_found)
                }
            )
