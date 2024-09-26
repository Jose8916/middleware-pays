import psycopg2
from django.conf import settings


class ConnectionDatabase(object):

    @staticmethod
    def connect():
        ddbname = settings.DATABASES['default']['NAME']
        duser = settings.DATABASES['default']['USER']
        dpassword = settings.DATABASES['default']['PASSWORD']
        dhost = settings.DATABASES['default']['HOST']
        dport = settings.DATABASES['default']['PORT']
        conn = psycopg2.connect(dbname=ddbname, user=duser, host=dhost, password=dpassword, port=dport)
        return conn

    @staticmethod
    def connect_cursor():
        dbconnect = ConnectionDatabase.connect()
        dbcursor = dbconnect.cursor()
        return dbcursor
