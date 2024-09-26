from base64 import b64decode
import datetime

from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import MPPToDhwSerializer, MPPToDhwUserDesactivateSerializer
from apps.ecoid.models.mpp_to_dwh import DmpToDhw
from apps.ecoid.utils import generate_dmp_hash_v2


user = 'jhon'
pw = '123456'

HTTP_HEADER_ENCODING = 'iso-8859-1'


def get_authorization_header(request):
    """
    Return request's 'Authorization:' header, as a bytestring.

    Hide some test client ickyness where the header can be unicode.
    """
    auth = request.META.get('HTTP_AUTHORIZATION', b'')
    if isinstance(auth, type('')):
        # Work around django test client oddness
        auth = auth.encode(HTTP_HEADER_ENCODING)
    return auth


def authentication(request):

    try:
        auth = get_authorization_header(request)
        auth = auth.split(' ')[1]
        try:
            auth.decode()
        except UnicodeError:
            return 'error'

        username, password = b64decode(auth).decode().split(':', 1)
        if username == user and password == pw:
            return True
        return False
    except Exception, e:
        return 'otro error' + e.message


@csrf_exempt
def accounts_transform_to_datamanagemend(request):

    if authentication(request):
        if request.method.upper() == 'POST':
            myfile = request.FILES.get('myfile')
            if myfile:
                myfile_readed = myfile.read().decode("utf-8-sig").encode("utf-8")
                convert_to_list(myfile_readed)
            else:
                myfile_readed = request.body.decode("utf-8-sig").encode("utf-8")
                convert_to_list(myfile_readed)
            return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'fail'})


def convert_to_list(myfile_readed):
    """
    sConvierte lo recibido por el API, en un diccionario
    :param myfile_readed:
    :return:
    """
    myfile_list = myfile_readed.splitlines()
    head_line = get_head_line(myfile_list)
    list_data = []
    list_data = align_data(myfile_list, head_line, list_data)
    list_data = replace_and_quit_fields(list_data)
    i = 0

    for keys_field_dwh in get_order_fields_dwh():

        for ld in list_data:
            keys_list_data = ld.keys()
            if keys_field_dwh not in keys_list_data:
                ld[keys_field_dwh] = ''

            i = id_tmp_user_proccess(ld, keys_field_dwh, i)
            date_snapshot_proccess(ld, keys_field_dwh)
            domain_proccess(ld, keys_field_dwh)

            dmp_hash_proccess(ld, keys_field_dwh)
            dmp_hash_eco_id(ld, keys_field_dwh)
            if 'AccountStatus' in ld:
                accountstatus_for_proccess(ld, 'AccountStatus')

    save_row(list_data)


