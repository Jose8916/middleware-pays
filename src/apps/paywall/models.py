from datetime import datetime, timedelta
from uuid import uuid4
import json

from django.conf import settings
from django.contrib.postgres.fields import ArrayField, JSONField
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import signals
from django.dispatch import receiver
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.timezone import get_default_timezone
from sentry_sdk import add_breadcrumb, capture_exception, capture_event, capture_message

from ..arcsubs.models import ArcUser, Event
from ..arcsubs.utils import timestamp_to_datetime
from ..webutils.fields import ExclusiveBooleanField
from ..webutils.models import _BasicAuditedModel
from ..webutils.utils import normalize_text
from .constants import DOC_TYPE, DATA_LOADED_CHOICES, COLLABORATORS_ACTION, SITE_CHOICES
from .utils import utc_to_lima_time_zone
from apps.paywall.arc_clients import SalesClient
from apps.paywall.utils import is_email


class SiebelBase(_BasicAuditedModel):
    siebel_hits = models.IntegerField(
        verbose_name='Intentos a Siebel',
        default=0
    )
    siebel_request = models.TextField(
        null=True,
        blank=True
    )
    siebel_response = models.TextField(
        null=True,
        blank=True
    )

    class Meta:
        abstract = True


class OfferBase(_BasicAuditedModel):
    OFFER_PRINCIPAL = 'principal'
    OFFER_EVENT = 'event'
    OFFER_UNIVERSITY = 'university'
    OFFER_SUBSCRIBER = 'subscriber'
    OFFER_SUBSCRIBER_FULL = 'full_subscriber'
    OFFER_FACEBOOK = 'facebook_instant'

    OFFER_CHOICES = (
        (OFFER_PRINCIPAL, 'Regular'),
        (OFFER_EVENT, 'Eventos'),
        (OFFER_FACEBOOK, 'Facebook'),
        (OFFER_UNIVERSITY, 'Universitario'),
        (OFFER_SUBSCRIBER, 'Suscriptores'),
        (OFFER_SUBSCRIBER_FULL, 'Suscriptores 7 días'),
    )

    class Meta:
        abstract = True


class Partner(_BasicAuditedModel):
    partner_name = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Nombre',
    )
    partner_code = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name='Código',
    )
    partner_host = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Dominio',
    )
    # sender = models.EmailField(
    #     verbose_name='Email fuente',
    #     null=True,
    #     default='noreply@comercio.com.pe',
    #     help_text='Coordinar con infraestructura para que se habilite el correo.'
    # )
    promotional_sender = models.EmailField(
        verbose_name='Remitente para promociones',
        null=True,
        default='noreply@comercio.com.pe',
        help_text='Coordinar con infraestructura que se habilite el dominio.'
    )
    transactional_sender = models.EmailField(
        verbose_name='Remitente para transacciones',
        null=True,
        default='noreply@comercio.com.pe',
        help_text='Coordinar con infraestructura que se habilite el dominio.'
    )
    faq_url = models.URLField(
        verbose_name='Preguntas frecuentes',
        null=True,
        blank=True,
    )
    terms_of_service_url = models.URLField(
        verbose_name='Términos y condiciones',
        null=True,
        blank=True,
    )
    privacy_policy_url = models.URLField(
        verbose_name='Políticas de privacidad',
        null=True,
        blank=True,
    )
    nro_renewal_attempts = models.IntegerField(
        default=0,
        null=True,
        blank=True,
        verbose_name='Numero de intentos de renovación',
    )
    pixel_id = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        verbose_name='Pixel ID',
    )
    app_secret_facebook = models.CharField(
        max_length=60,
        null=True,
        blank=True,
        verbose_name='APP Secret Facebook',
    )
    subscription_node_id_facebook = models.CharField(
        max_length=60,
        null=True,
        blank=True,
        verbose_name='Subscription Node Id Facebook',
    )
    access_token_facebook = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        verbose_name='Access Token Facebook',
    )

    class Meta:
        verbose_name = 'Portal'
        verbose_name_plural = '[Config] Portales'

    def __str__(self):
        return self.partner_name


class CampaignManager(models.Manager):

    def get_default_by_site(self, site):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        return self.get_by_offer(site=site, offer=self.model.OFFER_PRINCIPAL)

    def get_offer_by_site(self, site):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        return self.get_by_offer(site=site, offer=self.model.OFFER_SUBSCRIBER)

    def get_offer_event_by_site(self, site, event):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        return self.get_by_offer_event(site=site, event=event)

    def get_free_by_site(self, site):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        return self.get_by_offer(site=site, offer=self.model.OFFER_SUBSCRIBER_FULL)

    def get_facebook_by_site(self, site):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        return self.get_by_offer(site=site, offer=self.model.OFFER_FACEBOOK)

    def get_by_offer(self, site, offer):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        if not site:
            raise ValueError('Debe definir site')

        campaign = None
        try:
            campaign = self.get_queryset().get(partner__partner_code=site, offer=offer)
            if campaign.data and campaign.order_plans == 'DESC':
                products = []
                for product in campaign.data['products']:
                    product['pricingStrategies'].reverse()
                    products.append(product)
                campaign.data['products'] = products
        except ObjectDoesNotExist:
            capture_message(
                'get_by_offer: No se encontró campaña de la oferta {} [{}]'.format(offer, site)
            )

        else:
            try:
                if not campaign.is_active:
                    capture_message(
                        'get_by_offer: Campaña {} inactiva [{}]'.format(campaign.name, site)
                    )
            except:
                print('error')

        return campaign

    def get_by_offer_event(self, site, event):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        if not site:
            raise ValueError('Debe definir site')

        campaign = None
        try:
            campaign = self.get_queryset().get(partner__partner_code=site, event=event)
            if campaign.data and campaign.order_plans == 'DESC':
                products = []
                for product in campaign.data['products']:
                    product['pricingStrategies'].reverse()
                    products.append(product)
                campaign.data['products'] = products
        except ObjectDoesNotExist:
            capture_message(
                'get_by_offer: No se encontró campaña de la oferta {} [{}]'.format(event, site)
            )

        else:
            try:
                if not campaign.is_active:
                    capture_message(
                        'get_by_offer: Campaña {} inactiva [{}]'.format(campaign.name, site)
                    )
            except:
                print('error')
        return campaign

    def get_by_event(self, site, event):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        if not site:
            raise ValueError('Debe definir site')

        try:
            campaign = self.get_queryset().get(partner__partner_code=site, event=event)

        except ObjectDoesNotExist:
            campaign = None
            capture_message('get_by_event: No se encontró campaña para el evento {} [{}]'.format(event, site))
        return campaign


