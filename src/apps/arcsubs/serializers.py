from rest_framework import serializers
from .models import ArcUser


class MPPToDhwSerializer(serializers.ModelSerializer):

    id = serializers.CharField(source='idx')

    class Meta:
        model = ArcUser
        exclude = ['idx']
        # fields = (
        #     'id',
        #     'first_name',
        #     'last_name',
        #     'last_name_f',
        #     'last_name_m',
        #     'email',
        #     'username',
        #     'register_date',
        #     'last_login',
        #     'high_date',
        #     'low_date',
        #     'low',
        #     'high',
        #     'newsletter',
        #     'token_activate',
        #     'migration',
        #     'migration_done',
        #     'estado',
        #     'type',
        #     'site',
        #     'nickname',
        #     'source',
        #     'dni',
        #     'birth_date',
        #     'birth_year',
        #     'gender',
        #     'civilstatus',
        #     'country',
        #     'city',
        #     'direction',
        #     'postalcode',
        #     'cellphone',
        #     'phone',
        #     'avatar',
        #     'avatar_50',
        #     'update_datetime',
        #     'update_last',
        #     'version',
        #     'term_conditions',
        #     'social_id',
        #     'eco_id',
        #     'privacy_version',
        #     'privacy_accepted_date',
        #     'tyc_version',
        #     'tyc_accepted_date',
        #     'device',
        #     'section',
        #     'dmp_hash',
        # )


class MPPToDhwUserDesactivateSerializer(serializers.ModelSerializer):
    id_source_user = serializers.CharField(source='id')
    date_desactivated = serializers.SerializerMethodField()
    id_motivodesactivated = serializers.SerializerMethodField()
    motivo_description = serializers.SerializerMethodField()
    site_id = serializers.CharField(source='site')
    otros = serializers.CharField()

    def get_date_desactivated(self, obj):
        return "1900-01-01"

    def get_id_motivodesactivated(self, obj):
        return ""

    class Meta:
        model = ArcUser
        fields = (
            'id_source_user',
            'date_desactivated',
            'id_motivodesactivated',
            'motivo_description',
            'site_id',
            'estado',
            'otros',
            'email',
        )

# class DmpToDhw(models.Model):
#     idx = models.CharField(max_length=9)
#     first_name = models.CharField(max_length=50, blank=True, null=True)
#     last_name = models.CharField(max_length=50, blank=True, null=True)
#     last_name_f = models.CharField(max_length=50, blank=True, null=True)
#     last_name_m = models.CharField(max_length=50, blank=True, null=True)
#     email = models.EmailField(max_length=50, blank=True, null=True)
#     username = models.CharField(max_length=50, blank=True, null=True)
#     register_date = models.DateTimeField(blank=True, null=True)
#     last_login = models.DateTimeField(blank=True, null=True)
#     high_date = models.DateTimeField(blank=True, null=True)
#     low_date = models.DateTimeField(blank=True, null=True)
#     low = models.NullBooleanField()
#     high = models.NullBooleanField()
#     newsletter = models.NullBooleanField()
#     token_activate = models.CharField(max_length=200, blank=True, null=True)
#     migration = models.NullBooleanField()
#     migration_done = models.NullBooleanField()
#     estado = models.CharField(max_length=200, blank=True, null=True)
#     type = models.CharField(max_length=200, blank=True, null=True)
#     site = models.CharField(max_length=200, blank=True, null=True)
#     nickname = models.CharField(max_length=200, blank=True, null=True)
#     source = models.CharField(max_length=200, blank=True, null=True)
#     dni = models.CharField(max_length=200, blank=True, null=True)
#     birth_date = models.DateTimeField(blank=True, null=True)
#     birth_year = models.CharField(max_length=200, blank=True, null=True)
#     gender = models.CharField(max_length=200, blank=True, null=True)
#     civilstatus = models.CharField(max_length=200, blank=True, null=True)
#     country = models.CharField(max_length=200, blank=True, null=True)
#     city = models.CharField(max_length=200, blank=True, null=True)
#     direction = models.CharField(max_length=200, blank=True, null=True)
#     postalcode = models.CharField(max_length=200, blank=True, null=True)
#     cellphone = models.CharField(max_length=15, blank=True, null=True)
#     phone = models.CharField(max_length=25, blank=True, null=True)
#     avatar = models.CharField(max_length=200, blank=True, null=True)
#     avatar_50 = models.CharField(max_length=200, blank=True, null=True)
#     update_datetime = models.DateTimeField(blank=True, null=True)
#     update_last = models.DateTimeField(blank=True, null=True)
#     version = models.CharField(max_length=12, blank=True, null=True)
#     term_conditions = models.CharField(max_length=12, blank=True, null=True)
#     social_id = models.CharField(max_length=200, blank=True, null=True)
#     eco_id = models.CharField(max_length=200, blank=True, null=True)
#     privacy_version = models.CharField(max_length=12, blank=True, null=True)
#     privacy_accepted_date = models.DateField(blank=True, null=True)
#     tyc_version = models.CharField(max_length=12, blank=True, null=True)
#     tyc_accepted_date = models.DateField(blank=True, null=True)
#     device = models.CharField(max_length=12, blank=True, null=True)
#     section = models.CharField(max_length=100, blank=True, null=True)
#     dmp_hash = models.CharField(max_length=200, blank=True, null=True)
