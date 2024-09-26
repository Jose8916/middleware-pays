from datetime import date, timedelta, datetime
import json
import csv

from django import forms
from django.shortcuts import redirect, render
from django.conf import settings
from django.conf.urls import url
from django.contrib import admin
from django.contrib.postgres import fields
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count
from django.db.models import Q
from django.db.models.functions import TruncDay
from django.forms import Textarea
from django.http import HttpResponse
from django.urls import reverse, path
from django.utils import formats, timezone
from django.utils.timezone import get_default_timezone
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django_json_widget.widgets import JSONEditorWidget
from import_export.admin import ExportMixin
from import_export.formats import base_formats
from rangefilter.filter import DateTimeRangeFilter, DateRangeFilter
from sentry_sdk import capture_exception, capture_event, push_scope
import xlwt

from ..arcsubs.utils import timestamp_to_datetime
from .models import (
    Benefit, BundlePlan, Campaign, Collaborators, Corporate, FinancialTransaction,
    FinancialTransactionProxy, LinkSubscription, OfferToken, Operation, OperationProxyModel,
    Partner, Payment, PaymentProfile, PaymentProxyModel, Plan, Product, RenovationProxyModel,
    SubscriberPrinted, Subscription, TermsConditionsPoliPriv, UserOffer, UserTermsConditionPoliPriv,
    FailRenewSubscription, HashCollegeStudent, Domain, University, SubscriptionReportProxyModel,
    SubscriptionState, SubscriptionFIA, PaymentTracking, ReportLinkedSubscription, BenefitsCoverPage, Log,
    LowBySuspension, EventTypeSuspension, ReportLongPeriodTime, TypeOfLowSubscription, ReporteUniversitarios,
    EventReport, CortesiaModel
)
from apps.piano.models import Subscription as SubscriptionPiano
from .resources import CollaboratorsResource, SubscriptionResource, CorporateResource, AcademicReportResource, \
    UserOfferResource, CortesiaCallResource, LogSiebelConciliacionResource

from apps.siebel.models import Rate, LogSiebelClient, LogSiebelOv, LogSiebelConciliacion, SiebelConfiguration, \
    ReasonExclude, SubscriptionExclude
from apps.webutils.admin import _AuditedModelMixin
from apps.webutils.utils import normalize_text
from apps.piano.utils.utils_functions import get_brand
from apps.piano.utils_models import update_payment_profile
from apps.paywall.functions.utils_report import get_subscription_data
from apps.paywall.arc_clients import SalesClient


@admin.register(LinkSubscription)
class LinkSubscriptionAdmin(_AuditedModelMixin, admin.ModelAdmin):
    list_display = ('plan', 'get_user', 'created',)
    list_filter = ('created',)
    readonly_fields = ('arc_user', 'plan', 'token', 'result', 'expiration',)
    search_fields = ('arc_user__uuid',)

    def get_user(self, obj):
        return obj.arc_user.get_display_html() if obj.arc_user_id else '-'

    get_user.short_description = 'Usuario'


@admin.register(Log)
class LogAdmin(_AuditedModelMixin, admin.ModelAdmin):
    list_display = ('text_log', 'created',)


@admin.register(BenefitsCoverPage)
class BenefitsCoverPageAdmin(_AuditedModelMixin, admin.ModelAdmin):
    list_display = ('menu', 'title', 'image', 'description', 'partner',)


@admin.register(SubscriptionState)
class SubscriptionStateAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'event_type', 'detail', 'date_timestamp', 'date',)
    search_fields = ('subscription__arc_id',)


@admin.register(BundlePlan)
class BundlePlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'partner', 'price', 'position', 'is_active',)
    list_filter = ('partner',)


@admin.register(Collaborators)
class CollaboratorsAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = CollaboratorsResource

    list_display = (
        'code', 'doc_type', 'doc_number', 'name', 'lastname', 'email', 'created', 'state', 'site', 'get_uuid',
        'collaborators_actions', 'next_renovation', 'subscription',
    )
    readonly_fields = ('site', 'doc_type', 'doc_number', 'action', 'data', 'created', 'state',
                       'collaborators_actions', 'data_annulled')
    search_fields = ('code', 'doc_number', 'name', 'lastname', 'email', 'subscription__arc_id',
                     'subscription__arc_user__uuid', )
    list_filter = (('created', DateRangeFilter), ('subscription__date_renovation', DateRangeFilter), 'site', 'state')

    def get_uuid(self, obj):
        if obj.subscription:
            try:
                return obj.subscription.arc_user.uuid
            except:
                return ''
        return ''

    def next_renovation(self, obj):
        tz = timezone.get_current_timezone()
        if obj.subscription:
            try:
                tz_next_renovation = obj.subscription.date_renovation.astimezone(tz)
                return formats.date_format(tz_next_renovation, settings.DATETIME_FORMAT)
            except:
                pass
        return ''

    def get_export_formats(self):
        # return self.formats + (SCSV, )
        return (base_formats.CSV,)  # Sólo opcion CSV

    def get_queryset(self, request):
        return super().get_queryset(request)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            url(
                r'^admin/paywall/collaborators_annulled/(?P<site>.*)/$',
                self.admin_site.admin_view(self.process_annulled),
                name='account-deposit',
            )
        ]
        return custom_urls + urls

    def collaborators_actions(self, obj):
        if obj.state:
            return format_html(
                '<a id="{}" class="button" href="{}">Anular</a>&nbsp;',
                'action-btn-' + str(obj.pk),
                'javascript:processAnnulled({})'.format(obj.pk),
            )

    collaborators_actions.short_description = 'Actions'
    collaborators_actions.allow_tags = True

    def process_annulled(self, request, account_id, *args, **kwargs):
        pass

    change_list_template = 'admin/paywall/collaborators_list.html'

    def has_add_permission(self, request):
        return False

    get_uuid.short_description = 'UUID'


@admin.register(OfferToken)
class OfferTokenAdmin(admin.ModelAdmin):
    readonly_fields = ('user_uuid',)
    list_filter = ('created',)
    list_display = ('user_uuid', 'dni_list', 'created', 'last_updated', 'token',)
    search_fields = ('user_uuid', 'token', 'dni_list')


class SubscriptionEmptyFilter(admin.SimpleListFilter):
    title = 'Estado'
    parameter_name = 'empty'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Con suscripción'),
            ('2', 'Intento'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(subscription__isnull=False)
        elif self.value() == '2':
            return queryset.filter(subscription__isnull=True)
        else:
            return queryset
        # if self.value() == '1':
        #     if request.GET.get('brand', ''):
        #         return queryset.filter(subscription__isnull=False, subscription__partner__id=request.GET.get('brand', ''))
        #     else:
        #         return queryset.filter(subscription__isnull=False)
        # elif self.value() == '2':
        #     if request.GET.get('brand', ''):
        #         return queryset.filter(subscription__isnull=True, subscription__partner__id=request.GET.get('brand', ''))
        #     else:
        #         return queryset.filter(subscription__isnull=True)
        # else:
        #     return queryset


class PlanOfferFilter(admin.SimpleListFilter):
    title = 'Plan'
    parameter_name = 'plan'

    def lookups(self, request, model_admin):
        choices = []
        if 'campaign' in request.GET:
            campaign_id = request.GET.get('campaign')
            campaign = Campaign.objects.get(id=campaign_id)
            planes = campaign.plans.all()
            for plan in planes:
                choices.append([plan.id, plan.plan_name])
            return choices
        return choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                campaign__plans__id=self.value()
            )
        return queryset


class BrandOfferFilter(admin.SimpleListFilter):
    title = 'Marca'
    parameter_name = 'brand'

    def lookups(self, request, model_admin):
        choices = []

        for brand in Partner.objects.all():
            choices.append(
                [brand.id, brand.partner_name]
            )
        return choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(subscription__partner__id=self.value())
        return queryset


class CampaignOfferFilter(admin.SimpleListFilter):
    title = 'Campaña'
    parameter_name = 'campaign'

    def lookups(self, request, model_admin):
        choices = []

        if 'site__exact' in request.GET:
            partner_code = request.GET.get('site__exact')

            for campaign in Campaign.objects.filter(partner__partner_code=partner_code):
                choices.append(
                    [campaign.id, campaign.name]
                )
            return choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(campaign__id=self.value())
        return queryset


class DoubleSubscriptionOfferFilter(admin.SimpleListFilter):
    title = 'Suscripciones Repetidos'
    parameter_name = 'repeated_subscription'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Repetidos'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            duplicates = UserOffer.objects.values(
                'subscription'
            ).annotate(subscription_count=Count('subscription')).filter(subscription_count__gt=1)

            return queryset.filter(subscription__in=[item['subscription'] for item in duplicates]). \
                order_by('subscription__arc_id')
        else:
            return queryset


class DoubleDniOfferFilter(admin.SimpleListFilter):
    title = 'DNIs Repetidos'
    parameter_name = 'repeated_dni'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Repetidos'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            duplicates_queryset = UserOffer.objects.values('dni').exclude(subscription__isnull=True)
            if 'site__exact' in request.GET:
                duplicates_queryset = duplicates_queryset.filter(site=request.GET['site__exact']). \
                    annotate(dni_count=Count('dni')).filter(dni_count__gt=1)
            else:
                duplicates_queryset = duplicates_queryset.annotate(dni_count=Count('dni')).filter(dni_count__gt=1)
            return queryset.filter(dni__in=[item['dni'] for item in duplicates_queryset]).order_by('dni')
        else:
            return queryset


class EmptyDniOfferFilter(admin.SimpleListFilter):
    title = 'DNIs Vacios'
    parameter_name = 'empty_dni'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Vacios'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            queryset.filter(subscription__isnull=False).filter(Q(dni='') | Q(dni__isnull=True))
        else:
            return queryset


@admin.register(UserOffer)
class UserOfferAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = UserOfferResource
    list_filter = (
        'site', SubscriptionEmptyFilter, CampaignOfferFilter, PlanOfferFilter, DoubleSubscriptionOfferFilter,
        DoubleDniOfferFilter,
    )
    readonly_fields = (
        'user_uuid', 'subscription', 'arc_user',
    )
    list_display = (
        'get_offer', 'get_user', 'get_plan', 'dni', 'get_uuid'
    )
    search_fields = (
        'user_uuid', 'dni', 'subscription__arc_id',
    )

    def get_export_formats(self):
        return (base_formats.XLS,)

    change_list_template = 'admin/chart_change_list.html'

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related(
            'campaign', 'campaign__partner', 'subscription', 'arc_user'
        )
        return queryset

    def get_uuid(self, obj):
        try:
            return obj.arc_user.uuid
        except Exception:
            return 'no tiene uuid'

    def get_offer(self, obj):
        tz_date = obj.created.astimezone(
            timezone.get_current_timezone()
        )

        return format_html(
            '{offer} [{sku}]</br>'
            '<i class="fas fa-clock"></i>  {date}</br>'
            '<i class="fas fa-calendar-alt"></i> {site}</br>',
            offer=obj.get_offer_display() or '--',
            date=formats.date_format(tz_date, settings.DATETIME_FORMAT),
            site=obj.site,
            sku='SKU {}'.format(obj.arc_sku) if obj.arc_sku else 'SKU',
        )

    def get_plan(self, obj):
        if obj.subscription_id:
            subscription_link = '/admin/paywall/subscription/{}/change/'.format(obj.subscription_id)
        else:
            subscription_link = '#'

        if obj.campaign_id:
            campaign_link = '/admin/paywall/subscription/{}/change/'.format(obj.campaign_id)
        else:
            campaign_link = '#'

        return format_html(
            'Campaña <strong>{campaign}</strong> '
            '<a href="{campaign_link}" target="_blank"><small>(ver)</small></a></br>'
            'Suscripción <strong>{subscription}</strong> '
            '<a href="{subscription_link}" target="_blank"><small>(ver)</small></a></br>',
            campaign=obj.campaign,
            campaign_link=campaign_link,
            subscription=obj.subscription or '--',
            subscription_link=subscription_link,
        )

    def changelist_view(self, request, extra_context=None):
        try:
            cl = self.get_changelist_instance(request)

        except Exception:
            pass

        else:
            if 'created__gte' not in request.GET:
                limit = timezone.now().date() - timedelta(days=45)
                queryset = cl.get_queryset(
                    request
                ).filter(created__gte=limit)

            else:
                queryset = cl.get_queryset(request)

            # Aggregate new subscribers per day
            chart_data = (
                queryset.annotate(date=TruncDay("created"))
                    .values("date")
                    .annotate(y=Count("id"))
                    .order_by("-date")
            )

            # Serialize and attach the chart data to the template context
            as_json = json.dumps(list(chart_data), cls=DjangoJSONEncoder)
            extra_context = extra_context or {"chart_data": as_json, "chart_title": "Acceso a ofertas"}

        # Call the superclass changelist_view to render the page
        return super().changelist_view(request, extra_context=extra_context)

    def get_user(self, obj):
        return obj.arc_user.get_display_html() if obj.arc_user_id else '-'

    get_offer.short_description = 'Oferta'
    get_plan.short_description = 'Plan'
    get_user.short_description = 'Usuario'
    get_uuid.short_description = 'UUID'