class Campaign(OfferBase):
    """docstring for Campaint"""

    partner = models.ForeignKey(
        Partner,
        null=True,
        related_name='campaints',
        verbose_name='Portal',
        on_delete=models.PROTECT
    )
    offer = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        verbose_name='Oferta',
        help_text='',
        choices=OfferBase.OFFER_CHOICES,
    )
    name = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='Nombre',
    )
    title = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='Título',
        help_text='Mensaje del baner superior',
    )
    event = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='Evento',
        help_text='Activa la campaña en la ruta /suscripcionesdigitales/eventos/[SLUG]/',
    )
    is_active = ExclusiveBooleanField(
        default=True,
        verbose_name='Activo',
        on=('partner', 'offer',),
        help_text='',
    )
    siebel_codes = ArrayField(
        models.CharField(max_length=20, blank=True),
        default=list,
        blank=True,
        verbose_name='Codigos Siebel',
        help_text='Codigos de productos Siebel con acceso gratuito por ser suscriptores de siete días.',
    )
    data = JSONField(
        null=True,
        blank=True,
        verbose_name='ARC data'
    )
    plans = models.ManyToManyField(
        'Plan',
        editable=False,
        related_name='campaigns',
    )
    is_default = ExclusiveBooleanField(
        default=False,
        verbose_name='Campaña principal',
        on=('partner',),
        help_text='Campaña con planes con precio regular.',
    )
    is_offer = ExclusiveBooleanField(
        default=False,
        verbose_name='Impresos',
        on=('partner',),
        help_text='Campaña con planes para suscriptores del impreso.',
    )
    is_free = ExclusiveBooleanField(
        default=False,
        verbose_name='Gratuito',
        on=('partner',),
        help_text='Campaña gratuita para suscriptores del impreso de 7 días.',
    )
    order_plans = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name='Orden de Planes',
        choices=(
            ('ASC', 'Ascendente'),
            ('DESC', 'Descendente')
        ),
    )

    objects = CampaignManager()

    class Meta:
        verbose_name = 'Campaña'
        verbose_name_plural = '[Config] Campañas'
        unique_together = ('name', 'partner',)
        ordering = ('-is_active', 'offer',)

    def __str__(self):
        return '{} [{}]'.format(self.name, self.get_category())

    def save(self, *args, **kwargs):
        try:
            self.download_data()
        except Exception:
            capture_exception()

        super().save(*args, **kwargs)

        self.load_plans()

    def get_category(self):

        if self.offer:
            return self.get_offer_display()

        elif self.event:
            return 'Evento {}'.format(self.event)

        else:
            return '--'

    def sync_data(self):
        self.save()

    def download_data(self):
        data = SalesClient().get_campaign(
            site=self.partner.partner_code,
            name=self.name
        )

        if data:
            self.data = data

        return self.data

    def load_plans(self):
        # Cargar los datos de ARC

        if not self.data:
            return

        plans = self.plans.all()
        new_plans = []

        for product_data in self.data['products']:
            arc_data = product_data.copy()
            arc_data.pop('pricingStrategies')
            product, created = Product.objects.get_or_create(arc_sku=product_data['sku'])
            product.prod_name = product_data['name']
            product.data = arc_data
            product.partner = self.partner
            product.save()

            for price in product_data['pricingStrategies']:
                plan, created = Plan.objects.get_or_create(
                    arc_pricecode=price['priceCode'],
                    product=product
                )
                plan.plan_name = price['name']
                plan.data = price
                plan.partner = self.partner
                plan.save()

                if plan not in plans:
                    new_plans.append(plan)

        if new_plans:
            self.plans.add(*new_plans)

    def is_available(self):
        # Validation available
        if self.data:
            today = datetime.now(get_default_timezone())
            date_init = timestamp_to_datetime(self.data.get('campaign').get('validFrom'))
            date_expired = timestamp_to_datetime(self.data.get('campaign').get('validUntil'))
            return date_init <= today <= date_expired

    def is_enabled(self):
        # Validation available
        return self.is_available() and self.is_active

    def get_sku(self):
        return self.data['products'][0]['sku']

    def link_user(self, user_uuid):

        plan = self.plans.all()[0]

        arc_user = ArcUser.objects.get_by_uuid(
            uuid=user_uuid,
        )

        LinkSubscription.objects.get_or_create(
            arc_user=arc_user,
            plan=plan,
        )

    def get_paywall_data(self):
        now = timezone.now()
        if not self.last_updated or now - self.last_updated > timedelta(minutes=15):
            self.get_display_data()
            self.save()

        return self.data

    def get_single_campaign(self):
        frequencys = {
            'Month': 'MES',
            'Year': 'AÑO',
            'OneTime': '',
        }

        now = timezone.now()
        if not self.last_updated or now - self.last_updated > timedelta(minutes=15):
            self.save()

        product = self.data['products'][0]

        try:
            description = product['pricingStrategies'][0]['description'].replace('<p>', '').replace('</p>', '')
            description = json.loads(description)
        except Exception:
            capture_exception()
            description = {}

        try:
            frequency = product['pricingStrategies'][0]['rates'][0]['billingFrequency']
            frequency = 'AL %s' % frequencys[frequency]
        except Exception:
            capture_exception()
            frequency = ''

        for plan in product['pricingStrategies']:
            price = float(plan['rates'][0]['amount'])
            print(price)

        return self.data

    def get_display_data(self):

        frequencys = {
            'Month': 'MES',
            'Year': 'AÑO',
            'OneTime': '',
        }

        product = self.data['products'][0]

        features = [
            attr['value'].replace('<p>', '').replace('</p>', '') for attr in product['attributes'] if attr['name'] == 'feature'
        ]

        sku = product['sku']

        price = float(product['pricingStrategies'][0]['rates'][0]['amount'])

        output_type = '?_website=gestion&outputType=paywall' if settings.ENVIRONMENT != 'production' else ''

        try:
            description = product['pricingStrategies'][0]['description'].replace('<p>', '').replace('</p>', '')
            description = json.loads(description)
        except Exception:
            capture_exception()
            description = {}

        try:
            frequency = product['pricingStrategies'][0]['rates'][0]['billingFrequency']
            frequency = 'AL %s' % frequencys[frequency]
        except Exception:
            capture_exception()
            frequency = ''

        return {
            'aditional': '',
            'detail': {
                'aditional': description.get('description', '').capitalize(),
                'duration': description.get('title', '').capitalize(),
                'frequency': frequency,
            },
            'features': features,
            'price': {
                'amount': price,
                'currency': 'S/',
                'currencyCode': 'PEN'
            },
            'recommended': False,
            'title': product['name'],
            'sku': sku,
            'url': '/suscripcionesdigitales/' + output_type,
        }


class Product(_BasicAuditedModel):
    """
        Relación entre campaña de ARC y producto de Siebel
    """
    prod_name = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Name',
    )
    arc_sku = models.CharField(
        max_length=128,
        null=True,
        verbose_name='Arc Sku',
    )
    state = models.BooleanField(
        default=True,
        verbose_name='State',
    )
    prod_code = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Code',
        editable=False,
    )
    prod_description = models.TextField(
        null=True,
        blank=True,
        verbose_name='Description',
        editable=False,
    )
    arc_id = models.IntegerField(
        default=0,
        null=True,
        blank=True,
        verbose_name='Arc ID',
        editable=False,
    )
    arc_campaign = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Arc Campaign',
    )
    prod_type = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name='Type',
        choices=(
            ('D', 'Digital'),
            ('I', 'Impreso')
        ),
    )
    is_printed = ExclusiveBooleanField(
        default=False,
        verbose_name='Oferta sus. print',
        on=('partner',),
    )
    is_web = ExclusiveBooleanField(
        default=False,
        verbose_name='Oferta principal',
        on=('partner',),
    )
    siebel_code = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Siebel Code',
    )
    siebel_name = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Siebel Name',
    )
    siebel_component = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Siebel Componente',
    )
    partner = models.ForeignKey(
        Partner,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='Partner',
        on_delete=models.PROTECT
    )
    data = JSONField(
        null=True,
        blank=True,
        verbose_name='ARC data'
    )

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = '[Config] Productos'

    def __str__(self):
        return '{} [SKU {}]'.format(self.prod_name or '', self.arc_sku)


class PlanManager(models.Manager):

    def get_by_code(self, sku, price_code, extra=None):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        if not sku or not price_code:
            raise ValueError('Debe definir sku y price_code.')

        try:
            plan = self.get_queryset().get(
                product__arc_sku=sku,
                arc_pricecode=price_code,
            )

        except ObjectDoesNotExist:
            capture_event(
                {
                    'message': 'paywall-middleware: No existe Plan con priceCode {price_code} y sku {sku}'.format(
                        price_code=price_code, sku=sku
                    ),
                    'extra': extra or {},
                }
            )

        else:
            return plan


class Plan(_BasicAuditedModel):
    """
        Registro de un Plan, debe tener codigo de ARC.
    """
    plan_name = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Name',
    )
    arc_pricecode = models.CharField(
        max_length=64,
        null=True,
        verbose_name='Arc PriceCode',
    )
    product = models.ForeignKey(
        Product,
        related_name='plans',
        verbose_name='Producto',
        null=True,
        on_delete=models.CASCADE
    )
    partner = models.ForeignKey(
        Partner,
        null=True,
        blank=True,
        related_name='plans',
        verbose_name='Portal',
        on_delete=models.PROTECT
    )
    state = models.BooleanField(
        default=True,
        blank=True,
        verbose_name='State',
    )
    plan_code = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name='Code',
        editable=False,
    )
    plan_months = models.PositiveSmallIntegerField(
        verbose_name='Months',
        default=0,
        null=True,
        blank=True,
        editable=False,
    )
    plan_days = models.PositiveSmallIntegerField(
        verbose_name='Days',
        default=0,
        null=True,
        blank=True,
        editable=False,
    )
    plan_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='monto',
        editable=False,
    )
    plan_detail = models.TextField(
        null=True,
        blank=True,
        verbose_name='Detail',
        editable=False,
    )
    plan_note = models.TextField(
        null=True,
        blank=True,
        verbose_name='ticket del tarifario'
    )
    piano_term_id = models.TextField(
        null=True,
        blank=True,
        verbose_name='Piano Term id'
    )
    data = JSONField(
        null=True,
        blank=True,
        verbose_name='ARC Data'
    )
    objects = PlanManager()

    class Meta:
        verbose_name = 'Plan'
        verbose_name_plural = '[Config] Planes'
        unique_together = ('arc_pricecode', 'product',)

    def __str__(self):
        return '{} - {}'.format(self.plan_name or '', self.product)

    def get_frequency_name(self):
        frequency = None
        if self.data:
            frequency = self.data['rates'][-1]['billingFrequency']
            billing_count = self.data['rates'][-1]['billingCount']

        if frequency == 'Day':
            return 'Diario'

        elif frequency == 'Month':
            if int(billing_count) == 6:
                return 'Semestral'
            elif int(billing_count) == 3:
                return 'Trimestral'
            else:
                return 'Mensual'

        elif frequency == 'Year':
            return 'Anual'
        else:
            return ''

    def get_rate_description(self):

        if not self.data.get('description'):
            return ''

        detail = self.data.get('description', '{}').replace('</p>', '').replace('<p>', '').replace('\n', '') \
            .replace('&nbsp;', '')

        try:
            cart = json.loads(detail).get('cart', '')

        except json.JSONDecodeError:
            return ''

        else:
            return cart


