from django.utils.translation import gettext as _
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response and isinstance(response.data, dict):
        response.data['detail'] = _(response.data.get('detail', ''))
    return response