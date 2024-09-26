from django.db import connection
from sentry_sdk import capture_exception


class reg(object):
    def __init__(self, cursor, registro):
        for (attr, val) in zip((d[0] for d in cursor.description), registro):
            setattr(self, attr, val)


def execute_query(query):
    with connection.cursor() as cursor:
        rows = []
        try:
            cursor.execute(query)

        except Exception:
            capture_exception()

        else:
            for row in cursor.fetchall():
                rows.append(reg(cursor, row))

        return rows


def execute_query_club(query):
    with connection['club'].cursor() as cursor:
        rows = []
        try:
            cursor.execute(query)

        except Exception:
            capture_exception()

        else:
            for row in cursor.fetchall():
                rows.append(reg(cursor, row))

        return rows


def MPP_clientePendSiebel():
    """
        Retorna los clientes pendientes para Siebel, limitados por el npumero de intentos.
    """
    return execute_query("""
        select t2.id pago_id,
            t3.id ppago_id,
            coalesce(trim(t3.ppago_apemat),'') ppago_apemat,
            coalesce(trim(t3.ppago_apepat),'') ppago_apepat,
            t3.ppago_fecnac ppago_fecnac,
            coalesce(trim(t3.ppago_nombre),'') ppago_nombre,
            t3.ppago_genero ppago_genero,
            t3.ppago_tipo ppago_tipo,
            t3.ppago_numdoc ppago_numdoc,
            upper(t3.ppago_tipodoc) ppago_tipodoc,
            t3.ppago_email ppago_email,
            t3.ppago_telefono ppago_telefono,
            t3.siebel_entecode ppago_siebel_entecode,
            t3.siebel_nombre ppago_siebel_nombre,

            t3.id ppago_parent_id,
            coalesce(trim(t3.ppago_apemat),'') ppagop_apemat,
            coalesce(trim(t3.ppago_apepat),'') ppagop_apepat,
            t3.ppago_fecnac ppagop_fecnac,
            coalesce(trim(t3.ppago_nombre),'') ppagop_nombre,
            t3.ppago_genero ppagop_genero,
            t3.ppago_tipo ppagop_tipo,
            t3.ppago_numdoc ppagop_numdoc,
            upper(t3.ppago_tipodoc) ppagop_tipodoc,
            t3.ppago_email ppagop_email,
            t3.siebel_entecode ppagop_siebel_entecode,
            t3.siebel_nombre ppagop_siebel_nombre,
            t3.siebel_estado ppagop_siebel_estado,
            t3.siebel_estado ppago_siebel_estado,
            t2.pa_tipo_recibo
        from paywall_pago t2 join paywall_suscription on t2.suscripcion_id = paywall_suscription.id
            join paywall_perfilpago t3 on t3.id = paywall_suscription.perfil_pago_id
            limit 10;
    """)


def Club_Suscriptor_Siebel():
    """
        Retorna los clientes pendientes para Siebel, limitados por el npumero de intentos.
    """
    return execute_query_club("""
        select * from t_suscriptor;
    """)


# cursor = connections['db_alias'].cursor()
# cursor.execute("select * from my_table")