class BundlePlan(_BasicAuditedModel):
    """
        Registro de un Plan, debe tener codigo de ARC.
    """
    name = models.CharField(
        max_length=50,
        null=True,
        verbose_name='Nombre',
    )
    subtitle = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='Subtítulo',
    )
    partner = models.ForeignKey(
        Partner,
        null=True,
        related_name='bundle_plans',
        verbose_name='Portal',
        on_delete=models.PROTECT
    )
    sku = models.CharField(
        max_length=64,
        verbose_name='Sku',
        null=True,
        blank=True,
        help_text='Código de producto Arc',
    )
    price = models.DecimalField(
        verbose_name='Precio',
        max_digits=15,
        decimal_places=2,
        null=True,
    )
    url = models.URLField(
        verbose_name='URL',
        null=True,
    )
    detail = models.CharField(
        max_length=250,
        verbose_name='Detalle',
        null=True,
        help_text='Ejm: AL MES | POR 3 MESES | LUEGO S/ 68 CADA MES',
    )
    features = models.TextField(
        verbose_name='Beneficios',
        null=True,
        blank=True,
        default='',
        help_text='Un beneficio por linea',
    )
    position = models.SmallIntegerField(
        verbose_name='Posición',
        null=True,
        blank=True,
        default=100,
    )
    is_active = models.BooleanField(
        verbose_name='Activo',
        default=True,
    )

    class Meta:
        verbose_name = '[Config] Plan Bundle'
        verbose_name_plural = '[Config] Planes Bundle'
        ordering = ('partner', '-is_active', 'position',)

    def __str__(self):
        return self.name

    def get_display_data(self):
        details = self.detail.split('|') + ['', '', '']

        data = {
            'title': self.name,
            'subtitle': self.subtitle,
            'url': self.url,
            'sku': self.sku,
            'price': {
                'amount': self.price,
                'currency': 'S/',
                'currencyCode': 'PEN'
            },
            'detail': {
                'frequency': details[0],
                'duration': details[1],
                'aditional': details[2],
            },
            'features': [f.strip() for f in self.features.split('\n')],
            'recommended': self.position == 3,
        }
        return data


class BenefitsCoverPage(_BasicAuditedModel):
    menu = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Menu',
    )
    title = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Titulo',
    )
    image = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name='URL imagen',
    )
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name='Descripción',
    )
    partner = models.ForeignKey(
        Partner,
        null=True,
        blank=True,
        verbose_name='Marca',
        on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = 'Beneficio Portada'
        verbose_name_plural = 'Beneficios en Portada'


class TermsConditionsPoliPriv(_BasicAuditedModel):
    name = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Nombre',
    )
    url_polit_priv = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Politicas de Privacidad',
    )
    url_term_conditions = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Terminos y Condiciones',
    )
    partner = models.ForeignKey(
        Partner,
        null=True,
        blank=True,
        verbose_name='Portal',
        on_delete=models.PROTECT
    )
    state = models.BooleanField(
        default=False,
        verbose_name='Estado',
    )
    version = models.IntegerField(
        verbose_name='Version de los terminos y condiciones',
        default=0
    )

    class Meta:
        verbose_name = 'Terminos y Condiciones y Politicas de Privacidad'
        verbose_name_plural = 'Terminos y Condiciones y Politicas de Privacidad'


class UserTermsConditionPoliPriv(_BasicAuditedModel):
    user_uuid = models.UUIDField(
        blank=True,
        null=True,
        unique=True
    )
    complete = models.NullBooleanField(
        verbose_name='Completo',
        null=True,
        blank=True
    )
    tyc_value = models.NullBooleanField(
        verbose_name='terminos y condiciones',
        null=True,
        blank=True
    )
    tyc_pp = models.ForeignKey(
        TermsConditionsPoliPriv,
        null=True,
        blank=True,
        verbose_name='Terminos y Condiciones',
        on_delete=models.PROTECT
    )
    arc_order = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Arc Order',
    )

    class Meta:
        verbose_name = 'User T&C y Politicas de Privacidad'
        verbose_name_plural = 'User T&C y Politicas de Privacidad'


class PaymentProfile(SiebelBase):
    # Perfil Pago
    arc_user = models.ForeignKey(
        ArcUser,
        null=True,
        related_name='payment_profiles',
        verbose_name='User',
        on_delete=models.PROTECT
    )
    state = models.BooleanField(
        default=False,
        verbose_name='Estado',
    )
    prof_name = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Nombre',
    )
    prof_lastname = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='A. Paterno',
    )
    prof_lastname_mother = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='A. Materno',
    )
    prof_doc_type = models.CharField(
        max_length=8,
        null=True,
        blank=True,
        verbose_name='Doc Tipo',
        choices=DOC_TYPE
    )
    prof_doc_num = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Doc Número',
    )
    prof_phone = models.CharField(
        max_length=16,
        null=True,
        blank=True,
        verbose_name='Phone',
    )
    portal_email = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Correo',
    )
    siebel_state = models.BooleanField(
        default=False,
        verbose_name='Siebel Estado',
    )
    siebel_date = models.DateTimeField(
        null=True,
        verbose_name='Siebel Fecha'
    )
    # Datos que retorna Siebel
    siebel_entecode = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Siebel Code',
        help_text='Respuesta del envio de cliente: EnteCliente'
    )
    siebel_name = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Siebel Name',
        help_text='Respuesta del envio de cliente: NameCliente'
    )
    siebel_entedireccion = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Siebel Ente Direccion',
        help_text='Respuesta del envio de cliente: EnteDireccion'
    )
    siebel_direction = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Siebel Name Direccion',
        help_text='Respuesta del envio de cliente: Nombre_spcDireccion'
    )
    user_terms_condition_pp = models.ForeignKey(
        UserTermsConditionPoliPriv,
        null=True,
        blank=True,
        verbose_name='Terminos y condiciones y Politicas de Privacidad',
        on_delete=models.PROTECT
    )
    note = models.CharField(
        max_length=120,
        null=True,
        blank=True,
        verbose_name='Nota',
        help_text='Nota'
    )

    class Meta:
        verbose_name = 'Perfil de pago'
        verbose_name_plural = '[Data] Perfiles de pago'

    def __str__(self):
        return u'%s %s [%s]' % (
            self.get_prof_doc_type_display(),
            self.prof_doc_num,
            self.siebel_entecode or 'EnteCode'
        )

    def get_full_name(self):
        full_name = '{} {} {}'.format(
            self.prof_name or '',
            self.prof_lastname or '',
            self.prof_lastname_mother or '',
        )
        return normalize_text(full_name, 'title')


class LinkSubscription(_BasicAuditedModel):
    arc_user = models.ForeignKey(
        ArcUser,
        null=True,
        related_name='link_subscriptions',
        verbose_name='Cliente',
        on_delete=models.PROTECT,
    )
    plan = models.ForeignKey(
        Plan,
        null=True,
        blank=True,
        related_name='link_subscriptions',
        verbose_name='Plan',
        on_delete=models.PROTECT,
    )
    token = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name='Token',
    )
    expiration = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de expiración',
    )
    result = JSONField(
        'Responce',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Suscripción gratuita'
        verbose_name_plural = '[Data] Ofertas • Suscripciones gratuitas'

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = str(uuid4())

        if not self.expiration:
            self.expiration = datetime(
                year=9999, month=11, day=2, hour=0, minute=0, tzinfo=get_default_timezone()
            )

        self.create_link()

        super().save(*args, **kwargs)

    def __str__(self):
        return '{} • {}'.format(self.arc_user, self.plan)

    def create_link(self):
        if self.result:
            return

        self.result = SalesClient().link_subscription(
            client_id=self.arc_user.uuid,
            sku=self.plan.product.arc_sku,
            price_code=self.plan.arc_pricecode,
            token=self.token,
            expiration=self.expiration,
        )


class ReportLinkedSubscription(LinkSubscription):
    class Meta:
        proxy = True
        verbose_name = 'Reporte de Suscripciones Gratuitas'
        verbose_name_plural = '[Report] Reporte de Suscripciones Gratuitas'


class University(_BasicAuditedModel):
    name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name='Nombre',
    )

    class Meta:
        verbose_name = 'Universidad'
        verbose_name_plural = '[Config] Ofertas • Universidades'


class Domain(_BasicAuditedModel):
    name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name='Nombre',
    )
    university = models.ForeignKey(
        University,
        null=True,
        blank=True,
        verbose_name='Domain',
        on_delete=models.PROTECT
    )

    class Meta:
        verbose_name_plural = 'Dominio'


class SubscriptionManager(models.Manager):

    def get_or_create_subs(self, site, subscription_id, sync_data=False):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        if not site:
            raise ValueError('Subscription must have an site')

        if not subscription_id:
            raise ValueError('Subscription must have an subscription_id')

        try:
            subscription = self.get_queryset().get(arc_id=subscription_id)

        except ObjectDoesNotExist:
            created = True

            partner = Partner.objects.get(
                partner_code=site
            )
            subscription = self.model(
                arc_id=subscription_id,
                partner=partner
            )
            subscription.save(using=self._db)

            # Se registra la oferta usada por el usuario
            subscription.register_offer()

        else:
            created = False

            if sync_data:
                subscription.sync_data()

        return subscription, created


