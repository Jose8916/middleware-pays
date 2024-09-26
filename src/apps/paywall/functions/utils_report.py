from datetime import datetime, timedelta

from django.conf import settings
from django.utils.html import format_html
from django.utils import formats, timezone

from apps.paywall.models import Subscription, Operation, Payment, PaymentTracking
from apps.paywall.arc_clients import SalesClient
from apps.arcsubs.utils import timestamp_to_datetime


def get_profile_old(self, obj):
    delivery = self.get_delivery(obj)
    if obj.payment_profile:
        return format_html(
            '<i class="fas fa-user fa-sm"></i> {full_name}</br>'
            '<b>{document_type}</b>: {document_number}</br>'
            '<b>Email de compra</b>: {email_compra}</br>'
            '<b>Entecode</b>: {entecode}</br>'
            '<b>Delivery</b>: {delivery}</br>',
            full_name=obj.payment_profile.get_full_name(),
            document_type=obj.payment_profile.prof_doc_type or '',
            document_number=obj.payment_profile.prof_doc_num or '',
            email_compra=obj.payment_profile.portal_email or '',
            entecode=obj.payment_profile.siebel_entecode or '',
            delivery=delivery or ''
        )
    else:
        return ''


def get_info_payment(obj):
    try:
        payment_profile_link = '/admin/paywall/paymentprofile/{}/change/'.format(
            obj.payment_profile.id
        )
    except Exception:
        payment_profile_link = ''

    tz = timezone.get_current_timezone()

    try:
        tz_date = obj.starts_date.astimezone(tz)
        date_start_suscription = formats.date_format(tz_date, settings.DATETIME_FORMAT)
    except Exception as name_exception:
        date_start_suscription = 'Error en la fecha de suscripcion' + str(name_exception)

    try:
        payment_traking = obj.traking if obj.traking else ''
    except Exception:
        payment_traking = ''

    points = ''
    url_referer = ''
    full_url_referer = ''

    if payment_traking and payment_traking.url_referer:
        url_referer = payment_traking.url_referer
        if len(url_referer) > 32:
            url_referer = url_referer[:32]
            points = '...'
        full_url_referer = payment_traking.url_referer

    try:
        full_name = obj.payment_profile.get_full_name()
    except Exception:
        full_name = ''

    try:
        doc_type = obj.payment_profile.prof_doc_type
    except Exception:
        doc_type = ''

    try:
        doc_num = obj.payment_profile.prof_doc_num
    except Exception:
        doc_num = ''

    try:
        portal_email = obj.payment_profile.portal_email
    except Exception:
        portal_email = ''

    try:
        user_agent_str = payment_traking.user_agent_str
    except Exception:
        user_agent_str = ''

    return format_html(
        '<i class="fas fa-user fa-sm"></i> {full_name}'
        '<a href="{payment_profile_link}" target="_blank"><small>(ver)</small></a></br>'
        '<b>{document_type}</b>: {document_number}</br>'
        '<i class="fas fa-calendar-alt"></i> {date}</br>'
        '<b>Email de pago:</b> {email_pago}</br>'
        '<i class="fas fa-wrench"></i> {device}</br>'
        '<i class="fas fa-tag"></i> {medium}</br>'
        '<i class="fas fa-link"></i> <div style="display:inline; max-width: 198px;overflow: hidden;"><div style="display:inline;">{url_referer}</div><div style="display:none;">{full_url_referer}</div><span onclick=show(this)>{points}</span></div></br>'
        '<b>Browser:</b> {browser}',
        full_name=full_name,
        document_type=doc_type,
        document_number=doc_num,
        payment_profile_link=payment_profile_link,
        date=date_start_suscription,
        email_pago=portal_email,
        device=payment_traking.get_device_display() if payment_traking else '',
        medium=payment_traking.medium if payment_traking else '',
        url_referer=url_referer if url_referer else '',
        points=points,
        full_url_referer=full_url_referer,
        browser=user_agent_str,
    )


