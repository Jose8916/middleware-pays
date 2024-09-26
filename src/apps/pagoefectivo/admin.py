from django.contrib import admin
from .models import PaymentNotification, CIP, SaleOrderPE, PaymentPE, PaymentTrackingPE
from apps.siebel.models import LogSiebelOvPE, LogSiebelConciliacionPE
from django.utils.html import format_html, format_html_join
# Register your models here.


@admin.register(PaymentNotification)
class PaymentNotificationAdmin(admin.ModelAdmin):
    list_display = (
        'get_user',
        'get_transaction',
        'get_data',
    )
    readonly_fields = (
        'arc_user',
    )
    list_filter = (
        'event_type',
        'sub_type',
    )

    def get_transaction(self, obj):
        return obj.get_transaction_display_html()

    def get_data(self, obj):
        return obj.get_data_display_html()

    def get_user(self, obj):
        return obj.arc_user.get_display_html() if obj.arc_user else '-'

    get_transaction.short_description = 'Transaccion'
    get_data.short_description = 'Data'
    get_user.short_description = 'Usuario(login)'


class EstadoPagoFilter(admin.SimpleListFilter):
    title = 'Estap Pago'
    parameter_name = 'estado_pago'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Enviado'),
            ('2', 'No Enviado'),
        )


    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(siebel_payment__cod_response=1)
        elif self.value() == '2':
            return queryset.exclude(siebel_payment__cod_response=1)
        else:
            return queryset


class DeliveryFilter(admin.SimpleListFilter):
    title = 'Delivery'
    parameter_name = 'delivery'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Sin delivery'),
            ('2', 'Con delivery'),
        )


    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.exclude(siebel_sale_order__delivery__isnull = False)
        elif self.value() == '2':
            return queryset.filter(siebel_sale_order__delivery__isnull = False)
        else:
            return queryset


class LogOVInline(admin.TabularInline):
    model = LogSiebelOvPE
    extra = 1


class LogSiebelConciliacionPEInline(admin.TabularInline):
    model = LogSiebelConciliacionPE
    extra = 1


@admin.register(CIP)
class CIPAdmin(admin.ModelAdmin):
    list_display = (
        'get_user', 'get_transaction', 'get_user_data', 'get_response_pe', 'get_siebel',
    )
    list_filter = (
       'plan__partner__partner_name', 'state', EstadoPagoFilter, DeliveryFilter, 'payment_notification_cip__sub_type',
       'plan__plan_name',
    )
    search_fields = (
        'cip', 'siebel_sale_order__delivery',
    )
    readonly_fields = (
        'arc_user', 'subscription',
    )
    inlines = [LogOVInline, LogSiebelConciliacionPEInline]

    def get_user(self, obj):
        return obj.arc_user.get_display_html() if obj.arc_user else '-'

    def get_transaction(self, obj):
        return obj.get_transaction_display_html()

    def get_user_data(self, obj):
        return obj.get_user_display_html()

    def get_response_pe(self, obj):
        return obj.get_response_display_html()

    def get_siebel(self, obj):
        return obj.get_siebel_html()

    get_user.short_description = 'Usuario(login)'
    get_transaction.short_description = 'Transaccion'
    get_user_data.short_description = 'Cliente'
    get_response_pe.short_description = 'P.E Response'
    get_siebel.short_description = 'Siebel'


@admin.register(SaleOrderPE)
class SaleOrderPEAdmin(admin.ModelAdmin):
    list_display = (
        'delivery',
    )
    search_fields = (
        'delivery', 'siebel_response',
    )


@admin.register(PaymentPE)
class PaymentPEAdmin(admin.ModelAdmin):
    list_display = (
        'cod_response',
    )
    search_fields = (
        'siebel_request',
    )


@admin.register(PaymentTrackingPE)
class PaymentTrackingPEAdmin(admin.ModelAdmin):
    list_display = (
        'get_user', 'get_user_data', 'navegador',
    )

    def navegador(self, obj):
        return format_html(
            '<b>Dispositivo: </b>{user_agent}</br>'
            '<b>Browser Version:</b> {browser_version}</br>'
            '<b>OS Version:</b> {os_version}</br>'
            '<b>Device U.A:</b> {device_user_agent}</br>',
            user_agent=obj.user_agent_str,
            browser_version=obj.browser_version,
            os_version=obj.os_version,
            device_user_agent=obj.device_user_agent,
        )

    def get_user(self, obj):
        try:
            cip_obj = CIP.objects.get(payment_tracking_pe=obj)
        except Exception:
            cip_obj = None
        if cip_obj:
            return cip_obj.arc_user.get_display_html() if cip_obj.arc_user else '-'
        else:
            return ''

    def get_user_data(self, obj):
        try:
            cip_obj = CIP.objects.get(payment_tracking_pe=obj)
        except Exception:
            cip_obj = None
        if cip_obj:
            return cip_obj.get_user_display_html()
        else:
            return ''

    get_user.short_description = 'Usuario(login)'
    get_user_data.short_description = 'Cliente'