class Subscription(_BasicAuditedModel):
    ARC_STATE_ACTIVE = 1
    ARC_STATE_TERMINATED = 2
    ARC_STATE_CANCELED = 3
    ARC_STATE_SUSPENDED = 4

    ORIGIN_PAYWALL = 'PAYWALL'

    arc_id = models.BigIntegerField(
        default=0,
        verbose_name='ID de ARC'
    )
    partner = models.ForeignKey(
        Partner,
        null=True,
        blank=True,
        related_name='subscriptions',
        verbose_name='Portal',
        on_delete=models.PROTECT
    )
    plan = models.ForeignKey(
        Plan,
        null=True,
        blank=True,
        related_name='subscriptions',
        verbose_name='Plan',
        on_delete=models.PROTECT,
    )
    arc_user = models.ForeignKey(
        ArcUser,
        null=True,
        related_name='subscriptions',
        verbose_name='Cliente',
        on_delete=models.PROTECT,
        editable=False,
    )
    data = JSONField(
        null=True,
        blank=True,
        verbose_name='ARC data'
    )
    state = models.IntegerField(
        verbose_name='Estado',
        null=True,
        blank=True,
        choices=(
            (ARC_STATE_ACTIVE, 'Activo'),
            (ARC_STATE_TERMINATED, 'Terminado'),
            (ARC_STATE_CANCELED, 'Cancelado'),
            (ARC_STATE_SUSPENDED, 'Suspendido'),
        ),
    )
    starts_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de alta',
    )
    subs_trial = models.IntegerField(
        default=0,
        null=True,
        blank=True,
        verbose_name='Trial Days',
        editable=False,
    )
    date_renovation = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Próxima de renovación'
    )
    date_anulled = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de baja'
    )
    motive_anulled = models.CharField(
        max_length=512,
        null=True,
        blank=True,
        verbose_name='Motivo de anulación',
    )
    motive_cancelation = models.CharField(
        max_length=512,
        null=True,
        blank=True,
        verbose_name='Motivo de cancelación',
    )
    subs_origin = models.CharField(
        max_length=16,
        null=True,
        blank=True,
        verbose_name='Origin',
        choices=(
            ('PAYWALL', 'PAYWALL'),
        ),
    )
    payment_profile = models.ForeignKey(
        PaymentProfile,
        null=True,
        blank=True,
        related_name='subscriptions',
        on_delete=models.PROTECT,
        verbose_name='Perfil de pago',
    )
    # address_profile = models.ForeignKey(
    #     AddressProfile,
    #     null=True,
    #     blank=True,
    #     related_name='subscriptions',
    #     verbose_name='Address Profile',
    #     on_delete=models.PROTECT
    # )
    data_loaded = models.NullBooleanField(
        verbose_name='Carga de datos',
        null=True,
        blank=True,
        choices=DATA_LOADED_CHOICES
    )
    campaign = models.ForeignKey(
        Campaign,
        null=True,
        blank=True,
        related_name='subscriptions',
        verbose_name='Campaña',
        on_delete=models.PROTECT,
    )
    delivery = models.IntegerField(
        verbose_name='Siebel Delivery',
        null=True,
        blank=True
    )
    creation_date_delivery = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de creacion del Delivery'
    )

    objects = SubscriptionManager()

    class Meta:
        verbose_name = 'Suscripción'
        verbose_name_plural = '[Data] Suscripciones'
        unique_together = ('partner', 'arc_id',)

    def save(self, *args, **kwargs):
        try:
            if not self.data:
                self.download_data()

            self.load_data()
        except Exception:
            capture_exception()

        super().save(*args, **kwargs)

    def __str__(self):
        return 'ID {} [{}]'.format(self.arc_id, self.partner)

    def get_email(self):

        email = None
        if self.payment_profile and is_email(self.payment_profile.portal_email):
            email = self.payment_profile.portal_email

        elif is_email(self.arc_user.get_email()):
            email = self.arc_user.get_email()

        return email

    def get_full_name(self):

        if self.payment_profile:
            return self.payment_profile.get_full_name()
        else:
            return self.arc_user.get_full_name()

    def get_plan(self, payment=None):
        if not self.data:
            return

        if hasattr(self, '_plan'):
            return self._plan

        self._plan = Plan.objects.get_by_code(
            sku=self.data['sku'],
            price_code=self.data['priceCode'],
            extra={
                'subscription.id': self.id,
                'subscription': self.data,
                'payment.id': payment.id if payment else None,
                'payment': payment.data if payment else None,
            },
        )

        return self._plan

    def sync_data(self, data=None):
        self.data = data if data else None
        self.data_loaded = None
        self.download_data()
        self.save()

    def update_profile(self, data=None):
        if not self.payment_profile:
            payments = Payment.objects.filter(subscription__arc_id=self.arc_id)
            self.data = SalesClient().get_subscription(
                site=self.partner.partner_code,
                subscription_id=self.arc_id
            )
            for payment in payments:
                payment.payment_profile = payment.get_payment_profile()
                payment.save()
            self.payment_profile = payment.get_payment_profile()
            self.save()

            operations = Operation.objects.filter(payment__subscription__arc_id=self.arc_id)
            for operation in operations:
                operation.payment_profile = payment.get_payment_profile()
                operation.save()

    def get_campaign(self):

        if self.by_free_method():
            return

        campaign = Campaign.objects.filter(
            plans=self.plan
        ).order_by('-is_active', '-id').first()

        return campaign

    def download_data(self):
        if not self.data or self.data_loaded is None:
            self.data = SalesClient().get_subscription(
                site=self.partner.partner_code,
                subscription_id=self.arc_id
            )
            # Coloca la bandera como datos pendientes
            self.data_loaded = None

    def load_data(self):
        # Cargar los datos de ARC

        if not self.data or self.data_loaded:
            return

        if not self.arc_user:
            self.arc_user = ArcUser.objects.get_by_uuid(
                uuid=self.data['clientID']
            )

        try:
            self.date_renovation = timestamp_to_datetime(self.data['nextEventDateUTC'])
        except Exception:
            capture_exception()

        # Carga fecha de inicio y fin de la suscripción
        for event in self.data['events']:

            event_date = timestamp_to_datetime(event['eventDateUTC'])

            if event['eventType'] == "START_SUBSCRIPTION":
                self.starts_date = event_date

            if event['eventType'] == "TERMINATE_SUBSCRIPTION":
                self.date_anulled = event_date
                self.motive_anulled = event.get('details')

            if event['eventType'] == "CANCEL_SUBSCRIPTION":
                self.motive_cancelation = event.get('details')

        self.state = self.data['status']

        self.plan = self.get_plan()

        if not self.campaign:
            self.campaign = self.get_campaign()

        self.data_loaded = True

    def get_or_create_payments(self):

        if hasattr(self, '_payments'):
            return self._payments

        self._payments = []

        if self.data:

            for order_data in self.data['salesOrders']:
                payment, created = self.get_or_create_payment(
                    order_number=order_data['orderNumber']
                )
                self._payments.append((payment, created))

        return self._payments

    def get_or_create_payment(self, order_number):
        try:
            payment = Payment.objects.get(
                arc_order=order_number
            )

        except Payment.DoesNotExist:
            created = True
            payment = Payment.objects.create(
                arc_order=order_number,
                partner=self.partner,
                subscription=self,
            )

        except Payment.MultipleObjectsReturned:
            capture_event(
                {
                    'message': 'get_or_create_payment error: MultipleObjectsReturned',
                    'extra': {'arc_order': order_number, },
                }
            )
            return

        else:
            created = False

        # Crea transacciones por cada item cart
        plan = self.get_plan(
            payment=payment
        )
        if plan and payment.is_paid():
            for item in payment.data['items']:
                if item['sku'] == self.data['sku'] and item['priceCode'] == self.data['priceCode']:
                    Operation.objects.get_or_create(
                        state=Operation.STATE_PAYMENT,
                        payment=payment,
                        plan=plan,
                        defaults={
                            'plan_desc': item['shortDescription'],
                            'ope_amount': item['total'],
                            'payment_profile': payment.payment_profile
                        }
                    )

        if not self.payment_profile and payment.payment_profile:
            self.payment_profile = payment.payment_profile
            self.save()

        return payment, created

    def by_payu_method(self):
        return self.data and self.data['currentPaymentMethod']['paymentPartner'] == 'PayULATAM'

    def by_free_method(self):
        return self.data and self.data['currentPaymentMethod']['paymentPartner'] == 'Free'

    def by_linked_method(self):
        return self.data and self.data['currentPaymentMethod']['paymentPartner'] == 'Linked'

    def get_siebel_delivery(self):
        """ Retorna el código delivery de una suscripción """
        if not hasattr(self, '_siebel_delivery'):
            try:
                operation = Operation.objects.get(
                    payment__subscription=self,
                    siebel_delivery__isnull=False
                )

            except Operation.DoesNotExist:
                self._siebel_delivery = None

            else:
                self._siebel_delivery = operation.siebel_delivery

        return self._siebel_delivery

    def register_offer(self):
        """
            Registra la oferta
        """
        from apps.pagoefectivo.models import CIP
        cip_exists = CIP.objects.filter(subscription_arc_id=self.arc_id).exists()

        # Sólo se registran ofertas de suscripciones pagadas o ofertas de 7 días o pago efectivo
        if not self.by_payu_method() and (
                self.campaign and self.campaign.offer != Campaign.OFFER_SUBSCRIBER_FULL
        ) and not cip_exists:
            return

        # Las suscripciones deben tener una campaña
        if not self.campaign:
            capture_message('register_offer error: Suscripción sin campaña')
            return

        # La campaña principal se compran sin ofertas.
        elif self.campaign.offer in (
                Campaign.OFFER_PRINCIPAL,
        ):
            return

        created = None
        try:
            user_offer, created = UserOffer.objects.get_or_create(
                arc_user=self.arc_user,
                campaign=self.campaign,
                defaults={
                    'subscription': self,
                }
            )

        except UserOffer.MultipleObjectsReturned:
            user_offer = UserOffer.objects.filter(
                arc_user=self.arc_user,
                campaign=self.campaign
            )[0]

        add_breadcrumb({
            "level": "info",
            "category": "register_offer",
            "message": 'user_offer ID {id} created {created}'.format(
                id=user_offer.id, created=created
            ),
            "data": {
                'campaign.id': self.campaign.id,
                'plan.id': self.plan_id,
                'subscription.id': self.id,
            },
        })

        if created is True:
            capture_message('register_offer: Cliente no siguió el flujo de ofertas')

        elif created is None:
            capture_message('register_offer: Cliente con multiples user_offers')

        # Se asigna la suscripción a la oferta
        if not user_offer.subscription:
            user_offer.subscription = self
            user_offer.save()

        elif user_offer.subscription != self:
            UserOffer.objects.get_or_create(
                arc_user=self.arc_user,
                campaign=self.campaign,
                subscription=self,
            )
            capture_message('register_offer: Cliente ya compró la misma oferta')


