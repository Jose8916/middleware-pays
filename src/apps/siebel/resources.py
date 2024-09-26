import json
from django.conf import settings
from apps.piano.piano_clients import VXClient

from import_export import resources
from import_export.fields import Field
from .models import LogRenovationPiano


class LogRenovationPianoResource(resources.ModelResource):
    siebel_request = Field(attribute='siebel_request', column_name='siebel_request')
    siebel_response = Field(attribute='siebel_response', column_name='siebel_response')
    suscription = Field(attribute='suscription', column_name='suscription')
    transaction_payu = Field(attribute='transaction_payu', column_name='transaction_payu')

    class Meta:
        model = LogRenovationPiano
        report_skipped = True
        fields = ('siebel_request', 'siebel_response', 'suscription', 'transaction_payu',)
        export_order = ('siebel_request', 'siebel_response', 'suscription', 'transaction_payu',)

    def dehydrate_suscription(self, logrenovationpiano):
        if logrenovationpiano.transaction:
            return logrenovationpiano.transaction.subscription_id_str
        else:
            return '-'

    def dehydrate_transaction_payu(self, logrenovationpiano):
        if logrenovationpiano.transaction:
            return logrenovationpiano.transaction.payu_transaction_id
        else:
            return '-'




