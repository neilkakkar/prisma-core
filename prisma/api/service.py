from twisted.internet import reactor
from twisted.internet.task import LoopingCall

from prisma.config import CONFIG
from prisma.api.methods import ApiMethods
from prisma.api.protocol import ApiFactory


PUSH_INFO_TIMER = 1


class ApiService:
    """
    Api Service
    """
    def __init__(self):
        self.port = CONFIG.getint('api', 'listen_port')
        self.factory = ApiFactory()
        self.listener = None
        self.push_info_lc = None

    def start(self):
        """
        Start API by listening to the port.
        """
        self.listener = reactor.listenTCP(self.port, self.factory)
        # start push info looping call
        self.push_info_lc = LoopingCall(lambda: self.push_info())
        self.push_info_lc.start(PUSH_INFO_TIMER)

    def stop(self):
        """
        Stop API by stop listening.
        """
        if self.push_info_lc is not None:
            self.push_info_lc.stop()
        self.listener.stopListening()

    def push(self, client, payload):
        """
        Sends a payload to a client.

        :param client:
        :param payload:
        """
        self.factory.clients[client].send_json(payload)

    def broadcast(self, payload):
        """
        This will push a message to all the connected clients.

        :param payload:
        """
        for c in self.factory.clients:
            self.push(c, payload)

    def push_info(self):
        """
        Push notification to the client with some general information about the node.
        """
        push = {'push': 'info'}
        push.update(ApiMethods.peer_count())
        push.update(ApiMethods.last_event_time())
        push.update(ApiMethods.get_my_balance())
        self.broadcast(push)
