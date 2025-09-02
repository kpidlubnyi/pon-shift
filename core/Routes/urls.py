from django.urls import path

from .views import *


urlpatterns = [
    path('nearest-stops/', NearestStops.as_view())
]
