import json
from twisted.internet import defer

from prisma.test.testutils.networktestcase import NetworkTestCase


class PrismaNetworkProtocolTestCase(NetworkTestCase):
    """
    Test Prisma network protocol.
    """
    def test_send_data(self):
        obj = {'test': 'ok'}
        self.protocol.send_data(obj)
        self.assertEqual(self.transport.value(), self._prepare_sending('{"test": "ok"}'))

    def test_testnetstring(self):
        received = self._test_netstring(b'1:a,')
        self.assertEqual(received, b'a')

    def test_send_get_peers(self):
        self.protocol.send_get_peers()
        received = self.transport.value()
        received = json.loads(self._prepare_received(received))
        self.assertTrue('method' in received and received['method'] == 'get_peers')
        self.assertTrue('latest_event' in received and '_id' in received and 'port' in received)

    def test_is_client(self):
        self.assertTrue(self.protocol.is_client())

    def test_timeout(self):
        self.clock.advance(0.5)
        self.assertTrue(self.error is None)
        self.clock.advance(0.5)
        if self.error == 'Error: Protocol timed out':
            self.assertTrue(True)
            self.error = None
            self.protocol.d = defer.Deferred()
            self.protocol.d.addCallbacks(self._defer_pass, self._defer_error)
