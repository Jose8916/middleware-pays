from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from .models import ClubSubscription
from apps.arcsubs.models import ArcUser
from apps.paywall.arc_clients import search_user_arc_param
from apps.clubelcomercio.utils import es_correo_valido
from apps.paywall.arc_clients import IdentityClient
from sentry_sdk import capture_event


class ChangeDocumentForm(forms.Form):
    """
        Ref. https://hakibenita.com/how-to-add-custom-action-buttons-to-django-admin
    """
    document_type = forms.ChoiceField(
        label='Tipo de documento',
        required=True,
        choices=((None, 'Seleccionar'), ) + ClubSubscription.DOCUMENT_TYPE_CHOICES
    )
    document_number = forms.CharField(
        label='Número de documento',
        required=True,
    )

    def clean_document_number(self):
        document_number = self.cleaned_data['document_number']
        document_type = self.cleaned_data['document_type']

        # Check date is not in past.
        if document_type == 'DNI':
            if len(document_number) < 8 or not document_number.isnumeric():
                raise ValidationError(_('Número invalido'))

        if document_type == 'CEX' or document_type == 'CDI':
            if not (15 >= len(document_number) >= 5):
                raise ValidationError(_('Número invalido'))

        return document_number

    def __init__(self, subscription, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subscription = subscription

    def form_action(self, account, user):
        raise NotImplementedError()

    def save(self, current_user=None):
        document_type = self.cleaned_data.get('document_type')
        document_number = self.cleaned_data.get('document_number')

        if ClubSubscription.objects.filter(subscription=self.subscription).exists():
            last_club_subscription = ClubSubscription.objects.filter(
                subscription=self.subscription
            ).latest('created')
            email = last_club_subscription.email
        else:
            email = self.subscription.payment_profile.portal_email

        if email:
            ClubSubscription.objects.deactivate_subscriptions(
                subscription=self.subscription
            )

            club_subscription = ClubSubscription.objects.create(
                email=email,
                subscription=self.subscription,
                document_number=document_number,
                document_type=document_type
            )
            club_subscription.club_activate()

            return club_subscription
        return ''


class ChangeEmailForm(forms.Form):
    """
        Ref. https://hakibenita.com/how-to-add-custom-action-buttons-to-django-admin
    """
    email = forms.EmailField(
        label='Correo electrónico',
        required=False,
        help_text='Email de notificación (Opcional)'
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        if not es_correo_valido(email):
            raise ValidationError(_('Email invalido'))

        user_arc = search_user_arc_param('email', email)
        
        if user_arc.get('totalCount', ''):
            raise ValidationError(_('El Email ya existe en Arc'))
        return email

    def __init__(self, subscription, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subscription = subscription

    def form_action(self, account, user):
        raise NotImplementedError()

    def save(self, current_user=None):
        email = self.cleaned_data.get('email')

        club_subscription = ClubSubscription.objects.filter(
            subscription=self.subscription
        ).latest('created')
        club_subscription.email = email
        club_subscription.save()
        club_subscription.club_update()
        IdentityClient().update_profile_by_uuid(club_subscription.subscription.arc_user.uuid, email)
        return club_subscription