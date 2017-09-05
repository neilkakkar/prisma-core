import json
from twisted.test import proto_helpers
from autobahn.twisted.websocket import WebSocketServerProtocol

from prisma.test.testutils.testcase import PrismaTestCase


class PrismaNetworkProtocolTestCase(PrismaTestCase):
    """
    Test Prisma network protocol.
    """
    def setUp(self):
        """
        Build protocol with localhost address and give it a mock transport.
        """
        self._set_up()
        self.transport = proto_helpers.StringTransport()
        self.api = self.prisma.api
        self.port = self.api.port
        self.protocol = self.api.factory.buildProtocol(None)
        self.protocol.factory.openHandshakeTimeout = 0
        self.protocol.makeConnection(self.transport)
        self.protocol.state = WebSocketServerProtocol.STATE_OPEN
        self.protocol.websocket_version = 13

    def tearDown(self):
        self.clock.advance(10)
        self._tear_down()

    def _test_on_message(self, obj):
        message = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.protocol.onMessage(message, False)
        response = self.transport.value()[2:]
        return json.loads(response.decode('utf-8'))

    def test_error_request(self):
        obj = {
            'req': 'error_request'
        }
        response = self._test_on_message(obj)
        self.assertFalse(response['ok'])

    def test_peer_list(self):
        obj = {
            'req': 'peer_list'
        }
        response = self._test_on_message(obj)
        self.assertTrue(response['ok'])
        self.assertTrue('peer_list' in response and not response['peer_list'])
