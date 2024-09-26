from apps.piano.piano_clients import IDClient, Payu
from apps.piano.models import Transaction, Term
from apps.paywall.models import PaymentProfile, Subscription as SubscriptionArc
from apps.piano.models import Subscription, SubscriptionMatchArcPiano
from apps.piano.constants import LIST_EMAIL_SENDER
from django.conf import settings
from apps.piano.piano_clients import VXClient
from apps.paywall.shortcuts import render_send_email
import time
from sentry_sdk import capture_exception, capture_event, push_scope
from datetime import datetime
from django.utils import formats, timezone
from apps.paywall.models import Partner


def format_timestamp_to_date(date_timestamp):
    date_time_obj = datetime.fromtimestamp(date_timestamp)
    tz = timezone.get_current_timezone()
    return date_time_obj.astimezone(tz)


def send_message_error(brand, payment_profile, suscripcion_id):
    message_error = ''
    if payment_profile:
        try:
            if not payment_profile.get('portal_email', ''):
                message_error = 'No tiene email'
        except:
            message_error = 'No tiene email'

        try:
            if not payment_profile.get('prof_name', ''):
                message_error = 'no tiene nombre'
        except:
            message_error = 'no tiene nombre'

        try:
            if not payment_profile.get('prof_lastname', ''):
                message_error = 'no tiene apellido'
        except:
            message_error = 'no tiene apellido'

        try:
            if not payment_profile.get('prof_doc_type', ''):
                message_error = 'no tiene tipo de documento'
        except:
            message_error = 'no tiene tipo de documento'

        try:
            if not payment_profile.get('prof_doc_num', ''):
                message_error = 'No tiene numero de documento'
        except:
            message_error = 'No tiene numero de documento'

        if payment_profile.get('prof_doc_num', '') and payment_profile.get('prof_doc_type', '') == 'DNI':
            try:
                doc_number = int(payment_profile.get('prof_doc_num', ''))
            except:
                message_error = 'con numero de documento invalido: ' + payment_profile.get('prof_doc_num', '')
            else:
                if len(payment_profile.get('prof_doc_num', '')) != 8:
                    message_error = 'DNI no tiene 8 digitos: ' + payment_profile.get('prof_doc_num', '')

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

        if message_error:
            text_message = 'Usuario {} con id de suscripcion: {}: {}'.format(
                payment_profile.get('portal_email', ''),
                suscripcion_id,
                message_error
            )
            render_send_email(
                template_name='mailings/error.html',
                subject=('[Test]' if settings.ENVIRONMENT == 'test' else '[Production]') + 'Perfil de pago',
                to_emails=LIST_EMAIL_SENDER,
                from_email=from_email,
                context={
                    'error': text_message
                }
            )


def get_payment_profile(uid, brand, subscription_obj):
    second_last_name = payment_profile = document_number = document_type = subscription_id_arc = ''

    if subscription_obj.payment_profile:
        return subscription_obj.payment_profile

    try:
        subs = SubscriptionMatchArcPiano.objects.get(subscription_id_piano=subscription_obj.subscription_id)
        subscription_id_arc = subs.subscription_id_arc
    except:
        subscription_id_arc = ''

    if subscription_id_arc:
        try:
            subs_arc_obj = SubscriptionArc.objects.get(arc_id=subscription_id_arc)
            return subs_arc_obj.payment_profile
        except:
            return None
    else:
        data = IDClient().get_uid(uid, brand)
        user = data.get('user')

        try:
            email_user = user.get('email', '')
        except Exception as e:
            print(e)
            capture_exception()
            email_user = None

        if email_user:
            for fields in user.get('custom_fields', ''):
                if fields.get('fieldName', '') == 'document_type':
                    document_type = fields.get('value', '')
                    inicial = '[\"'
                    final = '\"]'
                    try:
                        document_type = document_type.replace(inicial, "")
                        document_type = document_type.replace(final, "")
                    except Exception as e:
                        capture_exception()
                        print(e)
                        document_type = ''
                elif fields.get('fieldName', '') == 'document_number':
                    document_number = fields.get('value', '')
                elif fields.get('fieldName', '') == 'contact_phone':
                    contact_phone = fields.get('value', '')
                elif fields.get('fieldName', '') == 'second_last_name':
                    second_last_name = fields.get('value', '')

            if document_type in ['Otro', 'otro', 'Otros', 'otros', 'OTROS']:
                document_type = 'OTR'

            kwargs = {
                'prof_name': user.get('first_name', ''),
                'prof_lastname': user.get('last_name', ''),
                'portal_email': user.get('email', ''),
                'prof_doc_type': document_type,
                'prof_doc_num': document_number,
            }

            if document_number and document_type:
                try:
                    payment_profile = PaymentProfile.objects.get(**kwargs)

                except PaymentProfile.MultipleObjectsReturned:
                    payment_profile = PaymentProfile.objects.filter(**kwargs)[0]
                except PaymentProfile.DoesNotExist:
                    send_message_error(brand, kwargs, subscription_obj.subscription_id)
                    payment_profile = PaymentProfile(**kwargs)
                    if contact_phone:
                        payment_profile.prof_phone = contact_phone
                        payment_profile.prof_lastname_mother = second_last_name
                    payment_profile.save()
                    payment_profile = PaymentProfile.objects.get(**kwargs)

                return payment_profile
            else:
                send_message_error(brand, kwargs, subscription_obj.subscription_id)
        else:
            return None