class LowBySuspension(_BasicAuditedModel):
    subscription = models.ForeignKey(
        Subscription,
        verbose_name='Subscription',
        on_delete=models.PROTECT,
        null=True
    )
    event_type = models.CharField(
        max_length=80,
        null=True,
        blank=True,
        verbose_name='Tipo de evento',
    )
    detail = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        verbose_name='Detalle',
    )


class EventTypeSuspension(_BasicAuditedModel):
    name = models.CharField(
        max_length=80,
        null=True,
        blank=True,
        unique=True,
        verbose_name='Tipo de evento',
    )


class TypeOfLowSubscription(_BasicAuditedModel):
    LOW_BY_ADMIN = 1
    LOW_BY_SUSPENSION = 2
    LOW_BY_CANCELLATION = 3
    LIST_TYPE_OF_LOW = (
        (LOW_BY_ADMIN, 'Baja por el modulo del administrador'),
        (LOW_BY_SUSPENSION, 'Baja por suspencion'),
        (LOW_BY_CANCELLATION, 'Baja por cancelacion'),
    )

    subscription = models.ForeignKey(
        Subscription,
        verbose_name='Subscription',
        on_delete=models.PROTECT,
        related_name='type_of_low',
        null=True
    )
    type = models.IntegerField(
        verbose_name='Tipo de Baja',
        null=True,
        blank=True,
        choices=LIST_TYPE_OF_LOW,
    )


class SubscriptionFIA(_BasicAuditedModel):
    SYNCING_FIA_SUCCESS = 1
    SYNCING_FIA_ERROR = 2

    subscription = models.ForeignKey(
        Subscription,
        verbose_name='Subscription',
        on_delete=models.PROTECT,
        null=True
    )
    fia_request = models.TextField(
        null=True,
        blank=True
    )
    fia_response = models.TextField(
        null=True,
        blank=True
    )
    state = models.IntegerField(
        verbose_name='Estado del Envio',
        null=True,
        blank=True,
        choices=(
            (SYNCING_FIA_SUCCESS, 'Exito'),
            (SYNCING_FIA_ERROR, 'Error'),
        ),
    )
    partner = models.ForeignKey(
        Partner,
        null=True,
        verbose_name='Brand',
        on_delete=models.PROTECT,
        blank=True
    )


class SubscriptionState(_BasicAuditedModel):
    ARC_STATE_ACTIVE = 1
    ARC_STATE_TERMINATED = 2
    ARC_STATE_CANCELED = 3
    ARC_STATE_SUSPENDED = 4

    state = models.IntegerField(
        verbose_name='Estado',
        null=True,
        blank=True,
        choices=(
            (ARC_STATE_ACTIVE, 'Activo'),
            (ARC_STATE_TERMINATED, 'Terminado'),
            (ARC_STATE_CANCELED, 'Cancelado'),
            (ARC_STATE_SUSPENDED, 'Suspendido'),
        ),
    )
    event_type = models.CharField(
        max_length=512,
        null=True,
        blank=True,
        verbose_name='Event type',
    )

    detail = models.CharField(
        max_length=512,
        null=True,
        blank=True,
        verbose_name='Event detail',
    )
    date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha',
    )
    date_timestamp = models.BigIntegerField(
        null=True,
        verbose_name='Timestamp Date'
    )

    subscription = models.ForeignKey(
        Subscription,
        verbose_name='Subscription',
        on_delete=models.PROTECT,
        null=True
    )


class SubscriptionReportProxyModel(Subscription):
    class Meta:
        proxy = True
        verbose_name = 'Reporte de estados de las Suscripciones'
        verbose_name_plural = '[Report] Estados de las Suscripciones'


class CortesiaModel(Subscription):
    class Meta:
        proxy = True
        verbose_name = 'Cortesia Callcenter'
        verbose_name_plural = '[Report] Cortesia Callcenter'


class FailRenewSubscription(_BasicAuditedModel):
    subscription = models.ForeignKey(
        Subscription,
        verbose_name='Subscription',
        on_delete=models.PROTECT,
        null=True
    )
    event = models.ForeignKey(
        Event,
        null=True,
        verbose_name='Evento',
        on_delete=models.PROTECT
    )
    event_type = models.CharField(
        max_length=60,
        null=True,
        blank=True,
        verbose_name='event_type',
    )


class Payment(_BasicAuditedModel):
    """
        Registra los order de una subscription
    """
    ARC_STATE_PENDING = 1
    ARC_STATE_PARTIAL = 2
    ARC_STATE_PAID = 'Paid'
    ARC_STATE_PAID3 = 3
    ARC_STATE_CANCELED = 4

    GATEWAY_PAYWALL = 'PAYWALL'

    ORIGIN_RECURRENCE = 'RECURRENCE'

    REFUND_FROM_ARC = 1
    REFUND_FROM_SIEBEL = 2

    status = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Estado',
        default=ARC_STATE_PENDING,
        choices=(
            (ARC_STATE_PENDING, 'Pendiente'),
            (ARC_STATE_PAID, 'Pagado'),
            (ARC_STATE_CANCELED, 'Anulado'),
            (ARC_STATE_PARTIAL, 'Error'),
        )
    )
    data = JSONField(
        null=True,
        blank=True,
        verbose_name='ARC data'
    )
    pa_amount = models.DecimalField(
        verbose_name='Amount',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    date_payment = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Payment Order'
    )
    pa_method = models.CharField(
        max_length=16,
        null=True,
        blank=True,
        verbose_name='Method',
        choices=(
            ('AMEX', 'AMEX'),
            ('DINERSCLUB', 'DINERSCLUB'),
            ('MASTERCARD', 'MASTERCARD'),
            ('VISA', 'VISA'),
        ),
    )
    arc_order = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Arc Order',
        unique=True
    )
    # arc_current_method = JSONField(
    #     null=True,
    #     blank=True,
    #     verbose_name='Json Method'
    # )
    payu_order = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='PayU Order'
    )
    payu_transaction = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='PayU Transaction',
    )
    pa_origin = models.CharField(
        max_length=16,
        verbose_name='Origin',
        choices=(
            ('WEB', 'WEB'),
            ('RECURRENCE', 'RECURRENCE'),
        ),
        default='WEB',
        blank=True,
        null=True,
    )
    pa_gateway = models.CharField(
        max_length=16,
        verbose_name='Gateway',
        blank=True,
        null=True,
        choices=(
            ('PAYWALL', 'PAYWALL'),
        ),
    )
    subscription = models.ForeignKey(
        Subscription,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name='Subscription',
        on_delete=models.PROTECT
    )
    payment_profile = models.ForeignKey(
        PaymentProfile,
        related_name='payments',
        verbose_name='Payment Profile',
        on_delete=models.PROTECT,
        blank=True,
        null=True
    )
    partner = models.ForeignKey(
        Partner,
        null=True,
        related_name='payments',
        verbose_name='Partner',
        on_delete=models.PROTECT,
        blank=True
    )
    data_loaded = models.NullBooleanField(
        verbose_name='Carga de datos',
        null=True,
        blank=True,
        choices=DATA_LOADED_CHOICES
    )
    transaction_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Transaction Date'
    )
    refund_type = models.CharField(
        max_length=16,
        choices=(
            (REFUND_FROM_ARC, 'Reembolso desde ARC'),
            (REFUND_FROM_SIEBEL, 'Reembolso desde SIEBEL'),
        ),
        null=True,
        blank=True,
    )
    refund_amount = models.DecimalField(
        verbose_name='Amount',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    refund_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Transaction Date'
    )

    class Meta:
        # unique_together = ('arc_order', 'partner', )
        verbose_name = 'ARC transacción'
        verbose_name_plural = '[Data] Transacciones de ARC • payments'

    def __str__(self):
        return '{} • {}'.format(self.subscription, self.payment_profile)

    def is_paid(self):
        return self.data and self.data.get('status') == 'Paid'

    def save(self, *args, **kwargs):
        try:
            self.download_data()
            self.load_data()
        except Exception:
            capture_exception()

        super().save(*args, **kwargs)

    def sync_data(self, data=None):
        self.data = data if data else None
        self.data_loaded = None
        self.save()

    def download_data(self):
        if not self.data:
            self.data = SalesClient().get_order(
                site=self.partner.partner_code,
                order_id=self.arc_order
            )

            # Coloca la bandera como datos pendientes
            self.data_loaded = not bool(self.data)

    def load_data(self):
        # Cargar los datos de ARC

        if not self.data or self.data_loaded:
            return

        self.partner = self.subscription.partner
        self.subscription = self.subscription
        self.pa_amount = self.data['total']
        self.pa_gateway = Payment.GATEWAY_PAYWALL
        self.status = self.data['status']
        self.date_payment = timestamp_to_datetime(self.data['orderDate'])
        # self.transaction_date = timestamp_to_datetime(self.data['transactionDate'])

        if self.data['orderType'] == 'Parent':
            self.pa_origin = 'WEB'
        elif self.data['orderType'] == 'Renewal':
            self.pa_origin = 'RECURRENCE'

        for pay in self.data['payments']:
            if pay and pay['paymentMethod'] and pay['paymentMethod']['creditCardType']:
                self.pa_method = pay['paymentMethod']['creditCardType'].upper()

            for transaction in pay['financialTransactions']:
                if transaction['transactionType'] == 'Payment':
                    self.transaction_date = timestamp_to_datetime(transaction['transactionDate'])
                    break

        if self.subscription.payment_profile:
            self.payment_profile = self.subscription.payment_profile
        else:
            self.payment_profile = self.get_payment_profile()

        self.data_loaded = True

    def get_payment_profile(self):

        doc_type = doc_number = None

        for pay in self.data['payments']:

            for transaction in pay['financialTransactions']:

                if transaction['billingAddress']:
                    line2 = transaction['billingAddress'].get('line2', '').split('_')

                    if len(line2) == 2:
                        if line2[0] != 'undefined' and line2[1] != 'undefined':
                            doc_type, doc_number = line2
                        break

            if doc_type and doc_number:
                break

        else:
            capture_event(
                {
                    'message': 'get_payment_profile: Sin DNI',
                    'extra': {
                        'payment': self.id,
                        'data': self.data,
                    }
                }
            )

        kwargs = {
            'arc_user': self.subscription.arc_user,
            'prof_doc_type': doc_type,
            'prof_doc_num': doc_number,
        }

        try:
            payment_profile = PaymentProfile.objects.get(**kwargs)

        except PaymentProfile.MultipleObjectsReturned:
            payment_profile = PaymentProfile.objects.filter(**kwargs)[0]

        except PaymentProfile.DoesNotExist:
            payment_profile = PaymentProfile(**kwargs)

        if self.data['email']:
            payment_profile.portal_email = self.data['email']

        if self.data['phone']:
            payment_profile.prof_phone = self.data['phone']

        if self.data['firstName']:
            payment_profile.prof_name = self.data['firstName']

        if self.data['lastName']:
            payment_profile.prof_lastname = self.data['lastName']

        if self.data['secondLastName']:
            payment_profile.prof_lastname_mother = self.data['secondLastName']

        payment_profile.save()

        return payment_profile


