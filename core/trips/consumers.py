import json
import urllib
import asyncio

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from common.services.mongo import get_rt_vehicle_data
from .services.ws import *


class TripConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        trip_id = self.scope['url_route']['kwargs']['trip_id']
        self.trip_id = urllib.parse.unquote(trip_id)
        self.running = True
        
        await self.accept()
        
        self.update_task = asyncio.create_task(self.send_updates())

    async def disconnect(self, close_code):
        self.running = False
        if hasattr(self, 'update_task'):
            self.update_task.cancel()

    async def send_updates(self):        
        while self.running:
            try:
                carrier, data = await database_sync_to_async(get_rt_vehicle_data)(self.trip_id)
                data = await database_sync_to_async(transform_rt_vehicle_data)(carrier, data)

                await self.send(text_data=json.dumps({
                    'status': 'ok',
                    'data': data
                }))
                
                await asyncio.sleep(10)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.send(text_data=json.dumps({
                    'status': 'error',
                    'message': str(e)
                }))
                break