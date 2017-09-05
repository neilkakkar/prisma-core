import json
from twisted.internet import defer

from prisma.test.testutils.networktestcase import NetworkTestCase


class PrismaNetworkProtocolTestCase(NetworkTestCase):
    def _add_example_states(self):
        self.prisma.db.insert_state(
            {
                "3558462963507083618PR": 100000,
                "3832901052830737971PR": -500000,
                "3918807197700602162PR": 100000,
                "7306589250910697267PR": 300000
            },
            9,
            'cace9158277350b011a7336fc2ded9466a37f9119912909f693973e74231f5ab'
        )
        self.prisma.db.insert_state(
            {
                "3558462963507083618PR": 100000,
                "3761975960047924065PR": 1,
                "3832901052830737971PR": -500000,
                "3918807197700602162PR": 99999,
                "7306589250910697267PR": 300000
            },
            14,
            'bb423e2c04ede3e3fe7091ff56810c4b0d0bd1fa9ee472271b642adb3c7dec3e'
        )
        self.prisma.db.insert_state(
            {
                "3558462963507083618PR": 100000,
                "3832901052830737971PR": -500000,
                "3918807197700602162PR": 100000,
                "7306589250910697267PR": 300000
            },
            4,
            'cace9158277350b011a7336fc2ded9466a37f9119912909f693973e74231f5ab'
        )

    def test_send_get_state(self):
        self.protocol.send_get_state()
        received = self.transport.value()
        data = json.loads(self._prepare_received(received))
        self.assertTrue('method' in data and data['method'] == 'get_state')

    def test_handle_get_state_empty(self):
        # send the request
        send = self._prepare_sending('{"method": "get_state"}')
        send = self._test_netstring(send)
        # receive the request
        self.protocol.stringReceived(send)
        received = self.transport.value()
        received = json.loads(self._prepare_received(received))
        self.assertTrue('method' in received and received['method'] == 'get_state_response')
        self.assertTrue('state' in received and received['state'] is False)

    def test_handle_get_state(self):
        self._add_example_states()
        # send the request
        send = self._prepare_sending('{"method": "get_state"}')
        send = self._test_netstring(send)
        # receive the request
        self.protocol.stringReceived(send)
        received = self.transport.value()
        received = json.loads(self._prepare_received(received))
        self.assertTrue('method' in received and received['method'] == 'get_state_response')
        self.assertTrue('state' in received and received['state'] is not False)
        state = received['state']
        self.assertTrue('_id' in state and state['_id'] == 14)
        self.assertTrue('wallets' in state)
        self.assertTrue('hash' in state)

    def test_handle_get_state_response(self):
        # check that we have no states
        last_state = self.prisma.db.get_last_state()
        self.assertFalse(last_state)
        # send the request
        send = json.dumps({
            'method': 'get_state_response',
            'state': {
                'wallets': {
                    '3761975960047924065PR': 1,
                    '7306589250910697267PR': 300000,
                    '3832901052830737971PR': -500000,
                    '3918807197700602162PR': 99999,
                    '3558462963507083618PR': 100000
                },
                'hash': 'bb423e2c04ede3e3fe7091ff56810c4b0d0bd1fa9ee472271b642adb3c7dec3e',
                '_id': 14
            }
        })
        send = self._prepare_sending(send)
        send = self._test_netstring(send)
        # receive the request and check if successful
        self.protocol.stringReceived(send)
        last_state = self.prisma.db.get_last_state()
        self.assertTrue(last_state['_id'] == 14)
        # check empty response
        received = self.transport.value()
        self.assertTrue(received == b'')
        # this solves testing issues with reactor
        if self.error is None:
            self.protocol.d = defer.Deferred()
            self.protocol.d.addCallbacks(self._defer_pass, self._defer_error)
