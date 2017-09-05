import zlib
from twisted.test import proto_helpers
from twisted.internet import defer
from twisted.protocols.test.test_basic import TestNetstring

from prisma.test.testutils.testcase import PrismaTestCase


class NetworkTestCase(PrismaTestCase):
    def setUp(self):
        """
        Build protocol with localhost address and give it a mock transport.
        """
        self._set_up()
        self.error = None
        self.transport = proto_helpers.StringTransport()
        self.network = self.prisma.network
        self.protocol = self.network.factory.buildProtocol(None)
        self.protocol.d = defer.Deferred()
        self.protocol.d.addCallbacks(self._defer_pass, self._defer_error)
        self.protocol.makeConnection(self.transport)

    def tearDown(self):
        if self.error is None:
            self.protocol.d.callback(None)
            self._tear_down()
        else:
            self._tear_down()
            self.fail(self.error)

    def _defer_pass(self, result):
        pass

    def _defer_error(self, reason):
        error_message = reason.getErrorMessage()
        self.error = 'Error: {0}'.format(error_message)

    @staticmethod
    def _test_netstring(payload):
        """
        Create and connect to a Netstring to verify that the data is received correctly.

        :param payload:
        """
        t = proto_helpers.StringTransport()
        p = TestNetstring()
        p.MAX_LENGTH = 9999999
        p.makeConnection(t)
        p.dataReceived(payload)
        return p.received.pop()

    def _prepare_sending(self, data):
        data = zlib.compress(data.encode(), self.prisma.config.getint('network', 'zlib_level'))
        data = str(len(data)).encode() + ':'.encode() + data + ','.encode()
        return data

    def _prepare_received(self, data):
        data = self._test_netstring(data)
        return zlib.decompress(data).decode()