class PaymentProxyModel(Payment):
    class Meta:
        proxy = True
        verbose_name = 'Registro de pago'
        verbose_name_plural = '[Report] Registros de pagos'


class Operation(SiebelBase):
    """
        Registro de un pago de siebel
    """
    STATE_PENDING = 0
    STATE_PAYMENT = 1
    STATE_ANNULLED = 2
    STATE_ERROR = 3

    # FIRST_CHANGE_FEE = 1

    state = models.IntegerField(
        verbose_name='State',
        default=0,
        null=True,
        choices=(
            (STATE_PENDING, 'Pendiente'),
            (STATE_PAYMENT, 'Pagado'),
            (STATE_ANNULLED, 'Anulado'),
            (STATE_ERROR, 'Error'),
        )
    )
    payment_profile = models.ForeignKey(
        PaymentProfile,
        null=True,
        blank=True,
        related_name='operations',
        verbose_name='Payment Profile',
        on_delete=models.PROTECT
    )
    plan_desc = models.CharField(
        max_length=1028,
        null=True,
        blank=True,
        verbose_name='Plan Desc',
    )
    ope_amount = models.DecimalField(
        verbose_name='Amount',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    ope_comment = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        verbose_name='Comment',
    )
    payment = models.ForeignKey(
        Payment,
        null=True,
        blank=True,
        related_name='operations',
        verbose_name='Payment',
        on_delete=models.PROTECT
    )
    plan = models.ForeignKey(
        Plan,
        related_name='operations',
        verbose_name='Plan',
        on_delete=models.PROTECT
    )
    siebel_state = models.BooleanField(
        default=False,
        verbose_name='Siebel state',
    )
    siebel_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Siebel date'
    )
    siebel_delivery = models.IntegerField(
        verbose_name='Siebel Delivery',
        null=True,
        blank=True
    )
    conciliation_state = models.BooleanField(
        default=False,
        verbose_name='Conciliation State',
    )
    conciliation_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Conciliation Date'
    )
    conciliation_siebel_request = models.TextField(
        null=True,
        blank=True
    )
    conciliation_siebel_response = models.TextField(
        null=True,
        blank=True
    )
    conciliation_cod_response = models.TextField(
        null=True,
        blank=True
    )
    conciliation_siebel_hits = models.IntegerField(
        verbose_name='Intentos a Siebel Conciliacion',
        default=0,
        null=True,
        blank=True
    )
    recurrencia_request = models.TextField(
        null=True,
        blank=True
    )
    recurrencia_response = models.TextField(
        null=True,
        blank=True
    )
    recurrencia_response_state = models.NullBooleanField(
        verbose_name='Estado de la Recurrencia',
        null=True,
        blank=True,
    )

    rate_total_sent_conciliation = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        verbose_name='Total'
    )
    observations = models.TextField(
        null=True,
        blank=True,
        verbose_name='Observaciones de la transacción'
    )

    class Meta:
        verbose_name = 'Siebel transacción'
        verbose_name_plural = '[Data] Transacciones de Siebel • operations'

    def __str__(self):
        return str(self.id)

    def load_data(self, commit=True):
        # self.data_loaded = True
        if commit:
            self.save()


class OperationProxyModel(Operation):
    class Meta:
        proxy = True
        verbose_name = 'Transacciones Siebel'
        verbose_name_plural = '[Report] Transacciones Siebel'


class RenovationProxyModel(Operation):
    class Meta:
        proxy = True
        verbose_name = 'Renovaciones Siebel'
        verbose_name_plural = '[Report] Renovaciones Siebel'


