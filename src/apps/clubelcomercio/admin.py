"""
    Ref. https://hakibenita.com/how-to-add-custom-action-buttons-to-django-admin
"""

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html, format_html_join
from rangefilter.filter import DateTimeRangeFilter

from .models import DigitalSubscription, ClubSubscription, ClubIntegration, ClubLog, ClubRegister
from apps.paywall.models import Subscription
from apps.paywall.admin import SubscriptionAdmin, PaymentPartnerFilter
from .forms import ChangeDocumentForm, ChangeEmailForm


class AltasEnviadasFilter(admin.SimpleListFilter):
    title = 'Enviado'
    parameter_name = 'alta'

    def lookups(self, request, model_admin):
        choices = []
        if 'action__exact' in request.GET:
            if request.GET.get('action__exact') == '1':
                return (
                    ('1', 'Suscriptor se registro correctamente'),  #valid: True
                    ('2', 'Suscriptor se registro incorrectamente'),  #valid:False
                    ('3', 'Suscriptor Nuevo'),  #  'create_credentials:': True,
                    ('4', 'Suscriptor Existente'),  # 'create_credentials:': False,
                    ('5', 'Se crearon credenciales de Suscriptor'),  # 'is_new': True,
                    ('6', 'No se crearon credenciales de Suscriptor'),  # 'is_new': False,
                )
        return choices

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(result__valid=True)
        if self.value() == '2':
            return queryset.filter(result__valid=False)
        if self.value() == '3':
            return queryset.filter(result__create_credentials=True)
        if self.value() == '4':
            return queryset.filter(result__create_credentials=False)
        if self.value() == '5':
            return queryset.filter(result__is_new=True)
        if self.value() == '6':
            return queryset.filter(result__is_new=False)
        return queryset


class ClubSubscriptionInline(admin.TabularInline):
    model = ClubSubscription
    readonly_fields = (
        'created',
        'document_type',
        'document_number',
        'email',
        'club_activated',
        'club_deactivated',
        'club_is_new',
        'club_credentials',
        'club_operation',
        'is_active',
    )
    exclude = (
        'club_data',
        'club_updated',
    )
    extra = 0

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(DigitalSubscription)
class DigitalSubscriptionAdmin(SubscriptionAdmin):
    readonly_fields = (
        'partner',
        'arc_id',
        'state',
        'plan',
        'campaign',
        'starts_date',
        'date_renovation',
        'date_anulled',
        'payment_profile',
        'motive_anulled',
        'motive_cancelation',
    )
    list_display = (
        'get_data',
        'get_user',
        'get_invoice',
        'get_club_html',
        'get_orders',
        'get_history_state',
    )
    search_fields = (
        'payment_profile__prof_doc_num',
        'payment_profile__portal_email',
        'payment_profile__siebel_entecode',
        'arc_user__email',
        'arc_id',
    )
    list_filter = (
        'partner',
        PaymentPartnerFilter,
        ('created', DateTimeRangeFilter),
        'state',
    )
    exclude = (
        'data',
        'data_loaded',
        'subs_origin',
    )
    inlines = (ClubSubscriptionInline, )
    list_per_page = 10

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:subscription_id>/change_document/',
                self.admin_site.admin_view(self.change_document),
                name='change_document',
            ),
            path(
                '<int:subscription_id>/change_email/',
                self.admin_site.admin_view(self.change_email),
                name='change_email',
            )
        ]
        return custom_urls + urls

    def change_email(self, request, subscription_id):
        subscription = self.get_object(request, subscription_id)
        if request.method != 'POST':
            form = ChangeEmailForm(subscription=subscription)
        else:
            form = ChangeEmailForm(data=request.POST, subscription=subscription)
            if form.is_valid():
                form.save(current_user=request.user)
                self.message_user(request, 'Success')
                url = reverse(
                    'admin:clubelcomercio_digitalsubscription_change',
                    args=[subscription_id],
                    current_app=self.admin_site.name,
                )
                return HttpResponseRedirect(url)

        context = self.admin_site.each_context(request)
        context['opts'] = self.model._meta
        context['form'] = form
        context['subscription'] = subscription
        context['title'] = 'Cambiar Email'
        return TemplateResponse(
            request,
            'admin/subscription/change_email.html',
            context,
        )

    def change_document(self, request, subscription_id):
        subscription = self.get_object(request, subscription_id)
        if request.method != 'POST':
            form = ChangeDocumentForm(subscription=subscription)
        else:
            form = ChangeDocumentForm(data=request.POST, subscription=subscription)
            if form.is_valid():
                form.save(current_user=request.user)
                self.message_user(request, 'Success')
                url = reverse(
                    'admin:clubelcomercio_digitalsubscription_change',
                    args=[subscription_id],
                    current_app=self.admin_site.name,
                )
                return HttpResponseRedirect(url)

        context = self.admin_site.each_context(request)
        context['opts'] = self.model._meta
        context['form'] = form
        context['subscription'] = subscription
        context['title'] = 'Cambiar tipo y número de documento'
        return TemplateResponse(
            request,
            'admin/subscription/change_document.html',
            context,
        )

    def get_club_html(self, obj):
        html = '<div style="margin-bottom: 10px;">'
        try:
            club_subsctiption = ClubSubscription.objects.filter(
                subscription=obj
            ).latest('created')
        except ClubSubscription.DoesNotExist:
            club_subsctiption = None

        if club_subsctiption:
            html += '<i class="fas fa-id-card fa-sm"></i> {} {}<br/>'.format(
                club_subsctiption.get_document_type_display(),
                club_subsctiption.document_number
            )
            html += '<i class="fas fa-at"></i> {}<br/>'.format(club_subsctiption.email)
            if club_subsctiption.is_active is True:
                html += '<i class="fas fas fa-check-circle"></i> Activo<br/>'
            elif club_subsctiption.is_active is False:
                html += '<i class="fas fas fa-minus-circle"></i> Terminado<br/>'
            else:
                html += '<i class="fa fa-question-circle" aria-hidden="true"></i> Pendiente<br/>'

        else:
            html += '-- Sin suscripción Club --'

        if obj.by_payu_method() and obj.state != Subscription.ARC_STATE_TERMINATED:
            html += '</div><table><tr><td><b>Documento de Identidad:</b> </td><td><a class="button" style="background-color:#007bff; border-color:#007bff;color: #fff;" href="{}">Cambiar</a>&nbsp;</td></tr>'.format(
                reverse('admin:change_document', args=[obj.pk])
            )
            html += '<br><tr><td><b>Email:</b> </td><td><a class="button" style="background-color:#17a2b8; border-color:#17a2b8;color: #fff;" href="{}">Cambiar</a>&nbsp;</td></tr></table>'.format(
                reverse('admin:change_email', args=[obj.pk])
            )

        return format_html(html)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(data__currentPaymentMethod__paymentPartner__contains="PayULATAM")

    get_club_html.short_description = 'Suscripción Club'
    get_club_html.allow_tags = True


