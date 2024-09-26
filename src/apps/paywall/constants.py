SITE_CHOICES = (
    ('elcomercio', 'El Comercio'),
    ('gestion', 'Gestión'),
    ('peru21', 'Perú21'),
)

DATA_LOADED_CHOICES = (
    (None, 'Pendiente'),
    (True, 'Completa'),
    (False, 'Incompleta'),
)

DOC_TYPE = (
    ('DNI', 'DNI'),
    ('RUC', 'RUC'),
    ('CEX', 'Carné extranjeria'),
    ('CDI', 'Carné de diplomático'),
    ('PAS', 'Pasaporte'),
    ('OTRO', 'OTRO'),
)

TIPOPER = (
    ('N', 'Natural'),
    ('J', 'Juridico'),
)
TIPOESTADO = (
    (1, 'Activo'),
    (0, 'Inactivo'),
)
TIPOESTADOCONCILIACION = (
    (1, 'Activo'),
    (0, 'Inactivo'),
    (2, 'Histórico'),
)
ESTADO_PEDIDO = (
    (0, 'Pendiente'),
    (1, 'Vendido'),
    (2, 'Anulado'),
)
TIPO_VENTA = (
    (1, 'Suscripciones'),
    (2, 'Producto'),
)
TIPOESTADO_ENVIO = (
    (1, 'Preparado'),
    (0, 'No preparado'),
)
SERV_OBJECT = (
    ('SIEBEL_CC', 'SIEBEL CC'),
    ('SIEBEL_OV', 'SIEBEL OV'),
    ('PQ', 'PQ'),
    ('CLUB', 'CLUB'),
    ('RECURRENCIA', 'RECURRENCIA'),
)
ESTADO_SERVICE = (
    (0, 'Pendiente'),
    (1, 'Ok'),
    (2, 'Error'),
    (3, 'Error alarmante'),
)

MICUENTA_CHOICES = ((1, 'Suscripcion Propia'), (0, 'Suscripcion a terceros'),)
SEXO_CHOICES = (('M', 'Masculino'), ('F', 'Femenino'),)
RENOVACION_CHOICES = ((1, 'Activo'), (0, 'Inactivo'),)

TIPDIR_CHOICES = (
    ('via', 'Via'),
    ('urbanizacion', 'Urbanizacion'),
)
TIPO_DETENTREGA = (
    ('', 'Seleccione opción'),
    ('vigilante', 'Al vigilante'),
    ('buzon', 'Buzón'),
    ('debajo-cochera', 'Debajo de puerta de cochera'),
    ('debajo-principal', 'Debajo puerta principal'),
    ('recepcion', 'Recepción'),
)

"""TIPO_ECTipoDptoPisoIntNom = (
    ('CHALET','CHALET'),
    ('DPTO.','DPTO.'),
    ('ESCUELA','ESCUELA'),
    ('INTERIOR','INTERIOR'),
    ('OFICINA','OFICINA'),
    ('PISO','PISO'),
    ('TIENDA','TIENDA'),
)"""

TIPO_ECCodigoDptoPisoInt = (
    ('CH', 'CHALET'),
    ('D', 'DPTO.'),
    ('E', 'ESCUELA'),
    ('I', 'INTERIOR'),
    ('O', 'OFICINA'),
    ('P', 'PISO'),
    ('TIENDA', 'TIENDA'),
)
"""TIPO_ECTipoEtapaSectorNom = (
    ('AGRUPACION','AGRUPACION'),
    ('AMPLIACION','AMPLIACION'),
    ('BARRIO','BARRIO'),
    ('BLOCK','BLOCK'),
    ('CASA','CASA'),
    ('COMITÉ','COMITÉ'),
    ('CUADRA','CUADRA'),
    ('EDIFICIO','EDIFICIO'),
    ('ETAPA','ETAPA'),
    ('FACULTAD','FACULTAD'),
    ('GRUPO','GRUPO'),
    ('LOTIZACION','LOTIZACION'),
    ('PARCELA','PARCELA'),
    ('SECTOR','SECTOR'),
    ('TORRE','TORRE'),
    ('ZONA','ZONA'),
    ('ZONA INDUSTRIAL','ZONA INDUSTRIAL'),
)"""
TIPO_ECTipoEtapaSectorCod = (
    ('AG', 'AGRUPACION'),
    ('AM', 'AMPLIACION'),
    ('BA', 'BARRIO'),
    ('B', 'BLOCK'),
    ('C', 'CASA'),
    ('CO', 'COMITÉ'),
    ('CU', 'CUADRA'),
    ('D', 'EDIFICIO'),
    ('E', 'ETAPA'),
    ('F', 'FACULTAD'),
    ('GR', 'GRUPO'),
    ('LT', 'LOTIZACION'),
    ('PA', 'PARCELA'),
    ('S', 'SECTOR'),
    ('T', 'TORRE'),
    ('Z', 'ZONA'),
    ('ZI', 'ZONA INDUSTRIAL'),
)
CONCILIACIONES = (
    ('WEB', 'WEB'),
    ('RECURRENCIA', 'RECURRENCIA'),
)

COLLABORATORS_ACTION = (
    ('ERROR_UUID', 'Sin Registro'),
    ('ERROR_LINKED', 'Error Linked'),
    ('SUCCESS', 'Correcto')
)
