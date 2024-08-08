# middleware.py
from django.utils.deprecation import MiddlewareMixin
from .models import Location

class TenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        loc_name = request.get_host().split('.')[0]
        try:
            loc_name = Location.objects.get(loc_name=loc_name)
            request.loc_name = loc_name
        except Location.DoesNotExist:
            request.loc_name = None