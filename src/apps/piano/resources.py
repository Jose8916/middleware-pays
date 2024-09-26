import json
from django.conf import settings
from import_export import resources
from import_export.fields import Field
from .models import LowSubscriptions, Transaction, TransactionsWithNewDate, RenovationPiano, PaymentPiano,\
    Subscription, BlockedSubscriptions, SaleOrderPiano
from apps.siebel.models import SiebelConfirmationPayment
from django.utils import formats, timezone


class TransactionResource(resources.ModelResource):
    subscription_id_str = Field(attribute='subscription_id_str', column_name='Suscripcion Id')
    entecode = Field(attribute='entecode', column_name='Entecode')
    log_envio_delivery = Field(attribute='log_envio_delivery', column_name='log_envio_delivery')
    log_respuesta_delivery = Field(attribute='log_respuesta_delivery', column_name='log_respuesta_delivery')
    delivery = Field(attribute='delivery', column_name='delivery')
    email = Field(attribute='email', column_name='Email')
    external_tx_id = Field(attribute='external_tx_id', column_name='external_tx_id')
    payu_transaction_id = Field(attribute='payu_transaction_id', column_name='payu_transaction_id')
    llegada_de_comprobantes = Field(attribute='llegada_de_comprobantes', column_name='llegada_de_comprobantes')
    con_pago = Field(attribute='con_pago', column_name='con_pago')

    class Meta:
        model = Transaction
        report_skipped = True
        fields = ('email', 'subscription_id_str', 'entecode', 'log_envio_delivery', 'log_respuesta_delivery',
                  'delivery', 'external_tx_id', 'payu_transaction_id', 'llegada_de_comprobantes', 'con_pago')
        export_order = ('email', 'subscription_id_str', 'entecode', 'log_envio_delivery', 'log_respuesta_delivery',
                        'delivery', 'external_tx_id', 'payu_transaction_id', 'llegada_de_comprobantes', 'con_pago')

    def dehydrate_entecode(self, transaction):
        if transaction.payment_profile:
            return transaction.payment_profile.siebel_entecode

    def dehydrate_log_envio_delivery(self, transaction):
        if transaction.siebel_sale_order:
            return transaction.siebel_sale_order.siebel_request

    def dehydrate_log_respuesta_delivery(self, transaction):
        if transaction.siebel_sale_order:
            return transaction.siebel_sale_order.siebel_response

    def dehydrate_delivery(self, transaction):
        if transaction.subscription:
            return transaction.subscription.delivery

    def dehydrate_email(self, transaction):
        if transaction.payment_profile:
            return transaction.payment_profile.portal_email

    def dehydrate_llegada_de_comprobantes(self, transaction):
        try:
            confirmation = SiebelConfirmationPayment.objects.get(num_liquidacion=transaction.payu_transaction_id)
            return confirmation.created
        except:
            return ''

    def dehydrate_con_pago(self, transaction):
        if transaction.siebel_payment:
            if transaction.siebel_payment.cod_response:
                return 'con pago'

        return 'sin pago'


class LowSubscriptionsResource(resources.ModelResource):
    subs_id = Field(attribute='subs_id', column_name='Suscripcion Id')
    user_email = Field(attribute='user_email', column_name='Email')
    delivery = Field(attribute='delivery', column_name='Delivery')
    enviado_a_siebel = Field(attribute='enviado_a_siebel', column_name='Enviado a Siebel')
    low_subscription = Field(attribute='low_subscription', column_name='Fecha de baja')

    class Meta:
        model = LowSubscriptions
        report_skipped = True
        fields = ('subs_id', 'user_email', 'delivery', 'enviado_a_siebel', 'exclude_to_send_siebel', 'resource_id', 'low_subscription',)
        export_order = ('subs_id', 'user_email', 'delivery', 'enviado_a_siebel', 'exclude_to_send_siebel', 'resource_id', 'low_subscription', )

    def dehydrate_delivery(self, lowSubscriptions):
        if lowSubscriptions.subscription:
            return lowSubscriptions.subscription.delivery

    def dehydrate_enviado_a_siebel(self, lowSubscriptions):
        if lowSubscriptions.unsubscribe:
            return lowSubscriptions.unsubscribe.sent_to_siebel


