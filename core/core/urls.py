from django.contrib import admin
from django.urls import path, include 
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('stops/', include('Stops.urls')),
    path('routes/', include('Routes.urls')),
    path('trips/', include('Trips.urls')),
    path('bikes/', include('Bikes.urls')),
    path('alerts/', include('common.urls')),
    path('health/', health_check), 
]
