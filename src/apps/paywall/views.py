from datetime import datetime
import uuid

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import TemplateView
from sentry_sdk import capture_exception
from tablib import Dataset
from sentry_sdk import capture_event

from ..paywall.arc_clients import SalesLinked
from .api.views.facebook_pixel import FacebookPixelGenerator
from .models import Collaborators


class FacebookPixelView(TemplateView):
    template_name = 'pixel.html'

    def get(self, request, **kwargs):
        cat = request.GET.get('cat', '--')
        count = request.GET.get('read_count', '--')
        capture_event(
            {
                'message': 'Paywall event "%s" read_count %s' % (cat, count),
                'extra': {
                    'GET': request.GET,
                    'POST': request.POST,
                }
            }
        )
        return super().get(request, **kwargs)

    def post(self, request, **kwargs):
        capture_event(
            {
                'message': 'URL analytics service',
                'extra': {
                    'GET': request.GET,
                    'POST': request.POST,
                }
            }
        )

        data = request.POST
        context_data = {}

        uuid = data.get('uuid')
        event = data.get('event')
        is_suscriber = data.get('is_suscriber')

        if uuid and event and settings.ENVIRONMENT != 'production':

            if event == 'Subscribe':
                event_name = "Subscribe"
                event_data = {
                    "value": 29.00,
                    "currency": "PEN",
                    "subscription_id": uuid
                }

            else:
                event_name = "LogIntoAccount"
                event_data = {
                    "is_subscriber": "true" if is_suscriber else "false",
                    "subscription_id": uuid,
                    # "arc-site": "gestion",
                }

            context_data = self.get_context_data()
            context_data['pixel'] = FacebookPixelGenerator().generate_signed_fb_event_tag(
                event_name=event_name,
                event_data=event_data
            )
            context_data['event_data'] = event_data
            context_data['event_name'] = event_name

        return self.render_to_response(context_data)

    def get_context_data(self, **kwargs):
        kwargs['querystring'] = dict(self.request.GET)
        kwargs['headers'] = self.request.headers
        return kwargs


class PaywallCollaboratorsView(TemplateView):
    template_name = 'admin/paywall/collaborators_upload.html'

    def post(self, request):
        try:
            dataset = Dataset()
            file_import = request.FILES['import_file']
            imported_data = dataset.load(file_import.read().decode('utf-8', 'ignore'), format='csv')
            count_record = 0

            for data in imported_data:
                (code, email, name, lastname, lastname_mother, doc_type, doc_number, site) = data
                site = site.strip()
                sales_linked = SalesLinked(site)
                user_uuid = sales_linked.get_uuid_by_email(email)
                records = []

                if user_uuid:
                    # date_expired = relativedelta(years=2) + datetime.now()
                    try:
                        collaborators = Collaborators.objects.get(email=email, site=site)
                        if not collaborators.state:
                            # Register
                            if not collaborators.uuid:
                                collaborators.uuid = uuid.uuid1()
                                collaborators.save()

                            response = sales_linked.create(collaborators.uuid, user_uuid)
                            if response.status_code == 200:
                                collaborators.state = True
                                collaborators.action = 'SUCCESS'
                                collaborators.data = response.json()
                                collaborators.data_annulled = {}
                                count_record += 1
                            else:
                                collaborators.state = False
                                collaborators.action = 'ERROR_UUID'
                                collaborators.data = {'error': response.text}
                            collaborators.save()
                        else:
                            continue

                    except Collaborators.DoesNotExist:
                        # Register
                        collaborators = Collaborators.objects.create(
                            code=code,
                            email=email,
                            name=name,
                            lastname=lastname,
                            lastname_mother=lastname_mother,
                            doc_type=doc_type,
                            doc_number=doc_number,
                            uuid=uuid.uuid1(),
                            site=site
                        )

                        response, data_body = sales_linked.create(collaborators.uuid, user_uuid)
                        if response.status_code == 200:
                            response_json = response.json()
                            collaborators.state = True
                            collaborators.action = 'SUCCESS'
                            collaborators.data = response.json()
                            collaborators.body_arc = data_body
                            try:
                                collaborators.subscription_arc = int(response_json.get('subscriptionID', None))
                            except:
                                pass

                            try:
                                collaborators.subscription = Subscription.objects.get(
                                    arc_id=int(response_json.get('subscriptionID', None))
                                )
                            except:
                                pass
                            count_record += 1
                        else:
                            collaborators.state = False
                            collaborators.action = 'ERROR_UUID'
                            collaborators.data = {'error': response.text}
                        collaborators.save()
                    except Exception:
                        capture_exception()
                else:
                    records.append(
                        {'code': code, 'email': email, 'error': 'El usuario no se encuentra registrado en Arc.'})

            if count_record > 0:
                messages.add_message(request, messages.INFO,
                                     'Se registraron {} usuarios de un total de {}'.format(count_record,
                                                                                           len(imported_data)))
            else:
                messages.add_message(request, messages.ERROR, 'No se encontraron registros a suscribir.')
        except:
            capture_exception()

        return redirect('/admin/paywall/collaborators/')


class PaywallCollaboratorsAnnulledView(TemplateView):
    def get_template_names(self, **kwargs):
        template_name = 'admin/paywall/collaborators_annulled.html'
        return template_name

    def post(self, request):
        dataset = Dataset()
        file_import = request.FILES['import_file']
        imported_data = dataset.load(file_import.read().decode('utf-8', 'ignore'), format='csv')
        count_record = 0
        for data in imported_data:
            (code, email, name, lastname, lastname_mother, doc_type, doc_number, site) = data
            site = site.strip()
            sales_linked = SalesLinked(site)
            user_uuid = sales_linked.get_uuid_by_email(email)
            records = []
            if user_uuid:
                date_expired = datetime.now()
                try:
                    collaborators = Collaborators.objects.get(email=email, site=site)
                    if collaborators.state:
                        response = sales_linked.revoke(collaborators.data['token'], user_uuid, date_expired)
                        if response.status_code == 200:
                            collaborators.state = False
                            collaborators.action = 'ANNULLED'
                            collaborators.data_annulled = response.json()
                            count_record += 1
                        else:
                            collaborators.state = False
                            collaborators.action = 'ERROR_UUID'
                            collaborators.data_annulled = {'error': response.text}
                        collaborators.save()
                    else:
                        continue

                except Exception:
                    capture_exception
            else:
                records.append({'code': code, 'email': email, 'error': 'Los usuarios no se encuentra registrado en Arc.'})

        if count_record > 0:
            messages.add_message(request, messages.INFO,
                                 'Se anularon {} usuarios de un total de {}.'.format(count_record, len(imported_data)))
        else:
            messages.add_message(request, messages.ERROR, 'No se encontraron registros para realizar la anulación.')

        return redirect('/admin/paywall/collaborators/')
