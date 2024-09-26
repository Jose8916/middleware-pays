# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from django.conf import settings
from django.utils.html import format_html
from django.utils.timezone import get_default_timezone
from django.utils import formats, timezone

from apps.paywall.models import Operation, Plan, Subscription, Product, Payment, ReportLongPeriodTime
from apps.arcsubs.utils import timestamp_to_datetime


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    """ 
        python3 manage.py long_perid_time_subscriptions --start_date 01-12-2020 --end_date 06-01-2021 --site elcomercio --days_quantity 10
    """

    def days_between(self, d1, d2):
        try:
            return abs((d2 - d1).days)
        except Exception:
            return 0

    def range_to_timestamp(self, start_date, end_date):
        starts = datetime.combine(
            start_date,
            datetime.min.time()
        )
        ends = datetime.combine(
            end_date,
            datetime.max.time()
        )
        return (
            get_default_timezone().localize(starts),
            get_default_timezone().localize(ends)
        )

    def start_day(self, start_date):
        starts = datetime.combine(
            start_date,
            datetime.min.time()
        )
        return get_default_timezone().localize(starts)

    def end_day(self, end_date):
        ends = datetime.combine(
            end_date,
            datetime.max.time()
        )
        return get_default_timezone().localize(ends)

    def format_date(self, obj):
        try:
            tz = timezone.get_current_timezone()
            tz_date = obj.astimezone(tz)
            return formats.date_format(tz_date, "b. d, Y").capitalize()
        except Exception as e:
            return str(e)

    def get_user(self, obj):
        return obj.arc_user.get_display_html() if obj.arc_user_id else '-'

    def get_data(self, obj):
        tz = timezone.get_current_timezone()
        tz_created = obj.starts_date.astimezone(tz)
        title = obj.plan.plan_name if obj.plan_id else ''
        title += ' [{}]'.format(obj.campaign.get_category()) if obj.campaign_id else ' [--]'

        if obj.state == Subscription.ARC_STATE_ACTIVE:
            name_icon = 'full'
        elif obj.state == Subscription.ARC_STATE_CANCELED or obj.state == Subscription.ARC_STATE_SUSPENDED:
            name_icon = 'half'
        elif obj.state == Subscription.ARC_STATE_TERMINATED:
            name_icon = 'empty'
        else:
            name_icon = ''

        return format_html(
            '<strong>{title}</strong></br>'
            '<i class="fas fa-key"></i> ID {key}</br>'
            '<i class="fas fa-arrow-circle-up"></i> <strong>{created}</strong></br>'
            '<i class="fas fa-newspaper"></i> {site}</br>'
            '<i class="fas fa-battery-{name_icon}"></i> {state}',
            title=title,
            site=obj.partner,
            key=obj.arc_id,
            created=formats.date_format(tz_created, settings.DATETIME_FORMAT),
            state=obj.get_state_display(),
            name_icon=name_icon
        )

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

        return format_html(
            '<i class="fas fa-id-card fa-sm"></i> {payment_profile} '
            '<a href="{payment_profile_link}" target="_blank"><small>(ver)</small></a></br>'
            '<i class="fas fa-calendar-alt"></i> {date}</br>'
            '<i class="fas fa-at"></i> {email_pago}</br>',
            payment_profile=obj.payment_profile or '--',
            payment_profile_link=payment_profile_link,
            date=date_start_suscription,
            email_pago=brand_email
        )

    def get_payments(self, obj):
        if not obj.data or not obj.data.get('salesOrders'):
            return '----'

        html = ''

        for order in obj.data['salesOrders']:
            _date = timestamp_to_datetime(order['orderDateUTC'])

            html += '<span title="{date_detail}">{date} • S/ {amount}</span></br>'.format(
                amount=order['total'],
                date_detail=formats.localize(_date),
                date=formats.date_format(_date, settings.DATE_FORMAT),
            )

        return format_html(html)

    def add_arguments(self, parser):
        parser.add_argument('--start_date', nargs='?', type=str)
        parser.add_argument('--end_date', nargs='?', type=str)
        parser.add_argument('--site', nargs='?', type=str)
        parser.add_argument('--days_quantity', nargs='?', type=str)

    def handle(self, *args, **options):
        """
            python3 manage.py long_perid_time_subscriptions --days_quantity 500
        """

        if settings.ENVIRONMENT == 'production':
            list_price_code_anual = ['1ZSTMJ', '96Y5EV', 'HIHSZ1', 'VG9EP8', 'CXFABO', 'L1NW79', 'HPMEUF', 'L87ZDN',
                                     'GYAADZ', 'O7XAFN', '2S46BW', 'C4K8IC', 'ZJFER9', '1RTILY']
        else:
            list_price_code_anual = ['DWVFDU', 'SVLSLC', 'C4INIY', 'UZV5IZ', '6JLBMD', '3PM31A', 'LT9XO7']

        site = options.get('site')

        if options.get('days_quantity'):
            days_ = options.get('days_quantity')
            start_date = options.get('start_date')
            start_date = self.start_day(datetime.strptime(start_date, '%d-%m-%Y'))
            end_date = options.get('end_date')
            end_date = self.end_day(datetime.strptime(end_date, '%d-%m-%Y'))

            list_subscription = []
            all_subscriptions = Subscription.objects.filter(
                data__currentPaymentMethod__paymentPartner='PayULATAM'
            )
            for obj_subs in all_subscriptions:
                if obj_subs.plan:
                    if obj_subs.plan.arc_pricecode in list_price_code_anual:
                        ndays_ = int(days_) + 365
                    else:
                        ndays_ = int(days_)

                    if site and start_date and end_date:
                        payments = Payment.objects.filter(
                            subscription=obj_subs,
                            subscription__partner__partner_code=site,
                            date_payment__range=self.range_to_timestamp(start_date, end_date)
                        ).order_by('date_payment')

                        last_date_payment = ''
                        list_payment_register = []
                        flag_append = False
                        list_days = []
                        for payment_obj in payments:
                            if last_date_payment:
                                list_payment_register.append(payment_obj.date_payment)
                                validate_long_days = self.days_between(last_date_payment, payment_obj.date_payment) > ndays_

                                if validate_long_days:
                                    flag_append = True
                                    list_days.append({
                                        'dias': self.days_between(last_date_payment, payment_obj.date_payment),
                                        'day_start': self.format_date(last_date_payment),
                                        'day_end': self.format_date(payment_obj.date_payment)
                                    })

                            last_date_payment = payment_obj.date_payment
                        if flag_append:
                            list_subscription.append({
                                'subscription': self.get_data(obj_subs),
                                'user_login': self.get_user(obj_subs),
                                'payment': self.get_invoice(obj_subs),
                                'dias': list_days,
                                'payments': self.get_payments(obj_subs)
                            })

            context = {
                'list_subscription': list_subscription,
                'days_gestion': 'days_gestion',
                'days_comercio': 'days_comercio',
                'days_quantity': days_
            }
        else:
            context = {
                'message': 'Ingrese el numero de días'
            }

        report = ReportLongPeriodTime(
            data=context,
            site=site
        )
        report.save()