class Benefit(_BasicAuditedModel):
    # Benefits
    be_name = models.CharField(
        max_length=128,
        null=True,
        verbose_name='Nombre',
    )
    be_code = models.CharField(
        max_length=64,
        null=True,
        verbose_name='Código',
    )
    state = models.BooleanField(
        default=True,
        verbose_name='Estado',
    )
    be_config = JSONField(
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = '    Beneficio'
        verbose_name_plural = '   Beneficios'

    def __str__(self):
        return "%s %s" % (self.id, self.be_code)


class PlanBenefit(_BasicAuditedModel):
    state = models.BooleanField(
        default=True,
        verbose_name='Estado',
    )
    name = models.CharField(
        max_length=128,
        null=True,
        verbose_name='Descripción',
    )
    delivery_days = models.IntegerField(
        default=0,
        null=True,
        verbose_name='Días Reparto',
    )
    siebel_code = models.CharField(
        max_length=16,
        null=True,
        verbose_name='Siebel Code',
    )
    benefit = models.ForeignKey(
        Benefit,
        related_name='fkPlanBenefitPaywallPlan',
        verbose_name='Beneficio',
        on_delete=models.PROTECT
    )
    plan = models.ForeignKey(
        Plan,
        related_name='kfPlanBenefitPaywallPlan',
        verbose_name='Plan',
        on_delete=models.PROTECT
    )


class SubscriptionBenefit(_BasicAuditedModel):
    state = models.BooleanField(
        verbose_name='State',
        default=False,
    )
    migrate = models.CharField(
        max_length=64,
        verbose_name='Migración',
        blank=True,
        null=True,
    )
    detail = JSONField(
        null=True,
        blank=True
    )
    state_cancelled = models.BooleanField(
        verbose_name='State Anulled',
        default=False
    )
    date_cancelled = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha anulación',
    )
    benefit = models.ForeignKey(
        Benefit,
        related_name='fkSubsBenefitPaywallBenefit',
        verbose_name='Benefits',
        on_delete=models.PROTECT
    )
    subscription = models.ForeignKey(
        Subscription,
        related_name='fkSubsBenefitsPaywallSubscription',
        verbose_name='Subscription',
        on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = 'Subscription Benefit'
        verbose_name_plural = 'Subscription Benefits'

    def __str__(self):
        return "%s %s" % (self.id, self.subscription)


class LogSubscriptionBenefits(_BasicAuditedModel):
    log_benefit = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        verbose_name='Beneficio',
    )
    log_type = models.CharField(
        max_length=128,
        verbose_name='Nombre',
        choices=(
            ('REGISTER', 'Registro'),
            ('MIGRATE', 'Migración'),
            ('CANCELLED', 'Anulación')
        )
    )
    log_request = JSONField(
        null=True,
        blank=True,
        verbose_name='Request'
    )
    log_response = JSONField(
        null=True,
        blank=True,
        verbose_name='Request'
    )
    subs_benefit = models.ForeignKey(
        SubscriptionBenefit,
        related_name='fkLogSubsBenefitPaywallSubsBenefit',
        verbose_name='Subscription Benefits',
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = 'Log Benefit'
        verbose_name_plural = 'Log Benefits'

    def __str__(self):
        return u'%s' % self.id


class FinancialTransactionManager(models.Manager):

    def get_or_create_by_report(self, site, report):
        """
        Crea un objeto FinancialTransaction con los datos de reporte.
        """
        if not report.get('providerReference'):
            raise ValueError('FinancialTransaction must have an providerReference')

        payu_order_id, payu_transaction_id = report.get('providerReference').split('~')
        defaults = {
            'amount': report.get('amount', ''),
            'client_id': report.get('clientId', ''),
            'country': report.get('country', ''),
            'created_on': utc_to_lima_time_zone(report.get('createdOn')),
            'currency': report.get('currency', ''),
            'data': report,
            'financial_transaction_id': report.get('financialTransactionId', ''),
            'first_name': report.get('firstName', ''),
            'initial_transaction': report.get('initialTransaction', ''),
            'last_name': report.get('lastName', ''),
            'line_one': report.get('line1', ''),
            'line_two': report.get('line2', ''),
            'locality': report.get('locality', ''),
            'order_id': payu_order_id,
            'order_number': report.get('orderNumber', ''),
            'period_from': utc_to_lima_time_zone(report.get('periodFrom')),
            'period_to': utc_to_lima_time_zone(report.get('periodTo')),
            'postal': report.get('postal', ''),
            'provider_reference': report.get('providerReference', ''),
            'region': report.get('region', ''),
            'second_last_name': report.get('secondLastName', ''),
            'site': str(site),
            'sku': report.get('sku', ''),
            'subscription_id': report.get('subscriptionId', ''),
            'tax': report.get('tax', ''),
            'transaction_id': payu_transaction_id,
            'transaction_type': report.get('transactionType', ''),
        }

        return self.model.objects.get_or_create(
            provider_reference=report.get('providerReference'),
            defaults=defaults,
        )


class FinancialTransaction(_BasicAuditedModel):
    data = JSONField(
        null=True,
        blank=True
    )
    country = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name='Country'
    )
    last_name = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='lastName'
    )
    period_to = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='periodTo'
    )
    second_last_name = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='secondLastName'
    )
    amount = models.DecimalField(
        verbose_name='amount',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    order_number = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='orderNumber'
    )
    client_id = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='clientId(uuid)'
    )
    locality = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='locality'
    )
    period_from = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='periodFrom'
    )
    tax = models.DecimalField(
        verbose_name='tax',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    financial_transaction_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='financialTransactionId'
    )
    created_on = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='createdOn'
    )
    transaction_type = models.CharField(
        max_length=80,
        null=True,
        blank=True,
        verbose_name='transactionType'
    )
    first_name = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='firstName'
    )
    initial_transaction = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name='initialTransaction'
    )
    provider_reference = models.CharField(
        max_length=120,
        null=True,
        blank=True,
        verbose_name='providerReference'
    )
    currency = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='currency'
    )
    postal = models.CharField(
        max_length=16,
        null=True,
        blank=True,
        verbose_name='postal'
    )
    region = models.CharField(
        max_length=16,
        null=True,
        blank=True,
        verbose_name='region'
    )
    subscription_id = models.CharField(
        max_length=70,
        null=True,
        blank=True,
        verbose_name='subscriptionId'
    )
    sku = models.CharField(
        max_length=70,
        null=True,
        blank=True,
        verbose_name='sku'
    )
    line_two = models.TextField(
        null=True,
        blank=True,
        verbose_name='line2',
    )
    line_one = models.TextField(
        null=True,
        blank=True,
        verbose_name='line1',
    )
    order_id = models.CharField(
        max_length=70,
        null=True,
        blank=True,
        verbose_name='order_id(PayU)'
    )
    transaction_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='transaction_id(PayU)'
    )
    site = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        verbose_name='site',
        choices=(
            ('1', 'Gestion'),
            ('2', 'El Comercio'),
        )
    )
    subscription_obj = models.ForeignKey(
        Subscription,
        null=True,
        editable=False,
        related_name='subscription_financial_transaction',
        verbose_name='Subscription',
        on_delete=models.PROTECT,
    )
    payment = models.ForeignKey(
        Payment,
        null=True,
        blank=True,
        editable=False,
        related_name='payment_financial_transaction',
        verbose_name='Payment',
        on_delete=models.PROTECT
    )
    operation = models.ForeignKey(
        Operation,
        null=True,
        blank=True,
        editable=False,
        related_name='operation_financial_transaction',
        verbose_name='Operation',
        on_delete=models.PROTECT
    )

    objects = FinancialTransactionManager()

    class Meta:
        verbose_name = 'Transacción'
        verbose_name_plural = '[Report] Transacciones'

    def __str__(self):
        return self.order_number


class FinancialTransactionProxy(FinancialTransaction):
    class Meta:
        proxy = True
        verbose_name = 'Transacción'
        verbose_name_plural = '[Report] Transacciones'


class EventReport(_BasicAuditedModel):
    current_product_name = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Nombre del Producto'
    )
    event_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name='Event Id'
    )
    client_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='UUID'
    )
    event_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='Tipo de Evento'
    )
    subscription_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name='SuscripcionID'
    )
    created_on = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='createdOn'
    )
    current_product_sku = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='SKU'
    )
    current_product_price_code = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Price code'
    )
    data = JSONField(
        null=True,
        blank=True
    )
    subscription_obj = models.ForeignKey(
        Subscription,
        null=True,
        editable=False,
        related_name='subscription_event_report',
        verbose_name='Subscription',
        on_delete=models.PROTECT,
    )
    site = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='site'
    )


class SubscriberPrinted(_BasicAuditedModel):
    state = models.BooleanField(
        default=False,
        verbose_name='Estado',
    )
    us_name = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Nombre',
    )
    us_lastname = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Apellidos',
    )
    us_doctype = models.CharField(
        max_length=8,
        null=True,
        blank=True,
        verbose_name='Doc Type',
        choices=DOC_TYPE
    )
    us_docnumber = models.CharField(
        max_length=16,
        null=True,
        blank=True,
        verbose_name='Doc Number',
    )
    printed_entecode = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='EnteCode'
    )
    us_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        unique=True,
        verbose_name='Hash'
    )
    us_data = JSONField(
        null=True,
        blank=True,
        verbose_name='Data',
    )

    # user_offer = models.OneToOneField(
    #     UserOffer,
    #     null=True,
    #     blank=True,
    #     verbose_name='Oferta del usuario',
    #     on_delete=models.PROTECT,
    # )
    # codigo_paquete = models.CharField(
    #     max_length=64,
    #     null=True,
    #     blank=True,
    #     verbose_name='Codigo del Paquete'
    # )
    # codigo_producto = models.CharField(
    #     max_length=64,
    #     null=True,
    #     blank=True,
    #     verbose_name='Codigo del Producto'
    # )
    # nombre_producto = models.CharField(
    #     max_length=64,
    #     null=True,
    #     blank=True,
    #     verbose_name='Nombre del Producto'
    # )

    class Meta:
        verbose_name = 'Suscriptor impreso'
        verbose_name_plural = '[Data] Ofertas • Suscriptores del impreso'

    def __str__(self):
        return '{} {}'.format(self.us_name, self.us_lastname)

    def get_siebel_codes(self):

        if hasattr(self, '_product_codes'):
            return self._product_codes

        self._product_codes = []

        if self.us_data and 'result' in self.us_data and 'product' in self.us_data['result']:
            for product in self.us_data['result']['product']:
                if 'codigo_paquete' in product:
                    self._product_codes.append(product['codigo_paquete'])

        return self._product_codes


class Corporate(_BasicAuditedModel):
    state = models.BooleanField(
        default=False,
        verbose_name='Estado',
    )
    corp_email = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        verbose_name='Correo',
    )
    corp_name = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        verbose_name='Nombre',
    )
    corp_lastname = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        verbose_name='Apellidos',
    )
    corp_type = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name='Tipo Consulta',
        choices=(
            ("1", 'Quiero una suscripción'),
            ("2", 'Tengo una suscripción'),
            ("3", 'Otros')
        ),
    )
    corp_organization = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        verbose_name='Organización',
    )
    corp_subject = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        verbose_name='Asunto',
    )
    telefono = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        verbose_name='Telefono',
    )
    corp_detail = models.TextField(
        null=True,
        blank=True,
        verbose_name='Detalle',
    )
    site = models.ForeignKey(
        Partner,
        null=True,
        verbose_name='Portal',
        on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = 'Suscripcion Corporativa'
        verbose_name_plural = '[Admin] Suscripciones Corporativas'


class OfferToken(_BasicAuditedModel):
    user_uuid = models.UUIDField(
        blank=True,
        null=True,
        unique=True
    )
    dni_list = ArrayField(
        models.CharField(max_length=20, blank=True),
        default=list,
        blank=True,
        verbose_name='Lista de DNIs',
    )
    current_dni = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='DNI',
    )
    token = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name='Token',
    )

    class Meta:
        verbose_name = 'Formulario print'
        verbose_name_plural = '[Data] Ofertas • Intentos de acceso'

    def save(self, *args, **kwargs):
        if not self.token:
            self.create_token()
        super().save(*args, **kwargs)

    def create_token(self):
        self.token = get_random_string(length=50)


