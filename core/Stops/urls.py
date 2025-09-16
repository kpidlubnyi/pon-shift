from django.urls import path

from .views import *


urlpatterns = [
    path('', AllStopsView.as_view()),
    path('nearest-stops/', NearestStops.as_view()),
    path('<str:stop_name>/', StopsView.as_view()),
    path('<str:stop_name>/<str:stop_code>/', StopView.as_view()),
]
