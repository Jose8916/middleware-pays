# from django.utils import timezone
from django.conf import settings
from django.db import models


class _BasicAuditedModel(models.Model):
    '''Base class which adds audit properties to a model.

    Attributes:
      owner: The user who owns the entity.
      created: Date when entity was created.
      last_modified: The date and time of last modification for the entity.
      last_modified_by: The user who last edited/modified the program.
    '''

    created = models.DateTimeField(
        verbose_name='Creado',
        # default=timezone.now,
        auto_now_add=True,
        null=True,
        editable=False,
    )
    last_updated = models.DateTimeField(
        verbose_name='Modificado',
        auto_now=True,
        null=True,
        editable=False,
    )

    class Meta:
        abstract = True
        ordering = ('-created', )


class _AuditedModel(_BasicAuditedModel):
    '''Base class which adds audit properties to a model.

    Attributes:
      created: Date when entity was created.
      created_by: The user who owns the entity.
      last_updated: The date and time of last modification for the entity.
      last_updated_by: The user who last edited/modified the program.
    '''

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        verbose_name='Creado por',
        related_name="%(class)s_created",
        editable=False,
        blank=True,
        null=True,
        default=None
    )
    last_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        verbose_name='Modificado por',
        related_name="%(class)s_last_modified",
        editable=False,
        blank=True,
        null=True,
        default=None
    )

    class Meta:
        abstract = True
        ordering = ('-created', )

    def save(self, current_user=None, *args, **kwargs):

        if current_user:
            self.last_updated_by = current_user
            if not self.id:
                self.created_by = current_user

        super(_AuditedModel, self).save(*args, **kwargs)
