from django.urls import path

from .views import *


urlpatterns = [
    path('', AlertsView.as_view()),
    path('<str:alert_id>/', AlertView.as_view()),   
]
