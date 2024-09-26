from dal import autocomplete
from django.http import JsonResponse
from django.views.generic import TemplateView

from .models import Ubigeo


class JSONResponseMixin(object):
    """
    A mixin that can be used to render a JSON response.
    """

    def render_to_json_response(self, context, **response_kwargs):
        """
        Returns a JSON response, transforming 'context' to make the payload.
        """
        return JsonResponse(
            self.get_data(context),
            **response_kwargs
        )

    def get_data(self, context):
        """
        Returns an object that will be serialized as JSON by json.dumps().
        """
        # Note: This is *EXTREMELY* naive; in reality, you'll need
        # to do much more complex handling to ensure that arbitrary
        # objects -- such as Django model instances or querysets
        # -- can be serialized as JSON.
        # return json.dumps(context)
        return context


class AddressGetDistrictsView(JSONResponseMixin, TemplateView):

    def render_to_response(self, context, **response_kwargs):
        code = self.kwargs.get('code', None)
        codes = code.split('-')
        department_code = codes[0]
        province_code = codes[1]
        districts = Ubigeo.objects.filter(estado=1, ubigeo_provc=province_code, ubigeo_depc=department_code). \
            exclude(ubigeo_disc='00').values('id', 'ubigeo_disn')
        response_data = dict()
        response_data['districts'] = list(districts)
        return self.render_to_json_response(response_data, **response_kwargs)


class UbigeoAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        # if not self.request.user.is_authenticated():
        #     return Via.objects.none()

        qs = Ubigeo.objects.all()

        if self.q:
            qs = qs.filter(ubigeo_disn__istartswith=self.q)

        return qs
