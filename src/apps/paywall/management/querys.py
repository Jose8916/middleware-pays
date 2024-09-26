# coding=utf-8

from .connection import ConnectionDatabase


class reg(object):
    def __init__(self, cursor, registro):
        for (attr, val) in zip((d[0] for d in cursor.description), registro):
            setattr(self, attr, val)


def get_clients_pending():
    # Retorna los clientes pendientes para Siebel, limitados por el npumero de intentos.

    try:
        db_cursor = ConnectionDatabase.connect_cursor()

        db_cursor.execute("""
            select
            t1.id,prof_name,prof_lastname,prof_lastname_mother,prof_doc_type,prof_doc_num,
            prof_phone,portal_email
            from paywall_paymentprofile t1
            where t1.state = true and siebel_state = false
            limit 20;
        """)

        rows = []
        for row in db_cursor.fetchall():
            rows.append(reg(db_cursor, row))

        response = {'status': True, 'data': rows}
    except Exception as e:
        print(e.message)
        response = {'status': False, 'message': e.message}

    return response


def get_operations_pending():
    # Retorna los clientes pendientes para Siebel, limitados por el npumero de intentos.

    try:
        db_cursor = ConnectionDatabase.connect_cursor()

        #  and t6.siebel_state = true and t6.siebel_entecode is not null
        db_cursor.execute("""
            select
            t1.id, ope_amount,plan_desc,
            date_payment,arc_order,payu_order,payu_transaction,
            t4.siebel_code as prod_siebel_code, t4.siebel_name as prod_siebel_name,
            t5.siebel_code as rate_siebel_code, t5.rate_neto, t5.rate_igv, t5.rate_total,
            t6.siebel_entecode as profile_siebel_entecode, t6.siebel_name as profile_siebel_name
            from paywall_operation t1
            inner join paywall_payment t2 on t1.pa_id = t2.id
            inner join paywall_plan t3 on t1.plan_id = t3.id
            inner join paywall_products t4 on t3.prod_id = t4.id
            inner join siebel_rate t5 on t3.rate_id = t5.id
            inner join paywall_paymentprofile t6 on t2.payment_profile_id = t6.id
            where t2.state = 1 and t1.state = 1 and t1.siebel_state = false
            and t2.pa_origin = 'WEB'
            limit 20;
        """)

        rows = []
        for row in db_cursor.fetchall():
            rows.append(reg(db_cursor, row))

        response = {'status': True, 'data': rows}
    except Exception as e:
        print(e.message)
        response = {'status': False, 'message': e.message}

    return response
