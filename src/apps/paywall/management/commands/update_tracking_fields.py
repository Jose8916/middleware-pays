from django.conf import settings
from django.core.management.base import BaseCommand
from apps.paywall.models import PaymentTracking
from user_agents import parse


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def get_user_agent_pretty(self, ua_string):
        try:
            return str(parse(ua_string))
        except Exception as e:
            return ''

    def get_browser_version(self, ua_string):
        try:
            user_agent = parse(ua_string)
            ua_family = user_agent.browser.family
            ua_version_string = user_agent.browser.version_string

            return '{ua_family} - {ua_version_string}'.format(ua_family=ua_family, ua_version_string=ua_version_string)
        except Exception as e:
            return ''

    def get_os_version(self, ua_string):
        try:
            user_agent = parse(ua_string)
            ua_os_family = user_agent.os.family
            ua_os_version_string = user_agent.os.version_string
            if ua_os_version_string and ua_os_family:
                return '{ua_os_family} {ua_os_version_string}'.format(
                    ua_os_family=ua_os_family,
                    ua_os_version_string=ua_os_version_string)
            elif ua_os_family:
                return ua_os_family
            elif ua_os_version_string:
                return ua_os_version_string
            else:
                return ''
        except Exception as e:
            return ''

    def get_device_user_agent(self, ua_string):
        try:
            user_agent = parse(ua_string)
            ua_family = user_agent.device.family
            ua_brand = user_agent.device.brand
            ua_model = user_agent.device.model

            return '{ua_family} - {ua_brand} - {ua_model}'.format(
                ua_family=ua_family,
                ua_brand=ua_brand,
                ua_model=ua_model
            )
        except Exception as e:
            return ''

    def handle(self, *args, **options):
        payments = PaymentTracking.objects.all()
        count = 0
        for payment in payments:
            try:
                if payment.user_agent:
                    payment.user_agent_str = self.get_user_agent_pretty(payment.user_agent)
                    payment.browser_version = self.get_browser_version(payment.user_agent)
                    payment.os_version = self.get_os_version(payment.user_agent)
                    payment.device_user_agent = self.get_device_user_agent(payment.user_agent)
                    payment.save()
                    count = count + 1
            except Exception as e:
                print(e)
        return 'Se actualizaron registros: ' + str(count)
