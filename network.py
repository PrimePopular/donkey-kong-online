import asyncio
from ably import AblyRealtime

class Network:
    def __init__(self):
        # Your specific Root Key
        self.api_key = 'HzRJUQ.VP8eQA:pdDNfZS95zNug5HBpzejr1FUsvkVBObI-ASQkzZjwDc'
        self.client = None
        self.channel = None
        self.others = {} # Dictionary to store {connection_id: {x, y}}

    async def connect(self):
        try:
            self.client = AblyRealtime(self.api_key)
            await self.client.connection.once_async('connected')
            
            self.channel = self.client.channels.get('donkey-ghost-room')
            
            # Subscribing to player moves
            await self.channel.subscribe("player_move", self.on_message)
            print("Connected to Ably Ghost Network!")
        except Exception as e:
            print(f"Network Connection Error: {e}")

    def on_message(self, message):
        # Prevent drawing yourself as a ghost
        if message.connection_id != self.client.connection.id:
            # We store the data (x and y) using the unique connection ID
            self.others[message.connection_id] = message.data

    async def send_position(self, x, y):
        # Only send if we are connected to avoid errors
        if self.channel and self.client.connection.state == 'connected':
            try:
                # We use publish_async to keep the game from lagging
                await self.channel.publish("player_move", {"x": x, "y": y})
            except:
                pass 
                