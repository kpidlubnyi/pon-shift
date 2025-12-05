from rest_framework import status
from rest_framework.views import APIView
from django.http import JsonResponse

from .services.mongo import get_wtp_alerts, get_wtp_alert
from .services.views import format_gtfs_rt_alert


class AlertsView(APIView):
    def get(self, request):
        alerts = get_wtp_alerts()
        formatted_alerts = [format_gtfs_rt_alert('WTP', alert) for alert in alerts]
        
        return JsonResponse({
            'alerts': formatted_alerts
        }, status=status.HTTP_200_OK)


class AlertView(APIView):
    def get(self, request, alert_id):
        alert = get_wtp_alert(alert_id)
        formatted_alert = format_gtfs_rt_alert('WTP', alert)

        return JsonResponse({
            'alert': formatted_alert
        }, status=status.HTTP_200_OK)