def get_subscription_data(obj):
    """
        Obtiene el detalle de uns subscripcion
        parametro de entrada:
        obj: la instancia de una subscripcion
    """
    tz = timezone.get_current_timezone()
    tz_created = obj.starts_date.astimezone(tz)
    title = obj.plan.plan_name if obj.plan_id else ''
    title += ' [{}]'.format(obj.campaign.get_category()) if obj.campaign_id else ' [--]'

    if obj.state == Subscription.ARC_STATE_ACTIVE:
        name_icon = 'full'
    elif obj.state == Subscription.ARC_STATE_CANCELED or obj.state == Subscription.ARC_STATE_SUSPENDED:
        name_icon = 'half'
    elif obj.state == Subscription.ARC_STATE_TERMINATED:
        name_icon = 'empty'
    else:
        name_icon = ''

    message = ''
    motivo_baja = ''

    for event in obj.data.get('events'):
        if event.get('eventType') == 'TERMINATE_SUBSCRIPTION':
            message = 'Motivo de baja: '
            motivo_baja = event.get('details')

    return format_html(
        '<strong>{title}</strong></br>'
        '<i class="fas fa-key"></i> ID {key}</br>'
        '<i class="fas fa-arrow-circle-up"></i> <strong>{created}</strong></br>'
        '<i class="fas fa-newspaper"></i> {site}</br>'
        '<i class="fas fa-battery-{name_icon}"></i> {state}</br>'
        '<b>{message}</b>{motivo_baja}',
        title=title,
        site=obj.partner,
        key=obj.arc_id,
        created=formats.date_format(tz_created, settings.DATETIME_FORMAT),
        state=obj.get_state_display(),
        name_icon=name_icon,
        message=message,
        motivo_baja=motivo_baja,
    )


def get_payments(obj):
    try:
        tz = timezone.get_current_timezone()
        payment_obj = Operation.objects.get(payment__pa_origin='WEB', payment__subscription=obj)
        delivery = payment_obj.siebel_delivery
        operations = Operation.objects.filter(payment__subscription=obj)
        list_payment = []
        for operation in operations:
            if operation.conciliation_cod_response == '1':
                estado_pago = 'Enviado a Siebel'
                color = 'blue'
            else:
                estado_pago = 'No enviado a Siebel'
                color = 'red'

            if operation.payment.paymenttracking.confirm_subscription == str(PaymentTracking.ACCEPT_PURCHASE):
                accept_double_charge = 'Acepta doble compra'
            elif operation.payment.paymenttracking.confirm_subscription == str(PaymentTracking.NOT_ACCEPTS_PURCHASE):
                accept_double_charge = 'No acepta doble compra'
            elif operation.payment.paymenttracking.confirm_subscription == str(PaymentTracking.NOT_GO_THROUGH_FLOW):
                accept_double_charge = 'No paso por el flujo'
            else:
                accept_double_charge = ''

            dict_payment = {
                'date_pay': formats.date_format(operation.payment.date_payment.astimezone(tz), settings.DATETIME_FORMAT),
                'monto': operation.payment.pa_amount,
                'estado_pago': estado_pago,
                'color': color,
                'arc_order': operation.payment.arc_order,
                'delivery': delivery,
                'accept_double_charge': accept_double_charge
            }
            list_payment.append(dict_payment)
        return list_payment
    except Exception:
        return ''


def get_first_payment_detail(obj):
    try:
        payment_obj = Operation.objects.get(payment__pa_origin='WEB', payment__subscription=obj)
        delivery = payment_obj.siebel_delivery
        if payment_obj.conciliation_cod_response == '1':
            estado_pago = 'Enviado'
            color = 'blue'
        else:
            estado_pago = 'No enviado'
            color = 'red'
    except Exception:
        estado_pago = 'No enviado'
        color = 'red'
        delivery = '--'

    return format_html(
        '<li><b>Delivery: {delivery} </li></br>'
        '<li><b>Pago:</b> <font color="{color}">{estado_pago}</font></li><br>',
        delivery=delivery,
        estado_pago=estado_pago,
        color=color
    )


def get_refund(obj):
    list_transactions = []
    try:
        operation_obj = Operation.objects.get(payment__pa_origin='WEB', payment__subscription=obj)
        delivery = operation_obj.siebel_delivery
        list_payment = Payment.objects.filter(subscription=obj)
        for payment_obj in list_payment:
            refund_obj = SalesClient().get_order(
                site=obj.partner.partner_code,
                order_id=payment_obj.arc_order
            )

            for pay in refund_obj['payments']:
                for transaction in pay['financialTransactions']:
                    if transaction['transactionType'] == 'Refund':
                        amount = transaction['amount']
                        transaction_date = timestamp_to_datetime(transaction['transactionDate'])
                        dict_transactions = {
                            'amount': amount,
                            'transaction_date': transaction_date,
                            'arc_order': payment_obj.arc_order,
                            'delivery': delivery
                        }
                        list_transactions.append(dict_transactions)
    except Exception as e:
        print(e)

    return list_transactions


def get_info_login_user(user):
    user_link = '/admin/arcsubs/arcuser/{}/change/'.format(user.id)
    full_name = user.get_full_name()

    return format_html(
        '<i class="fas fa-user fa-sm"></i> {full_name} '
        '<a href="{user_link}" target="_blank"><small>(ver)</small></a></br>'
        '<i class="fas fa-fingerprint"></i> {uuid}</br>'
        '<b>Email de Logueo:</b> {email}</br>',
        full_name=full_name if full_name else '--',
        user_link=user_link,
        email=user.get_email(),
        uuid=user.uuid,
    )