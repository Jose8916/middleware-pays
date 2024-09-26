import csv
from datetime import date, datetime, timedelta
from django.db.models import Count
from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.postgres import fields
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import path
from django.utils import formats, timezone
from django.utils.encoding import smart_str
from django.utils.html import format_html
from django_json_widget.widgets import JSONEditorWidget
from import_export.admin import ExportMixin
from rangefilter.filter import DateRangeFilter, DateTimeRangeFilter
from django.db.models import CharField
from django.db.models.functions import Length

from apps.clubelcomercio.clients import ClubClient
from apps.clubelcomercio.models import ClubRegister
from apps.paywall.models import Operation, Subscription as SubscriptionArc
from apps.piano.piano_clients import IDClient, VXClient
from apps.piano.constants import LIST_WITHOUT_TRANSACTIONS_RECOGNITION
from apps.piano.utils.utils_functions import (get_data_to_club,
                                              get_start_subscription, format_date_start_subscription)
from apps.piano.utils_models import (get_or_create_subscription,
                                     get_payment_profile)
from apps.siebel.models import SiebelConfirmationPayment

from .models import (BlockedSubscriptions, LoadReport, LowSubscriptions,
                     PaymentPiano, RenovationPiano, ReportTransactions,
                     SaleOrderPiano, Subscription, SubscriptionMatchArcPiano,
                     Term, Transaction, TransactionsWithNewDate, Unsubscribe, SubscriptionToFix, EnableSubscriptions,
                     PromotionTerm)
from .resources import (LowSubscriptionsResource, PaymentPianoResource,
                        RenovationResource, SubscriptionMatchArcPianoResource,
                        SubscriptionsResource, TransactionResource,
                        TransactionsWithNewDateResource, BlockedSubscriptionsResource, SaleOrderPianoResource)
from apps.piano.utils.download_report import VXProcess
import xlwt


def format_timestamp_to_date(date_timestamp):
    date_time_obj = datetime.fromtimestamp(date_timestamp)
    tz = timezone.get_current_timezone()
    return date_time_obj.astimezone(tz)


def sync_up_suscription(modeladmin, request, queryset):
    for instance in queryset:
        delivery = None
        if instance.app_id == settings.PIANO_APPLICATION_ID['gestion']:
            brand = 'gestion'
        elif instance.app_id == settings.PIANO_APPLICATION_ID['elcomercio']:
            brand = 'elcomercio'
        else:
            brand = ''

        if not instance.delivery:
            transactions = Transaction.objects.filter(subscription_id_str=instance.subscription_id)
            for transaction in transactions:
                if transaction.siebel_sale_order:
                    if transaction.siebel_sale_order.delivery:
                        delivery = transaction.siebel_sale_order.delivery
                        break
            instance.delivery = delivery
            instance.save()

            if not instance.delivery:
                try:
                    subs_match = SubscriptionMatchArcPiano.objects.get(
                        subscription_id_piano=instance.subscription_id
                    )
                except:
                    subs_match = None

                if subs_match:
                    try:
                        subscription_arc = SubscriptionArc.objects.get(arc_id=subs_match.subscription_id_arc)
                        delivery = subscription_arc.delivery
                    except:
                        pass

                    if delivery:
                        instance.delivery = delivery
                        instance.save()

        if not instance.start_date:
            subscription = VXClient().get_subscription(brand, instance.subscription_id)
            subscription_dict = subscription.get('subscription')

            subs = Subscription.objects.get(
                app_id=instance.app_id,
                subscription_id=instance.subscription_id
            )
            subs.start_date = format_timestamp_to_date(subscription_dict.get('start_date'))
            subs.save()

        if not instance.payment_profile:
            subscription = VXClient().get_subscription(brand, instance.subscription_id)
            subscription_dict = subscription.get('subscription')
            user_dict = subscription_dict.get('user')
            instance.payment_profile = get_payment_profile(user_dict.get('uid'), brand, instance)
            instance.save()

        if not instance.term:
            transaction = Transaction.objects.filter(
                subscription=instance
            ).first()
            try:
                if transaction.term:
                    instance.term = transaction.term
                    instance.save()
            except:
                pass
        if not instance.uid:
            subscription = VXClient().get_subscription(brand, instance.subscription_id)
            subscription_dict = subscription.get('subscription')
            instance.uid = subscription_dict.get('user', {}).get('uid', '')
            instance.save()


def export_payments_csv(modeladmin, request, queryset):
    import csv

    from django.utils.encoding import smart_str
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=report.csv'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))  # BOM (optional...Excel needs it to open UTF-8 file properly)
    writer.writerow([
        smart_str("Nro liquidacion"),
        smart_str("cod_response")
    ])

    for obj in queryset:
        if obj.siebel_request:
            start = '<tem:num_liquida_id>'
            end = '</tem:num_liquida_id>'
            csr = obj.siebel_request
            nro_liquida = csr[csr.find(start) + len(start):csr.find(end)]
        else:
            nro_liquida = ''

        writer.writerow([
            smart_str(nro_liquida),
            obj.cod_response
        ])
    return response


def reset_counter(modeladmin, request, queryset):
    for obj in queryset:
        obj.siebel_hits = 0
        obj.save()


def export_payments_with_log_csv(modeladmin, request, queryset):
    import csv

    from django.utils.encoding import smart_str
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=report.csv'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))  # BOM (optional...Excel needs it to open UTF-8 file properly)
    writer.writerow([
        smart_str("Nro liquidacion"),
        smart_str("request"),
        smart_str("response"),
        smart_str("fecha de creacion"),
        smart_str("cod_response")
    ])

    for obj in queryset:
        if obj.siebel_request:
            start = '<tem:num_liquida_id>'
            end = '</tem:num_liquida_id>'
            csr = obj.siebel_request
            nro_liquida = csr[csr.find(start) + len(start):csr.find(end)]
        else:
            nro_liquida = ''

        writer.writerow([
            smart_str(nro_liquida),
            obj.siebel_request,
            obj.siebel_response,
            obj.created,
            obj.cod_response
        ])
    return response


export_payments_csv.short_description = u"Export pagos CSV"
export_payments_with_log_csv.short_description = u"Export pagos con log CSV"


class Brand_Filter(admin.SimpleListFilter):
    title = 'brand_filter'
    parameter_name = 'brand_filter'

    def lookups(self, request, model_admin):
        return (
            ('gestion', 'Gestion'),
            ('elcomercio', 'Elcomercio'),
        )

    def queryset(self, request, queryset):
        if self.value() in ['gestion', 'elcomercio']:
            return queryset.filter(
                siebel_renovation_transaction__subscription__app_id=settings.PIANO_APPLICATION_ID[self.value()]
            )
        else:
            return queryset