class UserOfferManager(models.Manager):

    def get_or_create_promo(self, site, arc_user, offer):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        if not site:
            capture_message('get_or_create_offer: No tiene site')
            raise ValueError('Debe definir site')

        created = None
        user_offer = None
        try:
            user_offer = self.get_queryset().get(
                site=site,
                arc_user=arc_user,
                campaign__offer=offer,
            )
        except UserOffer.DoesNotExist:
            campaign = Campaign.objects.get_by_offer(site=site, offer=offer)

            if campaign:
                user_offer = self.model(
                    site=site,
                    arc_user=arc_user,
                    offer=offer,
                    campaign=campaign,
                )
                user_offer.save(using=self._db)
                created = True
        else:
            created = False

        return user_offer, created

    def get_by_token(self, token):

        try:
            user_offer = self.get_queryset().get(
                token=token,
            )

        except UserOffer.DoesNotExist:
            user_offer = None

        else:
            user_offer.create_token()
            user_offer.save(update_fields=('token',))

        return user_offer


class UserOffer(OfferBase):
    arc_user = models.ForeignKey(
        ArcUser,
        null=True,
        related_name='user_offers',
        verbose_name='Usuario',
        on_delete=models.PROTECT,
    )
    site = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Portal',
        choices=SITE_CHOICES,
    )
    offer = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Oferta',
        choices=OfferBase.OFFER_CHOICES,
    )
    campaign = models.ForeignKey(
        Campaign,
        null=True,
        blank=True,
        related_name='user_offers',
        verbose_name='Campaña',
        on_delete=models.PROTECT,
    )
    subscription = models.ForeignKey(
        Subscription,
        null=True,
        blank=True,
        related_name='user_offers',
        verbose_name='Suscripción',
        on_delete=models.PROTECT,
    )
    token = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name='Token',
    )
    # Legacy
    user_uuid = models.UUIDField(
        blank=True,
        null=True
    )
    dni = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='DNI',
    )
    arc_campaign = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='Campaña',
    )
    arc_sku = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='SKU',
    )

    objects = UserOfferManager()

    class Meta:
        verbose_name = 'Oferta'
        verbose_name_plural = '[Data] Ofertas • Acceso a ofertas'

    def save(self, *args, **kwargs):
        if not self.token:
            self.create_token()

        if self.subscription_id and not self.arc_sku:
            self.arc_sku = self.subscription.data.get('sku')

        if not self.arc_user_id and self.user_uuid:
            self.arc_user = ArcUser.objects.get_by_uuid(uuid=self.user_uuid)

        if not self.campaign_id and self.arc_campaign:
            try:
                self.campaign = Campaign.objects.get(name=self.arc_campaign)

            except Campaign.DoesNotExist:
                capture_exception()

        if self.campaign_id or self.campaign:
            if not self.arc_campaign:
                self.arc_campaign = self.campaign.name

            if not self.site:
                self.site = self.campaign.partner.partner_code

            if not self.offer:
                self.offer = self.campaign.offer

        super().save(*args, **kwargs)

    def create_token(self):
        self.token = get_random_string(length=50)


class Collaborators(_BasicAuditedModel):
    state = models.BooleanField(
        default=False,
        verbose_name='Activado',
    )
    uuid = models.UUIDField(
        blank=True,
        null=True,
        editable=False
    )
    date_annulled = models.DateTimeField(
        verbose_name='Baja',
        null=True,
        editable=False
    )
    doc_type = models.CharField(
        max_length=8,
        null=True,
        verbose_name='Tipo Doc',
        editable=False
    )
    doc_number = models.CharField(
        max_length=16,
        null=True,
        verbose_name='Documento',
        editable=False
    )
    code = models.CharField(
        max_length=16,
        null=True,
        blank=True,
        verbose_name='Código',
    )
    name = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Nombre',
    )
    lastname = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='A. Paterno',
    )
    lastname_mother = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='A. Materno',
    )
    email = models.CharField(
        max_length=128,
        null=True,
        verbose_name='Correo'
    )
    area = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        verbose_name='Área',
    )
    action = models.CharField(
        max_length=32,
        null=True,
        verbose_name='Action',
        choices=COLLABORATORS_ACTION
    )
    site = models.CharField(
        max_length=32,
        null=True,
        verbose_name='Site',
        choices=SITE_CHOICES,
    )
    data = JSONField(
        null=True,
        blank=True,
        verbose_name='ARC data'
    )
    data_annulled = JSONField(
        null=True,
        blank=True,
        verbose_name='ARC data annulled'
    )
    body_arc = JSONField(
        null=True,
        blank=True,
        verbose_name='ARC body'
    )
    subscription = models.ForeignKey(
        Subscription,
        verbose_name='Subscription',
        on_delete=models.PROTECT,
        editable=False,
        null=True
    )
    subscription_arc = models.BigIntegerField(
        verbose_name='ID de ARC',
        default=0,
        null=True
    )

    class Meta:
        verbose_name = 'Colaborador'
        verbose_name_plural = '[Admin] Colaboradores'
        unique_together = ('email', 'site')


class HashCollegeStudent(_BasicAuditedModel):
    arc_user = models.ForeignKey(
        ArcUser,
        null=True,
        related_name='user_hash',
        verbose_name='User',
        on_delete=models.PROTECT
    )
    email = models.CharField(
        max_length=120,
        null=True,
        blank=True,
        verbose_name='Email',
    )
    hash_user = models.CharField(
        max_length=80,
        null=True,
        blank=True,
        verbose_name='Hash',
    )
    state = models.BooleanField(
        default=False,
        verbose_name='Estado',
    )
    date_expire = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de expiración'
    )
    date_birth = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de nacimiento'
    )
    degree = models.CharField(
        max_length=120,
        null=True,
        blank=True,
        verbose_name='Grado',
    )
    user_offer = models.ForeignKey(
        UserOffer,
        null=True,
        blank=True,
        related_name='college_hashes',
        verbose_name='Oferta del usuario',
        on_delete=models.PROTECT,
    )
    site = models.ForeignKey(
        Partner,
        null=True,
        verbose_name='Portal',
        on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = 'Suscripción'
        verbose_name_plural = '[Data] Ofertas • Universitarios'


class ReporteUniversitarios(HashCollegeStudent):
    class Meta:
        proxy = True
        verbose_name = 'Reporte Universitario'
        verbose_name_plural = '[Reporte] Universitarios'


class PaymentTracking(_BasicAuditedModel):
    ACCEPT_PURCHASE = 1
    NOT_ACCEPTS_PURCHASE = 2
    NOT_GO_THROUGH_FLOW = 3

    IS_PWA = 1
    NO_PWA = 2

    subscription = models.OneToOneField(
        Subscription,
        null=True,
        verbose_name='Subscription',
        related_name='traking',
        on_delete=models.PROTECT
    )
    payment = models.OneToOneField(
        Payment,
        null=True,
        blank=True,
        verbose_name='Payment',
        on_delete=models.PROTECT
    )
    url_referer = models.CharField(
        max_length=350,
        null=True,
        blank=True,
        verbose_name='Url Referer',
    )
    medium = models.CharField(
        max_length=80,
        null=True,
        blank=True,
        verbose_name='Medio',
    )
    device = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        verbose_name='Dispositivo',
        help_text='',
        choices=(
            ("1", 'mobile'),
            ("2", 'desktop'),
            ("3", 'tablet'),
            ("4", 'otros')
        ),
    )
    confirm_subscription = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Confirmacion de suscripcion',
        help_text='',
        choices=(
            (ACCEPT_PURCHASE, 'Acepta doble compra'),
            (NOT_ACCEPTS_PURCHASE, 'No acepta doble compra'),
            (NOT_GO_THROUGH_FLOW, 'No paso por el flujo')
        ),
    )
    user_agent = models.CharField(
        max_length=350,
        null=True,
        blank=True,
        verbose_name='User Agent',
    )
    arc_order = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Arc Order',
        unique=True,
    )
    arc_user = models.ForeignKey(
        ArcUser,
        null=True,
        verbose_name='Cliente',
        on_delete=models.PROTECT,
        editable=False,
    )
    uuid = models.UUIDField(
        blank=True,
        null=True,
        verbose_name='UUID',
    )
    partner = models.ForeignKey(
        Partner,
        null=True,
        verbose_name='Portal',
        on_delete=models.PROTECT
    )
    site = models.CharField(
        max_length=60,
        null=True,
        blank=True,
        verbose_name='Site',
    )
    user_agent_str = models.CharField(
        max_length=350,
        null=True,
        blank=True,
        verbose_name='Browser',
    )
    browser_version = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Browser - version',
    )
    os_version = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Sistema Operativo',
    )
    device_user_agent = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='family - brand - model',
    )
    is_pwa = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='PWA',
        help_text='',
        choices=(
            (IS_PWA, 'SI'),
            (NO_PWA, 'NO')
        ),
    )

    class Meta:
        verbose_name = 'Tracking Suscripción'
        verbose_name_plural = 'Tracking • Subscriptions'


class Log(_BasicAuditedModel):
    text_log = models.TextField(
        null=True,
        blank=True
    )


class ReportLongPeriodTime(_BasicAuditedModel):
    data = JSONField(
        null=True,
        blank=True,
        verbose_name='data'
    )
    site = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        verbose_name='site',
    )
