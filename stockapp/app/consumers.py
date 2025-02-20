import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer



#add channel layers to group together all the websockets for the same stock
class StockConsumer(AsyncWebsocketConsumer):
    '''
    Primary socket for stock application. Echoes updates for a given stock data.
    '''


    async def connect(self):
        self.stockName = self.scope["url_route"]["kwargs"]["stock_name"]
        print(f"client connected for {self.stockName}")

        await self.accept()


        # implement update sending from here!
        
        # index = 1
        # while True:
                # data = api(stockName)
        #     index += 1
        #     # Send message to WebSocket
        #     await self.send(text_data=json.dumps({"message": index}))
        #     await asyncio.sleep(120)

    async def disconnect(self, code):
        # Leave room group
        pass

    