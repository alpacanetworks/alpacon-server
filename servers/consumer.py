import logging

from wsutils.consumer import APIClientAsyncConsumer


logger = logging.getLogger(__name__)


class BackhaulConsumer(APIClientAsyncConsumer):
    async def connect(self):
        if await super().connect():
            await self.send_json({
                'query': 'commit'
            })
        else:
            await self.send_json({
                'query': 'quit',
                'reason': 'Permission denied. Please check your id and key again.'
            })
