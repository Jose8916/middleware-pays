# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from sentry_sdk import capture_exception

from apps.paywall.models import Operation, Subscription, FinancialTransaction
from apps.siebel.models import SiebelConfiguration, ReasonExclude, LoadTransactionsIdSiebel, SiebelConfirmationPayment
from ...utils_siebel import SiebelConciliationSender
from datetime import datetime, timedelta
from django.db.models import Count
from apps.paywall.arc_clients import SalesClient


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def valid_last_payment(self, operation):
        """
            verifica que la anterior un pago anterior
        """
        operations_objs = Operation.objects.filter(
            payment__subscription__arc_id=operation.payment.subscription.arc_id
        ).order_by(
            'payment__date_payment'
        )

        for operation_obj in operations_objs:
            if operation_obj.payment.arc_order == operation.payment.arc_order:
                if last_object.conciliation_cod_response == "1":
                    return True
                else:
                    return False
            last_object = operation_obj

        return False

    def add_arguments(self, parser):
        parser.add_argument('--subscription_id', nargs='?', type=str)
        parser.add_argument('--first_sale', nargs='?', type=str)
        parser.add_argument('--recurrence', nargs='?', type=str)
        parser.add_argument('--load_transactionid', nargs='?', type=str)
        parser.add_argument('--inicio', nargs='?', type=str)
        parser.add_argument('--fecha_fin', nargs='?', type=str)
        parser.add_argument('--filter_elements', nargs='?', type=str)
        parser.add_argument('--test_mode', nargs='?', type=str)

    def handle(self, *args, **options):
        """
            - Servicio que envia los pagos a siebel
            - valida que en el primer servicio de siebel aya sido enviado(wsSuscripcionesPaywall/renovar.suscripcion?codDelivery)
              recurrencia_response__contains = 'Correcto',
            - valida que en el segundo servicio de siebel aya sido enviado conciliation_cod_response
            - forma de envio python3 manage.py send_payment --subscription_id 15555555555555
        """
        # para semestrales list_transactions_ids = ['7ea73c42-efd1-408a-b57e-f2ace6421c41', 'd0071c38-076b-4681-994e-fae9f30d6556', '2032332e-988f-4e82-9d8d-74d65c72ceee', 'c2859cac-8697-490e-bc56-a30bdbc32e1e', '187c9a7a-14af-467a-9bc7-2fbc811fb5ff', '3e726647-cd91-44a7-b77d-0f3db5944cb5', '738e89bb-ec83-4ffe-bbda-3a3e0e6b8e3b', 'cfbf39ff-2f5b-407a-b0ee-c8d58217aa51', '1d55d7f3-3512-4620-9376-a95739c90a94', '7ecea3c1-39bc-4e5a-aad1-931b157f3ad2', '27181d10-698a-4a9b-8858-8c7ae970aa92', 'f9bccabe-7afb-4612-b5f3-c554b275139a', 'efbe9d45-a695-4621-8f74-baa651810ae4', '2fd228de-ce61-45df-bc0d-68883569fe00', 'c2124f94-933e-4164-b5bd-176410bc2d3f', 'ccff0af8-f1b9-4f00-a01a-7b88c20b3ee9', '2005088b-6c74-4465-96f1-2f005b34269b', 'e356ca7a-79b9-4b4b-8067-236251778a5e', 'c34725a7-1b34-4e1c-89bb-7497aec718df', '3cb6d171-59f2-4867-903d-67ab626a752e', '2ab6f308-7930-430c-ac69-90bcbd0fc2e7', 'e271286d-4812-41f4-96e8-4668e812c12f', 'ab0e04fa-9385-4e81-89a4-e7509ed9fa0b', 'fe474032-c760-4c08-9f50-96392b9c6967', '44508a91-f628-4325-a492-864150ef3b74', '2d90220b-df16-4ad7-a623-49969db2cf54', '450cd765-fa90-4f04-92bf-e135543c6000', 'a10dd8c8-25ef-4b67-a093-66597591f064', '71a9dd1b-c8ae-4c2b-becf-0944c9bcb06f', '6f9be20e-aabf-44e8-8f0e-b5b4e0812056', 'fcb6f201-2006-478e-bdcf-580c3bd5db13', '5820978e-7526-446f-a74e-a426384b6597', '75de014e-d34d-4873-972c-94c5c2f7d13d', 'adaa9174-219a-4f56-93fa-2129425e7b41', 'a0fcbf5e-0864-4da4-8a7c-015c3db0cc8e', '882edd5c-ce48-436c-86ca-c24fad589b2d', 'e258507b-cbae-422f-99a3-a30440d11a51', '0e2f57b4-c34a-495f-ad21-78f17878f35d', '3fdad5e5-068b-4667-84b3-0f7dd0afa338', 'eed21d45-c0c9-459d-a3e5-8292897cb1f3', '439c7ef2-3005-491d-9d69-ea50e3ab2eae', 'ebd4805f-e096-4fc4-9ce3-9b52ac18e3e6', 'd2c9333b-a509-40e9-bd8b-656a44a94044', '9f6f9b66-a152-4124-93f8-4b0ce1a6fa45', '8dcbc7af-0ade-4a34-8334-ef2bb8270e1d']
        # list_transactions_ids = ['d685d431-ab3c-4b9d-89a2-f3e42d9957e6', '4c8c8240-0c64-40f0-b7cc-f50f5beeb5a2', 'cce69910-1461-42ab-85ea-a33a973da187', '4c8c8240-0c64-40f0-b7cc-f50f5beeb5a2', '1b103743-aaef-4502-9671-1686c1db52fd', '3791e9f0-2685-4e02-95f9-fc9058add7c1', 'd8bc03c1-5d46-4d7d-859f-14d284581ec2', '133286d7-16b7-4fea-82dc-3a9ade2cbcfc']

        """
        payment_obj = Operation.objects.get(payment__payu_transaction ='H2CY7GB457DVR6CL')
        print(payment_obj)
        guardar = SiebelConfirmationPayment.objects.get(id=189)
        guardar.operation = payment_obj
        guardar.save()
        return
        """
        test_mode = True if options.get('test_mode', '') == '1' else False
        config_siebel = SiebelConfiguration.objects.get(state=True)
        if not config_siebel.blocking:
            current_month = datetime.now().month

            if options.get('inicio'):
                ahora = datetime.utcnow() - timedelta(days=67)
            else:
                ahora = datetime.utcnow()

            last_month = ahora - timedelta(days=int(config_siebel.days_ago))
            operation_list = []
            list_reason = []
            reasons = ReasonExclude.objects.all()
            for reason in reasons:
                list_reason.append(reason.reason)

            if options.get('fecha_fin'):
                fecha_fin = int(options.get('fecha_fin'))
                ahora = datetime.utcnow() - timedelta(days=fecha_fin)

            if options.get('load_transactionid'):
                load_transactions_id_siebel = LoadTransactionsIdSiebel.objects.all()
                for transaction in load_transactions_id_siebel:
                    transactions = transaction.transaction_id
                    list_transactions = transactions.splitlines()

                operation_list = Operation.objects.filter(
                    payment__payu_transaction__in=list_transactions,
                    payment__pa_origin='RECURRENCE',
                    payment_profile__siebel_entecode__isnull=False,
                    payment_profile__siebel_entedireccion__isnull=False,
                    payment__subscription__delivery__isnull=False,
                    recurrencia_response_state__isnull=True
                )
            elif options.get('subscription_id'):
                operation_list = Operation.objects.filter(
                    payment__pa_origin='RECURRENCE',
                    payment__subscription__arc_id=options.get('subscription_id')
                )
            else:
                operation_list = Operation.objects.filter(
                    Q(conciliation_cod_response__isnull=True) | Q(conciliation_cod_response='')
                    | Q(conciliation_cod_response__exact='') | Q(conciliation_cod_response='0')
                    | Q(conciliation_cod_response__exact='0') | Q(conciliation_cod_response=0),
                    Q(recurrencia_response_state__isnull=True) | Q(recurrencia_response_state=False),
                    conciliation_siebel_hits__lte=int(config_siebel.conciliation_attempts),
                    ope_amount__gte=5,
                    payment__pa_origin='RECURRENCE',
                    payment_profile__siebel_entecode__isnull=False,
                    payment_profile__siebel_entedireccion__isnull=False,
                    created__range=[last_month, ahora],
                    payment__subscription__delivery__isnull=False
                ).exclude(
                    recurrencia_response__contains='Correcto',
                    conciliation_siebel_response__contains='ya se encuentra registrado'
                )

            for reason in list_reason:
                operation_list = operation_list.exclude(payment__subscription__motive_anulled__contains=reason)

            if options.get('filter_elements', ''):
                operation_list = operation_list[:int(options.get('filter_elements'))]

            operation_list = operation_list.order_by('payment__date_payment')
            # print(operation_list.query)
            for operation in operation_list.iterator():
                if not FinancialTransaction.objects.filter(order_number=operation.payment.arc_order,
                                                           transaction_type='Refund').exists():
                    siebel_client = SiebelConciliationSender(operation, test_mode)
                    try:
                        if self.valid_last_payment(operation):  # verifica que aya un pago anterior
                            print('Iniciando envio: {operation_id}'.format(operation_id=operation.id))
                            siebel_client.send_payment()
                        else:
                            print('No tiene un pago anterior: {operation_id}'.format(operation_id=operation.id))
                    except Exception as e:
                        print('error : {operation_id} {error_log}'.format(operation_id=operation.id, error_log=e))
                        capture_exception()
                else:
                    print('tiene devolucion: {operation_id}'.format(operation_id=operation.id))
        print('Termino la ejecucion del comando')
