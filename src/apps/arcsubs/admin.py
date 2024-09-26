from datetime import datetime

from django.contrib import admin
from django.utils.html import format_html
from django.utils.text import Truncator
from django.contrib.postgres import fields
from django_json_widget.widgets import JSONEditorWidget

from .models import ArcUser, Event, Report


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('hora_registro', 'timestamp', 'message', 'event_type', 'site', )
    list_filter = ('site', 'event_type', )
    search_fields = ('message', 'event_type')

    def hora_registro(self, obj):
        return datetime.fromtimestamp(obj.timestamp / 1000.0)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('start_date', 'end_date', 'report_type', 'site', 'records', 'data_loaded')
    list_filter = ('site', 'report_type', )


@admin.register(ArcUser)
class ArcUserAdmin(admin.ModelAdmin):
    list_display = ('get_display_name', 'get_important_dates', )
    list_filter = (
        'created_on',
    )
    search_fields = (
        'data',
    )
    formfield_overrides = {
        fields.JSONField: {'widget': JSONEditorWidget},
    }

    def get_display_name(self, obj):
        full_name = self.get_fullname(obj)
        email = self.get_email(obj)
        if full_name and email:
            return format_html('{}</br>{}', full_name, email)
        else:
            return full_name or email or '--'

    def get_username(self, obj):
        if obj.identities:
            username = []
            for identity in obj.identities:
                username.append(identity.get('username', ''))
            return username

    def get_email(self, obj):
        if obj.data:
            return obj.data.get('email')

    def get_fullname(self, obj):
        if obj.data:
            first_name = obj.data.get('firstName') or ''
            last_name = obj.data.get('lastName') or ''
            second_last_name = obj.data.get('secondLastName') or ''
            if first_name or last_name or second_last_name:
                full_name = '{} {} {}'.format(first_name, last_name, second_last_name)
            else:
                full_name = ''
            return Truncator(full_name).chars(50)

    def get_important_dates(self, obj):
        modified_on = self.get_modified_on(obj)
        last_login = self.get_last_login(obj)

        return format_html(
            'Creado: <strong>{}</strong></br>'
            'Modificado: <strong>{}</strong></br>'
            'Último login: <strong>{}</strong></br>',
            obj.created_on or '--',
            modified_on or '--',
            last_login or '--',
        )

    def get_created_on(self, obj):
        if obj.data and obj.data.get('createdOn'):
            timestamp = obj.data.get('createdOn')
            return datetime.fromtimestamp(timestamp / 1000)

    def get_modified_on(self, obj):
        if obj.data and obj.data.get('modifiedOn'):
            timestamp = obj.data.get('modifiedOn')
            return datetime.fromtimestamp(timestamp / 1000)

    def get_last_login(self, obj):
        last_login = 0
        if obj.data and obj.data.get('identities'):
            identities = obj.data.get('identities')
            for identity in identities:
                if identity.get('lastLoginDate') and identity.get('lastLoginDate') > last_login:
                    last_login = identity.get('lastLoginDate')
            if last_login:
                return datetime.fromtimestamp(last_login / 1000)
