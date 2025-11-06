from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from functools import wraps
import re 

from django.conf import settings

from.queries import OTPGraphQLQueries


class OTPGraphQLClient:
    def __init__(self):
        otp_host, otp_port = settings.OTP_HOST, settings.OTP_PORT
        url = f'http://{otp_host}:{otp_port}/otp/transmodel/v3'

        transport = RequestsHTTPTransport(
            url=url,
            timeout=5,
            retries=3,
        )
        
        self.client = Client(
            transport=transport,
            fetch_schema_from_transport=True
        )
    
    def execute(self, query_string: str, variables: dict = None):
        query = gql(query_string)
        return self.client.execute(query, variable_values=variables)


def get_args_from_query(query: OTPGraphQLQueries):
    query_head = query.split('\n')[1]
    args = {arg[1:-1] for arg in re.findall(r'\$\w+:', query_head)}
    return args

def _graphql_query(query: OTPGraphQLQueries):
    def decorator(func):
        @wraps(func)
        def wrapper(self, **kwargs):
            allowed_args = get_args_from_query(query)
            filtered_kwargs = {k: v for k, v in kwargs.items() if k in allowed_args}
            return func(self, query=query, variables=filtered_kwargs)
        return wrapper
    return decorator


class OTPService:
    def __init__(self):
        self.client = OTPGraphQLClient()
    
    @_graphql_query(OTPGraphQLQueries.GET_TRIPS)
    def get_trips(self, *, query, variables):
        return self.client.execute(query_string=query, variables=variables)

if __name__ == '__main__':
    OTPService.get_args_from_query(OTPGraphQLQueries.GET_TRIPS)