class SubscriptionsResource(resources.ModelResource):
    subscription_id = Field(attribute='subscription_id', column_name='Suscripcion Id')
    format_start_date = Field(attribute='format_start_date', column_name='start_date')
    uid = Field(attribute='uid', column_name='uid')
    delivery = Field(attribute='delivery', column_name='Delivery')
    app_id = Field(attribute='app_id', column_name='app_id')
    email = Field(attribute='email', column_name='email')
    prof_doc_type = Field(attribute='prof_doc_type', column_name='prof_doc_type')
    prof_doc_num = Field(attribute='prof_doc_num', column_name='prof_doc_num')
    prof_name = Field(attribute='prof_name', column_name='prof_name')
    prof_lastname = Field(attribute='prof_lastname', column_name='prof_lastname')
    plan_description = Field(attribute='plan_description', column_name='plan_description')
    plan_name = Field(attribute='plan_name', column_name='plan_name')
    term_id = Field(attribute='term_id', column_name='term_id')

    class Meta:
        model = Subscription
        report_skipped = True
        fields = ('subscription_id', 'format_start_date', 'uid', 'delivery', 'app_id', 'email', 'prof_doc_type',
                  'prof_doc_num', 'prof_name', 'prof_lastname', 'plan_description', 'plan_name', 'term_id',)
        export_order = ('subscription_id', 'format_start_date', 'uid', 'delivery', 'app_id', 'email', 'prof_doc_type',
                        'prof_doc_num', 'prof_name', 'prof_lastname', 'plan_description', 'plan_name', 'term_id',)

    def dehydrate_email(self, subscription):
        if subscription.payment_profile:
            return subscription.payment_profile.portal_email
        else:
            return ''

    def dehydrate_format_start_date(self, subscription):
        try:
            tz = timezone.get_current_timezone()
            start_date_ = formats.date_format(subscription.start_date.astimezone(tz), settings.DATETIME_FORMAT)
        except:
            start_date_ = ''
        return start_date_

    def dehydrate_prof_doc_type(self, subscription):
        if subscription.payment_profile:
            return subscription.payment_profile.prof_doc_type
        else:
            return ''

    def dehydrate_prof_doc_num(self, subscription):
        if subscription.payment_profile:
            return subscription.payment_profile.prof_doc_num
        else:
            return ''

    def dehydrate_prof_name(self, subscription):
        if subscription.payment_profile:
            return subscription.payment_profile.prof_name
        else:
            return ''

    def dehydrate_prof_lastname(self, subscription):
        if subscription.payment_profile:
            return subscription.payment_profile.prof_lastname
        else:
            return ''


    def dehydrate_plan_description(self, subscription):
        if subscription.term:
            return subscription.term.plan_description
        else:
            return ''

    def dehydrate_plan_name(self, subscription):
        if subscription.term:
            return subscription.term.plan_name
        else:
            return ''

    def dehydrate_term_id(self, subscription):
        if subscription.term:
            return subscription.term.term_id
        else:
            return ''


class SubscriptionMatchArcPianoResource(resources.ModelResource):
    subscription_id_piano = Field(attribute='subscription_id_piano', column_name='Suscripcion Id PIANO')
    subscription_id_arc = Field(attribute='subscription_id_arc', column_name='SubscripcionId ARC')

    class Meta:
        model = LowSubscriptions
        report_skipped = True
        fields = ('subscription_id_piano', 'subscription_id_arc',)
        export_order = ('subscription_id_piano', 'subscription_id_arc',)


