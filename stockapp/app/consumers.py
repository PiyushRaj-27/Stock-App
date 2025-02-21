import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer





class StockConsumer(AsyncWebsocketConsumer):
    """
    A WebSocket consumer that handles real-time stock data updates for a specific stock.

    Uses Channels groups to efficiently manage connections for the same stock, sending updates to all connected clients simultaneously.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stock_name = None
        self.group_name = None

    async def connect(self):
        """
        Handles WebSocket connection. Joins the appropriate Channels group for the stock.
        """
        self.stock_name = self.scope["url_route"]["kwargs"]["stock_name"]
        print(f"Client connected for {self.stock_name}")

        # Join stock group
        self.group_name = f"stock_{self.stock_name}"
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        # Start sending updates
        asyncio.create_task(self.send_updates())




    async def disconnect(self, code):
        """
        Handles WebSocket disconnection. Leaves the Channels group for the stock.
        """
        # Leave room group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )


    async def send_updates(self):
        """
        Periodically fetches (simulated) stock data and sends updates to the Channels group.
        Handles exceptions during update sending.
        """
        channel_layer = get_channel_layer()
        update = 1
        while True:
            try:
                # data = await api(self.stock_name) #Uncomment and replace with actual API call
                # Send message to WebSocket group
                await channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "stock_update",
                        "message": update
                    }
                )
                update += 1
                await asyncio.sleep(5) #adjust update interval as needed


            except Exception as e:
                print(f"Error sending updates: {e}")
                break #Exit the loop if there's an error


    async def stock_update(self, event):
        """
        Receives stock update events from the Channels group and sends them to the connected client.
        """
        message = event['message']
        await self.send(text_data=json.dumps(message))


    
    async def fetch_update(self):
        """
        Retrives the data from api and pass it to the front end users.
        """