def update_payment_profile(uid, brand, payment_profile):
    second_last_name = document_number = document_type = ''
    data = IDClient().get_uid(uid, brand)
    user = data.get('user')

    try:
        email_user = user.get('email', '')
    except Exception as e:
        print(e)
        capture_exception()
        email_user = None

    if email_user:
        for fields in user.get('custom_fields', ''):
            if fields.get('fieldName', '') == 'document_type':
                document_type = fields.get('value', '')
                inicial = '[\"'
                final = '\"]'
                try:
                    document_type = document_type.replace(inicial, "")
                    document_type = document_type.replace(final, "")
                except Exception as e:
                    capture_exception()
                    print(e)
                    document_type = ''
            elif fields.get('fieldName', '') == 'document_number':
                document_number = fields.get('value', '')
            elif fields.get('fieldName', '') == 'contact_phone':
                contact_phone = fields.get('value', '')
            elif fields.get('fieldName', '') == 'second_last_name':
                second_last_name = fields.get('value', '')

        if document_number and document_type:
            if document_type in ['Otro', 'otro', 'Otros', 'otros', 'OTROS']:
                document_type = 'OTR'

            payment_profile.prof_name = user.get('first_name', '')
            payment_profile.prof_lastname = user.get('last_name', '')
            payment_profile.portal_email = user.get('email', '')
            payment_profile.prof_doc_type = document_type
            payment_profile.prof_doc_num = document_number

            if contact_phone:
                payment_profile.prof_phone = contact_phone
                payment_profile.prof_lastname_mother = second_last_name
            payment_profile.save()
            return True


def get_or_create_subscription(id_subs, brand):
    subscription = None
    delivery = None
    profile = None

    try:
        return Subscription.objects.get(
            subscription_id=id_subs,
            app_id=settings.PIANO_APPLICATION_ID[brand]
        )
    except:
        subscription = VXClient().get_subscription(brand, id_subs)

    if subscription.get('subscription', ''):
        try:
            subs_match = SubscriptionMatchArcPiano.objects.get(
                subscription_id_piano=id_subs
            )
        except:
            subs_match = None

        if subs_match:
            try:
                subscription_arc = SubscriptionArc.objects.get(arc_id=subs_match.subscription_id_arc)
                delivery = subscription_arc.delivery
                profile = subscription_arc.payment_profile
            except:
                pass

        subscription_dict = subscription.get('subscription')
        subs = Subscription(
            subscription_id=id_subs,
            app_id=settings.PIANO_APPLICATION_ID[brand],
            start_date=format_timestamp_to_date(subscription_dict.get('start_date')),
            uid=subscription_dict.get('user', {}).get('uid', '')
        )
        if delivery:
            subs.delivery = delivery
        if profile:
            subs.payment_profile = profile

        subs.save()
        return Subscription.objects.get(
            subscription_id=id_subs,
            app_id=settings.PIANO_APPLICATION_ID[brand]
        )
    else:
        return None

