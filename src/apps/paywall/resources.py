from import_export import resources
from django.conf import settings
from import_export.fields import Field
from django.utils import formats, timezone
from django.utils.timezone import get_default_timezone
import json

from .models import Collaborators, Subscription, Corporate, ReporteUniversitarios, UserOffer, SubscriberPrinted, CortesiaModel
from apps.siebel.models import LogSiebelConciliacion


class CollaboratorsResource(resources.ModelResource):

    class Meta:
        model = Collaborators
        fields = [
            'code', 'doc_type', 'doc_number', 'name', 'lastname', 'email', 'created', 'data_annulled', 'state', 'site',
        ]

        export_order = (
            'code', 'doc_type', 'doc_number', 'name', 'lastname', 'email', 'created', 'data_annulled', 'state', 'site',
        )


class SubscriptionResource(resources.ModelResource):
    user_uuid = Field()
    portal = Field()
    sku = Field()
    price_code = Field()
    plan = Field()
    # starts_date = Field(attribute='starts_date', column_name='fecha_alta')

    class Meta:
        model = Subscription
        fields = (
            'id', 'arc_id', 'state', 'starts_date', 'date_anulled',
        )

    def dehydrate_user_uuid(self, obj):
        if obj.arc_user_id:
            return obj.arc_user.uuid

    def dehydrate_portal(self, obj):
        return obj.partner.partner_code

    def dehydrate_sku(self, obj):
        if obj.data:
            return obj.data['sku']

    def dehydrate_price_code(self, obj):
        if obj.data:
            return obj.data['priceCode']

    def dehydrate_plan(self, obj):
        if obj.plan_id:
            return obj.plan.plan_name


class CortesiaCallResource(resources.ModelResource):
    email = Field(attribute='email', column_name='Email')
    date_high = Field(attribute='date_high', column_name='Fecha de alta')
    date_low = Field(attribute='date_low', column_name='Fecha de baja')
    uuid = Field(attribute='uuid', column_name='UUID')
    arc_id = Field(attribute='arc_id', column_name='ARC ID')
    producto = Field(attribute='producto', column_name='Producto')
    plan = Field(attribute='plan', column_name='Plan')
    marca = Field(attribute='marca', column_name='Marca')
    plan = Field(attribute='plan', column_name='Plan')
    state = Field(attribute='state', column_name='Estado')
    document_type = Field(attribute='document_type', column_name='Tipo de documento')
    document_number = Field(attribute='document_number', column_name='Numero de documento')
    name = Field(attribute='name', column_name='Nombre')
    nro_telefono = Field(attribute='nro_telefono', column_name='Número de Telefono')

    class Meta:
        model = CortesiaModel
        report_skipped = True
        fields = ('arc_id', 'email', 'date_high', 'date_low', 'uuid', 'producto', 'marca', 'plan', 'state',
                  'document_type', 'document_number', 'name', 'nro_telefono',)
        export_order = ('arc_id', 'email', 'date_high', 'date_low', 'uuid', 'producto', 'marca', 'plan', 'state',
                        'document_type', 'document_number', 'name', 'nro_telefono',)

    def dehydrate_state(self, cortesiamodel):
        return cortesiamodel.get_state_display()

    def dehydrate_document_type(self, cortesiamodel):
        if cortesiamodel.arc_user:
            try:
                for atribute in cortesiamodel.arc_user.data.get('attributes', ''):
                    if atribute['name'] == 'documentType':
                        return atribute['value']
                return ''
            except:
                return ''

    def dehydrate_document_number(self, cortesiamodel):
        if cortesiamodel.arc_user:
            try:
                for atribute in cortesiamodel.arc_user.data.get('attributes', ''):
                    if atribute['name'] == 'documentNumber':
                        return atribute['value']
                return ''
            except:
                return ''

    def dehydrate_name(self, cortesiamodel):
        if cortesiamodel.arc_user:
            try:
                first_name = cortesiamodel.arc_user.data.get('firstName', '')
                last_name = cortesiamodel.arc_user.data.get('lastName', '')
                if first_name and last_name:
                    return "{} {}".format(first_name, last_name)
                else:
                    return ''
            except Exception as e:
                return ''

    def dehydrate_nro_telefono(self, cortesiamodel):
        if cortesiamodel.arc_user:
            if cortesiamodel.arc_user.data.get('contacts', ''):
                list_contacs = cortesiamodel.arc_user.data.get('contacts', '')
                for contacs in list_contacs:
                    return contacs.get('phone', '')
        return ''

    def dehydrate_marca(self, cortesiamodel):
        if cortesiamodel.partner:
            return cortesiamodel.partner.partner_name
        else:
            return '-'

    def dehydrate_producto(self, cortesiamodel):
        if cortesiamodel.plan:
            return cortesiamodel.plan.product.prod_name
        else:
            return '-'

    def dehydrate_plan(self, cortesiamodel):
        if cortesiamodel.plan:
            return cortesiamodel.plan.plan_name
        else:
            return '-'

    def dehydrate_arc_id(self, cortesiamodel):
        if cortesiamodel.arc_id:
            return str(cortesiamodel.arc_id)
        else:
            return '-'

    def dehydrate_date_high(self, cortesiamodel):
        if cortesiamodel.starts_date:
            tz_date = cortesiamodel.starts_date.astimezone(
                timezone.get_current_timezone()
            )
            return formats.date_format(tz_date, settings.DATETIME_FORMAT)
        else:
            return '-'

    def dehydrate_date_low(self, cortesiamodel):
        if cortesiamodel.date_anulled:
            tz_low = cortesiamodel.date_anulled.astimezone(
                timezone.get_current_timezone()
            )
            return formats.date_format(tz_low, settings.DATETIME_FORMAT)
        else:
            return '-'

    def dehydrate_email(self, cortesiamodel):
        if cortesiamodel.arc_user:
            return cortesiamodel.arc_user.email
        else:
            return '-'

    def dehydrate_uuid(self, cortesiamodel):
        if cortesiamodel.arc_user:
            return str(cortesiamodel.arc_user.uuid)
        else:
            return '--'