class FailSubscriptionStateFilter(admin.SimpleListFilter):
    title = 'Estado de la suscripcion'
    parameter_name = 'estado'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Activo'),
            ('2', 'Terminado'),
            ('3', 'Cancelado'),
            ('4', 'Suspendido'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(subscription__data__status="1")

        elif self.value() == '2':
            return queryset.filter(subscription__data__status="2")

        elif self.value() == '3':
            return queryset.filter(subscription__data__status="3")

        elif self.value() == '4':
            return queryset.filter(subscription__data__status="4")
        else:
            return queryset


class UserUniqueFilter(admin.SimpleListFilter):
    title = 'Usuarios unicos'
    parameter_name = 'uniques'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Unicos'),
            ('2', 'Todos'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.values('subscription').annotate(dcount=Count('subscription'))
            # return queryset.raw('SELECT event_type FROM paywall_failrenewsubscription limit 1')
            # return queryset.order_by('subscription__arc_id', 'created').distinct('subscription__arc_id')
            # return queryset.all().distinct('event_type', order_by=('-created',)).order_by('created')

            # return queryset.raw('SELECT * FROM paywall_failrenewsubscription GROUP BY subscription_id ORDER BY created')


@admin.register(FailRenewSubscription)
class FailRenewSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'name_subscription', 'email_user', 'name_user', 'date_event', 'subscription',
        'event_type', 'get_site', 'event',
    )
    list_filter = ('event__site', FailSubscriptionStateFilter, UserUniqueFilter)
    search_fields = ('subscription__arc_id',)

    def get_site(self, obj):
        if obj.event:
            return obj.event.site
        else:
            return ''

    def date_event(self, obj):
        if obj.event:
            return timestamp_to_datetime(obj.event.timestamp)
        else:
            return ''

    def name_subscription(self, obj):
        if obj.subscription:
            try:
                return obj.subscription.plan.plan_name
            except Exception:
                return ''
        else:
            return ''

    def name_user(self, obj):
        if obj.subscription.payment_profile:
            if obj.subscription.payment_profile.prof_name and obj.subscription.payment_profile.prof_lastname \
                    and obj.subscription.payment_profile.prof_lastname_mother:
                return "{name} {last_name} {lastname_mother}".format(
                    name=obj.subscription.payment_profile.prof_name,
                    last_name=obj.subscription.payment_profile.prof_lastname,
                    lastname_mother=obj.subscription.payment_profile.prof_lastname_mother
                )
            elif obj.subscription.payment_profile.prof_name and obj.subscription.payment_profile.prof_lastname:
                return "{name} {last_name}".format(
                    name=obj.subscription.payment_profile.prof_name,
                    last_name=obj.subscription.payment_profile.prof_lastname
                )
            else:
                return ""
        else:
            return ""

    def email_user(self, obj):
        if obj.subscription:
            try:
                return obj.subscription.payment_profile.portal_email
            except Exception:
                return ''
        else:
            return ''


@admin.register(SubscriberPrinted)
class SubscriberPrintedAdmin(admin.ModelAdmin):
    list_display = ('us_name', 'us_lastname', 'us_doctype', 'us_docnumber',)
    search_fields = ('us_name', 'us_lastname', 'us_docnumber',)
    formfield_overrides = {
        fields.JSONField: {'widget': JSONEditorWidget},
    }


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0
    formfield_overrides = {
        fields.JSONField: {'widget': JSONEditorWidget},
    }
    readonly_fields = (
        'payment_profile',
    )


def sync_with_arc(modeladmin, request, queryset):
    for instance in queryset:
        instance.sync_data()


def update_profile(modeladmin, request, queryset):
    for instance in queryset:
        instance.update_profile()


sync_with_arc.short_description = "Sincronizar con ARC"


@admin.register(Campaign)
class CampaignAdmin(_AuditedModelMixin, admin.ModelAdmin):
    list_display = ('get_campaign', 'get_info', 'offer', 'event', 'is_active',)
    list_filter = ('partner', 'is_active', 'offer')
    formfield_overrides = {
        fields.JSONField: {'widget': JSONEditorWidget},
        fields.ArrayField: {'widget': Textarea(attrs={'rows': 2, 'cols': 140})},
    }
    search_fields = ('data',)
    actions = (sync_with_arc,)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj and obj.id:
            return ('name', 'partner') + readonly_fields
        else:
            return ()

    def get_campaign(self, obj):
        return format_html(
            '{campaign}</br>'
            '<i class="fas fa-newspaper"></i> {site}',
            campaign=obj.name,
            site=obj.partner,
        )

    def get_info(self, obj):
        html = ''
        if obj.data:
            for product_data in obj.data['products']:
                product, created = Product.objects.get_or_create(arc_sku=product_data['sku'])

                plan_html = self.plans_info(product_data, product)

                html += '<li>{} <small><a href="{}">editar</a></small>{}</li>'.format(
                    product,
                    '/admin/paywall/product/%s/change/' % product.id,
                    plan_html,
                )

            return format_html(
                '<ul>{}</ul>'.format(html)
            )
        else:
            return ''

    def plans_info(self, product_data, product):
        plan_html = ''
        for price in product_data['pricingStrategies']:
            plan, created = Plan.objects.get_or_create(
                arc_pricecode=price['priceCode'],
                product=product
            )
            plan_html += '<li>{} <small><a href="{}">editar</a></small><br>{} {}</li>'.format(
                plan.plan_name,
                '/admin/paywall/plan/%s/change/' % plan.id,
                self.prom_siebel_name(plan),
                self.price_info(plan),
            )
        return '<ul>{}</ul>'.format(plan_html)

    def price_info(self, plan):
        html = ''
        if plan.data:
            for data in plan.data['rates']:
                html += '<li>{} x {} {}</li>'.format(
                    data['amount'],
                    data['durationCount'],
                    data['billingFrequency'],
                )
        return '<ul>{}</ul>'.format(html)

    def prom_siebel_name(self, plan):
        try:
            promocion = Rate.objects.filter(
                plan=plan
            ).filter(Q(type=1) | Q(type=2)).first()
            return promocion.siebel_code_promo
        except Exception:
            return ''

    get_campaign.short_description = 'Campaña'
    plans_info.short_description = 'Planes'


@admin.register(SubscriptionFIA)
class SubscriptionFIAAdmin(admin.ModelAdmin):
    list_display = (
        'subscription', 'fia_request', 'fia_response', 'state',
    )
    search_fields = (
        'subscription__arc_id',
        'fia_request',
        'fia_response',
        'subscription__arc_user__uuid',
    )
    list_filter = (
        'partner',
    )

    # def get_user(self, obj):
    #     return obj.subscription.arc_user.get_display_html() if obj.subscription.arc_user_id else '-'

    # def get_data(self, obj):
    #     title = obj.subscription.plan.plan_name if obj.subscription.plan_id else ''
    #     title += ' [{}]'.format(obj.subscription.campaign.get_category()) if obj.subscription.campaign_id else ' [--]'
    #
    #     return format_html(
    #         '<strong>{title}</strong></br>'
    #         '<i class="fas fa-key"></i> ID {key}</br>'
    #         '<i class="fas fa-newspaper"></i> {site}</br>',
    #         title=title,
    #         site=obj.subscription.partner,
    #         key=obj.subscription.arc_id,
    #     )


class PlanFilter(admin.SimpleListFilter):
    title = 'Plan'
    parameter_name = 'plan'

    def lookups(self, request, model_admin):

        choices = []
        if 'partner__id__exact' in request.GET:
            partner_id = request.GET.get('partner__id__exact')

            for plan in Plan.objects.filter(partner_id=partner_id):
                choices.append(
                    [plan.id, plan.plan_name]
                )

        return choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(plan_id=self.value())

        return queryset


class WithoutPlanFilter(admin.SimpleListFilter):
    title = 'Sin plan'
    parameter_name = 'sin_plan'

    def lookups(self, request, model_admin):
        return (
            ('sin_plan', 'Sin plan'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'sin_plan':
            return queryset.filter(plan__isnull=True)
        else:
            return queryset


class WithoutDeliveryFilter(admin.SimpleListFilter):
    title = 'Sin delivery'
    parameter_name = 'sin_delivery'

    def lookups(self, request, model_admin):
        return (
            ('sin_delivery', 'Sin delivery'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'sin_delivery':
            return queryset.filter(delivery__isnull=True)
        else:
            return queryset


class TypeOfLowFilter(admin.SimpleListFilter):
    title = 'tipo de baja'
    parameter_name = 'type_of_low'

    def lookups(self, request, model_admin):
        return (
            ('por_administrator', 'Por el administrador'),
            ('por_suspencion', 'Por suspencion'),
            ('por_cancelacion', 'Por cancelacion'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'por_suspencion':
            return queryset.filter(type_of_low__type=TypeOfLowSubscription.LOW_BY_SUSPENSION)
        elif self.value() == 'por_cancelacion':
            return queryset.filter(type_of_low__type=TypeOfLowSubscription.LOW_BY_CANCELLATION)
        elif self.value() == 'por_administrator':
            return queryset.filter(type_of_low__type=TypeOfLowSubscription.LOW_BY_ADMIN)
        else:
            return queryset


class TrackingFilter(admin.SimpleListFilter):
    title = 'Sin tracking'
    parameter_name = 'without_tracking'

    def lookups(self, request, model_admin):
        return (
            ('without_tracking', 'Sin tracking'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'without_tracking':
            return queryset.filter(traking=None)
        else:
            return queryset


class PaymentPartnerFilter(admin.SimpleListFilter):
    title = 'Método de pago'
    parameter_name = 'paymentPartner'

    def lookups(self, request, model_admin):
        return (
            ('PayULATAM', 'PayU'),
            ('Free', 'Gratuito'),
            ('Linked', 'Linked'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'PayULATAM':
            return queryset.filter(data__currentPaymentMethod__paymentPartner__contains="PayULATAM")

        elif self.value() == 'Linked':
            return queryset.filter(data__currentPaymentMethod__paymentPartner__contains="Linked")

        elif self.value() == 'Free':
            return queryset.filter(data__currentPaymentMethod__paymentPartner__contains="Free")

        else:
            return queryset


class SubscripcionWithRecurrenceFilter(admin.SimpleListFilter):
    title = 'Suscripciones con recurrencia'
    parameter_name = 'con_recurrencia'

    def lookups(self, request, model_admin):
        return (
            ('con_recurrencia', 'Con recurrencia'),
            ('sin_recurrencia', 'Sin recurrencia'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'con_recurrencia':
            return queryset.filter(data__events__contains=[{"eventType": "RENEW_SUBSCRIPTION"}])
        elif self.value() == 'sin_recurrencia':
            return queryset.exclude(data__events__contains=[{"eventType": "RENEW_SUBSCRIPTION"}])
        else:
            return queryset


class DeliveryFilter(admin.SimpleListFilter):
    title = 'Buscar por Delivery'
    parameter_name = 'delivery'
    template = 'admin/input_custom_filter.html'

    def lookups(self, request, model_admin):
        return (
            ('Yes', 'Yes'),
        )

    def queryset(self, request, queryset):
        delivery = self.value()
        try:
            if delivery:
                obj_operation = Operation.objects.get(siebel_delivery=delivery)
                return queryset.filter(arc_id=obj_operation.payment.subscription.arc_id)
        except Exception as e:
            return queryset


def export_csv_subscriptions(modeladmin, request, queryset):
    import csv
    from django.utils.encoding import smart_str
    tz = timezone.get_current_timezone()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=report-subscriptions.csv'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))  # BOM (optional...Excel needs it to open UTF-8 file properly)
    writer.writerow([
        smart_str(u"Marca"),
        smart_str(u"Plan"),
        smart_str(u"UUID"),
        smart_str(u"email de pago"),
        smart_str(u"email de login"),
        smart_str(u"Fecha de baja"),
        smart_str(u"Fecha de alta"),
        smart_str(u"Motivo de baja"),
        smart_str(u"Penultima Notificacion"),
        smart_str(u"Antepenultima Notificacion"),
        smart_str(u"Ultima Notificacion"),
        smart_str(u"Delivery"),
        smart_str(u"Telefono"),
        smart_str(u"Nombre"),
        smart_str(u"Tipo de documento"),
        smart_str(u"Documento"),
        smart_str(u"SubscriptionId"),
        smart_str(u"Estado"),
    ])

    for obj in queryset:
        try:
            plan = obj.plan.plan_name
        except Exception:
            plan = ''

        try:
            marca = obj.partner.partner_name
        except Exception:
            marca = ''

        try:
            tz_date_anulled = obj.date_anulled.astimezone(tz)
            date_anulled = formats.date_format(tz_date_anulled, settings.DATETIME_FORMAT)
        except Exception:
            date_anulled = ''

        try:
            tz_starts_date = obj.starts_date.astimezone(tz)
            date_start_subscription = formats.date_format(tz_starts_date, settings.DATETIME_FORMAT)
        except Exception:
            date_start_subscription = ''

        try:
            events = obj.data.get('events', '')
        except Exception:
            events = ''

        if events:
            ordered_events = sorted(events, key=lambda i: i['eventDateUTC'])
            total = len(ordered_events) - 1

        try:
            last_event = ordered_events[total]
            last_date_event = timestamp_to_datetime(last_event.get('eventDateUTC'))
            last_event = "{detalle} - {tipo} - {fecha}".format(
                detalle=last_event.get('details'),
                tipo=last_event.get('eventType'),
                fecha=formats.localize(last_date_event)
            )
        except Exception:
            last_event = ''

        try:
            penultimate_event = ordered_events[total - 1]
            _date = timestamp_to_datetime(penultimate_event.get('eventDateUTC'))
            penultimate_event = "{detalle} - {tipo} - {fecha}".format(
                detalle=penultimate_event.get('details'),
                tipo=penultimate_event.get('eventType'),
                fecha=formats.localize(_date)
            )
        except Exception:
            penultimate_event = ''

        try:
            antepenultimate = ordered_events[total - 2]
            date_ante_p = timestamp_to_datetime(antepenultimate.get('eventDateUTC'))
            antepenultimate = "{detalle} - {tipo} - {fecha}".format(
                detalle=antepenultimate.get('details'),
                tipo=antepenultimate.get('eventType'),
                fecha=formats.localize(date_ante_p)
            )
        except Exception:
            antepenultimate = ''

        try:
            email_pago = obj.payment_profile.portal_email
        except Exception:
            email_pago = ''

        try:
            email_login = obj.arc_user.email
        except Exception:
            email_login = ''

        try:
            uuid = obj.arc_user.uuid
        except Exception:
            uuid = ''

        try:
            obj_operation = Operation.objects.get(payment__subscription=obj,
                                                  siebel_delivery__isnull=False)
            delivery = obj_operation.siebel_delivery
        except Exception as e:
            delivery = ''

        try:
            phone = obj.payment_profile.prof_phone
        except Exception as e:
            phone = ''

        try:
            name = obj.payment_profile.get_full_name()
        except Exception as e:
            name = ''

        try:
            type_document = obj.payment_profile.prof_doc_type
        except Exception as e:
            type_document = ''

        try:
            document = obj.payment_profile.prof_doc_num
        except Exception as e:
            document = ''

        try:
            subscription_id = str(obj.arc_id) + ' '
        except Exception as e:
            subscription_id = ''

        try:
            estado = obj.get_state_display(),
        except Exception as e:
            estado = ''

        writer.writerow([
            smart_str(marca),
            smart_str(plan),
            smart_str(uuid),
            smart_str(email_pago),
            smart_str(email_login),
            smart_str(date_anulled),
            smart_str(date_start_subscription),
            smart_str(obj.motive_cancelation or ''),
            smart_str(penultimate_event or ''),
            smart_str(antepenultimate or ''),
            smart_str(last_event or ''),
            smart_str(delivery or ''),
            smart_str(phone),
            smart_str(name),
            smart_str(type_document),
            smart_str(document),
            smart_str(subscription_id),
            smart_str(estado)
        ])

    return response


class EmptyProfileSubscriptionFilter(admin.SimpleListFilter):
    title = 'Perfil de Pago incompleto'
    parameter_name = 'empty_profile'

    def lookups(self, request, model_admin):
        return (
            ('empty_profile', 'Perfil incompleto'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'empty_profile':
            return queryset.filter(
                Q(payment_profile=None) |
                Q(payment_profile__prof_doc_num=None) |
                Q(payment_profile__prof_doc_type=None) |
                Q(payment_profile__prof_name=None) |
                Q(payment_profile__prof_lastname=None)
            )
        else:
            return queryset


class SiteFilter(admin.SimpleListFilter):
    title = 'Portal'
    parameter_name = 'site'

    def lookups(self, request, model_admin):
        return (
            ('elcomercio', 'El Comercio'),
            ('gestion', 'Gestion'),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                subscription__partner__partner_code=self.value()
            )
        else:
            return queryset


@admin.register(EventTypeSuspension)
class EventTypeSuspensionAdmin(admin.ModelAdmin):
    list_display = (
        'name',
    )


@admin.register(LowBySuspension)
class LowBySuspensionAdmin(admin.ModelAdmin):
    list_display = (
        'subscription', 'event_type', 'detail',
    )
    list_filter = (('subscription__date_anulled', DateTimeRangeFilter), 'event_type', SiteFilter)
    search_fields = ('detail',)


class SubscriptionAdmin(ExportMixin, _AuditedModelMixin, admin.ModelAdmin):
    list_display = (
        'get_data', 'get_user', 'get_invoice', 'get_history_state',
    )
    list_filter = (
        ('starts_date', DateTimeRangeFilter),
        ('created', DateTimeRangeFilter),
        ('date_renovation', DateTimeRangeFilter),
        'partner',
        SubscripcionWithRecurrenceFilter,
        PlanFilter,
        'state',
        EmptyProfileSubscriptionFilter,
        PaymentPartnerFilter,
        'last_updated',
        TrackingFilter,
        WithoutPlanFilter,
        WithoutDeliveryFilter
    )
    formfield_overrides = {
        fields.JSONField: {'widget': JSONEditorWidget},
    }
    search_fields = (
        'payment_profile__prof_doc_num',
        'payment_profile__portal_email',
        'payment_profile__siebel_entecode',
        'arc_user__email',
        'arc_user__uuid',
        'arc_id',
        'delivery',
    )
    readonly_fields = (
        'payment_profile', 'plan',
    )
    actions = (sync_with_arc, update_profile, export_csv_subscriptions,)
    inlines = (PaymentInline,)
    change_list_template = 'admin/chart_change_list.html'
    resource_class = SubscriptionResource

    CHART_FIELD_NAME = ''
    CHART_TITLE = ''

    # def get_export_formats(self):
    # return self.formats + (SCSV, )
    # return (base_formats.CSV, )  # Sólo opcion CSV

    def changelist_view(self, request, extra_context=None):
        try:
            cl = self.get_changelist_instance(request)

        except Exception:
            pass

        else:
            if self.CHART_FIELD_NAME:

                if (
                        '{}__range__gte_0'.format(self.CHART_FIELD_NAME) not in request.GET or
                        '{}__range__lte_0'.format(self.CHART_FIELD_NAME) not in request.GET
                ):
                    limit = timezone.now().date() - timedelta(days=45)
                    kwargs = {'{}__gte'.format(self.CHART_FIELD_NAME): limit}

                    queryset = cl.get_queryset(
                        request
                    ).filter(**kwargs)

                else:
                    queryset = cl.get_queryset(request)

                # Aggregate new subscribers per day
                chart_data = (
                    queryset.annotate(date=TruncDay(self.CHART_FIELD_NAME))
                        .values("date")
                        .annotate(y=Count("id"))
                        .order_by("-date")
                )

                # Serialize and attach the chart data to the template context
                as_json = json.dumps(list(chart_data), cls=DjangoJSONEncoder)
                extra_context = extra_context or {"chart_data": as_json, "chart_title": self.CHART_TITLE}

        # Call the superclass changelist_view to render the page
        return super().changelist_view(request, extra_context=extra_context)

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'plan', 'payment_profile', 'arc_user', 'partner',
        )

    def get_data(self, obj):
        tz = timezone.get_current_timezone()
        tz_created = obj.created.astimezone(tz)
        try:
            tz_high = obj.starts_date.astimezone(tz)
        except Exception:
            tz_high = ''
        tz_last_updated = obj.last_updated.astimezone(tz)
        last_updated = formats.date_format(tz_last_updated, settings.DATETIME_FORMAT)

        title = obj.plan.plan_name if obj.plan_id else ''
        title += ' [{}]'.format(obj.campaign.get_category()) if obj.campaign_id else ' [--]'

        anulled = ''
        if obj.date_anulled:
            tz_date_anulled = obj.date_anulled.astimezone(tz)
            anulled = format_html(
                '<i class="fas fa-arrow-circle-down"></i> <strong title="Última modificación: {last_updated}">{date_anulled}</strong>',
                date_anulled=formats.date_format(tz_date_anulled, settings.DATETIME_FORMAT),
                last_updated=last_updated,
            )

        try:
            next_renovation = obj.date_renovation.astimezone(tz)
            next_renovation = formats.date_format(next_renovation, settings.DATETIME_FORMAT)
        except Exception:
            next_renovation = ''

        try:
            low_by_type = TypeOfLowSubscription.objects.get(subscription=obj)
            low_by_type = low_by_type.get_type_display()
        except Exception:
            low_by_type = None

        return format_html(
            '<strong>{title}</strong></br>'
            '<i class="fas fa-key"></i> ID {key}</br>'
            '<strong title="Fecha de creacion en el Middleware:" >Creation date in Middle:</strong> {created}</br>'
            '<i class="fas fa-arrow-circle-up"></i> <strong title="Última modificación: {last_updated}">{tz_high}</strong></br>'
            '{anulled} - {low_by_type}</br>'
            '<b>Prox. Renovación: </b> {next_renovation}</br>'
            '<i class="fas fa-newspaper"></i> {site}</br>'
            '<b>Delivery: </b> {delivery}</br>',
            title=title,
            site=obj.partner,
            key=obj.arc_id,
            anulled=anulled,
            created=formats.date_format(tz_created, settings.DATETIME_FORMAT),
            last_updated=last_updated,
            delivery=obj.delivery,
            tz_high=formats.date_format(tz_high, settings.DATETIME_FORMAT) if tz_high else '-',
            low_by_type=low_by_type,
            next_renovation=next_renovation,
        )

    def get_user(self, obj):
        return obj.arc_user.get_display_html() if obj.arc_user_id else '-'

    def get_history_state(self, obj):
        html = ''
        tz = timezone.get_current_timezone()

        subscription_states = SubscriptionState.objects.filter(subscription=obj).order_by('-date')
        for index, subscription in enumerate(subscription_states):
            try:
                tz_date = subscription.date.astimezone(tz)
                full_date = formats.localize(tz_date)
                date_state = formats.date_format(tz_date, settings.DATE_FORMAT)
            except Exception:
                full_date = ''
                date_state = ''

            html += '<span title="{full_date}">{state} • {date}</span></br>'.format(
                state=subscription.get_state_display(),
                date=date_state,
                full_date=full_date,
            )

            if index == 0:
                html = '<i class="fas fa-check-circle"></i> {}'.format(html)

        return format_html(html)

    def get_invoice(self, obj):
        payment_profile_link = '/admin/paywall/paymentprofile/{}/change/'.format(
            obj.payment_profile.id
        ) if obj.payment_profile else '#'
        brand_email = obj.payment_profile.portal_email if obj.payment_profile else '--'

        tz = timezone.get_current_timezone()

        try:
            tz_date = obj.starts_date.astimezone(tz)
            date_start_suscription = formats.date_format(tz_date, settings.DATETIME_FORMAT)
        except Exception as name_exception:
            date_start_suscription = 'Error en la fecha de suscripcion' + str(name_exception)

        try:
            payment_traking = obj.traking
            device = payment_traking.get_device_display()
            medium = payment_traking.medium
        except Exception:
            device = ''
            medium = ''

        try:
            payment_traking = obj.traking
            browser = payment_traking.user_agent_str
        except Exception:
            browser = ''

        return format_html(
            '<i class="fas fa-id-card fa-sm"></i> {payment_profile} '
            '<a href="{payment_profile_link}" target="_blank"><small>(ver)</small></a></br>'
            '<i class="fas fa-calendar-alt"></i> {date}</br>'
            '<i class="fas fa-at"></i> {email_pago}</br>'
            '<i class="fas fa-wrench"></i> {device}</br>'
            '<i class="fas fa-tag"></i> {medium}</br>'
            '<b>Dispositivo:</b> {browser}</br>',
            payment_profile=obj.payment_profile or '--',
            payment_profile_link=payment_profile_link,
            date=date_start_suscription,
            email_pago=brand_email,
            device=device,
            medium=medium,
            browser=browser
        )

    def get_orders(self, obj):
        if not obj.data or not obj.data.get('salesOrders'):
            return '----'

        html = ''

        for order in obj.data['salesOrders'][-2:]:
            _date = timestamp_to_datetime(order['orderDateUTC'])

            html += '<span title="{date_detail}">{date} • S/ {amount}</span></br>'.format(
                amount=order['total'],
                date_detail=formats.localize(_date),
                date=formats.date_format(_date, settings.DATE_FORMAT),
            )

        return format_html(html)

    get_data.short_description = 'Suscripción'
    get_invoice.short_description = 'Datos de pago'
    get_orders.short_description = 'Pagos'
    get_user.short_description = 'Usuario (Login)'
    get_history_state.short_description = 'Estados'


@admin.register(Subscription)
class SubscriptionDataAdmin(SubscriptionAdmin):
    pass


class SubscriptionReportUp(Subscription):
    class Meta:
        proxy = True
        verbose_name = 'Suscripción (Up)'
        verbose_name_plural = '[Report] Suscripciones • Altas'


@admin.register(SubscriptionReportUp)
class SubscriptionReportUpAdmin(SubscriptionAdmin):
    list_filter = (
        ('starts_date', DateTimeRangeFilter),
        PaymentPartnerFilter, 'partner', PlanFilter, 'state',
    )
    CHART_FIELD_NAME = 'starts_date'
    CHART_TITLE = 'Suscripciones Nuevas'


class SubscriptionReportDown(Subscription):
    class Meta:
        proxy = True
        verbose_name = 'Suscripción (Down)'
        verbose_name_plural = '[Report] Suscripciones • Bajas'


@admin.register(SubscriptionReportDown)
class SubscriptionReportDownAdmin(SubscriptionAdmin):
    list_filter = (
        ('date_anulled', DateTimeRangeFilter),
        PaymentPartnerFilter,
        'partner',
        PlanFilter,
        'state',
        TypeOfLowFilter,
    )
    CHART_FIELD_NAME = 'date_anulled'
    CHART_TITLE = 'Suscripciones Anuladas'


class SubscriptionInline(admin.TabularInline):
    model = Subscription
    extra = 0


@admin.register(Benefit)
class BenefitAdmin(admin.ModelAdmin):
    list_display = ['id', 'be_name', 'state', 'created']


@admin.register(TypeOfLowSubscription)
class TypeOfLowSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['subscription', 'type']
    search_fields = (
        'subscription__arc_id',
    )


class OperationSentFilter(admin.SimpleListFilter):
    title = 'Envio a Siebel'
    parameter_name = 'sentoperation'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Enviado'),
            ('2', 'No Enviado'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(conciliation_cod_response="1")

        elif self.value() == '2':
            return queryset.exclude(conciliation_cod_response="1")
        else:
            return queryset


class refundFilter(admin.SimpleListFilter):
    title = 'refund'
    parameter_name = 'Devoluciones'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Con devolucion'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            list_refund = []
            for obj in queryset:
                try:
                    refund_obj = SalesClient().get_order(
                        site=obj.payment.subscription.partner.partner_code,
                        order_id=obj.payment.arc_order
                    )

                    for pay in refund_obj['payments']:
                        for transaction in pay['financialTransactions']:
                            if transaction['transactionType'] == 'Refund':
                                list_refund.append(obj.id)
                                break
                        break
                except Exception as e:
                    continue

            return queryset.filter(id__in=list_refund)
        else:
            return queryset


class OperationFreeFilter(admin.SimpleListFilter):
    title = 'Free'
    parameter_name = 'gratuitas'

    def lookups(self, request, model_admin):
        return (
            ('1', 'No Gratuito'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(ope_amount__gte=5)
        else:
            return queryset


# class PlaFilter(admin.SimpleListFilter):
#     title = 'Plan'
#     parameter_name = 'plan'
#
#     def lookups(self, request, model_admin):
#         return (
#             ('1', 'No Gratuito'),
#         )
#
#     def queryset(self, request, queryset):
#         if self.value() == '1':
#             return queryset.filter(ope_amount__gte=5)
#         else:
#             return queryset


class OperationDeliveryFilter(admin.SimpleListFilter):
    title = 'delivery'
    parameter_name = 'delivery'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Con delivery'),
            ('2', 'Sin delibery'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(payment__subscription__delivery__isnull=False)
        if self.value() == '2':
            return queryset.filter(payment__subscription__delivery__isnull=True)
        else:
            return queryset


class TwoPaymentsFilter(admin.SimpleListFilter):
    title = 'two_payment'
    parameter_name = 'two_payment'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Con dos pagos'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            duplicates = Payment.objects.values(
                'subscription'
            ).annotate(subscription_count=Count('subscription')).filter(subscription_count=2)

            return queryset.filter(payment__subscription__in=[item['subscription'] for item in duplicates])
        else:
            return queryset


class SubscriptionFilter(admin.SimpleListFilter):
    title = 'Suscripcion'
    parameter_name = 'subscription'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Con suscripcion'),
            ('2', 'Sin suscripcion'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(user_offer__subscription__isnull=False)
        if self.value() == '2':
            return queryset.filter(user_offer__subscription__isnull=True)
        else:
            return queryset


@admin.register(HashCollegeStudent)
class HashCollegeStudentAdmin(admin.ModelAdmin):
    list_display = (
        'get_user', 'get_college', 'get_subscription'
    )
    search_fields = (
        'arc_user__uuid', 'arc_user__email', 'email', 'user_offer__subscription__payment_profile__portal_email'
    )
    list_filter = (
        'degree', 'site', SubscriptionFilter
    )

    def get_college(self, obj):
        tz = timezone.get_current_timezone()
        tz_created = obj.created.astimezone(tz)

        tz_last_updated = obj.last_updated.astimezone(tz)
        last_updated = formats.date_format(tz_last_updated, settings.DATETIME_FORMAT)

        return format_html(
            '<i class="fas fa-at"></i> <b>College:</b> {email}</br>'
            '<strong>Grado: </strong>{degree}</br>'
            '<b>Marca:</b> {site}</br>'
            '<b>Creación:</b> {created}</br>'
            '<b>Last Update:</b> {last_updated}</br>'
            'hash:{hash}</br>',
            email=obj.email,
            degree=obj.degree,
            site=obj.site,
            created=formats.date_format(tz_created, settings.DATETIME_FORMAT),
            last_updated=last_updated,
            hash=obj.hash_user
        )

    def get_user(self, obj):
        return obj.arc_user.get_display_html() if obj.arc_user_id else '-'

    def get_subscription(self, obj):
        try:
            if obj.user_offer:
                if obj.user_offer.subscription:
                    return get_subscription_data(obj.user_offer.subscription)
            else:
                return ''
        except Exception:
            return ''

    get_subscription.short_description = 'Suscripcion'
    get_user.short_description = 'Usuario(Login)'
    get_college.short_description = 'Universitario'


def export_csv_operation(modeladmin, request, queryset):
    import csv
    fecha_report = date.today().strftime("%d-%m-%Y")
    from django.utils.encoding import smart_str
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=report_operation_' + fecha_report + '.csv'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))  # BOM (optional...Excel needs it to open UTF-8 file properly)
    writer.writerow([
        smart_str(u"Observacion"),
        smart_str(u"Id base de datos"),
        smart_str(u"Email Logueo"),
        smart_str(u"Email Pago"),
        smart_str(u"Subscription Id"),
        smart_str(u"estado"),
        smart_str(u"UUID"),
        smart_str(u"Nombre del Pagador"),
        smart_str(u"Delivery"),
        smart_str(u"Ente Code"),
        smart_str(u"Tipo de documento"),
        smart_str(u"Numero de documento"),
        smart_str(u"OperationId - OrderId PAYU - sendt"),
        smart_str(u"num_liquida_id - TransactionId PAYU - sent"),
        smart_str(u"OperationId - OrderId PAYU"),
        smart_str(u"num_liquida_id - TransactionId PAYU"),
        smart_str(u"Monto"),
        smart_str(u"Tipo"),
        smart_str(u"Fecha de Pago"),
        smart_str(u"Plan"),
        smart_str(u"Pago enviado a Siebel"),
        smart_str(u"Nombre del promocion siebel"),
        smart_str(u"motivo de cancelacion"),
        smart_str(u"motivo de termino."),
        smart_str(u"trama envio O.V."),
        smart_str(u"trama respuesta O.V"),
        smart_str(u"trama envio Pago"),
        smart_str(u"trama respuesta Pago"),
        smart_str(u"Trama envio Renovacion"),
        smart_str(u"Trama respuesta Renovacion"),
        smart_str(u"Trama envio Cliente"),
        smart_str(u"Trama respuesta Cliente")
    ])
    for obj in queryset:
        try:
            observacion = []
            # validando dobles
            subs_count = Subscription.objects.filter(arc_user__uuid=obj.payment_profile.arc_user.uuid).exclude(
                state=Subscription.ARC_STATE_TERMINATED).count()
            if subs_count > 1:
                observacion.append('cuenta con ' + str(subs_count) + ' suscripciones')

            # validando entecode
            if obj.payment_profile.siebel_entecode and obj.payment_profile.siebel_name and \
                    obj.payment_profile.siebel_entedireccion and obj.payment_profile.siebel_direction:
                print('continua')
            else:
                observacion.append('No creo Entecode')

            # validando delivery
            if not obj.siebel_delivery:
                obj_operation = Operation.objects.filter(payment__subscription=obj.payment.subscription,
                                                         siebel_delivery__isnull=False).exists()
                if not obj_operation:
                    observacion.append('No creo delivery')

            # validando devolucion
            refund_obj = SalesClient().get_order(
                site=obj.payment.subscription.partner.partner_code,
                order_id=obj.payment.arc_order
            )
            for pay in refund_obj['payments']:
                for transaction in pay['financialTransactions']:
                    if transaction['transactionType'] == 'Refund':
                        observacion.append('Hubo reembolso')
        except Exception as e:
            observacion = []

        try:
            if obj.payment.pa_origin == 'WEB':
                recurrence_value = 'Primera Venta'
            else:
                recurrence_value = 'Recurrencia'
        except Exception as e:
            recurrence_value = ''

        try:
            razon_social = obj.payment_profile.siebel_name
        except Exception as e:
            razon_social = ''

        try:
            plan_name = obj.payment.subscription.plan.plan_name
        except Exception as e:
            plan_name = ''

        try:
            if obj.conciliation_cod_response == '1':
                estado_pago = 'Enviado'
            else:
                estado_pago = 'No Enviado'
        except Exception as e:
            estado_pago = 'No Enviado'

        try:
            if obj.siebel_request:
                start = '<eco:ProdPromName>'
                end = '</eco:ProdPromName>'
                s = obj.siebel_request
                prod_prom_name = s[s.find(start) + len(start):s.find(end)]
            else:
                prod_prom_name = ''
        except Exception as e:
            prod_prom_name = ''

        try:
            if obj.conciliation_siebel_request:
                start = '<tem:num_operacion>'
                end = '</tem:num_operacion>'
                csr = obj.conciliation_siebel_request
                operation_id_sent = csr[csr.find(start) + len(start):csr.find(end)]
            else:
                operation_id_sent = ''
        except Exception as e:
            operation_id_sent = ''

        try:
            if obj.conciliation_siebel_request:
                start = '<tem:num_liquida_id>'
                end = '</tem:num_liquida_id>'
                csr = obj.conciliation_siebel_request
                num_liquida_id_sent = csr[csr.find(start) + len(start):csr.find(end)]
            else:
                num_liquida_id_sent = ''
        except Exception as e:
            num_liquida_id_sent = ''

        try:
            arc_id = obj.payment.subscription.arc_id
        except Exception as e:
            arc_id = ''

        try:
            if obj.siebel_delivery:
                delivery = obj.siebel_delivery
            else:
                obj_operation = Operation.objects.get(payment__subscription=obj.payment.subscription,
                                                      siebel_delivery__isnull=False)
                delivery = obj_operation.siebel_delivery
        except Exception as e:
            delivery = ''

        try:
            if obj.payment_profile.siebel_entecode and obj.payment_profile.siebel_name and \
                    obj.payment_profile.siebel_entedireccion and obj.payment_profile.siebel_direction:
                entecode = obj.payment_profile.siebel_entecode
            else:
                entecode = ''
        except Exception as e:
            entecode = ''

        try:
            if obj.payment_profile.prof_doc_type:
                document_type = obj.payment_profile.prof_doc_type
            else:
                document_type = ''
        except Exception as e:
            document_type = ''

        try:
            if obj.payment_profile.prof_doc_num:
                document_number = obj.payment_profile.prof_doc_num
            else:
                document_number = ''
        except Exception as e:
            document_number = ''

        try:
            monto = obj.payment.pa_amount
        except Exception as e:
            monto = ''

        try:
            fecha_pago = local_format(obj.payment.date_payment)
        except Exception as e:
            fecha_pago = ''

        try:
            request_ov = obj.siebel_request
        except Exception as e:
            request_ov = ''

        try:
            response_ov = obj.siebel_response
        except Exception as e:
            response_ov = ''

        try:
            request_payment_siebel = obj.conciliation_siebel_request
        except Exception as e:
            request_payment_siebel = ''

        try:
            response_payment_siebel = obj.conciliation_siebel_response
        except Exception as e:
            response_payment_siebel = ''

        try:
            recurrencia_request = obj.recurrencia_request
        except Exception as e:
            recurrencia_request = ''

        try:
            recurrencia_response = obj.recurrencia_response
        except Exception as e:
            recurrencia_response = ''

        try:
            request_siebel_client = obj.payment_profile.siebel_request
        except Exception as e:
            request_siebel_client = ''

        try:
            response_siebel_client = obj.payment_profile.siebel_response
        except Exception as e:
            response_siebel_client = ''

        try:
            uuid = obj.payment_profile.arc_user.uuid
        except Exception as e:
            uuid = ''

        try:
            state_subscription = obj.payment.subscription.get_state_display()
        except Exception as e:
            state_subscription = ''

        try:
            if obj.payment.subscription.motive_cancelation:
                reason_for_cancellation = obj.payment.subscription.motive_cancelation
            else:
                reason_for_cancellation = ''
                events_list = obj.payment.subscription.data.get('events', '')
                list_events_ordered = sorted(events_list, key=lambda i: i['eventDateUTC'])
                for event in list_events_ordered:
                    if event.get('eventType', '') == 'CANCEL_SUBSCRIPTION' and event.get('details', ''):
                        reason_for_cancellation = event.get('details', '')
        except Exception as e:
            reason_for_cancellation = ''

        try:
            reason_for_termination = obj.payment.subscription.motive_anulled
        except Exception as e:
            reason_for_termination = ''

        try:
            obj_financial_transaction = FinancialTransaction.objects.get(order_number=obj.payment.arc_order,
                                                                         transaction_type='Payment')
            num_liquida_id = obj_financial_transaction.transaction_id
            operation_id = obj_financial_transaction.order_id
        except Exception:
            num_liquida_id = ''
            operation_id = ''

        try:
            email_login = obj.payment.subscription.arc_user.email
        except Exception:
            email_login = ''

        try:
            email_payment = obj.payment_profile.portal_email
        except Exception:
            email_payment = ''

        writer.writerow([
            smart_str(observacion),
            smart_str(obj.id),
            smart_str(email_login),
            smart_str(email_payment),
            smart_str(arc_id),
            smart_str(state_subscription),
            smart_str(uuid),
            smart_str(razon_social),
            smart_str(delivery),
            smart_str(entecode),
            smart_str(document_type),
            smart_str(document_number),
            smart_str(operation_id_sent),
            smart_str(num_liquida_id_sent),
            smart_str(operation_id),
            smart_str(num_liquida_id),
            smart_str(monto),
            smart_str(recurrence_value),
            smart_str(fecha_pago),
            smart_str(plan_name),
            smart_str(estado_pago),
            smart_str(prod_prom_name),
            smart_str(reason_for_cancellation),
            smart_str(reason_for_termination),
            smart_str(request_ov),
            smart_str(response_ov),
            smart_str(request_payment_siebel),
            smart_str(response_payment_siebel),
            smart_str(recurrencia_request),
            smart_str(recurrencia_response),
            smart_str(request_siebel_client),
            smart_str(response_siebel_client),
        ])
    return response


export_csv_operation.short_description = u"Export CSV"


@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    list_display = ('get_plan', 'get_profile', 'get_transaction', 'get_envio_a_siebel', 'get_siebel_hits', )
    list_filter = (
        ('created', DateTimeRangeFilter), 'payment__partner__partner_name', OperationDeliveryFilter, TwoPaymentsFilter,
        'payment__pa_origin',
        OperationSentFilter, OperationFreeFilter, refundFilter, 'payment__subscription__state', 'plan__plan_name',
    )
    search_fields = (
        'siebel_delivery', 'payment_profile__siebel_entecode', 'payment__subscription__arc_id',
        'payment_profile__prof_doc_num', 'payment_profile__portal_email', 'payment__subscription__arc_user__uuid',
        'payment__subscription__arc_user__email', 'siebel_request',
    )
    actions = [export_csv_operation]
    readonly_fields = ('payment', 'payment_profile', 'plan',)

    def get_refund(self, obj):
        if self.obj_financial_transaction:
            if self.obj_financial_transaction.transaction_type == 'Refund':
                string_refund = '<li><b>Monto: </b>{amount}</li><br>' \
                                 '<li><b>Nro de Orden: </b><br>{arc_order}</li><br>'.format(
                    amount=self.obj_financial_transaction.amount,
                    arc_order=obj.payment.arc_order)
                return format_html(string_refund)
        else:
            return ''

        """
        try:
            string_refund = '<div style="align-content: center; color: #5151ea; font-weight: bold;"><b>DEVOLUCIÓN</b></div><br>'
            refund_obj = SalesClient().get_order(
                site=obj.payment.subscription.partner.partner_code,
                order_id=obj.payment.arc_order
            )

            for pay in refund_obj['payments']:
                for transaction in pay['financialTransactions']:
                    if transaction['transactionType'] == 'Refund':
                        amount = transaction['amount']
                        transaction_date = timestamp_to_datetime(transaction['transactionDate'])
                        string_refund += '<li><b>Monto: </b>{amount}</li><br>' \
                                         '<li><b>Fecha de transacción: </b>{transaction_date}</li><br>' \
                                         '<li><b>Nro de Orden: </b><br>{arc_order}</li><br>'.format(
                            amount=amount,
                            transaction_date=transaction_date,
                            arc_order=obj.payment.arc_order,
                        )
                return format_html(string_refund)
        except Exception:
            return ''
        """
        return ''

    def get_envio_a_siebel(self, obj):
        try:
            motivo_baja = ''
            for event in obj.payment.subscription.data.get('events'):
                if event.get('eventType') == 'TERMINATE_SUBSCRIPTION':
                    motivo_baja = event.get('details')

            if obj.conciliation_cod_response == '1':
                estado_pago = 'Enviado'
                return format_html(
                    '<li><b>Motivo de baja: </b>{estado}</li><br>'
                    '<li><b>Observación: </b>{observacion}</li><br>'
                    '<li><b>Pago Regular:</b> <font color="blue">{estado_pago}</font></li><br>'
                    '<li><b>Recurrencia: </b><br>{recurrencia_response}</li><br>',
                    estado=motivo_baja,
                    recurrencia_response=obj.recurrencia_response,
                    estado_pago=estado_pago,
                    observacion=obj.observations,
                )
            else:
                estado_pago = 'No enviado'
                return format_html(
                    '<li><b>Motivo de baja: </b>{estado}</li><br>'
                    '<li><b>Observación: </b>{observacion}</li><br>'
                    '<li><b>Pago Regular:</b> <font color="red">{estado_pago}</font></li><br>'
                    '<li><b>Recurrencia: </b><br>{recurrencia_response}</li><br>',
                    estado=motivo_baja,
                    recurrencia_response=obj.recurrencia_response,
                    estado_pago=estado_pago,
                    observacion=obj.observations,
                )

        except Exception:
            return ''

    def get_delivery(self, obj):
        try:
            if obj.siebel_delivery:
                id_delivery = obj.siebel_delivery
            else:
                obj_operation = Operation.objects.get(payment__subscription=obj.payment.subscription,
                                                      siebel_delivery__isnull=False)
                id_delivery = obj_operation.siebel_delivery
            return id_delivery
        except Exception:
            return ''

    def get_siebel_hits(self, obj):
        try:
            return format_html(
                '<b>O.V: </b>{OV_hits}<br>'
                '<b>Pago: </b>{payment_hits}<br>',
                OV_hits=obj.siebel_hits,
                payment_hits=obj.conciliation_siebel_hits,
            )
        except Exception:
            return ''

    def get_transaction(self, obj):
        tz = timezone.get_current_timezone()
        tz_created = obj.created.astimezone(tz)
        obj_financial_transaction = None
        transaction_id = ''
        order_id = ''
        devolution = False
        try:
            obj_financial_transaction = FinancialTransaction.objects.get(order_number=obj.payment.arc_order,
                                                                         transaction_type='Payment')
            transaction_id = obj_financial_transaction.transaction_id
            order_id = obj_financial_transaction.order_id
        except Exception:
            pass

        if not obj_financial_transaction:
            try:
                obj_financial_transaction = FinancialTransaction.objects.get(order_number=obj.payment.arc_order,
                                                                             transaction_type='Refund')
                transaction_id = obj_financial_transaction.transaction_id
                order_id = obj_financial_transaction.order_id
                devolution = True
            except Exception:
                pass

        if obj.payment.pa_origin == 'RECURRENCE':
            color_tipo = '#ff8000'
        else:
            color_tipo = '#00aae4'

        try:
            if obj.siebel_request:
                start = '<eco:ProdPromName>'
                end = '</eco:ProdPromName>'
                s = obj.siebel_request
                promo_code = s[s.find(start) + len(start):s.find(end)]
            else:
                promo_code = ''
        except Exception:
            promo_code = ''

        try:
            payment_date = obj.payment.date_payment.astimezone(tz)
            payment_date = formats.date_format(payment_date, settings.DATETIME_FORMAT)
        except Exception:
            payment_date = ''

        return format_html(
            '<b>Monto: </b>{amount}<br>'
            '<b>Tipo: </b><span style="color:{color_tipo}; ">{tipo_suscripcion}</span><br>'
            '<b>Payu Transaction Id:</b><br>{transaction_id}<br>'
            '<b>Payu Order Id: </b>{order_id}<br>'
            '<b>ARC Order Id: </b>{arc_order}<br>'
            '<b>Con devolución:</b> {devolution}<br>'
            '<b>Fecha de Pago:</b><br>{payment_date}<br>'
            '<b>Creacion:</b><br>{created}<br>'
            '<b>Codigo de Promoción:</b><br>{promo_code}',
            amount=obj.ope_amount,
            tipo_suscripcion=obj.payment.pa_origin,
            transaction_id=transaction_id,
            order_id=order_id,
            arc_order=obj.payment.arc_order,
            payment_date=payment_date,
            created=formats.date_format(tz_created, settings.DATETIME_FORMAT),
            color_tipo=color_tipo,
            promo_code=promo_code,
            devolution=devolution
        )

    def get_plan(self, obj):
        return format_html(
            '<strong>{name_plan} </strong></br>'
            '<i class="fas fa-key"></i> ID {subscription_id}</br>'
            '<i class="fas fa-newspaper"></i> {brand}</br>'
            '<b>Estado:</b> {estado}</br>',
            name_plan=obj.plan.plan_name,
            brand=obj.payment.partner.partner_name,
            subscription_id=obj.payment.subscription.arc_id,
            estado=obj.payment.subscription.get_state_display(),
        )

    def get_full_name(self, obj):
        try:
            nombre = obj.payment_profile.prof_name
        except Exception:
            nombre = ''

        try:
            last_name = obj.payment_profile.prof_lastname
        except Exception:
            last_name = ''

        try:
            last_name_mother = obj.payment_profile.prof_lastname_mother
        except Exception:
            last_name_mother = ''

        return '{nombre} {last_name} {last_name_mother}'.format(nombre=nombre, last_name=last_name,
                                                                last_name_mother=last_name_mother)

    def get_doc_type(self, obj):
        try:
            return obj.payment_profile.prof_doc_type
        except Exception:
            return ''

    def get_profile(self, obj):
        delivery = self.get_delivery(obj)

        try:
            payment_profile_link = '/admin/paywall/paymentprofile/{}/change/'.format(
                obj.payment.subscription.payment_profile.id
            )
        except Exception:
            payment_profile_link = ''

        try:
            uuid = obj.payment.subscription.arc_user.uuid
        except Exception:
            uuid = ''

        try:
            email_login = obj.payment.subscription.arc_user.email
        except Exception:
            email_login = ''

        try:
            payment_traking = obj.payment.subscription.traking
            browser = payment_traking.user_agent_str
        except Exception:
            browser = ''

        if obj.payment_profile:
            if obj.payment_profile.siebel_entecode and obj.payment_profile.siebel_name and \
                    obj.payment_profile.siebel_entedireccion and obj.payment_profile.siebel_direction:
                entecode = obj.payment_profile.siebel_entecode
            else:
                entecode = ''

            return format_html(
                '<i class="fas fa-user fa-sm"></i> {full_name}'
                '<a href="{payment_profile_link}" target="_blank"><small>(ver)</small></a></br>'
                '<b>{document_type}</b>: {document_number}</br>'
                '<b>Email de compra</b>: {email_compra}</br>'
                '<b>Entecode</b>: {entecode}</br>'
                '<b>Delivery</b>: {delivery}</br>'
                '<b>UUID</b>: {uuid}</br>'
                '<b>Email login</b>: {email_login}</br>'
                '<b>Dispositivo:</b> {browser}',
                full_name=obj.payment_profile.get_full_name(),
                document_type=obj.payment_profile.prof_doc_type or '',
                document_number=obj.payment_profile.prof_doc_num or '',
                email_compra=obj.payment_profile.portal_email or '',
                entecode=entecode,
                delivery=delivery or '',
                payment_profile_link=payment_profile_link,
                uuid=uuid,
                email_login=email_login,
                browser=browser
            )
        else:
            return ''

    get_profile.short_description = 'Perfil de Pago'
    get_plan.short_description = 'Suscripcion'
    get_siebel_hits.short_description = 'Nro. de Peticiones'
    get_transaction.short_description = 'Transaccion'
    get_delivery.short_description = 'Delivery'
    get_envio_a_siebel.short_description = 'Envio a siebel'
    get_refund.short_description = 'Devolución'


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('partner_name', 'partner_code', 'partner_host', 'created')


class RateInline(admin.TabularInline):
    model = Rate
    extra = 0


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        'plan_name', 'arc_pricecode', 'product', 'arc_rates', 'siebel_rates', 'created', 'partner', 'state',
        'plan_months',
    )
    inlines = (RateInline,)
    list_filter = ('partner',)
    readonly_fields = ('plan_name', 'arc_pricecode', 'product', 'state', 'partner',)
    formfield_overrides = {
        fields.JSONField: {'widget': JSONEditorWidget},
    }
    search_fields = (
        'arc_pricecode',
    )

    def has_add_permission(self, request, obj=None):
        return False

    def arc_rates(self, obj):

        if not obj.data:
            return '--'

        rates = []
        for data in obj.data['rates']:
            rates.append(
                '{} x {} {}'.format(
                    data['amount'],
                    data['durationCount'],
                    data['billingFrequency'],
                )
            )

        return format_html('</br>'.join(rates))

    def siebel_rates(self, obj):

        rate_list = obj.rates.all()

        if not rate_list:
            return '--'

        rates = []
        for rate in rate_list:
            rates.append(
                '{}'.format(
                    rate.rate_total
                )
            )

        return format_html('</br>'.join(rates))

    arc_rates.short_description = 'T. ARC'
    siebel_rates.short_description = 'T. Siebel'


@admin.register(LogSiebelClient)
class LogSiebelClientAdmin(admin.ModelAdmin):
    list_display = ('email', 'dni', 'ente_code', 'payment_profile', 'log_request', 'log_response', 'created',)
    search_fields = ('payment_profile__prof_doc_num', 'payment_profile__portal_email',
                     'payment_profile__siebel_entecode',)

    def dni(self, obj):
        try:
            return obj.payment_profile.prof_doc_num
        except Exception:
            return ''

    def ente_code(self, obj):
        try:
            return obj.payment_profile.siebel_entecode
        except Exception:
            return ''

    def email(self, obj):
        try:
            return obj.payment_profile.portal_email
        except Exception:
            return ''


@admin.register(LogSiebelOv)
class LogSiebelOvAdmin(admin.ModelAdmin):
    list_display = (
    'operation', 'subscription_id', 'siebel_delivery', 'created', 'last_updated', 'log_request', 'log_response',)
    search_fields = ('operation__siebel_delivery', 'operation__payment_profile__siebel_entecode', 'log_response',
                     'operation__payment__subscription__arc_id', 'log_request')
    list_filter = ('operation__payment__pa_origin', 'operation__payment__partner__partner_name',)

    def subscription_id(self, obj):
        try:
            return obj.operation.payment.subscription.arc_id
        except Exception:
            return ''

    def siebel_delivery(self, obj):
        try:
            return obj.operation.siebel_delivery
        except Exception:
            return ''


class ConciliacionEnvioFilter(admin.SimpleListFilter):
    title = 'Envio de conciliación a Siebel'
    parameter_name = 'sentconciliation'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Enviado'),
            ('0', 'Pendiente'),
            ('2', 'Todo'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(operation__conciliation_cod_response="1")

        elif self.value() == '0':
            return queryset.filter(operation__conciliation_cod_response="0")
        else:
            return queryset


@admin.register(LogSiebelConciliacion)
class LogSiebelConciliacionAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = LogSiebelConciliacionResource
    list_display = (
    'siebel_code', 'ente_code', 'type', 'created', 'last_updated', 'envio_a_siebel', 'log_request', 'log_response',
    'log_recurrence_request', 'log_recurrence_response', 'operation',)
    search_fields = ('operation__payment__subscription__delivery', 'operation__payment_profile__siebel_entecode',
                     'operation__payment_profile__prof_doc_num', 'log_request',
                     'operation__payment__subscription__arc_id', 'operation__payment__payu_transaction',)
    readonly_fields = ['operation']
    list_filter = (
        ('created', DateTimeRangeFilter), 'operation__payment__pa_origin', 'operation__payment__partner__partner_name',
        ConciliacionEnvioFilter)

    def siebel_code(self, obj):
        try:
            return obj.operation.siebel_delivery
        except Exception:
            return ''

    def ente_code(self, obj):
        try:
            return obj.operation.payment_profile.siebel_entecode
        except Exception:
            return ''

    def envio_a_siebel(self, obj):
        try:
            if obj.operation.conciliation_cod_response == '1':
                return 'Enviado'
            else:
                return 'No enviado'
        except Exception:
            return 'No enviado'


class WithSubscriptionFilter(admin.SimpleListFilter):
    title = 'Con suscripcion'
    parameter_name = 'with_subscription'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Con suscripcion'),
            ('2', 'Sin suscripcion'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.exclude(subscription_obj=None)
        if self.value() == '2':
            return queryset.filter(subscription_obj=None)
        else:
            return queryset


class WithPaymentFilter(admin.SimpleListFilter):
    title = 'Con Pago'
    parameter_name = 'with_payment'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Con pago'),
            ('2', 'Sin pago'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.exclude(payment=None)
        if self.value() == '2':
            return queryset.filter(payment=None, transaction_type='Payment')
        else:
            return queryset


class WithOperationFilter(admin.SimpleListFilter):
    title = 'Con Operacion'
    parameter_name = 'with_operation'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Con operacion'),
            ('2', 'Sin operacion'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.exclude(operation=None, transaction_type='Payment')
        if self.value() == '2':
            return queryset.filter(operation=None, transaction_type='Payment')
        else:
            return queryset


class DifferentZeroFilter(admin.SimpleListFilter):
    title = 'Diferente de cero'
    parameter_name = 'different_zero'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Diferente de cero'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(amount__gte=5, transaction_type='Payment')
        else:
            return queryset


def get_export_formats():
    return (base_formats.XLS,)


@admin.register(ReporteUniversitarios)
class ReporteUniversitariosModelAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = AcademicReportResource
    list_display = (
        'get_user', 'get_college', 'get_subscription'
    )
    search_fields = (
        'arc_user__uuid', 'arc_user__email', 'email', 'user_offer__subscription__payment_profile__portal_email'
    )
    list_filter = (
        ('created', DateTimeRangeFilter), 'degree', 'site', SubscriptionFilter
    )

    def get_export_filename(self, file_format):
        filename = "%s.%s" % ("Reporte",
                              file_format.get_extension())
        return filename

    def get_college(self, obj):
        tz = timezone.get_current_timezone()
        tz_created = obj.created.astimezone(tz)

        return format_html(
            '<b>Email Universidad:</b> {email}</br>'
            '<strong>Grado: </strong>{degree}</br>'
            '<b>Marca:</b> {site}</br>'
            '<b>Creación:</b> {created}</br>',
            email=obj.email,
            degree=obj.degree,
            site=obj.site,
            created=formats.date_format(tz_created, settings.DATETIME_FORMAT)
        )

    def get_user(self, obj):
        return obj.arc_user.get_display_html() if obj.arc_user_id else '-'

    def get_subscription(self, obj):
        try:
            if obj.user_offer:
                if obj.user_offer.subscription:
                    return get_subscription_data(obj.user_offer.subscription)
            else:
                return 'Sin Suscripcion'
        except Exception:
            return 'Sin Suscripcion'

    def get_export_formats(self):
        return (base_formats.XLS,)

    get_subscription.short_description = 'Suscripcion'
    get_user.short_description = 'Usuario(Login)'
    get_college.short_description = 'Universitario'


@admin.register(FinancialTransactionProxy)
class FinancialTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'order_id', 'transaction_id', 'order_number', 'client_id', 'created_on', 'subscription_id',
        'provider_reference', 'initial_transaction', 'transaction_type', 'subscription_obj', 'payment', 'operation',
    )
    search_fields = (
        'provider_reference', 'order_id', 'transaction_id', 'order_number', 'client_id', 'subscription_id',
    )
    list_filter = (
        ('created_on', DateTimeRangeFilter), 'transaction_type', 'site', 'initial_transaction', WithSubscriptionFilter,
        WithPaymentFilter, WithOperationFilter, DifferentZeroFilter,
    )
    formfield_overrides = {
        fields.JSONField: {'widget': JSONEditorWidget},
    }

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['text_seach'] = 'Buscar...'
        return super(FinancialTransactionAdmin, self).changelist_view(request, extra_context=extra_context)

    class Media:
        js = ('js/admin_custom.js',)


@admin.register(Corporate)
class CorporateAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = CorporateResource
    list_display = (
        'get_site', 'user', 'asunto',
    )
    list_filter = (
        ('created', DateTimeRangeFilter), 'corp_type',
    )
    search_fields = (
        'corp_email', 'corp_name', 'corp_lastname',
    )

    def user(self, obj):
        if obj.corp_name and obj.corp_lastname:
            full_name = '{} {}'.format(obj.corp_name, obj.corp_lastname)
        elif obj.corp_name and not obj.corp_lastname:
            full_name = '{}'.format(obj.corp_name)
        elif not obj.corp_name and obj.corp_lastname:
            full_name = '{}'.format(obj.corp_lastname)
        else:
            full_name = ''

        return format_html(
            '<b>Nombre</b>: {full_name}</br>'
            '<b>Email</b>: {corp_email}</br>'
            '<b>Telefono</b>: {telefono}</br>'
            '<b>Organización</b>: {corp_organization}</br>',
            full_name=full_name,
            corp_email=obj.corp_email,
            telefono=obj.telefono,
            corp_organization=obj.corp_organization
        )

    def get_site(self, obj):
        try:
            site = obj.site.partner_name
        except:
            site = ''

        tz = timezone.get_current_timezone()
        tz_created = obj.created.astimezone(tz)
        created = formats.date_format(tz_created, settings.DATETIME_FORMAT)

        return format_html(
            '<b>{site}</b></br>'
            '<b>Creado</b>: {created}</br>',
            site=site,
            created=created
        )

    def asunto(self, obj):
        return obj.get_corp_type_display()

    def get_export_formats(self):
        return (base_formats.XLS,)

    get_site.short_description = 'Portal'
    user.short_description = 'Usuario'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    search_fields = (
        'siebel_code', 'siebel_name',
    )
    list_display = ('prod_name', 'arc_sku', 'siebel_name', 'arc_campaign', 'prod_type', 'created', 'partner', 'state',)
    list_filter = ('partner',)
    readonly_fields = (
        'arc_sku', 'state',
    )
    formfield_overrides = {
        fields.JSONField: {'widget': JSONEditorWidget},
    }

    def siebel_name(self):
        return format_html(
            '{name} - {code}',
            name=self.siebel_name.upper(),
            code=self.siebel_code
        )

    #def has_add_permission(self, request, obj=None):
    #   return False


"""
class PortalFilter(admin.SimpleListFilter):
    title = 'Portal User'
    parameter_name = 'portal'

    def lookups(self, request, model_admin):
        return (
            ('1', 'El Comercio'),
            ('2', 'Gestion'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            Subscription.objects.filter(payment_profile=queryset)
            return queryset.filter(subscription__data__status="1")

        elif self.value() == '2':
            return queryset.filter(subscription__data__status="2")
        else:
            return queryset
"""


def sync_piano_profile(modeladmin, request, queryset):
    for instance in queryset:
        subscription = SubscriptionPiano.objects.get(payment_profile=instance)
        update_payment_profile(subscription.uid, get_brand(subscription.app_id), instance)


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


def reset_counter(modeladmin, request, queryset):
    for obj in queryset:
        obj.siebel_hits = 0
        obj.save()


@admin.register(PaymentProfile)
class PaymentProfileAdmin(admin.ModelAdmin):
    list_display = (
        'prof_name', 'prof_lastname', 'prof_lastname_mother',
        'prof_doc_type', 'prof_doc_num', 'portal_email', 'arc_user',
        'prof_phone', 'siebel_entecode', 'created', 'last_updated', 'siebel_hits'
    )
    list_filter = (('created', DateTimeRangeFilter), HitsFilter, 'note',)
    search_fields = (
        'prof_name',
        'prof_lastname',
        'prof_lastname_mother',
        'prof_doc_num',
        'portal_email',
        'siebel_entecode',
    )
    readonly_fields = (
        'arc_user',
    )
    actions = [sync_piano_profile, reset_counter]


class OperationInline(admin.StackedInline):
    model = Operation
    extra = 0


def local_format(_date):
    try:
        if not isinstance(_date, datetime):
            return ''

        _date = _date.astimezone(
            get_default_timezone()
        )

        _date = _date.replace(tzinfo=None)

        return _date
    except Exception as e:
        return ''
    except SystemExit:
        return ''


def export_csv_payment_resume(modeladmin, request, queryset):
    import csv
    fecha_report = date.today().strftime("%d-%m-%Y")
    from django.utils.encoding import smart_str
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=report' + fecha_report + '.csv'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))  # BOM (optional...Excel needs it to open UTF-8 file properly)
    writer.writerow([
        smart_str(u"Subscription Id"),
        smart_str(u"Tipo Renovación"),
        smart_str(u"UUID"),
        smart_str(u"TransactionId"),
        smart_str(u"Estado"),
    ])
    for obj in queryset:
        if obj.pa_origin == 'WEB':
            recurrence_value = 'Primera Venta'
        else:
            recurrence_value = obj.pa_origin

        try:
            uuid = obj.subscription.arc_user.uuid
        except Exception as e:
            uuid = ''

        try:
            ft = FinancialTransaction.objects.get(order_number=obj.arc_order, transaction_type='Payment')
            transaction_id = ft.transaction_id
        except Exception as e:
            transaction_id = ''

        try:
            estado = obj.subscription.get_state_display()
        except Exception as e:
            estado = ''

        writer.writerow([
            smart_str(obj.subscription.arc_id),
            smart_str(recurrence_value),
            smart_str(uuid),
            smart_str(transaction_id),
            smart_str(estado),
        ])
    return response


export_csv_payment_resume.short_description = u"Export CSV payments"


def export_csv_payment(modeladmin, request, queryset):
    import csv
    fecha_report = date.today().strftime("%d-%m-%Y")
    from django.utils.encoding import smart_str
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=report' + fecha_report + '.csv'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))  # BOM (optional...Excel needs it to open UTF-8 file properly)
    writer.writerow([
        smart_str(u"Subscription Id"),
        smart_str(u"Nombre del Pagador"),
        smart_str(u"Delivery"),
        smart_str(u"Monto"),
        smart_str(u"Tipo Renovación"),
        smart_str(u"Fecha de Cobro"),
        smart_str(u"Fecha de Orden"),
        smart_str(u"Plan"),
        smart_str(u"UUID"),
        smart_str(u"TransactionId"),
        smart_str(u"Estado"),
    ])
    for obj in queryset:
        if obj.pa_origin == 'WEB':
            recurrence_value = 'Primera Venta'
        else:
            recurrence_value = obj.pa_origin

        try:
            obj.subscription.delivery
        except Exception as e:
            delivery = ''

        try:
            razon_social = obj.payment_profile.siebel_name
        except Exception as e:
            razon_social = ''

        try:
            plan_name = obj.subscription.plan.plan_name
        except Exception as e:
            plan_name = ''

        try:
            uuid = obj.subscription.arc_user.uuid
        except Exception as e:
            uuid = ''

        try:
            ft = FinancialTransaction.objects.get(order_number=obj.arc_order, transaction_type='Payment')
            transaction_id = ft.transaction_id
        except Exception as e:
            transaction_id = ''

        try:
            estado = obj.subscription.get_state_display()

        except Exception as e:
            estado = ''

        writer.writerow([
            smart_str(obj.subscription.arc_id),
            smart_str(razon_social),
            smart_str(delivery),
            smart_str(obj.pa_amount),
            smart_str(recurrence_value),
            smart_str(local_format(obj.transaction_date)),
            smart_str(local_format(obj.date_payment)),
            smart_str(plan_name),
            smart_str(uuid),
            smart_str(transaction_id),
            smart_str(estado),
        ])
    return response


export_csv_payment.short_description = u"Export CSV"


class WithTransactionFilter(admin.SimpleListFilter):
    title = 'Con Transaccion'
    parameter_name = 'with_transaction'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Con transaccion'),
            ('2', 'Sin Transaccion'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.exclude(payu_transaction='')
        if self.value() == '2':
            return queryset.filter(Q(payu_transaction='') | Q(payu_transaction__isnull=True ))
        else:
            return queryset

class amountDifferentZeroFilter(admin.SimpleListFilter):
    title = 'Diferente de cero'
    parameter_name = 'different_zero'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Diferente a cero'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(pa_amount__gte=4)
        else:
            return queryset


@admin.register(Payment)
class PaymentAdmin(ExportMixin, _AuditedModelMixin, admin.ModelAdmin):
    list_display = (
        'pa_method', 'pa_amount', 'date_payment', 'arc_order', 'subscription', 'payment_profile', 'partner', 'status',
        'reembolso', 'pa_origin',
    )
    # 'transaction_date',
    list_filter = (
        ('date_payment', DateTimeRangeFilter), ('transaction_date', DateTimeRangeFilter), 'partner__partner_name',
        'pa_origin', 'pa_method', WithTransactionFilter, amountDifferentZeroFilter,
    )
    actions = [export_csv_payment, export_csv_payment_resume]
    inlines = (OperationInline,)
    formfield_overrides = {
        fields.JSONField: {'widget': JSONEditorWidget},
    }
    readonly_fields = (
        'subscription',
    )
    search_fields = (
        'arc_order', 'subscription__arc_id',
    )

    def reembolso(self, obj):
        type_refund = None
        amount = None
        transaction_date = None

        if obj.refund_type:
            type_refund = 'Reembolso desde SIEBEL'
            amount = obj.refund_amount
            transaction_date = obj.refund_date
        """
        else:
            refund_obj = SalesClient().get_order(
                site=obj.partner.partner_code,
                order_id=obj.arc_order
            )
            amount = ''
            transaction_date = ''
            type_refund = ''
            for pay in refund_obj['payments']:
                for transaction in pay['financialTransactions']:
                    if transaction['transactionType'] == 'Refund':
                        amount = transaction['amount']
                        transaction_date = timestamp_to_datetime(transaction['transactionDate'])
                        type_refund = 'Reembolso desde ARC'
                        break
        """
        return format_html(
            '<b>Tipo</b>: Reembolso desde ARC</br>'
            '<b>Monto</b>: {amount}</br>'
            '<b>Fecha</b>: {transaction_date}</br>',
            amount=amount,
            transaction_date=transaction_date,
            tipo_reembolso=type_refund,
        )

    def get_export_formats(self):
        # return self.formats + (SCSV, )
        return (base_formats.CSV,)  # Sólo opcion CSV


def get_from_field(field, field_label):
    def _func(_self, obj):
        return getattr(obj.subscription, field)

    _func.short_description = field_label
    _func.allow_tags = True
    return _func


@admin.register(TermsConditionsPoliPriv)
class TermsConditionsPoliPrivAdmin(admin.ModelAdmin):
    list_display = ('name', 'partner',)


@admin.register(UserTermsConditionPoliPriv)
class UserTermsConditionPoliPrivAdmin(admin.ModelAdmin):
    list_display = ('user_uuid',)


class OperationReportInline(admin.TabularInline):
    model = Operation
    fields = readonly_fields = ('state', 'ope_amount', 'plan', 'siebel_state', 'siebel_delivery', 'conciliation_state',
                                'conciliation_date')
    extra = 0

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


def export_csv(modeladmin, request, queryset):
    import csv
    fecha_report = date.today().strftime("%d-%m-%Y")
    from django.utils.encoding import smart_str
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=report' + fecha_report + '.csv'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))  # BOM (optional...Excel needs it to open UTF-8 file properly)
    writer.writerow([
        smart_str(u"CeBe(siebel_entecode)"),
        smart_str(u"Razon Social"),
        smart_str(u"Delivery"),
        smart_str(u"Monto"),
        smart_str(u"Tipo Renovación"),
        smart_str(u"Fecha de Cobro"),
        smart_str(u"Producto"),
        smart_str(u"Medio de Pago"),
    ])
    for obj in queryset:
        if obj.payment.pa_origin == 'WEB':
            recurrence_value = 'Venta'
        else:
            recurrence_value = obj.payment.pa_origin

        writer.writerow([
            smart_str(obj.payment_profile.siebel_entecode),
            smart_str(obj.payment_profile.siebel_name),
            smart_str(obj.siebel_delivery),
            smart_str(obj.rate_total_sent_conciliation),
            smart_str(recurrence_value),
            smart_str(obj.created),
            smart_str(obj.plan.product.siebel_name),
            smart_str(obj.payment.pa_method),
        ])
    return response


export_csv.short_description = u"Export CSV"


def export_xls(modeladmin, request, queryset):
    fecha_report = date.today().strftime("%d-%m-%Y")
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename=report' + fecha_report + '.xls'
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet("MyModel")

    row_num = 0

    columns = [
        (u"CeBe(siebel_entecode)", 6000),
        (u"Razon Social", 6000),
        (u"Delivery", 6000),
        (u"Monto", 6000),
        (u"Tipo Renovación", 6000),
        (u"Fecha de Cobro", 6000),
        (u"Producto", 6000),
        (u"Medio de Pago", 6000),
        (u"Fecha de renovacion", 8000),
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
        if obj.payment.pa_origin == 'WEB':
            recurrence_value = 'Venta'
        else:
            recurrence_value = obj.payment.pa_origin

        row_num += 1
        row = [
            obj.payment_profile.siebel_entecode,
            obj.payment_profile.siebel_name,
            obj.siebel_delivery,
            obj.rate_total_sent_conciliation,
            recurrence_value,
            obj.created,
            obj.plan.product.siebel_name,
            obj.payment.pa_method,
            obj.payment.subscription.date_renovation
        ]

        for col_num in range(len(row)):
            ws.write(row_num, col_num, str(row[col_num]), font_style)

    wb.save(response)
    return response


export_xls.short_description = u"Export XLS"


class StateSubscriptionFilter(admin.SimpleListFilter):
    title = 'Estado de la Suscripción'
    parameter_name = 'state_subscription'

    def lookups(self, request, model_admin):
        return (
            ('canceled', 'Cancelados'),
            ('canceled_terminated', 'Cancelaciones que fueron terminadas'),
            ('suspended', 'Suspenciones'),
            ('suspended_terminated', 'Suspenciones que fueron terminadas'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'canceled':
            return queryset.filter(state=3)

        elif self.value() == 'canceled_terminated':
            return queryset.filter(state=2, data__events__contains=[{"eventType": "CANCEL_SUBSCRIPTION"}])

        elif self.value() == 'suspended':
            return queryset.filter(state=4)

        elif self.value() == 'suspended_terminated':
            return queryset.filter(state=2, data__events__contains=[{"eventType": "SUSPEND_SUBSCRIPTION"}])


class InputFilter(admin.SimpleListFilter):
    template = 'admin/input_filter_subscription.html'

    def lookups(self, request, model_admin):
        # Dummy, required to show the filter.
        return ((),)

    def choices(self, changelist):
        # Grab only the "all" option.
        all_choice = next(super().choices(changelist))
        all_choice['query_parts'] = (
            (k, v)
            for k, v in changelist.get_filters_params().items()
            if k != self.parameter_name
        )
        yield all_choice


class UUIDFilter(InputFilter):
    parameter_name = 'uuid'
    title = 'UID'

    def queryset(self, request, queryset):
        if self.value() is not None:
            uuid = self.value()
            print('raro')
            print(self.value())
            print(type(self.value()))
            print(queryset.filter(state=self.value()))
            print('haberx')

            return queryset.filter(
                state=self.value()
            )


def export_linked_csv(modeladmin, request, queryset):
    import csv
    fecha_report = date.today().strftime("%d-%m-%Y")
    from django.utils.encoding import smart_str
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=report_' + fecha_report + '.csv'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))  # BOM (optional...Excel needs it to open UTF-8 file properly)
    writer.writerow([
        smart_str(u"UUID User"),
        smart_str(u"email de logueo"),
    ])
    for obj in queryset:
        try:
            email = obj.arc_user.email
        except Exception as e:
            email = ''

        writer.writerow([
            smart_str(obj.arc_user.uuid),
            smart_str(email),
        ])
    return response


export_linked_csv.short_description = u"Exportar usuarios"


@admin.register(ReportLinkedSubscription)
class ReportLinkedSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('plan', 'get_user',)
    readonly_fields = ('arc_user', 'plan', 'token', 'result', 'expiration',)
    search_fields = ('arc_user__uuid',)
    # list_filter = ('plan',)
    actions = [export_linked_csv]

    def get_user(self, obj):
        return obj.arc_user.get_display_html() if obj.arc_user_id else '-'

    get_user.short_description = 'Usuario'


@admin.register(SubscriptionReportProxyModel)
class SubscriptionReportAdmin(admin.ModelAdmin):
    list_display = (
        'get_data', 'get_user', 'get_invoice', 'get_orders', 'state',
    )
    list_filter = (
        'partner', StateSubscriptionFilter, UUIDFilter,
    )
    formfield_overrides = {
        fields.JSONField: {'widget': JSONEditorWidget},
    }
    search_fields = (
        'data', 'payment_profile__prof_doc_num',
        'payment_profile__portal_email',
        'payment_profile__siebel_entecode',
    )
    readonly_fields = (
        'payment_profile', 'plan',
    )
    actions = (sync_with_arc,)
    inlines = (PaymentInline,)
    change_list_template = 'admin/chart_change_list.html'
    resource_class = SubscriptionResource

    CHART_FIELD_NAME = ''
    CHART_TITLE = ''

    def get_export_formats(self):
        # return self.formats + (SCSV, )
        return (base_formats.CSV,)  # Sólo opcion CSV

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'plan', 'payment_profile', 'arc_user', 'partner',
        )

    def get_data(self, obj):
        tz = timezone.get_current_timezone()

        tz_created = obj.created.astimezone(tz)

        tz_last_updated = obj.last_updated.astimezone(tz)
        last_updated = formats.date_format(tz_last_updated, settings.DATETIME_FORMAT)

        title = obj.plan.plan_name if obj.plan_id else ''
        title += ' [{}]'.format(obj.campaign.get_category()) if obj.campaign_id else ' [--]'

        anulled = ''
        if obj.date_anulled:
            tz_date_anulled = obj.date_anulled.astimezone(tz)
            anulled = format_html(
                '<i class="fas fa-arrow-circle-down"></i> <strong title="Última modificación: {last_updated}">{date_anulled}</strong></br>',
                date_anulled=formats.date_format(tz_date_anulled, settings.DATETIME_FORMAT),
                last_updated=last_updated,
            )

        return format_html(
            '<strong>{title}</strong></br>'
            '<i class="fas fa-key"></i> ID {key}</br>'
            '<i class="fas fa-arrow-circle-up"></i> <strong title="Última modificación: {last_updated}">{created}</strong></br>'
            '{anulled}'
            '<i class="fas fa-newspaper"></i> {site}</br>',
            title=title,
            site=obj.partner,
            key=obj.arc_id,
            anulled=anulled,
            created=formats.date_format(tz_created, settings.DATETIME_FORMAT),
            last_updated=last_updated,
        )

    def get_user(self, obj):
        return obj.arc_user.get_display_html() if obj.arc_user_id else '-'

    def get_invoice(self, obj):
        payment_profile_link = '/admin/paywall/paymentprofile/{}/change/'.format(
            obj.payment_profile.id
        ) if obj.payment_profile else '#'

        tz = timezone.get_current_timezone()

        try:
            tz_date = obj.starts_date.astimezone(tz)
            date_start_suscription = formats.date_format(tz_date, settings.DATETIME_FORMAT)
        except Exception as name_exception:
            date_start_suscription = 'Error en la fecha de suscripcion' + str(name_exception)

        return format_html(
            '<i class="fas fa-id-card fa-sm"></i> {payment_profile} '
            '<a href="{payment_profile_link}" target="_blank"><small>(ver)</small></a></br>'
            '<i class="fas fa-calendar-alt"></i> {date}</br>',
            payment_profile=obj.payment_profile or '--',
            payment_profile_link=payment_profile_link,
            date=date_start_suscription,
        )

    def get_orders(self, obj):
        if not obj.data or not obj.data.get('salesOrders'):
            return '----'

        html = ''

        for order in obj.data['salesOrders'][-2:]:
            _date = timestamp_to_datetime(order['orderDateUTC'])

            html += '<span title="{date_detail}">{date} • S/ {amount}</span></br>'.format(
                amount=order['total'],
                date_detail=formats.localize(_date),
                date=formats.date_format(_date, settings.DATE_FORMAT),
            )

        return format_html(html)

    get_data.short_description = 'Suscripción'
    get_invoice.short_description = 'Datos de pago'
    get_orders.short_description = 'Transacciones'
    get_user.short_description = 'Usuario'


@admin.register(RenovationProxyModel)
class RenovationTransactionAdmin(admin.ModelAdmin):
    list_display = ('siebel_ente', 'siebel_name_client', 'siebel_delivery', 'rate_total_sent_conciliation',
                    'tipo_renovacion', 'created', 'siebel_name_product', 'metodo_pago', 'fecha_de_renovacion',)

    actions = [export_csv, export_xls]
    list_filter = (('payment__subscription__date_renovation', DateTimeRangeFilter), 'payment__partner__partner_name')

    def fecha_de_renovacion(self, obj):
        return obj.payment.subscription.date_renovation

    def siebel_ente(self, obj):
        return obj.payment_profile.siebel_entecode

    def siebel_name_client(self, obj):
        return obj.payment_profile.siebel_name

    def siebel_name_product(self, obj):
        return obj.plan.product.siebel_name

    def metodo_pago(self, obj):
        return obj.payment.pa_method

    def tipo_renovacion(self, obj):
        if obj.payment.pa_origin == 'WEB':
            return 'Venta'
        else:
            return obj.payment.pa_origin

    def get_queryset(self, request):
        qs = super(RenovationTransactionAdmin, self).get_queryset(request)
        return qs.filter(
            conciliation_cod_response='1',
            siebel_delivery__gte=1,
            payment_profile__gte=1,
        ).exclude(
            payment_profile__siebel_entecode=None,
            payment_profile__siebel_name=None,
            siebel_delivery__isnull=True,
            siebel_delivery__exact=None,
            payment_profile__isnull=True,
            payment_profile__exact=None,
        ).order_by('-payment__subscription__date_renovation')


@admin.register(OperationProxyModel)
class SiebelTransactionAdmin(admin.ModelAdmin):
    list_display = ('siebel_ente', 'siebel_name_client', 'siebel_delivery', 'rate_total_sent_conciliation',
                    'tipo_renovacion', 'created', 'siebel_name_product', 'metodo_pago', 'date_state_subscription',
                    'payment_period',)
    actions = [export_csv, export_xls]
    list_filter = (('created', DateTimeRangeFilter), 'payment__partner__partner_name', 'payment__subscription__state',)

    def payment_period(self, obj):
        if not obj.payment.subscription.data or not obj.payment.subscription.data.get('paymentHistory'):
            return '----'

        html = ''
        final_payment = obj.payment.subscription.data.get('paymentHistory')[-1]

        period_from = timestamp_to_datetime(final_payment['periodFrom'])
        period_to = timestamp_to_datetime(final_payment['periodTo'])
        html += '<b>De: </b>{period_from} </br> <b>A: </b> {period_to}'.format(
            period_from=formats.localize(period_from),
            period_to=formats.localize(period_to),
        )

        return format_html(html)

    def date_state_subscription(self, obj):
        if not obj.payment.subscription.data or not obj.payment.subscription.data.get('events'):
            return '----'

        html = ''
        final_event = obj.payment.subscription.data.get('events')[-1]
        event_type = final_event['eventType']
        if event_type in ['CANCEL_SUBSCRIPTION', 'TERMINATE_SUBSCRIPTION', 'SUSPEND_SUBSCRIPTION']:
            _date = timestamp_to_datetime(final_event['eventDateUTC'])
            html += 'fecha {date_detail} de {event_type}'.format(
                date_detail=formats.localize(_date),
                event_type=event_type,
            )

        return format_html(html)

    def siebel_ente(self, obj):
        return obj.payment_profile.siebel_entecode

    def siebel_name_client(self, obj):
        return obj.payment_profile.siebel_name

    def siebel_name_product(self, obj):
        return obj.plan.product.siebel_name

    def metodo_pago(self, obj):
        return obj.payment.pa_method

    def tipo_renovacion(self, obj):
        if obj.payment.pa_origin == 'WEB':
            return 'Venta'
        else:
            return obj.payment.pa_origin

    def get_queryset(self, request):
        qs = super(SiebelTransactionAdmin, self).get_queryset(request)
        return qs.filter(
            conciliation_cod_response='1',
            ope_amount__gte=5,
            siebel_delivery__gte=5,
            payment_profile__gte=1,
        ).exclude(
            payment_profile__siebel_entecode=None,
            payment_profile__siebel_name=None,
            siebel_delivery__isnull=True,
            siebel_delivery__exact=None,
            payment_profile__isnull=True,
            payment_profile__exact=None,
        ).order_by('created')

    # change_list_template = 'admin/paywall/siebel_transactions_list.html'


class DomainInline(admin.TabularInline):
    model = Domain
    extra = 1


class CsvImportForm(forms.Form):
    csv_file = forms.FileField()


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ['name', 'dominios']
    inlines = [DomainInline]
    change_list_template = "admin/paywall/university_changelist.html"

    def dominios(self, obj):
        list_domain = []
        domains = Domain.objects.filter(university=obj)
        for domain in domains:
            list_domain.append(domain.name)
        return list_domain

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.import_csv),
        ]
        return my_urls + urls

    def decode_utf8(self, input_iterator):
        for l in input_iterator:
            yield l.decode('utf-8')

    def import_csv(self, request):
        if request.method == "POST":
            error = ''
            list_not_load = []

            file = request.FILES['csv_file']
            decoded_file = file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            for row in reader:
                if not University.objects.filter(name=row.get("universidad", "")).exists():
                    try:
                        college = University(
                            name=row.get("universidad", ""),
                        )
                        college.save()

                        for i in range(1, 10):
                            if row.get("dominio" + str(i), ""):
                                domain = Domain(
                                    name=row.get("dominio" + str(i), ""),
                                    university=college
                                )
                                domain.save()
                            else:
                                break
                    except Exception as e:
                        error = 1
                        capture_event(
                            {
                                'message': 'error al subir csv de universidades',
                                'extra': {
                                    'detalle': e
                                }
                            }
                        )
                        break
                else:
                    list_not_load.append(row.get("universidad", ""))
            # Create Hero objects from passed in data
            # ...
            cadena = ''
            count = 0
            for iterar in list_not_load:
                count = count + 1

                if len(list_not_load) == count:
                    cadena = cadena + iterar
                else:
                    cadena = cadena + iterar + ', '

            if error:
                self.message_user(request, "Ocurrio un Error")
            elif cadena:
                self.message_user(request, "Procesado correctamente, No cargaron las Universidades: " + cadena)
            else:
                self.message_user(request, "Procesado correctamente")
            return redirect("..")

        form = CsvImportForm()
        payload = {"form": form}
        return render(
            request, "admin/paywall/university_csv_form.html", payload
        )


class ReasonExcludeInline(admin.TabularInline):
    model = ReasonExclude
    extra = 1


class SubscriptionExcludeInline(admin.TabularInline):
    model = SubscriptionExclude
    extra = 1


@admin.register(SiebelConfiguration)
class SiebelConfigurationAdmin(admin.ModelAdmin):
    list_display = ['customer_attempts', 'ov_attempts', 'conciliation_attempts']
    inlines = [ReasonExcludeInline, SubscriptionExcludeInline]


@admin.register(ReportLongPeriodTime)
class ReportLongPeriodTimeAdmin(admin.ModelAdmin):
    list_display = ['data', 'site']


class EmptyProfileFilter(admin.SimpleListFilter):
    title = 'Perfil de Pago incompleto'
    parameter_name = 'empty_profile'

    def lookups(self, request, model_admin):
        return (
            ('empty_profile', 'Perfil incompleto'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'empty_profile':
            return queryset.filter(
                Q(subscription__payment_profile=None) |
                Q(subscription__payment_profile__prof_doc_num=None) |
                Q(subscription__payment_profile__prof_doc_type=None) |
                Q(subscription__payment_profile__prof_name=None) |
                Q(subscription__payment_profile__prof_lastname=None)
            )
        else:
            return queryset


class WebViewFilter(admin.SimpleListFilter):
    title = 'WebView'
    parameter_name = 'webview'

    def lookups(self, request, model_admin):
        return (
            ('is_webview', 'Es WebView'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'is_webview':
            return queryset.filter(browser_version__contains='WebView')
        else:
            return queryset


class SubscriptionExistsFilter(admin.SimpleListFilter):
    title = 'Suscripción'
    parameter_name = 'subscription_exists'

    def lookups(self, request, model_admin):
        return (
            ('with_subscription', 'Con Suscripción'),
            ('without_subscription', 'Sin Suscripción'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'with_subscription':
            return queryset.filter(subscription__isnull=False)
        elif self.value() == 'without_subscription':
            return queryset.filter(subscription__isnull=True)
        else:
            return queryset


class SubscriptionEventExistsFilter(admin.SimpleListFilter):
    title = 'Suscripción'
    parameter_name = 'subscription_event_exists'

    def lookups(self, request, model_admin):
        return (
            ('with_subscription', 'Con Suscripción'),
            ('without_subscription', 'Sin Suscripción'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'with_subscription':
            return queryset.filter(subscription_obj__isnull=False)
        elif self.value() == 'without_subscription':
            return queryset.filter(subscription_obj__isnull=True)
        else:
            return queryset


@admin.register(EventReport)
class EventReportAdmin(admin.ModelAdmin):
    list_display = ['current_product_name', 'client_id', 'event_type', 'subscription_id', 'created_on',
                    'current_product_sku', 'current_product_price_code']
    list_filter = (
        SubscriptionEventExistsFilter, 'event_type', 'current_product_name',
    )


@admin.register(PaymentTracking)
class PaymentTrackingAdmin(admin.ModelAdmin):
    list_display = ['get_data', 'profile', 'url_referer', 'get_user', 'get_transaction', 'navegador']
    list_filter = (
        ('created', DateTimeRangeFilter), 'partner', PlanFilter, WebViewFilter, 'device', EmptyProfileFilter,
        SubscriptionExistsFilter,
        'medium', 'is_pwa', 'confirm_subscription', 'user_agent_str', 'browser_version', 'os_version',
        'device_user_agent',
    )
    search_fields = ('arc_order', 'uuid',)
    readonly_fields = ('subscription', 'payment',)

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

    def profile(self, obj):
        if obj.site:
            data = SalesClient().get_order(
                site=obj.site,
                order_id=obj.arc_order
            )
            try:
                full_name = "{} {} {}".format(
                    data.get('firstName', ''),
                    data.get('lastName', ''),
                    data.get('secondLastName', ''),
                ).strip()

                full_name = full_name.replace('undefined', '')
                full_name = normalize_text(full_name, 'title')
            except Exception:
                full_name = ''

            doc_type = ''
            doc_number = ''
            try:
                if data.get('billingAddress', ''):
                    line2 = data['billingAddress'].get('line2', '').split('_')

                    if len(line2) == 2:
                        doc_type, doc_number = line2

            except Exception:
                pass

            try:
                email = data.get('email', '')
            except Exception:
                email = ''

            try:
                phone = data.get('phone', '') or ''
            except Exception:
                phone = ''

            if obj.confirm_subscription == str(PaymentTracking.ACCEPT_PURCHASE):
                accept_double_charge = 'Acepta doble compra'
            elif obj.confirm_subscription == str(PaymentTracking.NOT_ACCEPTS_PURCHASE):
                accept_double_charge = 'No acepta doble compra'
            elif obj.confirm_subscription == str(PaymentTracking.NOT_GO_THROUGH_FLOW):
                accept_double_charge = 'No paso por el flujo'
            else:
                accept_double_charge = ''

            return format_html(
                '<strong>Nombre: </strong>{full_name}</br>'
                '<b>Email:</b> {email}</br>'
                '<b>{doc_type}:</b> {doc_number}</br>'
                '<b>Telefono:</b> {phone}</br>'
                '<b>UUID:</b> {uuid}</br>'
                '<i class="fas fa-money-bill-wave"></i> {accept_double_charge}',
                full_name=full_name,
                email=email,
                phone=phone,
                doc_type=doc_type,
                doc_number=doc_number,
                uuid=obj.uuid or '',
                accept_double_charge=accept_double_charge
            )
        else:
            return ''

    def get_user(self, obj):
        return obj.subscription.arc_user.get_display_html() if obj.subscription else '-'

    def get_data(self, obj):
        if obj.subscription:
            tz = timezone.get_current_timezone()
            tz_created = obj.subscription.created.astimezone(tz) if obj.subscription else ''
            title = obj.subscription.plan.plan_name if obj.subscription else ''

            anulled = ''
            if obj.subscription:
                if obj.subscription.date_anulled:
                    tz_date_anulled = obj.subscription.date_anulled.astimezone(tz)
                    anulled = format_html(
                        '<i class="fas fa-arrow-circle-down"></i>{date_anulled}</strong></br>',
                        date_anulled=formats.date_format(tz_date_anulled, settings.DATETIME_FORMAT),
                    )

            return format_html(
                '<strong>{title}</strong></br>'
                '<i class="fas fa-key"></i> ID {key}</br>'
                '<i class="fas fa-arrow-circle-up"></i> {created}</strong></br>'
                '{anulled}'
                '<i class="fas fa-newspaper"></i> {site}</br>',
                title=title,
                site=obj.subscription.partner if obj.subscription else '',
                key=obj.subscription.arc_id if obj.subscription else '',
                anulled=anulled,
                created=formats.date_format(tz_created, settings.DATETIME_FORMAT) if obj.subscription else '',
            )
        else:
            return '--'

    def get_transaction(self, obj):
        if obj.is_pwa == '1':
            is_pwa = 'PWA'
        elif obj.is_pwa == '2':
            is_pwa = 'No es PWA'
        else:
            is_pwa = ''

        if 'WebView' in obj.browser_version:
            is_webview = 'WebView'
        else:
            is_webview = ''

        # is_pwa = obj.is_pwa
        tz = timezone.get_current_timezone()
        tz_created = obj.created.astimezone(tz) if obj.created else ''
        return format_html(
            '<strong>ARC Orden: </strong>{full_name}</br>'
            '<b>Portal:</b> {site}</br>'
            '<b>Creacion:</b> {created}</br>'
            '<b>Medio:</b> {medium} - {pwa}</br>'
            '<b>Dispositivo:</b> {device} - <span style="color:blue"><b>{web_view}</b></span></br>',
            full_name=obj.arc_order,
            site=obj.site,
            created=formats.date_format(tz_created, settings.DATETIME_FORMAT) if obj.created else '',
            medium=obj.medium,
            device=obj.get_device_display(),
            pwa=is_pwa,
            web_view=is_webview
        )

    get_data.short_description = 'Suscripción'
    get_transaction.short_description = 'Operación'
    get_user.short_description = 'User Login'
    profile.short_description = 'Perfil de Pago'


@admin.register(PaymentProxyModel)
class PaymentListAdmin(admin.ModelAdmin):
    list_display = ['id', 'payment_profile', 'pa_method', 'pa_amount', 'date_payment', 'arc_order', 'get_subs_arc_id',
                    'partner', 'status', 'pa_origin']
    readonly_fields = ['pa_method', 'pa_amount', 'created', 'date_payment', 'arc_order', 'payu_order',
                       'payu_transaction', 'pa_origin', 'get_state', 'get_created', 'get_arc_id', 'get_client_card',
                       'get_link_payment', 'get_link_subscription', 'get_profile_id',
                       'get_profile_email', 'get_profile_doc_type', 'get_profile_doc_number', 'get_profile_name',
                       'get_profile_lastname', 'get_profile_lastname_mother', 'get_state_entecode',
                       'get_profile_siebel_entecode', 'get_profile_id']
    search_fields = (
        'arc_order',
        'pa_origin',
        'subscription__arc_id',
    )
    list_filter = (
        ('created', DateTimeRangeFilter), 'partner__partner_name', 'pa_origin', 'pa_method',
    )

    inlines = [OperationReportInline]

    fieldsets = (
        ('Pago', {
            'fields': (
                'pa_method',
                'pa_amount',
                'created',
                'date_payment',
                'arc_order',
                'payu_order',
                'payu_transaction',
                'pa_origin',
                'get_link_payment'
            )
        }),
        ('Subscripción', {
            'fields': (
                'get_state',
                'get_created',
                'get_arc_id',
                'get_client_card',
                'get_link_subscription'
            )
        }),
        ('PerfilPago', {
            'fields': (
                'get_profile_id',
                'get_profile_email',
                'get_profile_doc_type',
                'get_profile_doc_number',
                'get_profile_name',
                'get_profile_lastname',
                'get_profile_lastname_mother',
                'get_state_entecode',
                'get_profile_siebel_entecode'
            )
        }),
    )

    # Subscription
    get_state = get_from_field('state', 'Estado')
    get_created = get_from_field('created', 'Fecha')
    get_arc_id = get_from_field('arc_id', 'Arc ID')
    get_client_card = get_from_field('client_card', 'Cliente Card')

    # Profile Payment
    def get_subs_arc_id(self, obj):
        if obj.subscription:
            return obj.subscription.arc_id

    get_subs_arc_id.short_description = "Subscription"

    # Profile Payment
    def get_profile_id(self, obj):
        return obj.payment_profile.id

    def get_profile_email(self, obj):
        return obj.payment_profile.portal_email

    def get_profile_doc_type(self, obj):
        return obj.payment_profile.prof_doc_type

    def get_profile_doc_number(self, obj):
        return obj.payment_profile.prof_doc_num

    def get_profile_name(self, obj):
        return obj.payment_profile.prof_name

    def get_profile_lastname(self, obj):
        return obj.payment_profile.prof_lastname

    def get_profile_lastname_mother(self, obj):
        return obj.payment_profile.prof_lastname_mother

    def get_profile_siebel_entecode(self, obj):
        return obj.payment_profile.siebel_entecode

    get_profile_id.short_description = "ID"
    get_profile_email.short_description = "Email"
    get_profile_doc_type.short_description = "Doc tipo"
    get_profile_doc_number.short_description = "Doc número"
    get_profile_name.short_description = "Nombre"
    get_profile_lastname.short_description = "A. Paterno"
    get_profile_lastname_mother.short_description = "A. Materno"
    get_profile_siebel_entecode.short_description = "EnteCode"

    @mark_safe
    def get_link_payment(self, obj):
        return '<a href="{}" target="_blank">Ver detalle</a>'.format(reverse("admin:paywall_payment_change",
                                                                             args=(obj.id,)))

    get_link_payment.short_description = "Detalle"
    get_link_payment.allow_tags = True

    @mark_safe
    def get_link_subscription(self, obj):
        return '<a href="{}" target="_blank">Ver detalle</a>'.format(reverse("admin:paywall_subscription_change",
                                                                             args=(obj.subscription.id,)))

    get_link_subscription.short_description = "Detalle"
    get_link_subscription.allow_tags = True

    @mark_safe
    def get_state_entecode(self, obj):
        return self.get_label(obj.payment_profile.siebel_state)

    get_state_entecode.short_description = "Siebel Estado"
    get_state_entecode.allow_tags = True

    def get_label(self, state):
        return "<p style='margin: 0;padding: 0;margin-top: -1px;'>{}</span></p>".format(
            '<img style="margin-top: -2px;" src="/static/admin/img/icon-{}.svg" alt="{}">'.format(
                'yes' if state else 'no', self.get_state(state)))

    def get_state(self, state):
        return 'Enviado' if state else 'Pendiente'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ProductoFilter(admin.SimpleListFilter):
    title = 'Plan'
    parameter_name = 'plan'

    def lookups(self, request, model_admin):
        if settings.ENVIRONMENT == 'test':
            price_codes = ['PS3T0I', 'UJWWFG']
        else:
            price_codes = ['HCOXH0', 'SFGOWP', 'E8JAAM', 'LKHH4J', 'LAP2DN', 'NGDY3J', 'UKH9PV', 'B6KT1C', 'KJCSUX']
            
        choices = []
        for plan in Plan.objects.filter(arc_pricecode__in = price_codes):
            choices.append(
                [plan.arc_pricecode, plan.plan_name]
            )

        return choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(data__priceCode=self.value())

        return queryset


@admin.register(CortesiaModel)
class CortesiaModelAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = CortesiaCallResource
    list_display = (
         'arc_id', 'get_email', 'date_create', 'get_uuid', 'get_plan',
    )
    list_filter = (
        ('starts_date', DateTimeRangeFilter), ('date_anulled', DateTimeRangeFilter), 'partner', ProductoFilter,
    )

    def get_email(self, obj):
        if obj.arc_user:
            return obj.arc_user.email
        else:
            return '-'

    def date_create(self, obj):
        if obj.starts_date:
            tz_date = obj.starts_date.astimezone(
                timezone.get_current_timezone()
            )
            if obj.date_anulled:
                tz_baja = obj.date_anulled.astimezone(
                    timezone.get_current_timezone()
                )
            else:
                tz_baja = ''

            return format_html(
                '<b>Fecha de alta:</b> {alta}</br>'
                '<b>Fecha de baja:</b> {baja}',
                alta=formats.date_format(tz_date, settings.DATETIME_FORMAT),
                baja=formats.date_format(tz_baja, settings.DATETIME_FORMAT) if tz_baja else '-')
        else:
            return ''

    def get_queryset(self, request):
        qs = super(CortesiaModelAdmin, self).get_queryset(request)
        if settings.ENVIRONMENT == 'test':
            return qs.filter(
                Q(data__priceCode='PS3T0I') | Q(data__priceCode='UJWWFG')
            )
        else:
            return qs.filter(
                Q(data__priceCode='HCOXH0') |  # Cortesia clientes print Gestion
                Q(data__priceCode='SFGOWP') |  # cortesía 3D ec
                Q(data__priceCode='E8JAAM') |  # 7días free ec
                Q(data__priceCode='LKHH4J') | Q(data__priceCode='LAP2DN') |  # retención ec, gestion
                Q(data__priceCode='NGDY3J') | Q(data__priceCode='UKH9PV') |  # Plan Cortesia por Migracion EC, Gestion
                Q(data__priceCode='B6KT1C') | Q(data__priceCode='KJCSUX')  # colaborador ec, gestion
            )

    def get_uuid(self, obj):
        if obj.arc_user:
            return obj.arc_user.uuid
        else:
            return '-'

    def get_export_formats(self):
        return (base_formats.XLS,)

    def get_plan(self, obj):
        return format_html(
            '<b>Producto:</b> {producto}</br>'
            '<b>Plan:</b> {plan}</br>'
            '<b>Marca:</b> {marca}',
            producto=obj.plan.product.prod_name if obj.plan else '-',
            plan=obj.plan.plan_name if obj.plan else '-',
            marca=obj.partner.partner_name if obj.partner else '-'
        )

    get_email.short_description = 'Email'
    date_create.short_description = 'Fechas'
    get_uuid.short_description = 'UUID'
    get_plan.short_description = 'Plan'