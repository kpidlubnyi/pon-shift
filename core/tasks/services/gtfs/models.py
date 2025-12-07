from common.models import *


REQUIRED_MODELS = {
    'agency': CarrierStaging,
    'calendar_dates': CalendarDateStaging,
    'routes': RouteStaging,
    'shapes': ShapeSequenceStaging,
    'stops': StopStaging,
    'trips': TripStaging,
    'stop_times': StopTimeStaging,
    'frequencies': FrequenceStaging,
    'transfers': TransferStaging,
}


def get_related_by_fk_models(model: models.Model) -> list[models.Model]:
    related_objects = model._meta.related_objects
    return {rel.related_model for rel in related_objects if rel.one_to_many}

models_should_have_carrier_prefix = (
        {RouteStaging} | get_related_by_fk_models(RouteStaging) 
        | {TripStaging} | get_related_by_fk_models(TripStaging)
)


def get_allowed_fields(model: models.Model) -> list:
    return [field.attname for field in model._meta.fields]


def add_carrier_prefix(carrier:str, val:str) -> str:
    return f'{carrier}:{val}'


def split_value_with_carrier_prefix(val:str) -> tuple[str, str]:
    return val.split(':')


def get_carrier_prefix_from_value(val:str) -> str:
    return split_value_with_carrier_prefix(val)[0]


def remove_carrier_prefix(val:str) -> str:
    return split_value_with_carrier_prefix(val)[1]


def add_carrier_prefix_to_fields(carrier, model, row):
    if model is TransferStaging:
        row['from_trip_id'] = add_carrier_prefix(carrier, row['from_trip_id'])
        row['to_trip_id'] = add_carrier_prefix(carrier, row['to_trip_id'])
    
    elif model is RouteStaging:
        row['route_id'] = add_carrier_prefix(carrier, row['route_id'])

    elif model is TripStaging:
        row['route_id'] = add_carrier_prefix(carrier, row['route_id'])
        row['trip_id'] = add_carrier_prefix(carrier, row['trip_id'])

    else:
        row['trip_id'] = add_carrier_prefix(carrier, row['trip_id'])

    return row


def get_table_name(model: models.Model):
    return model._meta.db_table
