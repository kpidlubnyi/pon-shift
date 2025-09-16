from django.contrib import admin
from django.urls import path, include 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('stops/', include('Stops.urls')),
    path('routes/', include('Routes.urls')),
    path('bikes/', include('Bikes.urls'))
]
