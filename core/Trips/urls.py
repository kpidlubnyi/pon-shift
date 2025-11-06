from django.urls import path

from .views import *


urlpatterns = [
    path('search-trip/', SearchedTrips.as_view()),
    path('<str:trip_id>/', TripInfo.as_view())

]
