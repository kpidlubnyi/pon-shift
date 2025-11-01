from django.urls import path

from .views import *


urlpatterns = [
    path('<str:trip_id>/', TripInfo.as_view()),
]
