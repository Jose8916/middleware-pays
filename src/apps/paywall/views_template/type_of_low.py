from datetime import datetime, timedelta
from django.shortcuts import render
from django.db.models import Q, Count, DateTimeField
from django.http import HttpResponse
from django.template import loader
from django.views import View
from apps.paywall.models import Subscription, TypeOfLowSubscription
from django.db.models.functions import TruncDay, Trunc
from django.utils.timezone import get_default_timezone

import pytz
from dateutil.relativedelta import relativedelta, MO

TIMEZONE = pytz.timezone('America/Lima')


class TypeOfLowView(View):
    """

    """
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
            starts.astimezone(TIMEZONE),
            ends.astimezone(TIMEZONE)
        )

    def min_date(self, date_input):
        min_date = datetime.combine(
            date_input,
            datetime.min.time()
        )
        return min_date.astimezone(TIMEZONE),

    def get(self, request, *args, **kwargs):
        template = loader.get_template('admin/report/type_of_low.html')
        list_color = [
            'rgb(0, 0, 255)',  # BLUE  # 0000FF
            'rgb(255, 0, 0)',  # RED  # FF0000
            'rgb(255, 255, 0)'  # YELLOW  # FFFF00
        ]

        start_date = datetime.now(TIMEZONE) - timedelta(days=20)
        # end_date = datetime.now(TIMEZONE)

        list_days = []

        for count in range(20):
            start_date = start_date + timedelta(days=1)
            dict_type_low = {}
            low_by_admin_total = TypeOfLowSubscription.objects.filter(
                subscription__date_anulled__range=self.range_to_timestamp(start_date, start_date),
                type=TypeOfLowSubscription.LOW_BY_ADMIN
            ).count()
            low_by_suspension_total = TypeOfLowSubscription.objects.filter(
                subscription__date_anulled__range=self.range_to_timestamp(start_date, start_date),
                type=TypeOfLowSubscription.LOW_BY_SUSPENSION
            ).count()
            low_by_cancellation_total = TypeOfLowSubscription.objects.filter(
                subscription__date_anulled__range=self.range_to_timestamp(start_date, start_date),
                type=TypeOfLowSubscription.LOW_BY_CANCELLATION
            ).count()

            dict_type_low["low_by_admin_total"] = low_by_admin_total
            dict_type_low["low_by_suspension_total"] = low_by_suspension_total
            dict_type_low["low_by_cancellation_total"] = low_by_cancellation_total
            dict_type_low["fecha"] = start_date.strftime("%d-%m-%Y")
            list_days.append(dict_type_low)

        # Armando grafico
        data_sets = [
            {
                'label': 'Bajas por el Administrador',
                'backgroundColor': list_color[0],
                'borderColor': list_color[0],
                'data': [row['low_by_admin_total'] for row in list_days]
            },
            {
                'label': 'Bajas por suspencion',
                'backgroundColor': list_color[1],
                'borderColor': list_color[1],
                'data': [row['low_by_suspension_total'] for row in list_days]
            },
            {
                'label': 'Bajas por cancelaciones',
                'backgroundColor': list_color[2],
                'borderColor': list_color[2],
                'data': [row['low_by_cancellation_total'] for row in list_days]
            }
        ]

        data_graph = {
            'labels': [sub['fecha'] for sub in list_days],
            'datasets': data_sets
        }

        context = {
            'data_graph': data_graph,
            'type_report': 'bajas_por_tipo',
            'reportes': list_days
        }
        return HttpResponse(template.render(context, request))

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

    def post(self, request, *args, **kwargs):
        template = loader.get_template('admin/report/type_of_low.html')
        list_color = [
            'rgb(0, 0, 255)',  # BLUE  # 0000FF
            'rgb(255, 0, 0)',  # RED  # FF0000
            'rgb(255, 255, 0)'  # YELLOW  # FFFF00
        ]
        list_days = []
        start_day = request.POST.get('start_day', '')
        end_day = request.POST.get('end_day', '')
        start_date = self.start_day(datetime.strptime(start_day, '%d/%m/%Y'))
        end_date = self.end_day(datetime.strptime(end_day, '%d/%m/%Y'))
        range_date_search = end_date - start_date

        for count in range(range_date_search.days + 1):
            start_date = start_date + timedelta(days=1)
            dict_type_low = {}
            low_by_admin_total = TypeOfLowSubscription.objects.filter(
                subscription__date_anulled__range=self.range_to_timestamp(start_date, start_date),
                type=TypeOfLowSubscription.LOW_BY_ADMIN
            ).count()
            low_by_suspension_total = TypeOfLowSubscription.objects.filter(
                subscription__date_anulled__range=self.range_to_timestamp(start_date, start_date),
                type=TypeOfLowSubscription.LOW_BY_SUSPENSION
            ).count()
            low_by_cancellation_total = TypeOfLowSubscription.objects.filter(
                subscription__date_anulled__range=self.range_to_timestamp(start_date, start_date),
                type=TypeOfLowSubscription.LOW_BY_CANCELLATION
            ).count()

            dict_type_low["low_by_admin_total"] = low_by_admin_total
            dict_type_low["low_by_suspension_total"] = low_by_suspension_total
            dict_type_low["low_by_cancellation_total"] = low_by_cancellation_total
            dict_type_low["fecha"] = start_date.strftime("%d-%m-%Y")
            list_days.append(dict_type_low)

        # Armando grafico
        data_sets = [
            {
                'label': 'Bajas por el Administrador',
                'backgroundColor': list_color[0],
                'borderColor': list_color[0],
                'data': [row['low_by_admin_total'] for row in list_days]
            },
            {
                'label': 'Bajas por suspencion',
                'backgroundColor': list_color[1],
                'borderColor': list_color[1],
                'data': [row['low_by_suspension_total'] for row in list_days]
            },
            {
                'label': 'Bajas por cancelaciones',
                'backgroundColor': list_color[2],
                'borderColor': list_color[2],
                'data': [row['low_by_cancellation_total'] for row in list_days]
            }
        ]

        data_graph = {
            'labels': [sub['fecha'] for sub in list_days],
            'datasets': data_sets
        }

        context = {
            'data_graph': data_graph,
            'type_report': 'bajas_por_tipo',
            'reportes': list_days
        }
        return HttpResponse(template.render(context, request))