class TransactionsWithNewDateResource(resources.ModelResource):
    subscription_id_piano = Field(attribute='subscription_id_piano', column_name='Suscripcion Id PIANO')
    external_tx_id = Field(attribute='external_tx_id', column_name='external_tx_id')
    access_from = Field(attribute='access_from', column_name='access_from')
    access_to = Field(attribute='access_to', column_name='access_to')
    brand = Field(attribute='brand', column_name='brand')

    class Meta:
        model = TransactionsWithNewDate
        report_skipped = True
        fields = ('subscription_id_piano', 'external_tx_id', 'access_from', 'access_to', 'brand',)
        export_order = ('subscription_id_piano', 'external_tx_id', 'access_from', 'access_to', 'brand',)


class RenovationResource(resources.ModelResource):
    state = Field(attribute='state', column_name='state')
    siebel_request = Field(attribute='siebel_request', column_name='siebel_request')
    siebel_response = Field(attribute='siebel_response', column_name='siebel_response')
    created = Field(attribute='created', column_name='created')
    last_updated = Field(attribute='last_updated', column_name='last_updated')
    id_transaction = Field(attribute='id_transaction', column_name='id_transaction')

    class Meta:
        model = RenovationPiano
        report_skipped = True
        fields = ('id_transaction', 'state', 'siebel_request', 'siebel_response', 'created', 'last_updated', )
        export_order = ('id_transaction', 'state', 'siebel_request', 'siebel_response', 'created', 'last_updated',)

    def dehydrate_id_transaction(self, renovationPiano):
        if renovationPiano.siebel_request:
            siebel_request = renovationPiano.siebel_request
            siebel_request = siebel_request.replace("'", "\"")
            siebel_request = json.loads(siebel_request)
            return siebel_request.get('num_liquidacion')
        else:
            return ''


class SaleOrderPianoResource(resources.ModelResource):
    delivery = Field(attribute='delivery', column_name='delivery')
    created = Field(attribute='created', column_name='created')
    last_updated = Field(attribute='last_updated', column_name='last_updated')
    suscription = Field(attribute='suscription', column_name='suscription')

    class Meta:
        model = SaleOrderPiano
        report_skipped = True
        fields = ('delivery', 'created', 'last_updated', 'suscription',)
        export_order = ('delivery', 'created', 'last_updated', 'suscription',)

    def dehydrate_suscription(self, saleOrderPiano):
        try:
            transaction = Transaction.objects.get(siebel_sale_order=saleOrderPiano)
        except:
            pass
        else:
            return transaction.subscription_id_str
        return ''


class PaymentPianoResource(resources.ModelResource):
    state = Field(attribute='state', column_name='state')
    cod_response = Field(attribute='cod_response', column_name='cod_response')
    siebel_request = Field(attribute='siebel_request', column_name='siebel_request')
    created = Field(attribute='created', column_name='created')
    last_updated = Field(attribute='last_updated', column_name='last_updated')
    id_transaction = Field(attribute='id_transaction', column_name='id_transaction')

    class Meta:
        model = PaymentPiano
        report_skipped = True
        fields = ('id_transaction', 'state', 'cod_response', 'siebel_request', 'created', 'last_updated',)
        export_order = ('id_transaction', 'state', 'cod_response', 'siebel_request', 'created', 'last_updated',)

    def dehydrate_id_transaction(self, paymentPiano):
        if paymentPiano.siebel_request:
            start = '<tem:num_liquida_id>'
            end = '</tem:num_liquida_id>'
            csr = paymentPiano.siebel_request
            return csr[csr.find(start) + len(start):csr.find(end)]
        else:
            return ''


class BlockedSubscriptionsResource(resources.ModelResource):
    subscription_id_piano = Field(attribute='subscription_id_piano', column_name='subscription_id_piano')
    type = Field(attribute='type', column_name='type')

    class Meta:
        model = BlockedSubscriptions
        report_skipped = True
        fields = ('subscription_id_piano', 'type', )
        export_order = ('subscription_id_piano', 'type', )

