from django.urls import re_path
from .consumers import *

websocket_urlpatterns = [
    re_path(r"(?P<trip_id>[\w:\-]+)/$", TripConsumer.as_asgi()),
]