class TransactionIdFilter(admin.SimpleListFilter):
    title = 'transaction_id_filter'
    parameter_name = 'transaction_id_filter'

    def lookups(self, request, model_admin):
        return (
            ('with_transaction_id', 'con transactionid'),
            ('without_transaction_id', 'sin transactionid'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'with_transaction_id':
            return queryset.exclude(payu_transaction_id__isnull=True).exclude(payu_transaction_id='')
        elif self.value() == 'without_transaction_id':
            return queryset.filter(payu_transaction_id__isnull=True)
        else:
            return queryset


class HitsFilter(admin.SimpleListFilter):
    title = 'hitsfilter'
    parameter_name = 'hits_filter'

    def lookups(self, request, model_admin):
        return (
            ('greater_than_10', 'Mayor a 10'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'greater_than_10':
            return queryset.filter(siebel_hits__gte=10)
        else:
            return queryset


@admin.register(PaymentPiano)
class PaymentPianoAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = PaymentPianoResource
    search_fields = ('siebel_request', )
    list_display = ('cod_response', 'created', 'last_updated', 'siebel_hits',)
    list_filter = (('created', DateTimeRangeFilter), ('last_updated', DateTimeRangeFilter), 'cod_response', HitsFilter, 'siebel_hits')
    actions = (export_payments_csv, export_payments_with_log_csv, reset_counter)


class WidthoutProfileFilter(admin.SimpleListFilter):
    title = 'profile'
    parameter_name = 'profile_filter'

    def lookups(self, request, model_admin):
        return (
            ('sin_profile', 'Sin profile'),
            ('con_profile', 'Con profile'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'sin_profile':
            return queryset.filter(payment_profile__isnull=True)
        elif self.value() == 'con_profile':
            return queryset.filter(payment_profile__isnull=False)
        else:
            return queryset


class WithoutTermFilter(admin.SimpleListFilter):
    title = 'Sin term'
    parameter_name = 'withoutterm'

    def lookups(self, request, model_admin):
        return (
            ('sin_term', 'Sin term'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'sin_term':
            return queryset.filter(term__isnull=True)
        else:
            return queryset


class WithoutUIDFilter(admin.SimpleListFilter):
    title = 'Sin UID'
    parameter_name = 'withoutUID'

    def lookups(self, request, model_admin):
        return (
            ('sin_uid', 'Sin UID'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'sin_uid':
            return queryset.filter(uid__isnull=True)
        else:
            return queryset


class SubscriptionDeliveryFilter(admin.SimpleListFilter):
    title = 'Delivery'
    parameter_name = 'delivery_filter'

    def lookups(self, request, model_admin):
        return (
            ('con_delivery', 'Con delivery'),
            ('sin_delivery', 'Sin delivery'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'con_delivery':
            return queryset.filter(delivery__isnull=False)
        elif self.value() == 'sin_delivery':
            return queryset.filter(delivery__isnull=True)
        else:
            return queryset


def send_club(modeladmin, request, queryset):
    for subscription in queryset:
        if subscription.start_date >= get_start_subscription(subscription.app_id):
            data = get_data_to_club(subscription)
            if data:
                valida = ClubRegister.objects.filter(
                    subscription_str=subscription.subscription_id,
                    status_response=200
                ).exists()
                if not valida:
                    club_client = ClubClient()
                    response_status, response_detail = club_client.register_club(body=data, club=ClubRegister())
                    if response_status:
                        messages.info(request, 'Ejecucion exitosa ' + str(subscription.subscription_id))
                    else:
                        messages.info(request, 'Error ' + str(response_detail))
                else:
                    messages.info(request, 'suscripcion ya fue enviada anteriormente ' + str(subscription.subscription_id))
            else:
                print('Club Register no ejecutado')
                messages.info(request, 'Club Register no ejecutado ' + str(data))
        else:
            messages.info(request, 'fecha de inicio no valida ' + str(subscription.subscription_id))


def export_subscriptions_csv(modeladmin, request, queryset):
    import csv
    fecha_report = date.today().strftime("%d-%m-%Y")
    from django.utils.encoding import smart_str
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=report' + fecha_report + '.csv'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))  # BOM (optional...Excel needs it to open UTF-8 file properly)
    writer.writerow([
        smart_str("subscription_id"),
        smart_str("delivery"),
        smart_str(u"app_id"),
        smart_str(u"email"),
        smart_str(u"prof_doc_type"),
        smart_str(u"prof_doc_num"),
        smart_str(u"first_name"),
        smart_str(u"last_name"),
        smart_str(u"personal_name")
    ])

    for obj in queryset:
        if obj.app_id == settings.PIANO_APPLICATION_ID['gestion']:
            brand = 'gestion'
        elif obj.app_id == settings.PIANO_APPLICATION_ID['elcomercio']:
            brand = 'elcomercio'
        else:
            brand = ''

        document_type = document_number = None
        subscription_ = VXClient().get_subscription(brand, obj.subscription_id)
        subscription_dict = subscription_.get('subscription')
        user_dict = subscription_dict.get('user')
        try:
            email = user_dict.get('email')
        except:
            email = ''

        data = IDClient().get_uid(user_dict.get('uid'), brand)
        user = data.get('user')

        try:
            custom_fields = user.get('custom_fields', '')
        except:
            custom_fields = []

        for fields in custom_fields:
            if fields.get('fieldName', '') == 'document_type':
                document_type = fields.get('value', '')
                inicial = '[\"'
                final = '\"]'
                try:
                    document_type = document_type.replace(inicial, "")
                    document_type = document_type.replace(final, "")
                except Exception:
                    document_type = ''
            if fields.get('fieldName', '') == 'document_number':
                document_number = fields.get('value', '')

        writer.writerow([
            smart_str(obj.subscription_id),
            smart_str(obj.delivery),
            smart_str(obj.app_id),
            smart_str(email),
            smart_str(document_type),
            smart_str(document_number),
            smart_str(user_dict.get('first_name')),
            smart_str(user_dict.get('last_name', '')),
            smart_str(user_dict.get('personal_name', ''))
        ])
    return response


export_subscriptions_csv.short_description = u"Export CSV"


class WrongDNIFilter(admin.SimpleListFilter):
    title = 'dni erroneo'
    parameter_name = 'wrong_dni'

    def lookups(self, request, model_admin):
        return (
            ('wrong_dni', 'DNI diferente a 8 digitos'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'wrong_dni':
            CharField.register_lookup(Length, 'length')

            return queryset.filter(
                payment_profile__prof_doc_type='DNI'
            ).exclude(
                payment_profile__prof_doc_num__length=8
            )
        else:
            return queryset


class EnteFilter(admin.SimpleListFilter):
    title = 'Con ente'
    parameter_name = 'with_ente'

    def lookups(self, request, model_admin):
        return (
            ('with_ente', 'Con entecode'),
            ('without_ente', 'Sin entecode'),
            ('only_ente', 'Solo con entecode'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'with_ente':
            return queryset.filter(
                payment_profile__siebel_entecode__isnull=False,
                payment_profile__siebel_entedireccion__isnull=False
            )
        elif self.value() == 'without_ente':
            return queryset.filter(
                payment_profile__siebel_entecode__isnull=True,
                payment_profile__siebel_entedireccion__isnull=True
            )
        elif self.value() == 'only_ente':
            return queryset.filter(
                payment_profile__siebel_entecode__isnull=False,
                payment_profile__siebel_entedireccion__isnull=True
            )
        else:
            return queryset


def siebel_tramas(modeladmin, request, queryset):
    fecha_report = date.today().strftime("%d-%m-%Y")
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename=report' + fecha_report + '.xls'
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet("MyModel")

    row_num = 0

    columns = [
        (u"subscription_id", 6000),
        (u"delivery", 6000),
        (u"entecode", 6000),
        (u"Payu transactionId", 6000),
        (u"ENTE Trama envio", 6000),
        (u"Ente trama respuesta", 6000),
        (u"Delivery trama envio", 6000),
        (u"Delivery trama respuesta", 6000),
        (u"Bloqueado", 6000),
        (u"Pago Descripcion", 6000),
        (u"Nota de suscripcion", 6000),
    ]

    font_style = xlwt.XFStyle()
    font_style.font.bold = True

    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num][0], font_style)
        # set column width
        ws.col(col_num).width = columns[col_num][1]

    font_style = xlwt.XFStyle()
    font_style.alignment.wrap = 1

    for obj in queryset:
        row_num += 1
        bloqueado = None
        ov_request = None
        ov_response = None

        try:
            transaction = Transaction.objects.get(
                subscription_id_str=obj.subscription_id,
                initial_payment=True
            )
        except:
            transaction = ''
        else:
            if transaction.block_sending or transaction.devolution:
                bloqueado = True

            if transaction.siebel_sale_order:
                ov_request = transaction.siebel_sale_order.siebel_request
                ov_response = transaction.siebel_sale_order.siebel_response

        if obj.locked:
            bloqueado = True

        row = [
            obj.subscription_id,
            obj.delivery,
            obj.payment_profile.siebel_entecode if obj.payment_profile else '',
            transaction.payu_transaction_id if transaction else '',
            obj.payment_profile.siebel_request if obj.payment_profile else '',
            obj.payment_profile.siebel_response if obj.payment_profile else '',
            ov_request,
            ov_response,
            bloqueado,
            transaction.observation if transaction else '',
            obj.note
        ]

        for col_num in range(len(row)):
            ws.write(row_num, col_num, str(row[col_num]), font_style)

    wb.save(response)
    return response


siebel_tramas.short_description = u"Exportar tramas siebel"


@admin.register(Subscription)
class SubscriptionAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = SubscriptionsResource
    list_display = ('delivery', 'subscription_id', 'app_id', 'start_date', 'get_profile', 'term', 'uid', 'created',
                    'last_updated',)
    list_filter = (('start_date', DateTimeRangeFilter), 'app_id', SubscriptionDeliveryFilter, WidthoutProfileFilter,
                   'locked', EnteFilter, WrongDNIFilter, 'sent_club', WithoutTermFilter, 'term', WithoutUIDFilter,)
    search_fields = ('delivery', 'subscription_id', 'uid', 'term__term_id', )
    readonly_fields = ['subscription_id', 'app_id', 'start_date', 'sent_club', 'delivery', 'payment_profile']
    actions = (siebel_tramas, sync_up_suscription, export_subscriptions_csv, send_club)

    def has_delete_permission(self, request, obj=None):
        # Disable delete
        return False

    def get_profile(self, obj):
        if obj.payment_profile:
            profile_link = '/admin/paywall/paymentprofile/{}/change/'.format(obj.payment_profile.id)

            return format_html(
                '<b>{document_type}:</b> <a href="{profile_link}" target="_blank">{document_number}</a> <br>'
                '<b>Entecode:</b> {entecode} <br>'
                '<b>EnteDirection:</b> {entedirection}<br>',
                document_type=obj.payment_profile.prof_doc_type,
                document_number=obj.payment_profile.prof_doc_num,
                entecode=obj.payment_profile.siebel_entecode,
                entedirection=obj.payment_profile.siebel_entedireccion,
                profile_link=profile_link
            )
        else:
            return ''


@admin.register(SaleOrderPiano)
class SaleOrderPianoAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = SaleOrderPianoResource
    list_display = ('delivery', 'siebel_response', 'created', 'last_updated', 'siebel_hits',)
    search_fields = ('delivery', 'siebel_request',)
    list_filter = (('created', DateTimeRangeFilter), HitsFilter,)
    actions = (reset_counter,)


def sync_up(modeladmin, request, queryset):
    for instance in queryset:
        if not instance.subscription:
            for brand_ in ['elcomercio', 'gestion']:
                obj_sub = get_or_create_subscription(instance.subscription_id_str, brand_)
                if obj_sub:
                    instance.subscription = obj_sub
                    instance.save()
                    break

        if instance.subscription.app_id == settings.PIANO_APPLICATION_ID['gestion']:
            brand = 'gestion'
        elif instance.subscription.app_id == settings.PIANO_APPLICATION_ID['elcomercio']:
            brand = 'elcomercio'
        else:
            brand = ''

        if not instance.term:
            try:
                term = Term.objects.get(
                    term_id=instance.term_identifier
                )
            except:
                term = None
            if term:
                instance.term = term
                instance.save()
        if not instance.payment_profile:
            instance.payment_profile = get_payment_profile(instance.user_id, brand, instance.subscription)
            instance.save()

        if not instance.access_from_date:
            date_time_obj = datetime.strptime(instance.access_from, '%m/%d/%Y')
            tz = timezone.get_current_timezone()
            instance.access_from_date = date_time_obj.astimezone(tz)
            instance.save()


def sync_up_low_subscriptions(modeladmin, request, queryset):
    for instance in queryset:
        if instance.subscription:
            if not instance.subscription.delivery:
                delivery = None
                subs = instance.subscription

                try:
                    subs_match = SubscriptionMatchArcPiano.objects.get(
                        subscription_id_piano=subs.subscription_id
                    )
                except:
                    subs_match = None

                if subs_match:
                    try:
                        subscription_arc = SubscriptionArc.objects.get(arc_id=subs_match.subscription_id_arc)
                        delivery = subscription_arc.delivery
                    except:
                        pass

                if delivery:
                    subs.delivery = delivery
                    subs.save()


class FailPaymentFilter(admin.SimpleListFilter):
    title = 'pagos fallidos'
    parameter_name = 'fail_payment'

    def lookups(self, request, model_admin):
        return (
            ('fail_payment', 'Pagos fallidos'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'fail_payment':
            return queryset.filter(siebel_payment__cod_response=False)
        else:
            return queryset


class FailRenovationVouchersFilter(admin.SimpleListFilter):
    title = 'renovacion fallida(generacion de comprobantes)'
    parameter_name = 'fail_renovation'

    def lookups(self, request, model_admin):
        return (
            ('fail_renovation', 'Renovacion fallida'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'fail_renovation':
            return queryset.filter(siebel_renovation__state=False)
        else:
            return queryset


class TransactionWithoutTermFilter(admin.SimpleListFilter):
    title = 'Sin Term'
    parameter_name = 'without_term'

    def lookups(self, request, model_admin):
        return (
            ('without_term', 'Sin term'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'without_term':
            return queryset.filter(term__isnull=True)
        else:
            return queryset


class DeliveryFilter(admin.SimpleListFilter):
    title = 'Delivery'
    parameter_name = 'delivery_filter'

    def lookups(self, request, model_admin):
        return (
            ('con_delivery', 'Con delivery'),
            ('sin_delivery', 'Sin delivery'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'con_delivery':
            return queryset.filter(subscription__delivery__isnull=False)
        elif self.value() == 'sin_delivery':
            return queryset.filter(subscription__delivery__isnull=True)
        else:
            return queryset


class SiebelConfirmationPaymentFilter(admin.SimpleListFilter):
    title = 'Confirmacion'
    parameter_name = 'confirmacion_filter'

    def lookups(self, request, model_admin):
        return (
            ('con_confirmacion', 'Con confirmacion'),
            ('sin_confirmacion', 'Sin confirmacion'),
        )

    def queryset(self, request, queryset):
        list_filter = []
        if self.value() == 'con_confirmacion':
            for obj in queryset:
                if SiebelConfirmationPayment.objects.filter(num_liquidacion=obj.payu_transaction_id).exists():
                    list_filter.append(obj.payu_transaction_id)
            return queryset.filter(payu_transaction_id__in=list_filter)
        elif self.value() == 'sin_confirmacion':
            for obj in queryset:
                if not SiebelConfirmationPayment.objects.filter(num_liquidacion=obj.payu_transaction_id).exists():
                    list_filter.append(obj.payu_transaction_id)
            return queryset.filter(payu_transaction_id__in=list_filter)
        else:
            return queryset


class BrandFilter(admin.SimpleListFilter):
    title = 'brand'
    parameter_name = 'brand_filter'

    def lookups(self, request, model_admin):
        return (
            ('elcomercio', 'El Comercio'),
            ('gestion', 'gestion'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'elcomercio':
            return queryset.filter(term__app_id=settings.PIANO_APPLICATION_ID['elcomercio'])
        elif self.value() == 'gestion':
            return queryset.filter(term__app_id=settings.PIANO_APPLICATION_ID['gestion'])
        else:
            return queryset


class LowDeliveryFilter(admin.SimpleListFilter):
    title = 'Con delivery'
    parameter_name = 'delivery_filter'

    def lookups(self, request, model_admin):
        return (
            ('con_delivery', 'Con delivery'),
            ('sin_delivery', 'Sin delivery'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'con_delivery':
            return queryset.filter(subscription__delivery__isnull=False)
        elif self.value() == 'sin_delivery':
            return queryset.filter(subscription__delivery__isnull=True)
        else:
            return queryset


class PaymentFilter(admin.SimpleListFilter):
    title = 'Con pago'
    parameter_name = 'payment_filter'

    def lookups(self, request, model_admin):
        return (
            ('with_payment', 'Con pago'),
            ('without_payment', 'Sin pago'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'with_payment':
            return queryset.filter(siebel_payment__cod_response=True)
        elif self.value() == 'without_payment':
            return queryset.exclude(siebel_payment__cod_response=True)
        else:
            return queryset


class RenewalFilter(admin.SimpleListFilter):
    title = 'Con renovacion'
    parameter_name = 'renewal_filter'

    def lookups(self, request, model_admin):
        return (
            ('with_renewal', 'Con renovación'),
            ('without_renewal', 'Sin renovación'),
            ('fail_renewal', 'renovacion fallida'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'with_renewal':
            return queryset.filter(siebel_renovation__state=True)
        elif self.value() == 'without_renewal':
            return queryset.exclude(siebel_renovation__state=True)
        elif self.value() == 'fail_renewal':
            return queryset.filter(siebel_renovation__state=False)
        else:
            return queryset


class LowSendSiebelFilter(admin.SimpleListFilter):
    title = 'Enviado a siebel'
    parameter_name = 'low_send_siebel'

    def lookups(self, request, model_admin):
        return (
            ('send_to_siebel', 'Baja enviada a siebel'),
            ('no_send_to_siebel', 'Baja no enviada a siebel'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'send_to_siebel':
            return queryset.filter(unsubscribe__sent_to_siebel=True)
        elif self.value() == 'no_send_to_siebel':
            return queryset.exclude(unsubscribe__sent_to_siebel=True)
        else:
            return queryset


@admin.register(LowSubscriptions)
class LowSubscriptionsAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = LowSubscriptionsResource
    list_display = ('subs_id', 'user_email', 'resource_name', 'resource_id', 'start_date', 'status',
                    'get_dates', 'get_siebel_status',)
    list_filter = (
        ('low_subscription', DateTimeRangeFilter),
        'status',
        'resource_id',
        LowDeliveryFilter,
        LowSendSiebelFilter,
        'exclude_to_send_siebel',
    )
    search_fields = ('subs_id',)
    actions = (sync_up_low_subscriptions,)

    def format_dates(self, date):
        return date.strftime("%d-%m-%Y, %H:%M:%S")

    def get_dates(self, obj):
        return format_html(
            '<b>Baja Suscripción:</b> {low_subscription} <br>'
            '<b>Access Expiration:</b> {user_access_expiration_date} <br>',
            low_subscription=self.format_dates(obj.low_subscription),
            user_access_expiration_date=self.format_dates(obj.user_access_expiration_date),
        )

    def get_siebel_status(self, obj):
        try:
            if obj.unsubscribe:
                if obj.unsubscribe.sent_to_siebel:
                    return format_html('<span style="color:blue;"><b>Enviado</b></span>')
        except:
            pass
        return 'No enviado'

    def get_queryset(self, request):
        qs = super(LowSubscriptionsAdmin, self).get_queryset(request)
        return qs.order_by('-low_subscription')

    get_dates.short_description = 'Fechas'
    get_siebel_status.short_description = 'Envio a Siebel'


@admin.register(RenovationPiano)
class RenovationPianoAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = RenovationResource
    search_fields = ('siebel_response', 'siebel_request',)
    list_display = ('state', 'siebel_request', 'created', 'last_updated', 'siebel_hits',)
    list_filter = (('created', DateTimeRangeFilter), ('last_updated', DateTimeRangeFilter),  'state', HitsFilter,
                   Brand_Filter, TransactionIdFilter)
    actions = (reset_counter,)


def download_transactions(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=report_transaction.csv'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))
    writer.writerow([
        smart_str(u"external_tx_id"),
        smart_str(u"access_from"),
        smart_str(u"access_to"),
        smart_str(u"Fecha de pago"),
        smart_str(u"fecha de inicio de suscripcion")
    ])
    for obj in queryset:
        row = [
            obj.external_tx_id,
            obj.access_from,
            obj.access_to,
            obj.payment_date,
            obj.subscription.start_date
        ]
        writer.writerow(row)
    return response


download_transactions.short_description = u"Export pagos CSV"


def download_transactions_payu(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=report_transaction.csv'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))
    writer.writerow([
        smart_str(u"transaction_id"),
        smart_str(u"subscription_id")
    ])
    for obj in queryset:
        row = [
            obj.payu_transaction_id,
            obj.subscription_id_str
        ]
        writer.writerow(row)
    return response


@admin.register(Transaction)
class TransactionAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = TransactionResource
    list_filter = (BrandFilter, 'initial_payment', 'tx_type', DeliveryFilter, PaymentFilter, RenewalFilter,
                   EnteFilter, SiebelConfirmationPaymentFilter, 'original_price', 'block_sending', 'devolution',
                   FailRenovationVouchersFilter, FailPaymentFilter, TransactionWithoutTermFilter, ('subscription__start_date', DateTimeRangeFilter),
                   ('created', DateTimeRangeFilter), ('payment_date', DateTimeRangeFilter), 'term_name',
                   'initial_transaction', )
    list_display = ('get_subscription', 'get_transaction_detail', 'get_period', 'get_payu', 'get_profile',
                    'get_siebel_data',)
    search_fields = ('external_tx_id', 'subscription__subscription_id', 'payu_transaction_id', 'subscription__delivery',
                     'term_identifier',)
    readonly_fields = ['external_tx_id', 'tx_type', 'status', 'term_name', 'term_identifier', 'subscription_id',
                       'user_id', 'initial_transaction', 'payu_order_id', 'siebel_renovation', 'access_from',
                       'access_to', 'payment_date', 'access_from_date', 'amount', 'payu_transaction_id',
                       'payment_source_type', 'term', 'reconciliation_id', 'payment_profile', 'subscription_id_str',
                       'subscription', 'siebel_sale_order', 'id_transaction_paymentos', 'siebel_payment', 'report_data']

    actions = (sync_up, download_transactions, download_transactions_payu, )
    formfield_overrides = {
        fields.JSONField: {'widget': JSONEditorWidget},
    }

    def has_delete_permission(self, request, obj=None):
        # Disable delete
        return False

    def get_queryset(self, request):
        qs = super(TransactionAdmin, self).get_queryset(request)
        return qs.order_by('-payment_date')

    def get_profile(self, obj):
        try:
            payment_profile = obj.subscription.payment_profile
        except:
            payment_profile = None

        payment_profile_link = '/admin/paywall/paymentprofile/{}/change/'.format(
            payment_profile.id
        ) if payment_profile else '#'

        return format_html(
            '<b>Email: </b> {email} '
            '<a href="{payment_profile_link}" target="_blank"><small>(ver)</small></a></br>'
            '<b>Nombre: </b> {siebel_name} <br>'
            '<b>Número de documeneto: </b> {document_number} <br>'
            '<b>Tipo de documento: </b> {type_document} <br>',
            payment_profile_link=payment_profile_link,
            email=payment_profile.portal_email if payment_profile else '',
            siebel_name=payment_profile.siebel_name if payment_profile else '',
            document_number=payment_profile.prof_doc_num if payment_profile else '',
            type_document=payment_profile.prof_doc_type if payment_profile else '',
        )

    def get_subscription(self, obj):
        subs_arc_id = ''
        if obj.subscription:
            if obj.term:
                if obj.term_identifier == 'TMGM0F7MK839' or obj.subscription.start_date < get_start_subscription(obj.term.app_id):
                    try:
                        subs_arc = SubscriptionMatchArcPiano.objects.get(subscription_id_piano=obj.subscription_id_str)
                        subs_arc_id = subs_arc.subscription_id_arc
                    except:
                        pass
        try:
            tz = timezone.get_current_timezone()
            start_date_ = formats.date_format(obj.subscription.start_date.astimezone(tz), settings.DATETIME_FORMAT)
        except:
            start_date_ = ''

        return format_html(
            '<b>ID PIANO: </b> {subscription_id} <br>'
            '<b>ID ARC: </b> {subscription_id_arc} <br>'
            '<b>UID:</b> {user_id} <br>'
            '<b>Fecha de Inicio:</b> {start_date} <br>',
            subscription_id=obj.subscription_id_str,
            subscription_id_arc=subs_arc_id,
            user_id=obj.user_id,
            start_date=start_date_
        )

    def get_payu(self, obj):
        return format_html(
            '<b>TransactionId:</b> {payu_transaction_id} <br>'
            '<b>OrderId:</b> {payu_order_id} <br>'
            '<b>PaymentsOS ReconciliationId:</b> {reconciliation_id} <br>'
            '<b>PaymentsOS Id:</b> {id_transaction_paymentos} <br>',
            payu_transaction_id=obj.payu_transaction_id,
            payu_order_id=obj.payu_order_id,
            reconciliation_id=obj.reconciliation_id,
            id_transaction_paymentos=obj.id_transaction_paymentos,
        )

    def get_period(self, obj):
        try:
            tz = timezone.get_current_timezone()
            payment_date = formats.date_format(obj.payment_date.astimezone(tz), "Y-m-d")
        except:
            payment_date = ''
        brand = ''

        try:
            if obj.term:
                if obj.term.app_id == settings.PIANO_APPLICATION_ID['gestion']:
                    brand = 'gestion'
                elif obj.term.app_id == settings.PIANO_APPLICATION_ID['elcomercio']:
                    brand = 'elcomercio'
        except:
            brand = '*******'

        return format_html(
            '{plan_name} - {brand} <small><a target="_blank" href=/admin/piano/term/{id_plan}/change/>editar</a></small><br>'
            '<b>Term id:</b> {term_id} <br>'
            '<b>access_from:</b> {access_from} <br>'
            '<b>access_to:</b> {access_to} <br>'
            '<b>Fecha de pago: </b> {payment_date}',
            access_from=obj.access_from,
            access_to=obj.access_to,
            payment_date=payment_date,
            plan_name=obj.term.plan_name if obj.term else '',
            id_plan=obj.term.id if obj.term else '',
            brand=brand,
            term_id=obj.term.term_id if obj.term else ''
        )

    def get_transaction_detail(self, obj):
        try:
            date_create = formats.date_format(obj.created, settings.DATETIME_FORMAT)
        except:
            date_create = ''

        return format_html(
            '<b>External tx id:</b> {external_tx_id} <br>'
            '<b>Tx Type:</b> {tx_type} <br>'
            '<b>Initial Payment:</b> {initial_payment} <br>'
            '<b>Monto:</b> {amount} <br>'
            '<b>Fecha de creacion:</b> {date_create}',
            external_tx_id=obj.external_tx_id,
            tx_type=obj.tx_type,
            initial_payment=obj.initial_payment,
            amount=obj.amount,
            date_create=date_create
        )

    def get_siebel_data(self, obj):
        payment_link = '#'
        renewal_link = '#'
        ov_link = '#'

        try:
            delivery = obj.subscription.delivery
            if obj.siebel_sale_order:
                ov_link = '/admin/piano/saleorderpiano/{}/change/'.format(obj.siebel_sale_order.id)
        except:
            delivery = ''

        try:
            entecode = obj.subscription.payment_profile.siebel_entecode
        except Exception as e:
            entecode = e

        try:
            sent_payment = 'No Enviado'
            color = 'black'
            if obj.siebel_payment:
                payment_link = '/admin/piano/paymentpiano/{}/change/'.format(obj.siebel_payment.id)
                if obj.siebel_payment.cod_response:
                    sent_payment = 'Enviado'
                    color = 'blue'

        except Exception as e:
            sent_payment = 'No enviado'

        try:
            if obj.siebel_renovation.state:
                renewal = 'Enviado'
                renewal_link = '/admin/piano/renovationpiano/{}/change/'.format(obj.siebel_renovation.id)
                color_r = '#00008B'
            elif obj.siebel_renovation:
                renewal = 'Enviado pero siebel da error'
                renewal_link = '/admin/piano/renovationpiano/{}/change/'.format(obj.siebel_renovation.id)
                color_r = 'red'
            else:
                renewal = 'No Enviado'
                renewal_link = '/admin/piano/renovationpiano/{}/change/'.format(obj.siebel_renovation.id)
                color_r = 'black'
        except Exception as e:
            renewal = 'No enviado'
            color_r = 'black'

        return format_html(
            '<b>delivery:</b> <a href="{ov_link}" target="_blank">{delivery}</a> <br>'
            '<b>entecode:</b> {entecode} <br>'
            '<b>Pago:</b><a href="{payment_link}" target="_blank"><span style="color: {color};">{pago}</span></a></br>'
            '<b>Renovación:</b> <a href="{renewal_link}" target="_blank"><span style="color: {color_r};">{renewal}</span></a> <br>'
            '<b>Bloqueado:</b> {state}',
            delivery=delivery,
            entecode=entecode,
            pago=sent_payment,
            color=color,
            renewal=renewal,
            color_r=color_r,
            state=obj.block_sending,
            payment_link=payment_link,
            renewal_link=renewal_link,
            ov_link=ov_link
        )

    get_siebel_data.short_description = 'Siebel'
    get_period.short_description = 'Periodo'
    get_transaction_detail.short_description = 'Transacción'
    get_payu.short_description = 'Payu'
    get_subscription.short_description = 'Suscripcion'


def save_term(dict_term):
    if not Term.objects.filter(term_id=dict_term.get('term_id')).exists():
        term = Term(
            plan_name=dict_term.get('name'),
            plan_description=dict_term.get('description'),
            term_id=dict_term.get('term_id'),
            app_id=dict_term.get('aid'),
            data=dict_term
        )
        term.save()


def sync_piano_terms(modeladmin, request, queryset):
    for obj in queryset:
        if obj.app_id == settings.PIANO_APPLICATION_ID['gestion']:
            brand = 'gestion'
        elif obj.app_id == settings.PIANO_APPLICATION_ID['elcomercio']:
            brand = 'elcomercio'
        else:
            brand = ''
        if brand:
            list_terms = VXClient().get_terms(brand)
            for term_ in list_terms.get('terms'):
                if term_.get('type') == 'payment':
                    save_term(term_)
        break


def download_terms(modeladmin, request, queryset):
    fecha_report = date.today().strftime("%d-%m-%Y")
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=report_transaction_' + fecha_report + '.csv'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))
    writer.writerow([
        smart_str(u"payment_billing_plan"),
        smart_str(u"payment_billing_plan_description"),
        smart_str(u"name"),
        smart_str(u"description"),
        smart_str(u"type"),
        smart_str(u"create_date"),
        smart_str(u"payment_currency"),
        smart_str(u"currency_symbol"),
        smart_str(u"payment_renew_grace_period"),
        smart_str(u"payment_allow_promo_codes"),
        smart_str(u"payment_force_auto_renew"),
        smart_str(u"payment_new_customers_only"),
        smart_str(u"payment_trial_new_customers_only"),
        smart_str(u"Brand")
    ])

    list_terms = VXClient().get_terms('elcomercio')
    for term_ in list_terms.get('terms'):
        if term_.get('type') == 'payment':
            row = [
                term_.get('payment_billing_plan'),
                term_.get('payment_billing_plan_description'),
                term_.get('name'),
                term_.get('description'),
                term_.get('type'),
                format_timestamp_to_date(term_.get('create_date')).strftime("%d-%m-%Y, %H:%M:%S"),
                term_.get('payment_currency'),
                term_.get('currency_symbol'),
                term_.get('payment_renew_grace_period'),
                term_.get('payment_allow_promo_codes'),
                term_.get('payment_force_auto_renew'),
                term_.get('payment_new_customers_only'),
                term_.get('payment_trial_new_customers_only'),
                'elcomercio'
            ]
            writer.writerow(row)
    list_terms = VXClient().get_terms('gestion')
    for term_ in list_terms.get('terms'):
        if term_.get('type') == 'payment':
            row = [
                term_.get('payment_billing_plan'),
                term_.get('payment_billing_plan_description'),
                term_.get('name'),
                term_.get('description'),
                term_.get('type'),
                format_timestamp_to_date(term_.get('create_date')).strftime("%d-%m-%Y, %H:%M:%S"),
                term_.get('payment_currency'),
                term_.get('currency_symbol'),
                term_.get('payment_renew_grace_period'),
                term_.get('payment_allow_promo_codes'),
                term_.get('payment_force_auto_renew'),
                term_.get('payment_new_customers_only'),
                term_.get('payment_trial_new_customers_only'),
                'gestion'
            ]
            writer.writerow(row)
    return response


def update_term(modeladmin, request, queryset):
    for obj in queryset:
        if not obj.plan_description:
            if obj.app_id == settings.PIANO_APPLICATION_ID['gestion']:
                brand = 'gestion'
            elif obj.app_id == settings.PIANO_APPLICATION_ID['elcomercio']:
                brand = 'elcomercio'
            else:
                brand = ''
            if brand:
                try:
                    response_term = VXClient().get_term(brand, obj.term_id)
                    dict_term = response_term.get('term')
                    plan_description = dict_term.get('description')
                except:
                    plan_description = ''
                if plan_description:
                    obj.plan_description = plan_description
                    obj.save()


class PromotionTermInline(admin.TabularInline):
    model = PromotionTerm
    extra = 0


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ('plan_name', 'plan_description', 'term_id', 'app_id', 'period', 'product', 'get_dates', 'siebel_code_promo',)
    list_filter = ('app_id', 'period', 'migrated',)
    search_fields = ('siebel_code_promo', 'term_id',)
    readonly_fields = ['plan_name', 'plan_description', 'term_id', 'app_id', 'data']
    formfield_overrides = {
        fields.JSONField: {'widget': JSONEditorWidget},
    }
    inlines = (PromotionTermInline,)
    actions = [
        update_term,
        download_terms,
        sync_piano_terms
    ]

    def get_dates(self, obj):
        return format_html(
            '<b>created:</b> {created} <br>'
            '<b>last_updated:</b> {last_updated}',
            created=obj.created,
            last_updated=obj.last_updated
        )


@admin.register(Unsubscribe)
class UnsubscribeAdmin(admin.ModelAdmin):
    list_display = ('get_subscription', 'sent_to_siebel', 'siebel_request', 'siebel_response',)
    list_filter = ('sent_to_siebel',)

    def get_subscription(self, obj):
        try:
            low = LowSubscriptions.objects.get(unsubscribe=obj)
        except:
            low = None
        if low:
            return low.subscription.subscription_id


@admin.register(TransactionsWithNewDate)
class TransactionsWithNewDateAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = TransactionsWithNewDateResource
    list_display = ('subscription_id_piano', 'external_tx_id', 'access_from', 'access_to', 'brand', 'created', 'last_updated')
    search_fields = ('subscription_id_piano', 'external_tx_id',)
    list_filter = (('created', DateTimeRangeFilter), ('last_updated', DateTimeRangeFilter), 'brand',)
    change_list_template = "admin/piano/subscription_exclude_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            file = request.FILES['csv_file']
            decoded_file = file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            for row in reader:
                if not TransactionsWithNewDate.objects.filter(
                        external_tx_id=row.get('External Tx ID'),
                        subscription_id_piano=row.get('suscripcion')
                ).exists():
                    obj = TransactionsWithNewDate(
                        subscription_id_piano=row.get('suscripcion'),
                        external_tx_id=row.get('External Tx ID'),
                        access_from=row.get('period_from'),
                        access_to=row.get('period_to'),
                        brand=row.get('brand')
                    )
                    obj.save()

            self.message_user(request, "Procesado correctamente")
            return redirect("..")

        form = CsvImportForm()
        payload = {"form": form}
        return render(
            request, "admin/piano/subscription_exclude_csv_form.html", payload
        )


def update_subscription_relation_piano_arc(modeladmin, request, queryset):
    for obj in queryset:
        if not obj.brand:
            try:
                subs = SubscriptionArc.objects.get(arc_id=obj.subscription_id_arc)
            except:
                subs = ''
            if subs:
                if subs.partner.partner_code == 'elcomercio':
                    obj.brand = 'elcomercio'
                    obj.save()
                elif subs.partner.partner_code == 'gestion':
                    obj.brand = 'gestion'
                    obj.save()


@admin.register(SubscriptionMatchArcPiano)
class SubscriptionMatchArcPianoAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = SubscriptionMatchArcPianoResource
    list_display = ('subscription_id_piano', 'subscription_id_arc', 'brand', 'created', 'last_updated',)
    search_fields = ('subscription_id_piano', 'subscription_id_arc',)
    list_filter = (('created', DateTimeRangeFilter), ('last_updated', DateTimeRangeFilter), 'brand',)
    actions = [
        update_subscription_relation_piano_arc,
    ]
    change_list_template = "admin/piano/subscription_exclude_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            file = request.FILES['csv_file']
            decoded_file = file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            for row in reader:
                if not SubscriptionMatchArcPiano.objects.filter(
                        subscription_id_piano=row.get('subscription_id_piano'),
                        subscription_id_arc=row.get('subscription_id_arc'),
                        brand=row.get('brand')
                ).exists():
                    obj = SubscriptionMatchArcPiano(
                        subscription_id_piano=row.get('subscription_id_piano'),
                        subscription_id_arc=row.get('subscription_id_arc'),
                        brand=row.get('brand')
                    )
                    obj.save()

            self.message_user(request, "Procesado correctamente")
            return redirect("..")

        form = CsvImportForm()
        payload = {"form": form}
        return render(
            request, "admin/piano/subscription_exclude_csv_form.html", payload
        )


def validate(name, obj):
    if name == 'external_tx_id':
        try:
            return obj.external_tx_id
        except:
            return ''
    elif name == 'payu_transaction_id':
        try:
            return obj.payu_transaction_id
        except:
            return ''
    elif name == 'suscripcionid':
        try:
            return obj.subscription_id_str
        except:
            return ''
    elif name == 'delivery':
        try:
            if obj.siebel_sale_order.delivery:
                return obj.siebel_sale_order.delivery
            else:
                if obj.subscription.delivery:
                    return obj.subscription.delivery
                else:
                    subs_match = SubscriptionMatchArcPiano.objects.get(
                        subscription_id_piano=obj.subscription_id_str
                    )
                    if subs_match:
                        subscription_arc = SubscriptionArc.objects.get(arc_id=subs_match.subscription_id_arc)
                        return subscription_arc.delivery
        except:
            return ''
    elif name == 'renovacion_enviada':
        try:
            return obj.siebel_renovation.state
        except:
            return ''
    elif name == 'pago_enviado':
        try:
            return obj.siebel_payment.cod_response
        except:
            return ''
    elif name == 'respuesta_ov_request':
        try:
            return obj.siebel_sale_order.siebel_response
        except:
            return ''
    elif name == 'respuesta_renovacion':
        try:
            return obj.siebel_renovation.siebel_response
        except:
            return ''
    elif name == 'respuesta_pago':
        try:
            return obj.siebel_payment.siebel_response
        except:
            return ''
    elif name == 'envio_renovacion':
        try:
            return obj.siebel_renovation.siebel_request
        except:
            return ''
    elif name == 'envio_pago':
        try:
            return obj.siebel_payment.siebel_request
        except:
            return ''
    elif name == 'envio_ov_resquest':
        try:
            return obj.siebel_sale_order.siebel_request
        except:
            return ''
    elif name == 'plan':
        try:
            return obj.subscription.term.plan_name + ' - ' + obj.subscription.term.plan_description
        except:
            return ''
    elif name == 'entecode':
        try:
            return obj.subscription.payment_profile.siebel_entecode
        except:
            return ''
    elif name == 'ente_request':
        try:
            return obj.subscription.payment_profile.siebel_request
        except:
            return ''
    elif name == 'ente_response':
        try:
            return obj.subscription.payment_profile.siebel_response
        except:
            return ''

    else:
        return ''


def export_csv_transactions_by_field(modeladmin, request, queryset):
    fecha_report = date.today().strftime("%d-%m-%Y")
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=report_transaction_' + fecha_report + '.csv'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))
    writer.writerow([
        smart_str(u"TransactionId"),
        smart_str(u"SuscriptionId"),
        smart_str(u"tipo de documento"),
        smart_str(u"Nro de documento")
    ])
    for obj in queryset:
        transactions = obj.transaction_id
        list_transactions = transactions.splitlines()
        transactions_ = Transaction.objects.filter(
            payu_transaction_id__in=list_transactions
        )

        for obj in transactions_:
            document_type = document_number = ''
            if obj.subscription:
                if obj.subscription.payment_profile:
                    document_type = obj.subscription.payment_profile.prof_doc_type
                    document_number = obj.subscription.payment_profile.prof_doc_num

            row = [
                validate('payu_transaction_id', obj),
                validate('suscripcionid', obj),
                document_type,
                document_number
            ]
            writer.writerow(row)
    return response


export_csv_transactions_by_field.short_description = u"Export pagos CSV"


def export_csv_transactions_resume(modeladmin, request, queryset):
    fecha_report = date.today().strftime("%d-%m-%Y")
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=report_transaction_' + fecha_report + '.csv'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))
    writer.writerow([
        smart_str(u"TransactionId"),
        smart_str(u"SuscriptionId"),
        smart_str(u"Delivery"),
        smart_str(u"Envio Renovación"),
        smart_str(u"Envio Pago")
    ])
    for obj in queryset:
        transactions = obj.transaction_id
        list_transactions = transactions.splitlines()
        transactions_ = Transaction.objects.filter(
            subscription_id_str__in=list_transactions
        )

        for obj in transactions_:
            row = [
                validate('payu_transaction_id', obj),
                validate('suscripcionid', obj),
                validate('delivery', obj),
                validate('renovacion_enviada', obj),
                validate('pago_enviado', obj)
            ]
            writer.writerow(row)
    return response


def export_csv_transactions(modeladmin, request, queryset):
    fecha_report = date.today().strftime("%d-%m-%Y")
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=report_transaction_' + fecha_report + '.csv'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))
    writer.writerow([
        smart_str(u"External Tx Id"),
        smart_str(u"TransactionId"),
        smart_str(u"SuscriptionId"),
        smart_str(u"Delivery"),
        smart_str(u"Renovacion Enviada"),
        smart_str(u"Pago enviado"),
        smart_str(u"Respuesta Renovación"),
        smart_str(u"Respuesta Pago"),
        smart_str(u"Envio Renovación"),
        smart_str(u"Envio Pago")
    ])
    for obj in queryset:
        transactions = obj.transaction_id
        list_transactions = transactions.splitlines()
        transactions_ = Transaction.objects.filter(
            subscription_id_str__in=list_transactions
        )

        for obj in transactions_:
            row = [
                validate('external_tx_id', obj),
                validate('payu_transaction_id', obj),
                validate('suscripcionid', obj),
                validate('delivery', obj),
                validate('renovacion_enviada', obj),
                validate('pago_enviado', obj),
                validate('respuesta_renovacion', obj),
                validate('respuesta_pago', obj),
                validate('envio_renovacion', obj),
                validate('envio_pago', obj)
            ]
            writer.writerow(row)
    return response


def send_payment(modeladmin, request, queryset):
    state_message = ""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=reporte_ejecutados.csv'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))
    writer.writerow([
        smart_str(u"idtransaccion"),
        smart_str(u"detalle")
    ])
    for obj in queryset:
        transactions = obj.transaction_id
        list_transactions = transactions.splitlines()

    for transaction in list_transactions:
        try:
            operation = Operation.objects.get(payment__payu_transaction=transaction)
        except Exception as e:
            operation = None
            print(e)

        if operation:
            if not int(operation.conciliation_cod_response):
                operation.conciliation_cod_response = '1'
                operation.save()
                state_message = "ejecutado"
            else:
                state_message = "cod response ya fue cargado"
        else:
            state_message = "No se encontro operacion"

        writer.writerow([
            transaction,
            state_message
        ])
    return response


def export_csv_transaction_with_vouchers(modeladmin, request, queryset):
    fecha_report = date.today().strftime("%d-%m-%Y")
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=report_transaction_' + fecha_report + '.csv'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))
    writer.writerow([
        smart_str(u"idtransaccion"),
        smart_str(u"recepcion Nro liquidacion"),
        smart_str(u"recepcion Delivery"),
        smart_str(u"recepcion Nro renovacion"),
        smart_str(u"recepcion Folio"),
        smart_str(u"recepcion cod_interno"),
        smart_str(u"monto")

    ])
    for obj in queryset:
        transactions = obj.transaction_id
        list_transactions = transactions.splitlines()
        transactions_ = Transaction.objects.filter(
            payu_transaction_id__in=list_transactions
        )
        for obj in transactions_:
            confirmation = None
            try:
                confirmation = SiebelConfirmationPayment.objects.get(num_liquidacion=obj.payu_transaction_id)
            except Exception as e:
                try:
                    confirmation = SiebelConfirmationPayment.objects.get(
                        cod_delivery=obj.subscription.delivery,
                        num_liquidacion='VENTA'
                    )
                except:
                    pass

            if confirmation:
                recepcion_nro_liquidacion = confirmation.num_liquidacion
                recepcion_delivery = confirmation.cod_delivery
                recepcion_nro_renovacion = confirmation.nro_renovacion
                recepcion_folio = confirmation.folio_sunat
                recepcion_cod_interno = confirmation.cod_interno_comprobante
                recepcion_monto = confirmation.monto
            else:
                recepcion_nro_liquidacion = ''
                recepcion_delivery = ''
                recepcion_nro_renovacion = ''
                recepcion_folio = ''
                recepcion_cod_interno = ''
                recepcion_monto = ''

            row = [
                validate('payu_transaction_id', obj),
                recepcion_nro_liquidacion,
                recepcion_delivery,
                recepcion_nro_renovacion,
                recepcion_folio,
                recepcion_cod_interno,
                recepcion_monto
            ]
            writer.writerow(row)
    return response


def export_csv_transactions_from_payu_transaction(modeladmin, request, queryset):
    fecha_report = date.today().strftime("%d-%m-%Y")
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=report_transaction_' + fecha_report + '.csv'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))
    writer.writerow([
        smart_str(u"External Tx Id"),
        smart_str(u"TransactionId"),
        smart_str(u"SuscriptionId"),
        smart_str(u"Plan"),
        smart_str(u"Entecode"),
        smart_str(u"Delivery"),
        smart_str(u"Renovacion Enviada"),
        smart_str(u"Pago enviado"),
        smart_str(u"Respuesta Renovación"),
        smart_str(u"Respuesta Pago"),
        smart_str(u"Envio Renovación"),
        smart_str(u"Envio Pago"),
        smart_str(u"Llegada de comprobantes"),
        smart_str(u"envio O.V trama"),
        smart_str(u"Respuesta O.V trama"),
        smart_str(u"Ente resquest"),
        smart_str(u"Ente response")
    ])
    for obj in queryset:
        transactions = obj.transaction_id
        list_transactions = transactions.splitlines()
        transactions_ = Transaction.objects.filter(
            payu_transaction_id__in=list_transactions
        )

        for obj in transactions_:
            try:
                if obj.initial_payment:
                    confirmation = SiebelConfirmationPayment.objects.get(
                        cod_delivery=obj.subscription.delivery,
                        num_liquidacion='VENTA'
                    )
                    date_arrived = confirmation.created
                elif obj.initial_payment == False:
                    confirmation = SiebelConfirmationPayment.objects.get(num_liquidacion=obj.payu_transaction_id)
                    date_arrived = confirmation.created
                else:
                    date_arrived = ''
            except:
                date_arrived = ''

            row = [
                validate('external_tx_id', obj),
                validate('payu_transaction_id', obj),
                validate('suscripcionid', obj),
                validate('plan', obj),
                validate('entecode', obj),
                validate('delivery', obj),
                validate('renovacion_enviada', obj),
                validate('pago_enviado', obj),
                validate('respuesta_renovacion', obj),
                validate('respuesta_pago', obj),
                validate('envio_renovacion', obj),
                validate('envio_pago', obj),
                date_arrived,
                validate('envio_ov_resquest', obj),
                validate('respuesta_ov_request', obj),
                validate('ente_request', obj),
                validate('ente_response', obj)
            ]
            writer.writerow(row)
    return response


export_csv_transactions.short_description = u"Export transacciones CSV de una lista de subs"


@admin.register(ReportTransactions)
class ReportTransactionsAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'tipo',)
    actions = [
        export_csv_transactions_from_payu_transaction,
        export_csv_transactions,
        export_csv_transactions_resume,
        export_csv_transactions_by_field,
        export_csv_transaction_with_vouchers,
        send_payment,
    ]


class CsvImportForm(forms.Form):
    csv_file = forms.FileField()


@admin.register(EnableSubscriptions)
class EnableSubscriptionsAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = BlockedSubscriptionsResource
    list_display = ('subscription_id_piano', 'type', 'created', 'last_updated',)
    search_fields = ('subscription_id_piano', )
    list_filter = ('type',)
    change_list_template = "admin/piano/subscription_exclude_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            file = request.FILES['csv_file']
            decoded_file = file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            for row in reader:
                if not EnableSubscriptions.objects.filter(subscription_id_piano=row.get("suscripcion", "")).exists():
                    enable_subscription = EnableSubscriptions(
                        subscription_id_piano=row.get("suscripcion", ""),
                        type=row.get("tipo", "")
                    )
                    enable_subscription.save()

            self.message_user(request, "Procesado correctamente")
            return redirect("..")

        form = CsvImportForm()
        payload = {"form": form}
        return render(
            request, "admin/piano/subscription_exclude_csv_form.html", payload
        )


@admin.register(BlockedSubscriptions)
class BlockedSubscriptionsAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = BlockedSubscriptionsResource
    list_display = ('subscription_id_piano', 'type', 'created', 'last_updated',)
    search_fields = ('subscription_id_piano', )
    list_filter = ('type',)
    change_list_template = "admin/piano/subscription_exclude_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            file = request.FILES['csv_file']
            decoded_file = file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            for row in reader:
                if not BlockedSubscriptions.objects.filter(subscription_id_piano=row.get("suscripcion", "")).exists():
                    blocked_subscription = BlockedSubscriptions(
                        subscription_id_piano=row.get("suscripcion", ""),
                        type=row.get("tipo", "")
                    )
                    blocked_subscription.save()

            self.message_user(request, "Procesado correctamente")
            return redirect("..")

        form = CsvImportForm()
        payload = {"form": form}
        return render(
            request, "admin/piano/subscription_exclude_csv_form.html", payload
        )


def load_transactions(modeladmin, request, queryset):
    for obj in queryset:
        export_id_recognition = obj.export_id_recognition
        export_id_transaction_report = obj.export_id_transaction_report
        brand = obj.brand

        export_csv_link = VXClient().get_export_download(brand, export_id_transaction_report)
        url = export_csv_link.get('data', '')
        list_transactions = VXClient().get_csv_from_url(url)

        export_csv_link_recognition = VXClient().get_rest_export_download(brand, export_id_recognition)
        url_recognition = export_csv_link_recognition.get('url', '')
        list_transactions_recognition = VXClient().get_csv_from_url_recognition(url_recognition)
        VXProcess().report_save_transactions(list_transactions, list_transactions_recognition, brand)


@admin.register(LoadReport)
class LoadReportAdmin(admin.ModelAdmin):
    list_display = ('export_id_recognition', 'export_id_transaction_report',)
    actions = [
        load_transactions,
    ]


@admin.register(SubscriptionToFix)
class SubscriptionToFixAdmin(admin.ModelAdmin):
    list_display = ('subscription_id', 'payu_transaction_id',)
    change_list_template = "admin/piano/subscription_exclude_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            file = request.FILES['csv_file']
            decoded_file = file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            for row in reader:
                if not SubscriptionToFix.objects.filter(payu_transaction_id=row.get("payu_transaction_id", "")).exists():
                    subscription_to_fix = SubscriptionToFix(
                        payu_transaction_id=row.get("payu_transaction_id", ""),
                        subscription_id=row.get("subscription_id", "")
                    )
                    subscription_to_fix.save()

            self.message_user(request, "Procesado correctamente")
            return redirect("..")

        form = CsvImportForm()
        payload = {"form": form}
        return render(
            request, "admin/piano/subscription_exclude_csv_form.html", payload
        )
