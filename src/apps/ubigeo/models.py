from django.contrib.postgres.fields import JSONField

from django.db import models


class Ubigeo(models.Model):
    STATUS_ACTIVE = 1
    STATUS_INACTIVE = 0

    STATUS_CHOICES = (
        (STATUS_ACTIVE, u'Activo'),
        (STATUS_INACTIVE, u'Inactivo'),
    )

    ubigeo_depc = models.CharField(max_length=8, verbose_name='cod. departamento', blank=True, null=True)
    ubigeo_depn = models.CharField(max_length=64, verbose_name='nombre departamento', blank=True, null=True)

    ubigeo_provc = models.CharField(max_length=8, verbose_name='cod. provincia', blank=True, null=True)
    ubigeo_provn = models.CharField(max_length=64, verbose_name='nombre provincia', blank=True, null=True)

    ubigeo_disc = models.CharField(max_length=8, verbose_name='cod. distrito', blank=True, null=True)
    ubigeo_disn = models.CharField(max_length=64, verbose_name='nombre distrito', blank=True, null=True)

    siebel_codigo = models.IntegerField(verbose_name='siebel codigo', blank=True, null=True)
    siebel_prefijo = models.CharField(max_length=32, verbose_name='siebel prefijo', blank=True, null=True)

    fecha_registro = models.DateTimeField(auto_now_add=True, blank=True, null=True, verbose_name='fecha registro')

    coordenadas = JSONField(verbose_name='coordenadas por default', blank=True, null=True, help_text='["lat","lng"]')
    # coordenadas = models.CharField(max_length = 64, verbose_name = 'coordenadas por default',null=True)
    estado = models.IntegerField(verbose_name='estado', default=STATUS_INACTIVE, null=True, choices=STATUS_CHOICES)

    # default_home = models.BooleanField(verbose_name='Default Home', default=False)

    class Meta:
        verbose_name = 'Ubigeo'
        verbose_name_plural = 'Ubigeo'

    def __unicode__(self):
        return "%s, %s, %s" % (self.ubigeo_depn, self.ubigeo_provn, self.ubigeo_disn)
