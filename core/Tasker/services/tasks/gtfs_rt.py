import requests
from grpc_tools import protoc
from google.protobuf import json_format

from django.conf import settings


def get_proto():
    resp = requests.get(r'https://gtfs.org/documentation/realtime/gtfs-realtime.proto')
    resp.raise_for_status()

    with open('gtfs-realtime.proto', 'wb') as f:
        f.write(resp.content)

def compile_proto_to_py():
    protoc.main([
        "protoc", 
        "--python_out=.", 
        "--proto_path=.", 
        "gtfs-realtime.proto"
    ])

def parse_gtfs_realtime(pb) -> dict:
    try:
        gtfs_realtime_pb2 = __import__('gtfs_realtime_pb2')
    except:
        get_proto()
        compile_proto_to_py()
        gtfs_realtime_pb2 = __import__('gtfs_realtime_pb2')


    message = gtfs_realtime_pb2.FeedMessage()
    message.ParseFromString(pb)
    
    return json_format.MessageToDict(
        message,
        preserving_proto_field_name=True,
    )

def get_rt_gtfs(feed: dict):
    urls: dict = feed['feeds'][0]['urls']

    for k, v in urls.items():
        if v:
            response = requests.get(v).content
            return parse_gtfs_realtime(response)
