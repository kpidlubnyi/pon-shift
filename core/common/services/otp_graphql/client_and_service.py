from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from django.conf import settings


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


class OTPService:
    def __init__(self):
        self.client = OTPGraphQLClient()