def save_row(list_data):
    for x in list_data:
        if x.has_key('register_date'):
            x['register_date'] = datetime.datetime.strptime(x['register_date'], '%Y-%m-%d  %H:%M:%S')
        if x.has_key('birth_date'):
            if not x['birth_date']:
                x['birth_date'] = datetime.datetime(1900, 01, 01)
            else:
                x['birth_date'] = datetime.datetime.strptime(x['birth_date'].split(' ')[0], '%Y-%m-%d').date()
        if x.has_key('last_login'):
            if not x['last_login']:
                x['last_login'] = datetime.datetime(1900, 01, 01, 00, 00, 00)
            else:
                x['last_login'] = datetime.datetime.strptime(x['last_login'],
                                                             '%Y-%m-%d %H:%M:%S')
        if x.has_key('high_date'):
            if not x['high_date']:
                x['high_date'] = datetime.datetime(1900, 01, 01, 00, 00, 00)
            else:
                x['high_date'] = datetime.datetime.strptime(x['high_date'],
                                                            '%Y-%m-%d %H:%M:%S')
        if x.has_key('low_date'):
            if not x['low_date']:
                x['low_date'] = datetime.datetime(1900, 01, 01, 00, 00, 00)
            else:
                x['low_date'] = datetime.datetime.strptime(x['low_date'],
                                                           '%Y-%m-%d %H:%M:%S')

        if x.has_key('update_datetime'):
            if not x['update_datetime']:
                x['update_datetime'] = datetime.datetime(1900, 01, 01, 00, 00, 00)
            else:
                x['update_datetime'] = datetime.datetime.strptime(x['update_datetime'],
                                                                  '%Y-%m-%d %H:%M:%S')
        if x.has_key('update_last'):
            if not x['update_last']:
                x['update_last'] = datetime.datetime(1900, 01, 01, 00, 00, 00)
            else:
                x['update_last'] = datetime.datetime.strptime(x['update_last'],
                                                              '%Y-%m-%d %H:%M:%S')

        if x.has_key('privacy_accepted_date'):
            if not x['privacy_accepted_date']:
                x['privacy_accepted_date'] = datetime.datetime(1900, 01, 01)
            else:
                x['privacy_accepted_date'] = datetime.datetime.strptime(x['privacy_accepted_date'],
                                                                        '%Y-%m-%d')

        if x.has_key('tyc_accepted_date'):
            if not x['tyc_accepted_date']:
                x['tyc_accepted_date'] = datetime.datetime(1900, 01, 01)
            else:
                x['tyc_accepted_date'] = datetime.datetime.strptime(x['tyc_accepted_date'],
                                                                    '%Y-%m-%d')

        DmpToDhw.objects.update_or_create(
            idx=x['idx'],
            defaults=x,
        )


def align_data(myfile_list, head_line, list_data):
    """
    Alinea la data, como primer paso
    :param list_data:
    :param head_line:
    :return:
    """
    for mfl in myfile_list[1:]:
        mfl = quit_quote_double(mfl)
        list_data.append(
            # dict(zip(head_line, mfl.split(',')))
            dict(zip(head_line, mfl))
        )
    return list_data


def replace_and_quit_fields(list_data):
    for ld in list_data:
        keys = ld.keys()
        for k in keys:
            _relation_field_mpp_dwh = get_relation_field_mpp_dwh(k)
            if _relation_field_mpp_dwh is not None:
                # reemplaza los campos  que son equivalentes
                ld[_relation_field_mpp_dwh] = ld.pop(k)
                # print _relation_field_mpp_dwh
            else:
                if k != 'AccountStatus':
                    ld.pop(k)

    return list_data


def quit_quote_double(list):
    """
    Quita las comillas dobles en los valores
    :param list:
    :return:
    """
    mfl_list = list.split(',')
    mfl = [m.replace('"', '') for m in mfl_list]
    return mfl

##############################
# procesos para los campos
###########################


def domain_proccess(data, key_field_dwh):
    domain = ''
    if key_field_dwh == 'site':
        domain_dict = {
            'gestion': 1,
            'peru21.pe': 2,
            'peru.com': 3,
            'trome.pe': 4,
            'publimetro.pe': 5,
            'depor.pe': 6,
            'elcomercio': 7,
            'menuperu.elcomercio.pe': 8,
            'suscripciones.elcomercio.pe': 9,
            'mujerpandora.com': 10,
            'elbocon.pe': 11,
            'diariocorreo.pe': 12,
            'ojo.pe': 13,
            'elshow.pe': 14,
            'pwa.elcomercio.pe': 15,
            'suscripciones.gestion.pe': 16,
        }
        domain = domain_dict.get(data[key_field_dwh])
        data['site'] = domain
    return domain


def low_date_proccess(data, key_field_dwh):
    if key_field_dwh == 'low_date':
        pass


def accountstatus_for_proccess(data, key_field_dwh):
    """
    Crea el campo high en base a los valores de AccountStatus de esuite
    :param data:
    :param key_field_dwh:
    :return:
    """
    # print key_field_dwh

    if key_field_dwh == 'AccountStatus':
        if data[key_field_dwh] == 'Activated':
            data['high'] = True
        if data[key_field_dwh] == 'Closed':
            data['low'] = True
        data.pop(key_field_dwh)


