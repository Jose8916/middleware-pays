from django.conf import settings

TERMS_EXCLUDE = [
    'TM0JBFKUSGT7',  # Plan Universitario antiguo
    'TMO45TQ5KCLM',  # Plan cross antiguo
    'TM93F79NQKV7',  # Anterior termino del plan Trimestral
    'TMGM0F7MK839'  # Nuevo termino de plan trimestral fix
]
# transacciones que no aparecen en el reporte de recognition por error en PIANO
LIST_WITHOUT_TRANSACTIONS_RECOGNITION = [
    "ec2e2cf8-9ed1-47ea-b511-8cf22450989e",
    "95a25288-b769-4052-818d-4643fb9b983e",
    "2b7d31e2-3020-42e5-bd3a-2f2f8aa0afe0",
    "5819ab25-b683-4168-b307-f01baeeec884",
    "7d877f95-d86e-4034-9e47-2e0637326717"
]

LIST_ENABLE_SEND_SIEBEL = [
    'RCM2LGMPY03W',
    'RCHV2TU0AJYP',
    'RCZDDANEHSDV',
    'RCGCSAMWOZA2',  # plan univ 1er plan
    'RCB80DIBFGD3',  # plan univ 1er plan
    'RCYQCND4J9JB',  # plan univ 1er plan
    'RCU4NOAM9R31',  # plan univ 1er plan
    'RC9QRA9MO3XT',  # plan univ 1er plan
    'RCMNLMXBP987',  # plan univ 1er plan
    'RCFI44B3HCC3',  # plan univ 1er plan
    'RCI237WK3LQY',  # corte 4 , term2 trimestral
    'RCLEJUU46NAH',  # corte 4 , term2 trimestral
    'RCHGLUA2OLON',  # corte 4 , term2 trimestral
    'RCUCDOPC3YS0',  # corte 4 , term2 trimestral
    'RCUJ2IE8QJ1M',  # corte 4 , term2 trimestral
    'RCN7WXB0721J',  # corte 4 , term2 trimestral
    'RCPJDSZKIQ7Z',  # corte 4 , term2 trimestral
    'RCG4SB1L1ITE',  # corte 4 , term2 trimestral
    'RC4367NI0DO3',  # corte 4 , term2 trimestral
    'RCL7EBQ1UXST',  # corte 4 , term2 trimestral
    'RCUZB2DQIXHT',  # corte 4 , term2 trimestral
    'RC3F1C3I212U',  # corte 4 , term2 trimestral
    'RC1WESYMIQS8',  # corte 4 , term2 trimestral
    'RCM86KIR29ME',  # corte 4 , term2 trimestral
    'RCJ1OBUWV0A5',  # corte 4 , term2 trimestral
    'RC22BSISZB8L',  # corte 4 , term2 trimestral
    'RCFZ7J7R56MY',  # corte 4 , term2 trimestral
    'RCG26206DX5T',  # corte 4 , term2 trimestral
    'RCXOABH3SNFQ',  # corte 4 , term2 trimestral
    'RCHMUR5UV9ZV',  # corte 4 , term2 trimestral
    'RCA84YRT03QV',  # corte 4 , term2 trimestral
    'RCMYUEL3M3Q1',  # corte 4 , term2 trimestral
    'RCQ48TAMV0EY',  # corte 4 , term2 trimestral
    'RC5JXTM4NRA8',  # corte 4 , term2 trimestral
    'RCXZQ5DVY00M',  # corte 4 , term2 trimestral
    'RCOCUK2GS6L2',  # corte 4 , term2 trimestral
    'RCNY14OYJI6I',  # corte 4 , term2 trimestral
    'RC7KC7VS4ER6',  # corte 4 , term2 trimestral
    'RCTYF11PITNE',  # corte 4 , term2 trimestral
    'RCJFT7X052OU',  # corte 4 , term2 trimestral
    'RC7PR6RA7I74',  # corte 4 , term2 trimestral
    'RCIAKL5K3G8T',  # corte 4 , term2 trimestral
    'RCKCLGGZQ8DV',  # corte 4 , term2 trimestral
    'RCGLAY5QY6ZA',  # corte 4 , term2 trimestral
    'RC9445TCPJB5',  # corte 4 , term2 trimestral
    'RCMQFT5JDEOV',  # corte 4 , term2 trimestral
    'RCLU9GI8EFCE',  # corte 4 , term2 trimestral
    'RCWJNBTM3IUK',  # corte 4 , term2 trimestral
    'RCB7T8N596FQ',  # corte 4 , term2 trimestral
    'RCGC6S6MEREN',  # corte 4 , term2 trimestral
    'RCSNQ1WJCR1F',  # corte 4 , term2 trimestral
    'RC9RK0TLBH19',  # corte 4 , term2 trimestral
    'RCP2X3FSXT5P',  # corte 4 , term2 trimestral
    'RCHHZ0MYMWF7',  # corte 4 , term2 trimestral
    'RCAJ49V3ADCE',  # corte 4 , term2 trimestral
    'RCVZBPFQAK5S',  # corte 4 , term2 trimestral
    'RCQCW0PWERBH',  # corte 4 , term2 trimestral
    'RCGQ83D1WXNA',  # corte 4 , term2 trimestral
    'RCA8QDS1OGNL',  # corte 4 , term2 trimestral
    'RCXHFAKPBYF9',  # corte 4 , term2 trimestral
    'RC4MSLZEV3UY',  # corte 4 , term2 trimestral
    'RCMECD4OB1N1',  # corte 4 , term2 trimestral
    'RCPQG69D9NY6',  # corte 4 , term2 trimestral
    'RC39PCC4X9Y6',  # corte 4 , term2 trimestral
    'RCDMUKGLKKC1',  # corte 4 , term2 trimestral
    'RCB3JOFB912Y',  # corte 4 , term2 trimestral
    'RC3F1C3I212U',  # corte 4 , term2 trimestral
    'RC9X8JEDWBLC',  # corte 4 , term2 trimestral
    'RCKCLGGZQ8DV',  # corte 4 , term2 trimestral
    'RC1WESYMIQS8',  # corte 4 , term2 trimestral
    'RCGLAY5QY6ZA',  # corte 4 , term2 trimestral
    'RCIWLY8I3KDX',  # corte 4 , term2 trimestral
    'RCSNQ1WJCR1F',  # corte 4 , term2 trimestral
    'RC9RK0TLBH19',  # corte 4 , term2 trimestral
    'RCP2X3FSXT5P',  # corte 4 , term2 trimestral
    'RCHHZ0MYMWF7',  # corte 4 , term2 trimestral
    'RCG26206DX5T',  # corte 4 , term2 trimestral
    'RC9BA1M6EW3M',  # corte 4 , term2 trimestral
    'RCB5APH9OCFF',  # corte 4 , term2 trimestral
    'RCBQCXY4YPWG',  # corte 4 , term2 trimestral
    'RCXOABH3SNFQ',  # corte 4 , term2 trimestral
    'RCSJGA52R9YN',  # corte 4 , term2 trimestral
    'RCMQFT5JDEOV',  # corte 4 , term2 trimestral
    'RCLU9GI8EFCE',  # corte 4 , term2 trimestral
    'RCWJNBTM3IUK',  # corte 4 , term2 trimestral
    'RCB7T8N596FQ',  # corte 4 , term2 trimestral
    'RCHMUR5UV9ZV',  # corte 4 , term2 trimestral
    'RCA84YRT03QV',  # corte 4 , term2 trimestral
    'RCMYUEL3M3Q1',   # corte 4 , term2 trimestral
    'RCX933EXXTLQ',   # corte 4 , term2 trimestral
    'RC66AE0ANHSQ',  # corte 5, term2 trimestral
    'RC917WW4XA6M',  # corte 5, term2 trimestral
    'RCNTOOFTIL2W',  # corte 5, term2 trimestral
    'RC5HPZWLHV3P',  # corte 5, term2 trimestral
    'RC49GLSNGYOM',  # corte 5, term2 trimestral
    'RC7OE5FN83AD'  # corte 5, term2 trimestral
]
if settings.ENVIRONMENT == 'test':
    LIST_EMAIL_SENDER = ['j.machicado@rpalatam.com.pe']
else:
    LIST_EMAIL_SENDER = [
                    'j.machicado@rpalatam.com.pe',
                    'elizabeth.huacachi@comercio.com.pe',
                    'n.castillo@rpalatam.com.pe',
                    'milagros.cueva@fractalservicios.pe',
                    'l.manuel@rpalatam.com.pe'
                ]
