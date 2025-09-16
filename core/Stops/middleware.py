from django.http import JsonResponse
from rest_framework import status
from rest_framework.exceptions import ValidationError

from .exceptions import *


class ProcessExceptionsMiddleware:
    def __init__(self, get_response):
        self._get_response = get_response

    def __call__(self, request):
        return self._get_response(request)

    def process_exception(self, request, e: Exception):
        match e:
            case ValidationError():
                data = {'data': {f'Помилка в параметрах запиту' : str(e)}, 'status': status.HTTP_400_BAD_REQUEST}
            case AddressNotFoundError():
                data = {'data': {f'Не знайдено адресу' : str(e)}, 'status': status.HTTP_404_NOT_FOUND}
            case StopNotFoundError():
                data = {'data': {'error': str(e), 'status': status.HTTP_404_NOT_FOUND}}
            case _:
                data = {'data': {'Нечікуванна помилка': str(e)}, 'status':status.HTTP_500_INTERNAL_SERVER_ERROR}

        return JsonResponse(**data)