def id_tmp_user_proccess(data, key_field_dwh, i):
    """
    Autogenera un ID
    :param data:
    :param key_field_dwh:
    :param i:
    :return:
    """
    if key_field_dwh == 'id_tmp_user':
        i = i + 1
        data[key_field_dwh] = i
    return i


def date_snapshot_proccess(data, key_field_dwh):
    """
    Devuelve la fecha de proceso
    :param data:
    :param key_field_dwh:
    :return:
    """
    # print key_field_dwh
    if key_field_dwh == 'date_snapshot':
        data[key_field_dwh] = datetime.datetime.now().date().strftime('%Y-%m-%d')


def id_document_proccess(data, key_field_dwh):

    if key_field_dwh == 'id_document':
        pass


def dmp_hash_proccess(data, key_field_dwh):
    if key_field_dwh == 'dmp_hash':
        email = data.get('email')
        data['dmp_hash'] = generate_dmp_hash_v2(email)


def dmp_hash_eco_id(data, key_field_dwh):
    if key_field_dwh == 'idx':
        data['eco_id'] = data.get('idx')


################################
# fin procesos para los campos
###############################

def get_head_line(myfile_list):
    """
    Obtiene la fila que contiene las cabeceras
    :param myfile_lines:
    :return:
    """

    head_line = myfile_list[0].split(',')

    head_line = [hl.replace('"', '') for hl in head_line]
    # head_line_for_dwh = [get_relation_field_mpp_dwh(hl) for hl in head_line]

    # quita las comillas dobles que tiene cada nombre de campo

    # head_line = json.dumps(head_line)
    return head_line
    # return head_line_for_dwh


def relation_field_mpp_dwh():
    # campo MPP - campo para DWH
    head_relation = {
        'AccountId': 'idx',
        'CreateDate': 'register_date',
        'FirstName': 'first_name',
        'lastNameM': 'last_name_f',
        'lastNameF': 'last_name_m',
        'NickName': 'username',
        'Surname': 'last_name',
        'dni': 'dni',
        'DateOfBirth': 'birth_date',
        'MobilePhoneNumber': 'cellphone',
        'HomePhoneNumber': 'phone',
        'civilstatus': 'civilstatus',
        'Sex': 'gender',
        'NoMarketingInformation': 'newsletter',
        'EmailAddress': 'email',
        'type_source': 'source',  # revisar
        'last_login': 'last_login',  # averiguar de donde sacar este dato https://support.mppglobal.com/product/module-documentation/reporting/esuite-user-authentication-data-feed-specification/
        'low_date': 'low_date',  # averiguar como poner la fecha de baja
        'high_date': 'high_date',  # no hay fecha de alta
        'token_activate': 'token_activate',
        'migration': 'migration',
        'migration_done': 'migration_done',
        'domain': 'site',
        'accessType': 'type',
        'AccountStatus': None,
        'LastUpdated': 'update_datetime',
        'HomeCountry': 'country',
        'socialId': 'social_id',
        # dmp_hash lo creamos en la extraccion de datos, desde aqui el backend

        # 'AccountStatus': ['high', 'low'],
    }
    return head_relation


def get_relation_field_mpp_dwh(key):
    # if key == 'AccountStatus':

    return relation_field_mpp_dwh().get(key, None)


def field_aditionals(head_relation):
    pass


def get_order_fields_dwh():
    order_fields_dwh = [
        "idx",
        "first_name",
        "last_name",
        "last_name_f",
        "last_name_m",
        "email",
        "username",
        "register_date",
        "last_login",
        "high_date",
        "low_date",
        "low",
        "high",
        "newsletter",
        "token_activate",
        "migration",
        "migration_done",
        "estado",
        "type",
        "site",
        "nickname",
        "source",
        "dni",
        "birth_date",
        "birth_year",
        "gender",
        "civilstatus",
        "country",
        "city",
        "direction",
        "postalcode",
        "cellphone",
        "phone",
        "avatar",
        "avatar_50",
        "update_datetime",
        "update_last",
        "version",
        "term_conditions",
        "social_id",
        "eco_id",
        "privacy_version",
        "privacy_accepted_date",
        "tyc_version",
        "tyc_accepted_date",
        "device",
        "section",
        "dmp_hash",
    ]
    return order_fields_dwh


