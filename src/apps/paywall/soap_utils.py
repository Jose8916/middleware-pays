import requests
import time
import xmltodict

from django.conf import settings


class soap(object):
    tab = ''

    @staticmethod
    def fn_coalesce(s, d):
        if s:
            return s
        else:
            return d

    @staticmethod
    def getxml(allns):
        xmlns = ''
        for ns in allns:
            # print allns[ns]['url']
            xmlns += """ xmlns:%s="%s" """ % (allns[ns]['prefix'], allns[ns]['url'])
        # sys.exit()
        xopen = ""
        xclose = ""
        xopen += """<?xml version="1.0" encoding="UTF-8"?>
            <soapenv:Envelope %s >
                <soapenv:Header/>
                <soapenv:Body>
                """ % (xmlns,)
        xclose += """</soapenv:Body>
        </soapenv:Envelope>
        """
        body = {'xopen': xopen, 'xclose': xclose}
        return body

    @staticmethod
    def getbloques(bloques):
        xbloqueOpen = ''
        xbloqueClose = ''
        for bloque in bloques:
            # xbloqueOpen += """<%s>""" % (bloque)
            # xbloqueClose = """</%s>%s""" % (bloque,xbloqueClose)

            xbloqueOpen += """
            """ + soap.tab + """<%s>""" % (bloque)
            xbloqueClose = """
            """ + soap.tab + """</%s>%s""" % (bloque, xbloqueClose)
            soap.tab += """\t"""
        return {'bloqueOpen': xbloqueOpen, 'bloqueClose': xbloqueClose}

    @staticmethod
    def getrow(fields):
        xbody = ''
        for key, value in fields.items():
            # xbody += """<%s>%s</%s>""" % (key,value,key)
            xbody += """
            """ + soap.tab + """<%s>%s</%s>""" % (key, value, key)
        return xbody

    @staticmethod
    def removetilde(cad):
        cad = cad.replace('Á', 'A')
        cad = cad.replace('É', 'E')
        cad = cad.replace('Í', 'I')
        cad = cad.replace('Ó', 'O')
        cad = cad.replace('Ú', 'U')
        cad = cad.replace('á', 'A')
        cad = cad.replace('é', 'E')
        cad = cad.replace('í', 'I')
        cad = cad.replace('ó', 'O')
        cad = cad.replace('ú', 'U')
        cad = cad.replace('ñ', 'Ñ')
        return cad

    @staticmethod
    def prepareConciliacion(fields):
        xml = ''
        bloquesClose = ''
        allns = {
            0: {'prefix': 'soapenv', 'url': 'http://schemas.xmlsoap.org/soap/envelope/'},
            1: {'prefix': 'tem', 'url': 'http://tempuri.org/'},
        }
        xbody = soap.getxml(allns)
        xbloques = [
            'tem:CobrosRecibidos',
        ]

        xml += xbody['xopen']
        xbloques = soap.getbloques(xbloques)
        xml += xbloques['bloqueOpen']
        xml += soap.getrow(fields['xdata'])
        bloquesClose = xbloques['bloqueClose'] + xbody['xclose']
        xml += bloquesClose
        return xml

    @staticmethod
    def sendConciliacion(xml):
        url = str(settings.PAYWALL_SIEBEL_IP) + '/WSSOLCobrosRecibidos/wsCobrosRecibidos.asmx?wsdl'

        headers = {'content-type': 'text/xml; charset=utf-8'}
        resp = requests.post(url, data=xml, headers=headers)

        xvalresp = 1
        Cod_Response = ''
        resptc = ''

        xresp = xmltodict.parse(resp.content)
        Cod_Response = xresp['soap:Envelope']['soap:Body']['CobrosRecibidosResponse']['CobrosRecibidosResult']['Cod_Response']
        if int(Cod_Response) != 1:
            xvalresp = 0

        response = {
            'valresp': xvalresp,
            'Cod_Response': Cod_Response,
            'resp': resp.content,
            'resptc': resptc,
        }
        return response

    @staticmethod
    def prepareCC(fields):
        xml = ''
        bloquesClose = ''
        allns = {
            0: {'prefix': 'soapenv', 'url': 'http://www.w3.org/2003/05/soap-envelope'},
            1: {'prefix': 'tem', 'url': 'http://tempuri.org/'},
            2: {'prefix': 'eco', 'url': 'http://www.siebel.com/xml/ECO%20Account%20Interface%20w%20Address'}
        }
        xbody = soap.getxml(allns)
        xbloques = [
            'tem:CrearCliente',
            'tem:objCrearCliente_Input',
            'eco:ListOfEcoAccountInterfaceWAddress2',
            'eco:Account',
        ]

        xbloques2 = [
            'eco:ListOfCutAddress',
            'eco:CutAddress',
        ]
        xml += xbody['xopen']
        xbloques = soap.getbloques(xbloques)
        xml += xbloques['bloqueOpen']
        xml += soap.getrow(fields['Account'])
        xbloques2 = soap.getbloques(xbloques2)
        xml += xbloques2['bloqueOpen']
        for address in fields['CutAddress']:
            xml += soap.getrow(fields['CutAddress'][address])
        bloquesClose = xbloques2['bloqueClose'] + xbloques['bloqueClose'] + xbody['xclose']
        xml += bloquesClose
        return soap.removetilde(xml)

    @staticmethod
    def alertaError(xtitle, xrow, xml, response):
        xcbody = ''
        xcbody = """<table cellpadding="0" cellspacing="0" border="0" align="center">
            <tr>
            <td colspan="2" style="padding:10px;"><h4>Proceso de %s respondio con error</h4></td>
            </tr>
            <tr>
            <td height="30" width="100" style="padding:10px;">Perfil Pago Id:</td>
            <td style="padding:10px;">%s</td>
            </tr>
            <tr>
            <td height="30" width="100" style="padding:10px;">Operación Id:</td>
            <td style="padding:10px;">%s</td>
            </tr>
            </table>
            <br><br><h2>REQUEST</h2>
            %s
            <br><br><br><h2>RESPONSE</h2>
            %s
            """ % (
            xtitle,
            xrow.ppago_id,
            xrow.ope_id,
            xml,
            str(response)
        )
        return xcbody

    @staticmethod
    def alertaErrorCC(xrow, xml, response):
        xcbody = ''
        xcbody = """<table cellpadding="0" cellspacing="0" border="0" align="center">
            <tr>
            <td colspan="2" style="padding:10px;"><h4>Proceso de Siebel CrearCliente respondio con error</h4></td>
            </tr>
            <tr>
            <td height="30" width="100" style="padding:10px;">Perfil Pago Id:</td>
            <td style="padding:10px;">%s</td>
            </tr>
            <tr>
            <td height="30" width="100" style="padding:10px;">Operación Id:</td>
            <td style="padding:10px;">%s</td>
            </tr>
            <tr>
            <td height="30" width="100" style="padding:10px;">Usuario:</td>
            <td style="padding:10px;">%s</td>
            </tr>
            </table>
            <br><br><h2>REQUEST</h2>
            %s
            <br><br><br><h2>RESPONSE</h2>
            %s
            """ % (
            xrow.ppago_id,
            xrow.ope_id,
            xrow.ppago_apepat.upper() + ' ' + xrow.ppago_apemat.upper() + ', ' + xrow.ppago_nombre.upper(),
            xml,
            str(response)
        )
        return xcbody

    @staticmethod
    def alertaErrorCOV(xname, xrow, xml, response):
        xcbody = ''
        xcbody = """<table cellpadding="0" cellspacing="0" border="0" align="center">
            <tr>
            <td colspan="2" style="padding:10px;"><h4>Proceso de Siebel CrearOV respondio con error</h4></td>
            </tr>
            <tr>
            <td height="30" width="100" style="padding:10px;">Perfil Pago Id:</td>
            <td style="padding:10px;">%s</td>
            </tr>
            <tr>
            <td height="30" width="100" style="padding:10px;">Operación Id:</td>
            <td style="padding:10px;">%s</td>
            </tr>
            <tr>
            <td height="30" width="100" style="padding:10px;">Usuario:</td>
            <td style="padding:10px;">%s</td>
            </tr>
            </table>
            <br><br><h2>REQUEST</h2>
            %s
            <br><br><br><h2>RESPONSE</h2>
            %s
            """ % (
            xrow.ppago_id,
            xrow.ope_id,
            xname.upper(),
            xml,
            str(response)
        )
        return xcbody

    @staticmethod
    def prepareCOV(fields):
        xml = ''
        bloquesClose = ''
        allns = {
            0: {'prefix': 'soapenv', 'url': 'http://www.w3.org/2003/05/soap-envelope'},
            1: {'prefix': 'tem', 'url': 'http://tempuri.org/'},
            2: {'prefix': 'eco', 'url': 'http://www.siebel.com/xml/ECO%20Order%20Entry%20(Sales)%20Lite'}
        }
        xbody = soap.getxml(allns)

        xml += xbody['xopen']
        xbloques = [
            'tem:CrearOV',
            'tem:objCrearOV_Input',
            'eco:ListOfEcoOrderEntrySalesLite2',
            'eco:OrderEntry-Orders',
        ]
        xbloques = soap.getbloques(xbloques)
        xml += xbloques['bloqueOpen']
        xml += soap.getrow(fields['OrderEntry-Orders'])

        xbloques2 = soap.getbloques(['eco:ListOfOrderEntry-LineItems', ])
        xml += xbloques2['bloqueOpen']

        for oe_litem in fields['OrderEntry-LineItems']:
            xbloques2children = soap.getbloques(['eco:OrderEntry-LineItems', ])
            xml += xbloques2children['bloqueOpen']
            xml += soap.getrow(oe_litem)
            xml += xbloques2children['bloqueClose']
        bloquesClose = xbloques2['bloqueClose']
        xml += bloquesClose

        xbloques3 = [
            'eco:ListOfPayments',
            'eco:Payments'
        ]
        xbloques3 = soap.getbloques(xbloques3)
        xml += xbloques3['bloqueOpen']
        xml += soap.getrow(fields['xPayments'])
        bloquesClose = xbloques3['bloqueClose']
        xml += bloquesClose

        bloquesClose = xbloques['bloqueClose']
        bloquesClose += xbody['xclose']
        xml += bloquesClose
        # print xml
        # sys.exit()
        xml = soap.removetilde(xml)
        xml = xml.replace('ECModoRenovacion>AutomAtica', 'ECModoRenovacion>Automática')
        return xml

    @staticmethod
    def notifyOV(xname, xrow, response):
        xnow_current = str(time.strftime("%d-%m-%Y %H:%M:%S"))
        xcbody = ''
        xcbody = """<table cellpadding="0" cellspacing="0" border="0" align="center">
            <tr>
            <td colspan="2" style="padding:10px;"><h4>Se procesó la siguiente orden</h4></td>
            </tr>
            <tr>
            <td height="30" width="100" style="padding:10px;">Usuario:</td>
            <td style="padding:10px;">%s</td>
            </tr>
             <tr>
            <td height="30" width="100" style="padding:10px;">Fecha:</td>
            <td style="padding:10px;">%s</td>
            </tr>
            <tr>
            <td height="30" width="100" style="padding:10px;">Delivery:</td>
            <td style="padding:10px;">%s</td>
            </tr>
            <tr>
            <td height="30" width="100" style="padding:10px;">Entecode:</td>
            <td style="padding:10px;">%s</td>
            </tr>
            </table>""" % (
            xname.upper(),
            str(xnow_current),
            response['IdDelivery'],
            xrow.ppago_siebel_entecode
        )
        return xcbody
