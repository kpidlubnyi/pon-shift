from django.urls import path

from .views import *


urlpatterns = [
    path('', AllStopsView.as_view()),
    path('nearest-stops/', NearestStopsView.as_view()),
    path('<str:stop_name_or_id>/', StopsView.as_view()),
]
