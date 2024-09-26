from rest_framework import serializers

from .models import Logs


class SiebelSerializer(serializers.ModelSerializer):
    created = serializers.DateTimeField(format="%d/%m/%Y %H:%M")

    class Meta:
        model = Logs
        fields = [
            'id',
            'delivery',
            'log_type',
            'created',
            'log_request',
            'log_response'
        ]
