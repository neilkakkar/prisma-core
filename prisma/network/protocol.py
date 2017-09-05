# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging
import json
import zlib
from twisted.internet.protocol import Factory
from twisted.protocols.basic import NetstringReceiver

from prisma.manager import Prisma
from prisma.network.validator import Validator
from prisma.network.syncstate import SyncState
from prisma.network.syncpeers import SyncPeers
from prisma.network.syncevents import SyncEvents

TIMEOUT = 5  # general timeout, of which it closes the connection


class NetworkProtocol(NetstringReceiver):
    """
    This protocol will be used for communicate between peers. The methods are
    described in sync peers and sync events.
    """
    def __init__(self):
        self.logger = logging.getLogger('Protocol')
        self.validate = Validator()
        self.callLater = Prisma().callLater
        self.peer = None
        self.host = None
        self.d = None

    def connectionMade(self):
        """
        Save the peer and the host.
        """
        self.peer = self.transport.getPeer()
        self.host = self.transport.getHost()
        self.callLater(TIMEOUT, lambda: self.on_timeout())
        self.logger.debug('Connected successfully with {0}:{1}'.format(self.peer.host, str(self.peer.port)))

    def stringReceived(self, payload):
        """
        Called automatically when receiving a string. Will convert to json object and from then
        check the method that is being called.

        :param payload:
        """
        try:
            # decompress and convert payload json to object
            data = zlib.decompress(payload)
            self.logger.debug('Received from {0}:{1}: {2}'.format(self.peer.host, str(self.peer.port), data))
            data = json.loads(data.decode())
        except Exception as e:
            self.d.errback(Exception('Error: Data received from peer not parsed: {0}'.format(e)))
            return False

        try:
            # validate
            if not self.validate.validate_method(data):
                raise Exception('Malformed payload: not a valid method.')
            # do the corresponding action
            if data['method'] == 'get_state':
                SyncState.handle_get_state(self)
            elif data['method'] == 'get_state_response':
                SyncState.handle_get_state_response(self, data['state'])
            elif data['method'] == 'get_peers':
                SyncPeers.handle_get_peers(self, data['_id'], data['port'], data['latest_event'])
            elif data['method'] == 'get_peers_response':
                SyncPeers.handle_get_peers_response(self, data['peers'])
            elif data['method'] == 'get_events':
                SyncEvents.handle_get_events(self, data['latest_event'], data['event_info'])
            elif data['method'] == 'get_events_response':
                SyncEvents.handle_get_events_response(self, data['events'])
            else:
                raise Exception('Malformed payload: not a valid method.')
        except Exception as e:
            self.d.errback(Exception('Error when receiving data: ' + str(e)))

    def send_data(self, data):
        """
        This will transform data object into a json string bytes and sends it to the peer.

        :param data: object
        """
        try:
            data = json.dumps(data).encode()
            data_gzip = zlib.compress(data, Prisma().config.getint('network', 'zlib_level'))
            self.sendString(data_gzip)
            compress_ratio = int((len(data) - len(data_gzip))/len(data)*100)
            self.logger.debug('Sent to {0}:{1}: {2}, c: {3}%'.format(
                self.peer.host, str(self.peer.port), data, compress_ratio)
            )
        except Exception as e:
            # sendString mostly adds bytes to a buffer. So a connection error won't really be told.
            # to acknowledge that, we will have to wait for the response.
            self.d.errback(Exception('Could not send message: {0}'.format(e)))

    def send_get_state(self):
        """
        Sends get state.
        """
        if self.is_connected_to_myself():
            self.d.errback(Exception('Connected to myself.'))
        else:
            SyncState.send_get_state(self)

    def send_get_peers(self):
        """
        Sends get peers.
        """
        if self.is_connected_to_myself():
            self.d.errback(Exception('Connected to myself.'))
        else:
            SyncPeers.send_get_peers(self)

    def send_get_events(self):
        """
        Sends get events.
        """
        if self.is_connected_to_myself():
            self.d.errback(Exception('Connected to myself.'))
        else:
            SyncEvents.send_get_events(self)

    def is_client(self):
        """
        If our port is not our listen port then we are the client.

        :return: bool
        """
        return self.host.port != Prisma().network.listen_port

    def is_connected_to_myself(self):
        """
        This returns true if I'm the client and the remote peer is this running node.

        :return: bool
        """
        if self.is_client() and self.peer.host == self.host.host and self.peer.port == Prisma().network.listen_port:
            return True
        return False

    def on_timeout(self):
        if self.d is not None:
            self.d.errback(TimeoutError('Protocol timed out'))

    def close_connection(self):
        """
        Closes the connection cleanly.
        """
        self.d = None
        self.transport.loseConnection()

    def connectionLost(self, reason):
        """
        Print debug when connection lost.

        :param reason:
        """
        error = reason.getErrorMessage()
        self.logger.debug('Lost connection with {0}:{1}: {2}'.format(self.peer.host, str(self.peer.port), error))
        if self.d is not None:
            self.d.errback(reason)


class NetworkFactory(Factory):
    """
    Prisma Factory for PrismaNetworkProtocol
    """
    protocol = NetworkProtocol