class DataWarehouseAPIView(APIView):

    serializer = MPPToDhwSerializer
    items_per_page = 2000

    def _check_date(self, _date):
        try:
            return datetime.datetime.strptime(_date, "%Y-%m-%d").date()
        except Exception:
            pass
        return False

    def get(self, request, *args, **kwargs):
        page = request.GET.get('page')
        queryset = self.get_queryset(request, *args, **kwargs)

        if page:
            page = int(page)
            end_item = page * self.items_page
            if page == 1:
                start_item = 0
            else:
                start_item = (page - 1) * self.items_page
            queryset = queryset[start_item:end_item]

        result = self.serializer(queryset, many=True)
        return Response(result.data)

    def get_queryset(self, request, *args, **kwargs):

        site_key = kwargs.get('site_key')

        site_name = self.get_site_name(site_key)

        queryset = DmpToDhw.objects.filter(site_name=site_name)
        date_start = request.GET.get('date_start')
        date_end = request.GET.get('date_end')

        if date_start and date_end:
            if self._check_date(date_start) and self._check_date(date_end):
                queryset = queryset.filter(
                    Q(register_date__date__range=(date_start, date_end)) |
                    Q(update_datetime__date__range=(date_start, date_end)) |
                    Q(datawarehouse_sync=False)
                )
        return queryset

    def get_site_name(self, site_key):

        site_key_dict = {
            '108f85a3d8e750a325ced951af6cd758a90e73a34': 'gestion',  # gestion
            'f7bd562ca9912019255511635185bf2b': '2',  # peru21
            '67d8d54bf6861b19e505687672529907': '3',  # perucom
            '4895ff32853e4dd68b5bd63c6437d17c': '4',  # trome
            '359a5aad94014ded10626b607e426e93': '5',  # publimetro
            '6d83b35ec628d33d0606bcd9083dc2a6': '6',  # depor
            'a94a8fe5ccb19ba61c4c0873d391e987982fbbd3': 'elcomercio',  # EC
            'ccf63727b54ea4998c164a2b69639582': '8',  # menuperu
            '1d83b35ec628d22d0606bcd9083dc2a1': '9',  # suscripciones
            'e858ab7558f5a80a8e2d2370f56b518c': '10',  # mujerpandora
            'dcd90a2190d1682f39d41a4889a1cc57': '11',  # elbocon
            '547a1802dfdcaa443d08c92c8dac62e9': '12',  # diariocorreo
            'r2tbzg902jxaq6c0tmc2zr6txgzfzmiy': '13',  # ojo
            'u47nvo3i3z7tbrufs5rbvsg10ec3bjdj': '14',  # elshow
            'dcs90a2190d1682f39d41a4880a1cc51': '15',  # pwa
            '35ec628d2072d0606bcd9083dc2a1zs21': '16',  # suscripciones gestion
        }
        return site_key_dict.get(site_key, '')


class DataWarehouseDownAPIView(DataWarehouseAPIView):

    serializer = MPPToDhwUserDesactivateSerializer

    def get_queryset(self, request, *args, **kwargs):
        site_key = kwargs.get('site_key')

        domain = self.site_key_to_domain(site_key)

        ssouser = DmpToDhw.objects.filter(site=domain, high=True, low=True)
        date_start = request.GET.get('date_start')
        date_end = request.GET.get('date_end')

        if date_start and date_end:
            if self._check_date(date_start) and self._check_date(date_end):
                ssouser = ssouser.filter(Q(register_date__date__range=(date_start, date_end)) |
                                         Q(update_datetime__date__range=(date_start, date_end)))

        return ssouser