class ClubIntegrationInline(admin.TabularInline):
    model = ClubIntegration
    readonly_fields = (
        'action',
        'payload',
        'result',
        'hits',
        'status_ok',
    )
    extra = 0


@admin.register(ClubSubscription)
class ClubSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'created',
        'subscription',
        'email',
        'document_type',
        'document_number',
        'is_active',
    )
    list_filter = ('created', 'last_updated', 'is_active')
    search_fields = ('subscription__arc_id',)
    inlines = (ClubIntegrationInline, )
    readonly_fields = (
        'club_activated',
        'club_updated',
        'club_deactivated',
        'is_active',
    )


class ClubLogInline(admin.TabularInline):
    model = ClubLog
    readonly_fields = (
        'created',
        'url',
        'request_text',
        'response_text',
        'response_code',
        'response_time',
    )
    exclude = (
        'request_json',
        'response_json',
    )
    extra = 0


@admin.register(ClubIntegration)
class ClubIntegrationAdmin(admin.ModelAdmin):
    list_display = (
        'created',
        'action',
        'payload',
        'result',
        'hits',
        'status_ok',
    )
    list_filter = (
        'action',
        'created',
        'status_ok',
        AltasEnviadasFilter,
    )
    search_fields = (
        'club_subscription__subscription__arc_id',
    )
    inlines = (ClubLogInline, )


@admin.register(ClubLog)
class ClubLogAdmin(admin.ModelAdmin):
    list_display = (
        'url',
        'created',
        'request_text',
        'response_text',
        'response_code',
        'response_time',
    )
    list_filter = ('created', 'last_updated', )
    search_fields = ('club_integration__club_subscription__subscription__arc_id',)


@admin.register(ClubRegister)
class ClubRegisterAdmin(admin.ModelAdmin):
    list_display = (
        'subscription_str',
        'email',
        'send',
        'status_response',
        'is_new',
        'create_credentials',
        'valid',
        'created',
        'last_updated',
    )
    list_filter = ('status_response', 'create_credentials', 'is_new', 'valid', ('created', DateTimeRangeFilter),)
    search_fields = ('subscription_str', 'email', )
