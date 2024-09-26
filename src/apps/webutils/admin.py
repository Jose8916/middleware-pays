from django.contrib import admin


class _AuditedModelMixin(object):

    def save_model(self, request, obj, form, change):
        if hasattr(obj, 'last_updated_by'):
            obj.save(current_user=request.user)
        else:
            obj.save()

    def get_readonly_fields(self, request, obj=None):
        if obj and request.user.is_superuser:

            extra_readonly_fields = ('created', 'last_updated', )

            if hasattr(obj, 'last_updated_by'):
                extra_readonly_fields += ('created_by', 'last_updated_by', )

            return self.readonly_fields + extra_readonly_fields

        return self.readonly_fields


class _AuditedModelAdmin(_AuditedModelMixin, admin.ModelAdmin):
    pass
