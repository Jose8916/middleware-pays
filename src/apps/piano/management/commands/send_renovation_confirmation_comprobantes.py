# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand
from apps.piano.constants import TERMS_EXCLUDE, LIST_ENABLE_SEND_SIEBEL
from sentry_sdk import capture_exception

from apps.siebel.models import SiebelConfiguration, ReasonExclude, LoadTransactionsIdSiebel, SiebelConfirmationPayment
from apps.piano.utils.siebel_confirmation_renovation import SiebelConciliationSender
from apps.piano.models import Transaction, TransactionsWithNewDate, SubscriptionMatchArcPiano, BlockedSubscriptions
from apps.paywall.models import Operation as OperationArc
import csv
from apps.paywall.arc_clients import SalesClient
from datetime import datetime, timedelta
from django.utils import formats, timezone


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def add_arguments(self, parser):
        parser.add_argument('--test_mode', nargs='?', type=str)
        parser.add_argument('--print_log', nargs='?', type=str)
        parser.add_argument('--filter_elements', nargs='?', type=str)

    def valid_last_payment(self, operation):
        """
            verifica que aya un pago anterior
        """
        transactions_objs = Transaction.objects.filter(
            subscription_id_str=operation.subscription_id_str
        ).exclude(
            devolution=True
        ).order_by(
            'payment_date'
        )
        # if transactions_objs.count() == 1:
        #    return True

        count_ = 1
        for transaction_obj in transactions_objs:
            if count_ == 1 and operation.payu_transaction_id == transaction_obj.payu_transaction_id \
                    and transaction_obj.initial_payment is False:
                return True
            else:
                count_ = count_ + 1

            if transaction_obj.payu_transaction_id == operation.payu_transaction_id:
                try:
                    if last_object.siebel_payment.cod_response:
                        return True
                    else:
                        return False
                except:
                    return False
            last_object = transaction_obj

        return False

    def validation(self, operation):
        try:
            state_transaction = operation.siebel_renovation.state
        except:
            state_transaction = ''

        if SubscriptionMatchArcPiano.objects.filter(
                subscription_id_piano=operation.subscription.subscription_id
        ).exists():
            try:
                obj_subs_match = SubscriptionMatchArcPiano.objects.get(
                    subscription_id_piano=operation.subscription.subscription_id
                )
                count_subs_match = SubscriptionMatchArcPiano.objects.filter(
                    subscription_id_arc=obj_subs_match.subscription_id_arc
                ).count()
                if count_subs_match == 1:
                    pass
                else:
                    return False
            except Exception as e:
                return False

        try:
            term_id_ = operation.term.term_id
        except:
            term_id_ = ''

        if state_transaction is True:
            return False

        # se excluye Plan Universitario, cross, Digital CYBERWOW2021 Trimestral Web
        if term_id_ in TERMS_EXCLUDE:
            if operation.subscription.subscription_id in LIST_ENABLE_SEND_SIEBEL:
                return True
            else:
                return False
        else:
            return True

    def valid_last_payment_arc(self, piano_subs_id):
        """
            verifica que la anterior un pago anterior
        """
        if SubscriptionMatchArcPiano.objects.filter(subscription_id_piano=piano_subs_id).exists():
            try:
                obj_subs = SubscriptionMatchArcPiano.objects.get(subscription_id_piano=piano_subs_id)
            except Exception as e:
                return False
            operations_objs = OperationArc.objects.filter(
                payment__subscription__arc_id=obj_subs.subscription_id_arc
            ).order_by(
                'payment__date_payment'
            ).last()

            if operations_objs.conciliation_cod_response == "1":
                return True
            else:
                return False
        else:
            return True

    def handle(self, *args, **options):
        """
            - Servicio que envia las renovaciones
            - forma de envio python3 manage.py send_renovation_confirmation --test_mode 1
        """
        print('Inicio del comando. ')
        dt = datetime.now()
        ts = datetime.timestamp(dt)

        test_mode = True if options.get('test_mode', '') == '1' else False
        config_siebel = SiebelConfiguration.objects.get(state=True)
        list_to_send = [
            'f787d94b-54d4-43dd-9ca4-717b1dcef55f',
            'e88c64b2-f228-479b-aafb-ca2362397063',
            '0dad88eb-b2fe-4a8f-9a06-1f1dcd7a825a',
            '192f753f-cd00-40a6-8453-bb822664bcb3',
            '8f824aea-fc11-4923-ac90-0babd4b48dbd',
            '53efcad2-040b-4135-8d2e-380c8be1b160',
            'b9074c7d-4fff-4593-8551-63bbb73e58b6',
            '21dd1adf-774f-4300-b4fa-d6ecac3a7ec9',
            '72eb68b0-c700-44c2-b32c-cf86f32fea2e',
            '808caccc-adbe-4821-843f-d4d8ee028c91',
            '550fb823-ff4a-461c-86fd-86197a6fa122',
            'de7460d2-3f2f-44dc-a087-8ffa659f07bf',
            'f556c9c6-9b29-4a00-a2bb-a2fefb20e729',
            '0df1c9ac-d0d0-4c3f-a3f5-464380e5b74d',
            '9a9dd1b7-16c6-45a0-bb18-bea4af9c9215',
            '3bd44296-b8bb-4d9a-8261-eaa1fa2bf848',
            '96d5797c-03b3-4895-a26f-92238d37bd9d',
            '7a52c753-2090-4380-b01f-0192dd227b71',
            '984fa90b-3206-427a-91a8-f19fc4f3c104',
            'a1f585e9-c689-4ba5-b0fe-91a8acd5e6a2',
            '01cd0e9e-e056-4e40-8e8a-2e184454afff',
            '9e35a035-6157-47ed-b54f-4077a2961f4a',
            'cc38aef9-d2ab-44f0-8bfb-fe10b5bf6d55',
            '7662d182-7066-406c-a6b8-8e7705eb18b0',
            '499b49ed-d891-40cd-8851-758c227118ee',
            '650f31cf-57c9-4a1b-af96-d02a98e4a6f9',
            'e6f184fe-3f23-4c6e-92d6-503b05d88919',
            '0acf56e5-4d80-4e24-851f-1bb4ea83de58',
            '902e0f7a-b97f-460e-b8a7-2c4aac7cb6a7',
            'd41735ac-3c05-4b02-b864-ff12fdac0909',
            '936c5be8-50da-49ea-a3cb-b92a49d3e6b6',
            '0fca9be6-280e-4e80-bf4c-65ec85bfb862',
            'e97ea645-d7da-4d08-a4bd-cfaba854ec1d',
            'b7cd65bd-e869-4eb8-940c-fb594ed92804',
            '351ecf6b-27f3-4976-a185-a921d712e1fc',
            'd5445f7f-712d-4cdc-a10a-cfaf29441288',
            '1f4449cc-bd06-4852-b9f4-b01bf9648818',
            'f90aa754-e27e-4cd2-bacd-62746d3d4ade',
            '575210e4-e4ff-480d-9393-84c5e2c06812',
            'a3adc5e1-fed4-4b79-a554-d2f65de5bda1',
            'ddc004b9-b0e6-4bef-900c-09e21fd35126',
            '1efe2e86-3f2b-4082-b968-bdfac52b60f5',
            '4ef16773-16b7-45ce-8fe5-846ab5c4e81c',
            '6f9d66e3-c80d-4ddb-b6fd-a908062a7c8f',
            '749b3232-6d28-4074-bb42-155b8f073bb0',
            'e2f7c645-3ba0-4801-a8db-9ef58e5b79e8',
            '4ae24a52-5ccd-4bb9-979c-d12a93437ec6',
            'c8638189-b421-4b7c-a34f-2b5a6e8ded2a',
            '35874352-c90c-49d2-96af-ab9ad7b5fc87',
            '7fffb41e-2f2b-419b-a8ab-22a18bbf442c',
            'f6104878-9b51-4dc8-b721-b32b2bb4a614',
            'c316bbe1-3857-450d-92b4-f216d73d546c',
            'cd2202e5-be75-479d-bdf3-e2d62e371eb6',
            'd4e7f933-ba04-4495-b52f-bcb596e4bfac',
            '889a194d-167c-4c14-ad8d-608b3e005fc5',
            '59d164e9-e944-409b-8d6b-9fd16cdd51ff',
            '93ce8cd6-91ee-4925-8e2d-e1e67a985e7b',
            'aa3a2a1f-931d-4a84-a6d4-9139a70ab36c',
            '4f698473-67ba-4703-a1dd-4310fe1d6d82',
            '3e63d61c-1e6a-466e-b911-2a80d93fd587',
            '5701ef1e-408d-444f-b62b-65ed55e94bef',
            'c08c4f80-0aad-4d28-b31b-027698cc31fa',
            '55abb237-a497-4ee1-80c2-463d7ab5d34d',
            '2657c57b-ba47-4064-8a3f-2baab83db26c',
            'e1d55eba-f3ba-4e90-977e-b1c62dd91472',
            '60caf211-85c7-4bf1-a2a6-8bffe7edeefe',
            'c16033a3-7c89-40ec-be5d-19204e9bc5c6',
            '73f0cef1-335b-4116-86da-9c24e544d2b8',
            '9fa880e5-5c68-47df-90b8-cb75561d47f5',
            'e21bc406-fdfd-42ee-bc4c-85e26d0c1fb9',
            '8cff6b48-8527-49e0-8e2f-fb3685c0674a',
            '571a71d0-c062-4554-9782-55dbc65fb588',
            '503d62f5-be1e-45c6-84aa-81ba2c6ff261',
            '10cb5035-b1d4-4531-b1e9-3bbab326bb83',
            '40ef430e-6682-41a6-87ec-5fd5991c50aa',
            '4889513a-1cd7-4eb8-b4ab-dcf0b106edce',
            '488e2fed-dbc0-4922-9061-8ae1cd7a4556',
            '3c47e12b-ac21-43cc-997f-ab39b3124b5a',
            'beb0834e-c032-44fa-9475-0dee0a35fa6c',
            '4f2e9dcd-ea7d-470a-ae15-e588115f08bc',
            '5c7a0124-9594-4578-b859-6a98c9a7a153',
            'd502d3f4-6c3e-4d4b-8f58-8b23dbf8f86a',
            'a2bc53c5-476d-4ec8-9332-b499dac1610c',
            '81880e0b-c7d7-4610-894a-597236605ec0',
            'b6028294-5031-45ff-9dae-04ded1561592',
            '56c9e948-db6c-4e35-ad03-c862014ff1f3',
            'f8a4c5ff-187b-4e4d-9f3a-d008b375484a',
            'd2ddb56c-79f6-411f-990e-acc6dc40066e',
            '9c1ca9e3-fa84-4684-aaa9-a834ce93794e',
            'fdf6e791-20e7-4e63-996b-11268220546a',
            '812bc7f9-a953-4263-a165-c7b3afd42706',
            '77798147-80fe-44f4-b946-8ef8c84a1406',
            '16d0b7c6-f2c1-43d7-be76-0cd560ee6360',
            'c2bf1e90-e3c9-4741-8288-228f58ce6621',
            '478b311f-cb95-4997-9a6c-9c3179c97ded',
            'afe12ec9-e291-4927-8292-a929df8c1e9f',
            '037951af-9348-4fbc-b43b-d98294f030f0',
            '05267977-e421-4def-9dc8-9ef04c55bc29',
            'b4511e9f-8254-4031-b35f-264e096dc7c7',
            'fca0b7c6-29b5-421f-b66a-233ceb9db926',
            'fc3955a3-bbdf-4ea7-b13e-6134c76c1698',
            '9b1cfd00-9681-4386-9e98-5afe310317e4',
            'a9677efe-8c94-43a9-8f7e-f99e70833b1c',
            '726b2b17-876a-422d-8f67-5ac04e7a52ce',
            '882fe659-5506-4cbc-9d9b-0069dd412330',
            '86bf0e9a-6e3b-4e83-a89a-7a2b35636232',
            '63cf2f0e-a12f-4577-a059-87866b6fe90b',
            '9f2c0c55-d5db-4a76-888a-0b5021dce91e',
            '2e337573-7a7c-483a-8666-87c27ddeb25f',
            'ff80a685-172c-4c20-863a-3c6194cf1b5d',
            '74ec9093-d426-42eb-9887-be365be66285',
            '3b11aaf1-9fa8-426c-92e7-cf16c23c8416',
            '2dcde82a-2a97-4a83-a5f7-3d1add8a2f66',
            '50ef5fa0-111c-40e1-8b9f-a1a3c03708cc',
            '4314bd0b-eb93-4467-b703-d40ad79771dd',
            'd07d641d-aa6b-4c76-bf70-593fc2082631',
            'b882da92-3079-4944-955f-1221f11b6c88',
            '3ba5a5ec-b90a-48d1-a376-d618afd32ad5',
            '2e5310a7-5f66-4fde-baff-70c69e7440bb',
            '91b0fb7e-4fa2-4703-b991-2f19c529d926',
            '2ea8ab2b-24c8-4cfc-b583-ac350539f727',
            'e7ac074e-b5c1-4737-84ca-af9b65322c96',
            'a3ada727-1014-492b-b10d-39090fd3b967',
            '13ab543e-75ec-4b24-b2d2-6da338e56718',
            '5912f371-8e53-4082-bc76-4d30d7368f27',
            'bc4508da-1a60-4890-9b5f-29b3314ca0cf',
            'b2029c40-9657-4bf3-a303-c56c38ae27d4',
            '6b642ab7-16b9-48dc-b32c-5dcbca5e03ee',
            '9a40965d-86b4-4ae0-aab7-9f618e3575b1',
            '6e6e9919-181f-412f-80d5-77940e88da64',
            '4a548f75-6866-41d1-89f8-37690a13b63e',
            'c119aa2f-693a-489f-9ba5-f17e289ad8fe',
            '6d986d7e-384c-4e15-97cb-ba181e625f8a',
            '0a6b1c65-82db-431b-8750-c6176764d15e',
            '3ad30b2a-70f3-4efb-a0fb-4163884b188b',
            'a0cb3422-ab94-467c-8515-57f7a58cd502',
            'd8e3a2da-7864-4302-8a54-15c7c1ccd9ce',
            '0b118db3-652c-49eb-a159-b3c714f9de1e',
            '7438f926-cd14-47db-ab17-92dd4096898a',
            '4d8945e9-1171-428a-9663-89facfbca9de',
            'b8f4c0d6-4759-47bd-a3e2-c3bad1b4847c',
            '0aa668a9-198a-4d38-bcde-9f077904d121',
            '019b5bd5-7ec2-4887-a4fd-47e2b4882c12',
            '416917de-a68a-433e-a334-386e163628a4',
            'e6326884-5007-4eee-908e-44ee0a88b7cd',
            '204f0e57-cc54-4f90-a259-fd48d6aea68d',
            'b11cb040-54e5-48a0-ad77-827560126dbd',
            'cce15440-9cb8-479b-b565-e5b7c78d2c41',
            'ca20946d-6335-4bf5-9b1e-4480ac9a41ba',
            '6b893bcd-bf60-4c99-9dda-77421dfad583',
            '2ff794ca-be32-490b-8d08-e85244c95611',
            'c08e50d0-4cb0-49b8-a9dc-b0063d3f7db6',
            '7ad125b3-b4b8-43cd-9582-74263dfae301',
            'b2e490cc-c164-4611-980d-6797652bde53',
            'da0b1b4b-6624-4976-b923-781ff4f0ca91',
            'c7068c79-f48b-4b98-98fa-69fb474989f5',
            'eeeab881-a7ec-414f-95e6-0eef74321d5c',
            '508e56c8-f392-4ec2-b246-4f3770ae8133',
            '510af3f3-b079-4bc2-9554-5a3712e3ae66',
            'da915efe-1047-49c5-863c-fb76b291f0e5',
            'e72e2ec2-545c-4051-9de9-69f96b9abf7f',
            'f6dbfda6-7804-448b-9b24-dd9da528f7b8',
            'eaf547c5-0c97-4a77-8cd5-f2fc24de9a4c',
            '8f014aac-abc9-41f9-afd9-d8218d64a19f',
            '37a58284-2272-45ac-9792-fce0787c4c92',
            '48d64cfb-3e74-474a-9b7a-2d11822cccd6',
            '8ec52b09-1c1f-4a0b-8bdb-db2dae01fef6',
            'd85dda4a-efc2-490b-b572-a50d406a64c7',
            '0bbb957d-f4d5-4d95-973c-fbee75736bc4',
            '79a4eb43-118e-4468-9048-6f38f6cf0af2',
            'baa42828-0d9e-473c-a022-e63f2c70ed91',
            '82e6091d-efdd-4f6f-94d5-80a84eae0ebd',
            'd70da1f3-810d-4cd8-9f23-29ba005a0828',
            'a67ada7b-b340-47bf-8bef-eb22427409ad',
            'e72e8756-c2ed-4688-a73d-134d4e59eb9d',
            '9f9fa76e-26ad-4b26-a92b-1336290fa0b1',
            'a2ac3ab4-4c7f-4c62-844f-4c0ff406ce24',
            '1ececa93-82a9-4d66-a3b4-335776d1a8a7',
            'f312ae2a-b10d-4e7b-9917-af04907ac8df',
            '93667c50-81db-4a8c-8d03-324cc228dc46',
            '82b9a100-2413-4a32-b13e-5e0c30454931',
            'd5a7f11c-97f0-4f11-bc5e-bc157c0fea56',
            '47893a02-f58e-4d32-a111-3c417261a6cb',
            'f7129b70-8594-4b3f-bb00-23804b146e84',
            'a4e3b3c3-ec3c-4e96-8f28-39a4cdc77b15',
            'bc448eb9-c5e3-45d3-86a1-8812ff17db50',
            '981b62aa-c43d-43b6-be98-fb6fd59a2d57',
            '030ce772-7e2e-42b1-869e-6913b03c7d9d',
            '54d3b6ac-1701-44fc-b6d5-7283208662bf',
            '4aea0335-050d-4e36-826d-b1f8317b7707',
            'bec28f44-b530-40c6-a68f-b776d375bb90',
            '68afd28b-62db-4e91-8964-eeb327b556d0',
            '662f9293-4da4-490c-b0a5-a7d29c4aac30',
            '99812d4b-f203-4be7-b36f-dffbdca266fb',
            'f5ca7ae8-7ba2-4f23-9c17-310a8ea9f89a',
            'eeca3549-9e39-4a06-b778-6b8db9dbfd39',
            '19df0a4d-5600-4698-baa8-8a8374e2b9f1',
            'b7233f84-8765-4307-955a-1adcbe2a4d08',
            '604bc9f4-07c7-4d50-a9cf-25ec8fe53797',
            '29784ae7-8b77-4f38-a66f-aa1b26d2cb43',
            'df2a9f5e-0888-4575-a9a1-4bb52cea1dea',
            '5e5dbd93-b708-4efc-b8eb-e2c5d0c2418e',
            '1e5209a4-d98f-4b3a-9577-3c1c4ceb710b',
            'b923a36a-929c-4bb6-8cdb-547dea8d5b2b',
            '9a2ce66a-0fb7-4351-b9eb-a75f019c7b25',
            '86c7d7d3-4490-4881-acd5-60d4c5b4f3cc',
            '6eec80f6-f621-4a19-90a7-f5018cc0b4f1',
            '24193641-d469-4aaf-906f-e65885611fb0',
            'eeb555c1-5d99-4fe3-8c28-7f4fc3c35ed7',
            'fe08cb38-d7a5-44a9-9849-54cc88404b11',
            'e807422b-6592-468f-86ab-b0fd8d4f0234',
            '03dd83d3-b9ed-4c35-904d-856d1325a873',
            '50b16603-1228-44fd-b56c-a5ec9169e301',
            'eb7271bc-801e-49d8-92c7-456b35d30461',
            '08ee727a-5f2b-4ed0-8d6d-c0a29aec0dfe',
            '3727cca2-bf52-49c8-85fa-b56fd773a1a9',
            '96a62681-adcd-493a-8202-55fb641cf9a1',
            'bc357742-5aa1-4dcf-85e6-8258c4584b74',
            '3dc53c4e-d109-421b-8563-e393db1ef2c2',
            'c0f9b7dc-d5af-42db-bb2e-386a3015955e',
            '81f6ec90-865d-4dfd-998c-03c6bd0e4876',
            'd1e875d5-7844-46b4-81db-b0e703ccfa1d',
            '8f7d494c-0379-48ea-bdff-db6098281f29',
            '23ad00e1-1c41-455c-b120-1580921d59ed',
            'b278610e-163c-49fe-b7f0-21c24cf7971e',
            '61502da6-1716-41bd-998f-f54e61db4859',
            '8b0547ec-fdbf-46eb-99ce-8827dc063b05',
            '669d1d50-e95a-4723-9543-161a5c852174',
            '144bf099-e4c2-4acc-9cf7-94944ce68a54',
            'b2db4021-cf4a-4618-a352-e2eb5a417032',
            'b9293031-a8ab-4848-94fb-a9257925ea48',
            'bcfa2be5-eb7b-4e9f-8018-cf38565411e2',
            '2886af0b-3567-46ac-80d9-2072e40fe563',
            'c64ff19d-5807-4b62-a9c8-bfd6b7b13dde',
            'dddd54ab-def5-4505-ad63-62b09e8334ad',
            '6bdac264-2fe5-4ada-954f-85322d5bf60a',
            '65f478bf-8fa3-4974-bb6c-fed4c285fc03',
            '6816d1c9-8206-461e-9dc9-210850a90349',
            'bd58499e-c5f2-4d21-9e86-ce71ca02cfe1',
            '615f76bf-0d25-4a1b-9acd-1cb77ed4446c',
            '5b33a7ca-73e0-46c7-9299-79982b156d0e',
            'd6b69fc4-f312-4268-833b-3e416006a146',
            'd6409acc-0e07-4f17-b512-4fc6d7ade81e',
            '6ae6f17f-c258-43f2-83a6-71059e967ed3',
            '751705be-40b0-4dea-aa90-ea95e21fc014',
            'b9333aff-cdbf-49c4-9c3f-90941b9b583a',
            '78f1ab72-33fd-436d-abb9-ffea4f13b0f4',
            'b8c2959a-b7d4-4919-8e52-2e613458a326',
            '2ebd0dc3-0a91-4f8a-aab6-1cc44407b225',
            '7ccf2e7b-cd44-4ab8-9f75-c9e9b185e790',
            'c13b7fb2-47ed-4b8e-af19-b4a410bfcff6',
            '2daae810-cb1a-40a9-a76f-ae712f18002e',
            '036674d2-6338-4b95-8eb1-2c9c72f946c4',
            '22c901de-c1af-478d-aa59-0f9a0480f886',
            '4f96fd70-b39f-429c-acbc-bcd7055b56f1',
            '6321f9b8-072c-4746-8042-433ba76d1059',
            'a3d09a69-e5de-4b68-b47e-816b1626d5a8',
            '5f60e93b-f033-4a03-a4d9-a9966aac30d5',
            '6943aaff-a329-4bd3-bcd0-94d4b781aa60',
            '1198bc83-9883-4a75-9e66-4134f883dd24',
            'a8d019e4-39e0-47f9-89a1-6b449b7ad62d',
            'caed0a35-70ff-435b-80e8-4f912d5742c4',
            '35f7d14c-8c9d-442c-8369-ab3eccdcbcd6',
            'f4cb83f5-5099-46a4-975e-2be58f981d54',
            '84fd85c3-054c-4d9e-ae35-520a1ca105f9',
            '1248ac32-0d4c-48b3-bc38-2ccbaa0b5639',
            'b4c04c23-89f3-49c2-a31f-0c56c4409c6e',
            '63444d46-d71a-4995-bddc-c3d78be98b44',
            '4a688fd4-f003-43a3-985e-9d5f4acbcebd',
            'd9ddc8c1-26c3-4ef8-aa66-9bb4f40ef72d',
            'da5dd8ee-a450-4a94-9296-e73d4b2a8918',
            'dc33ba12-bd33-45d3-83c2-728ffcb27cc9',
            '8d8aab86-94fd-442f-9bba-b16c899dbce4',
            'fae771a6-d9e4-4b79-8cba-2f14402f2f32',
            'e0ee38dc-703d-49f8-bc9d-ee7d31289109',
            'e806ccc0-9659-45ca-94f3-dbe4725d0d14',
            '465e4c49-53aa-4ab6-b8c3-7a123d6323b4',
            '9b0ab769-7b89-4490-95e5-c9b7eb1bdafe',
            '78c14a55-e41b-4e67-8a71-d608bd8ed44f',
            '0dfa8040-3d1f-4bf2-a101-482ca615ea00',
            'bcd620e2-b983-4f3a-aeb7-f8a1961c9692',
            '6a34c23a-e878-4d97-9c48-6109c00b6268',
            'b632a2b5-d550-42a1-9851-d1fef88a4aaa',
            '26da3d85-5976-4d40-a17e-ea57e7da5cdc',
            '98d745ba-8a2a-4a51-9816-3eef3ddc3a37',
            '67f24116-99d9-4bf8-a76e-915ece2d80ad',
            '997ff7e9-f516-4de7-b1a8-b0ad03de8952',
            'c7eeb407-f7eb-425a-95c3-f873e1b5f534',
            '2f9f4a77-0ba8-4595-9830-0188f0318168',
            '68985f89-9c8c-4526-9225-bbf6130fa30a',
            '90c1081d-d178-42c2-90e2-4a9998a5e880',
            '2965c1df-0d33-4db1-9271-77fb780efe65',
            '9f8f37e9-4e34-4753-9963-c75c99251da8',
            '64215509-c827-4209-aaaf-9bf915c9cf21',
            '5be29f4f-3713-4ef4-9415-c6c521eda1d0',
            'c26ddbf4-dbc2-47d7-bc61-8adea89a1dc5',
            '1b34db5e-10b9-4892-9dbc-158cad6e5f67',
            '092c9cce-2f63-4f3f-9413-5951991da33d',
            'e489b536-bdb9-408b-a10b-7c7529ddabe6',
            '7402421b-6571-40cd-9563-0c45ddce50aa',
            '3a7c8428-67a5-4afd-8af7-8a53ba5131e8',
            '0a18e952-3b27-4cf9-8e79-703ac36792fc',
            'cd4d02f2-1d1c-463a-bd2c-5b376549b01d',
            'bd2cf924-ad1f-4efd-ac8e-ecf7e3dff53f',
            '5ab5e66b-3f28-4cdf-853e-b8638990aa77',
            'eaa6ef51-0a51-49af-aa8b-be1107242c6b',
            '22852138-f1ef-4b21-92b9-631792362831',
            'ac62d347-4b80-40b5-907f-3b1761f2b281',
            'c821abd2-fc66-486b-8b9e-aa6146b43dd0',
            '160b12fa-5a04-4c0b-9373-629edcd0eb72',
            '5810b8d4-cd3e-486a-84e9-e07a5d48337f',
            '4c69d7c2-9f8d-4f34-8f16-b60de73119f1',
            '14cd172d-fd7f-4081-80ae-e413a23dc61d',
            '436fa926-9c60-480b-afb8-17ebc921ab7a',
            '5d569fc3-7918-4597-809f-8bc8fc5c2e05',
            '8d31fe17-e50d-4d80-826f-9822bf12853b',
            'cf5cb75a-ae4f-4f0c-84eb-4ae8a45ef368',
            '61aeb34f-c85c-4eb0-8234-635629ed5568',
            '58dc5f5f-2eb7-4cca-bb16-17bad511ed96',
            '5533c2c1-3819-43d5-8824-f46332e56df8',
            '4cab056e-8c79-45d7-b23b-8a0ba19f8f20',
            '1e6bdd53-2da4-4dc3-b3eb-5c83a03d4057',
            'b1cc0f2b-edc3-44ae-9327-307118a591f9',
            '5ef1628a-273e-420c-b023-324c5b5fd3a8',
            'd5f9c9d8-94a3-4e6c-996d-bfa1099bd99b',
            '662c6621-d705-4f4e-8503-7709bfe5dc6b',
            '84cac5de-7520-4858-9f29-c21ae031379d',
            '18625253-a1de-420f-8ce9-d5d93e06451c',
            'dfefeba7-470e-4d90-8821-aad3909836c0',
            '0a69fadd-b3c7-40bb-b5b9-031e72e8a78d',
            '13561f2f-cd2e-4be0-8ae4-5426ddbae49a',
            '05669c97-42b2-4403-8b7a-e950345c1c71',
            'd89babcf-054c-45aa-846d-1ea844401ff7',
            '3921deaf-532a-43bc-a452-8cf99ae3468c',
            '6d166d39-f9ea-43d0-b4ae-85ce0def1949',
            'ec97bace-eefd-415d-94f9-28bdaf81999e',
            '53d9f3d7-9881-43b6-8987-776d893af9e7',
            '8859551d-57aa-4a7e-bfe7-f23c2abf99a8',
            'aa208526-c1ed-4a12-b43c-7d46016aeaac',
            '8ab6c614-5845-4149-9523-4f8f17ccfa45',
            '0db28d62-b602-460e-9625-ef68ed87ce8c',
            'ae7cd968-ed9a-4854-aba6-a48a7b1d38ad',
            'd869f812-ee77-4a7b-8587-8ca6c60cd5ec',
            'f5a4c311-dd5f-40b2-bd88-085262d47312',
            '096ade0e-05bd-4e9a-a855-01dcb95d0090',
            'b580fe6e-763d-415f-91fe-9820c455d88f',
            'fa4c4141-b242-4cd0-b0f6-1d1156253cc5',
            'e633ea0b-13ea-4ffc-87dd-8aa3bb5374da',
            '1799dde0-6595-4072-b5fa-f6f10c8e2f47',
            '24fcd104-d41b-4831-8187-6744d9a5a2d5',
            '2f3f702d-ed95-4a33-a394-1d939196a950',
            '84ba7a5a-efc4-4d3f-84cf-8be4ecde400d',
            '6ff9dd0a-c35c-4429-b94f-81084e69d9f0',
            '5dc2cc3f-0817-4444-82f2-197239e14d7a',
            'b06cc4a3-7124-4182-a937-f637a2a2278d',
            'ca60e5e2-cc59-417c-ba28-0a542ad69b3e',
            'a1fb3558-9b83-4b74-a725-36ec7ffc0ff3',
            'edc10e55-dc69-4c2e-a9a3-1960a6a3158b',
            '96d4247b-356a-40f3-b4a6-0bed7f75c666',
            '0c9eece9-5f03-4c3d-933d-1b22e1d22920',
            '4df037d4-8e9e-4cf1-9e55-e562dbf2a080',
            '8a881e62-c687-4313-ace4-c4690ab196a1',
            'ed68c476-1fca-485d-8ead-774d44b41957',
            'b89b0741-8d02-412a-840d-9f4a4be21e33',
            '8ece4b8e-73a3-40ba-93a0-bb6db26b73ad',
            '09ea11de-66bd-4ac8-bbe2-9cc74b6d2909',
            'efb2a61c-c69c-4a5b-908a-75eb12e45535',
            '5322c7d8-ec71-4cac-83bc-5e4f8d16b7b6',
            '855323b2-8574-405c-99b5-cd59dafd1557',
            'b54b7610-1106-4586-a67e-ee8695939e8e',
            '11284d29-4835-4ae5-9a8f-2b130b7d2880',
            '4cce1b05-3845-4d70-8db6-17e728d41d1e',
            '058bd104-ea16-4dab-9813-9b160c7aacb2',
            '12170040-edaa-42f6-ad22-4fdb96343844',
            '55150d9f-1e6d-4e52-9f25-d958f3bc80da',
            '10c61535-709c-498d-b67a-3aa603e95db1',
            '7724180b-c9e4-44d7-be39-ac9ce9c1bc72',
            '313bed29-01e6-4ec3-a432-68572838ce84',
            'fba8d0d5-ef6f-4079-a165-92645c175c8f',
            'ba6aa6d4-2e33-424e-9193-8c2ab85b42f5',
            '56d08533-5999-4492-a10f-55e3ac9304bd',
            '3bceb278-ebbd-4b1c-9469-b6a3a281e2e9',
            '6a3b9f41-894b-4959-a8ac-777c3dfe5f1d',
            'ffa57cd4-6b1b-43b1-b5cd-c85e71456881',
            'a1a2673c-b85a-4545-906b-569b76fff314',
            'cce47ab0-22ac-40f5-ba10-9a221aba117d',
            'ce005158-3916-435d-a1ea-774f6ba4e080',
            '5707732d-4b3f-467d-b52f-799be3058a7f',
            'adc855bd-3321-4789-a63a-705c5a514dd6',
            '564dc0a1-c9e6-4deb-aba8-7d3c04078757',
            '63a7df77-e925-4264-b235-18e54a9f7b26',
            'b3d08cc0-800d-4a49-994a-f961160efebe',
            '9da85617-f38e-407f-a315-aad2cc128c43',
            '414ceb6f-f3e0-4f41-a3c0-508df136c046',
            '3be0cb0a-9757-4b59-8233-4ffb2dfc6836',
            '8469ac6d-d235-412f-9488-df66dc499ca5',
            'b74b3e10-7b0c-45df-9173-d908d10d6a30',
            '94f0f978-1a4b-42b0-98fb-cfb6ce967898',
            '952c36af-0989-4506-8711-999ca058429a',
            'd9eb27fb-4997-4f37-b4fb-0a50713c5d34',
            'bb942523-45d2-4f35-8194-f816144bd209',
            '13dc3771-9c97-4127-b230-57afb41b2425',
            'a1b18c24-6cf1-4a80-9201-29e554aac011',
            'd83f3db0-fe0f-4e9c-9657-8ad9942c2b62',
            '4bb17ee3-368b-4ce7-9e37-b6b706199ab1',
            '4632d1eb-ce2b-47ae-8fa6-032e916c3b30',
            '141e7944-8460-4574-b315-4387fe1fc80f',
            '79796e68-c689-4c39-9f21-9ebca93a260c',
            '102cdc95-3d6a-40f8-a8b9-9c74e84e4cba',
            '84462878-fb96-4466-bc40-06ff8e44f7a9',
            '08a9f7b8-38f8-456c-8bfe-54c1940c9abc',
            '098f0120-ad1b-451e-8766-00bd9be7ee4f',
            '5de3b421-d7ca-4e69-bb9e-ef4dd3953bf6',
            '295a981d-ec44-4b63-b8c0-f35cf4234dc4',
            '071347e8-bb71-4ffc-b0e4-0a43ef689508',
            '994df9ec-e53d-4c7d-836e-f74baadc7007',
            '5b79b8f9-d6b4-4cb1-a480-1d29ae9e727c',
            '6ec40956-861c-4b17-ad38-9780417f5468',
            '52412c40-30b7-4e52-99d6-55e1665f3a30',
            '1feabef9-3155-451a-886c-07e5efe99447',
            '64d43898-14a4-436d-a7aa-e99e84a2560a',
            '3cd9b089-6bf2-4673-a1c0-781f97d75aed',
            '5ba049ec-b9fb-4d2e-ab6e-38b2f97f0ccb',
            '01f5bfdd-4a44-4683-af8f-b7d70f7a949c',
            '5cf87416-e73d-4aeb-b29d-48174a2901cd',
            '6b917afa-78ce-49c1-b5ea-73bbc0db346f',
            'ae008909-ecfb-4806-a1ee-9801c355c732',
            '1d923a32-bfbf-44a8-bc1c-3cfbe64ca03b',
            '1c43dd49-edc9-4718-aab9-811076fb65f1',
            '86f42c22-49f1-4958-982e-c42007f93e5e',
            'a98f36d5-918d-4adb-8205-2b1ac7d251fe',
            'd0cb4fd5-f54f-45b5-a55d-340752c32062',
            '01796311-23f8-49a6-ab87-b8e22b64beb7',
            '0e32f695-5e8b-4ece-8d8e-df80046aafed',
            '8404329e-07b9-4206-9fd4-a159b8e8c230'
        ]

        list_subscription_send = []
        list_ext_tx_id_send = []
        list_exclude = []
        if not config_siebel.blocking:
            transanciones_objects = TransactionsWithNewDate.objects.all()
            for obj_transaction in transanciones_objects:
                list_subscription_send.append(obj_transaction.subscription_id_piano)
                list_ext_tx_id_send.append(obj_transaction.external_tx_id)

            blocked_subscriptions = BlockedSubscriptions.objects.all()
            for blocked_subscription in blocked_subscriptions:
                list_exclude.append(blocked_subscription.subscription_id_piano)

            operation_list = Transaction.objects.filter(
                amount__gte=4,
                subscription__payment_profile__siebel_entecode__isnull=False,
                subscription__payment_profile__siebel_entedireccion__isnull=False
            ).exclude(initial_payment=True).exclude(siebel_renovation__state=True) \
                .exclude(subscription__locked=True) \
                .exclude(block_sending=True) \
                .exclude(devolution=True).filter(payu_transaction_id__in=list_to_send).exclude(subscription_id_str__in=list_exclude)

            if options.get('filter_elements', ''):
                operation_list = operation_list[:int(options.get('filter_elements'))]
            else:
                operation_list = operation_list.order_by('payment_date')

            if options.get('print_log', ''):
                with open('/tmp/log_ext_tx_id' + str(int(ts)) + '.csv', 'a', encoding="utf-8") as csvFile:
                    writer = csv.writer(csvFile)
                    for operation in operation_list:
                        writer.writerow([operation.external_tx_id])

            for operation in operation_list:
                if operation.subscription.delivery and self.validation(operation):
                    if self.valid_last_payment_arc(
                            operation.subscription.subscription_id) and self.valid_last_payment(
                        operation) and not SiebelConfirmationPayment.objects.filter(
                            num_liquidacion=operation.payu_transaction_id).exists():  # verifica que aya un pago anterior
                        siebel_client = SiebelConciliationSender(operation, test_mode)
                        try:
                            print('Iniciando external_tx_id: {operation_id}'.format(
                                operation_id=operation.external_tx_id))
                            if operation.external_tx_id in list_ext_tx_id_send:
                                try:
                                    obj_t = TransactionsWithNewDate.objects.get(
                                        external_tx_id=operation.external_tx_id,
                                        subscription_id_piano=operation.subscription.subscription_id
                                    )
                                except:
                                    continue
                                siebel_client.renovation_send(obj_t.access_from, obj_t.access_to)
                            else:
                                siebel_client.renovation_send(None, None)
                        except Exception:
                            capture_exception()

        print('Termino la ejecucion del comando')
