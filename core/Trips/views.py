from rest_framework.views import APIView
from rest_framework import status
from django.http import JsonResponse, HttpResponse

from Tasker.models.common import *
from .serializers import *
from .services.views import *