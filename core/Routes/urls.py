from django.urls import path

from .views import *


urlpatterns = [
    path('<str:trip_id>/route', ShowRoute.as_view()),
    path('<str:route_id>/', RouteInfo.as_view()),   
]
