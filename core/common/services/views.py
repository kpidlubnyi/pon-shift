from common.collections import NestedDict


def format_gtfs_rt_alert(carrier: str, alert: dict) -> dict:
    alert = NestedDict(alert)
    formatted_alert = dict()
    
    match carrier:
        case 'WTP':
            formatted_alert['id'] = alert['id']

            alert = alert['alert']
            formatted_alert['informed_routes'] = [
                'WTP:' + route['route_id']
                for route in alert['informed_entity']
            ]
            formatted_alert['url'] = alert['url.translation'][0]['text']
            formatted_alert['header_text'] = alert['header_text.translation'][0]['text']
            formatted_alert['description'] = alert['description_text.translation'][0]['text']

    return formatted_alert