class CorporateResource(resources.ModelResource):
    corp_email = Field(attribute='corp_email', column_name='Email')
    corp_organization = Field(attribute='corp_organization', column_name='Organización')
    corp_detail = Field(attribute='corp_detail', column_name='Descripción')
    nombre = Field(attribute='nombre', column_name='Nombre')
    tipo_corporate = Field(attribute='tipo_corporate', column_name='Asunto')
    portal = Field(attribute='portal', column_name='Portal')

    class Meta:
        model = Corporate
        report_skipped = True
        fields = ('nombre', 'corp_email', 'tipo_corporate', 'corp_organization', 'telefono', 'corp_detail', )
        export_order = ('nombre', 'corp_email', 'tipo_corporate', 'corp_organization', 'telefono', 'corp_detail',)

    def dehydrate_nombre(self, corporate):
        if corporate.corp_name and corporate.corp_lastname:
            return '{} {}'.format(corporate.corp_name, corporate.corp_lastname)
        elif corporate.corp_name and not corporate.corp_lastname:
            return '{}'.format(corporate.corp_name)
        elif not corporate.corp_name and corporate.corp_lastname:
            return '{}'.format(corporate.corp_lastname)
        else:
            return ''

    def dehydrate_portal(self, corporate):
        if corporate.site:
            return corporate.site.partner_name

    def dehydrate_tipo_corporate(self, corporate):
        if corporate.corp_type == '1':
            return 'Quiero una suscripción'
        elif corporate.corp_type == '2':
            return 'Tengo una suscripción'
        elif corporate.corp_type == '3':
            return 'Otros'
        else:
            return ''


class AcademicReportResource(resources.ModelResource):
    email_login = Field(attribute='email_login', column_name='Email de Login')
    email = Field(attribute='email', column_name='Email Universitario')
    with_subscription = Field(attribute='with_subscription', column_name='Suscripción')
    uuid = Field(attribute='uuid', column_name='UUID')
    degree = Field(attribute='degree', column_name='Grado de Estudios')
    date_birth = Field(attribute='date_birth', column_name='Fecha de Nacimiento')
    brand = Field(attribute='brand', column_name='Portal')

    class Meta:
        model = ReporteUniversitarios
        report_skipped = True
        fields = ('email', 'date_birth', 'degree', 'with_subscription', 'uuid', 'brand', )
        export_order = ('email_login', 'email', 'date_birth', 'degree', 'with_subscription', 'uuid', 'brand', )

    def dehydrate_email_login(self, reporteuniversitarios):
        try:
            return reporteuniversitarios.arc_user.email
        except:
            return ''

    def dehydrate_brand(self, reporteuniversitarios):
        try:
            return reporteuniversitarios.site.partner_name
        except:
            return ''

    def dehydrate_uuid(self, reporteuniversitarios):
        try:
            return str(reporteuniversitarios.arc_user.uuid)
        except:
            return ''

    def dehydrate_date_birth(self, reporteuniversitarios):
        try:
            tz = timezone.get_current_timezone()
            tz_birth = reporteuniversitarios.date_birth.astimezone(tz)
            return formats.date_format(tz_birth, 'd.m.Y')
        except:
            return ''

    def dehydrate_with_subscription(self, reporteuniversitarios):
        try:
            if reporteuniversitarios.user_offer.subscription:
                return "Con suscripción"
            else:
                return "Sin suscripción"
        except:
            return "Sin suscripción"


class LogSiebelConciliacionResource(resources.ModelResource):
    transactionid = Field(attribute='transactionid', column_name='transactionid')
    log_request = Field(attribute='log_request', column_name='log_request')
    log_response = Field(attribute='log_response', column_name='log_response')

    class Meta:
        model = LogSiebelConciliacion
        report_skipped = True
        fields = ('transactionid', 'log_request', 'log_response', )
        export_order = ('transactionid', 'log_request', 'log_response', )

    def dehydrate_transactionid(self, logSiebelConciliacion):
        try:
            if logSiebelConciliacion.log_request:
                start = '<tem:num_liquida_id>'
                end = '</tem:num_liquida_id>'
                csr = logSiebelConciliacion.log_request
                return csr[csr.find(start) + len(start):csr.find(end)]
        except:
            return ''
        return ''


class UserOfferResource(resources.ModelResource):
    nombre = Field(attribute='nombre', column_name='Nombre')

    class Meta:
        model = UserOffer
        report_skipped = True
        fields = ('dni', 'nombre', )

    def dehydrate_nombre(self, useroffer):
        try:
            subscriber_printed = SubscriberPrinted.objects.get(
                us_docnumber=useroffer.dni
            )
        except Exception as e:
            subscriber_printed = ''

        if subscriber_printed:
            return '{nombre} {apellido}'.format(
                nombre=subscriber_printed.us_name, apellido=subscriber_printed.us_lastname
            )
        return ''
