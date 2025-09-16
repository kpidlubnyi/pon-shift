from django.urls import path

from .views import *

urlpatterns = [
    #path('<str:route_id>/', RouteInfo.as_view()),
    path('nearest/', NearestBikeStations.as_view())
]
