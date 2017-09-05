# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging
import json
from binascii import hexlify
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.task import LoopingCall
from twisted.internet import defer

from prisma.manager import Prisma
from prisma.config import CONFIG
from prisma.network.protocol import NetworkFactory
from prisma.crypto.crypto import Crypto

STATUS_INIT = 0
STATUS_BOOTSTRAPPING = 1
STATUS_READY = 2


class NetworkService:
    """
    Prisma Network.
    """
    def __init__(self):
        self.logger = logging.getLogger('Network')
        self.status = STATUS_INIT
        self.callLater = Prisma().callLater
        self.reactor = reactor
        self.factory = NetworkFactory()
        self.listen_port = CONFIG.getint('network', 'listen_port')
        self.listener = None
        self.node_id = self.get_node_id()
        self.get_peers_lc = None
        self.get_events_lc = None
        self.get_peers_timer = CONFIG.getint('network', 'get_peers_timer')
        self.get_events_timer = CONFIG.getint('network', 'get_events_timer')
        self.timeout = CONFIG.getint('network', 'timeout')

    def start(self):
        """
        Start. Simply listen to the port and connect to a random peer.

        If remote_host and remote_port are specified, connect to that specific node.
        """
        # listen to the port
        self.listener = self.reactor.listenTCP(self.listen_port, self.factory)

        # bootstrap
        self.bootstrap()

        # start get_peers looping call
        self.get_peers_lc = LoopingCall(lambda: self.get_peers_from_random_peer())
        self.get_peers_lc.start(self.get_peers_timer)

        # start get_events looping call
        self.get_events_lc = LoopingCall(lambda: self.get_events_from_random_peer())
        self.get_events_lc.start(self.get_events_timer)

    def stop(self):
        """
        Close connections.
        """
        try:
            if self.get_peers_lc is not None:
                self.get_peers_lc.stop()
            if self.get_events_lc is not None:
                self.get_events_lc.stop()
            self.listener.stopListening()
        except Exception as e:
            self.logger.critical('Error while stopping Prisma network: ' + str(e))

    def bootstrap(self):
        """
        Delete all peers and bootstrap the peers in the config file by connecting and asking
        them the peers they know.
        """
        self.status = STATUS_BOOTSTRAPPING

        # delete first all peers
        Prisma().db.delete_peers()

        # bootstrap each of the nodes
        bootstrap_nodes = json.loads(CONFIG.get('bootstrap', 'bootstrap_nodes'))
        for bootstrap in bootstrap_nodes:
            host, port = bootstrap.split(":")
            self.bootstrap_peer(host, int(port))

        # get state from a random node
        self.download_state_from_random_peer()

    def bootstrap_peer(self, host, port):
        """
        This will ask for send_get_peers() and if it's successful it will add it to the
        available peers.

        :param host: host to connect to
        :param port: port to connect to
        """
        self.logger.info('Bootstrapping peer {0}:{1}'.format(host, str(port)))
        client = TCP4ClientEndpoint(self.reactor, host, port, self.timeout)
        d = client.connect(self.factory)

        # in case of connection ok, add the callbacks for get_peers and call send_get_peers
        def connection_ok(protocol):
            protocol.d = defer.Deferred()

            def get_peers_ok(_):
                self.logger.info('Successfully got peers from {0}:{1}'.format(host, port))
            protocol.d.addCallback(get_peers_ok)

            def get_peers_error(reason):
                error_message = reason.getErrorMessage()
                self.logger.error('Error when getting peers from {0}:{1}: {2}'.format(host, port, error_message))
                protocol.close_connection()
            protocol.d.addErrback(get_peers_error)

            protocol.send_get_peers()
        d.addCallback(connection_ok)

        # in case of connection error just show in debug
        def connection_error(reason):
            self.logger.warning('Error while connecting to {0}:{1}: {2}'.format(host, port, reason.getErrorMessage()))
        d.addErrback(connection_error)

    def download_state_from_random_peer(self):
        """
        This will get the state of a random peer.
        """
        random_peer = Prisma().db.get_random_peer()

        # if list is empty
        if not random_peer:
            self.logger.info('No peers to connect to. Wait to some peer to connect with you or restart with a peer.')
            self.callLater(2, lambda: self.download_state_from_random_peer())
            return

        random_peer = random_peer.pop()
        host = random_peer['host']
        port = random_peer['port']
        client = TCP4ClientEndpoint(self.reactor, host, port, self.timeout)
        d = client.connect(self.factory)

        # in case of connection ok, add the callbacks for get_state
        def connection_ok(protocol):
            protocol.d = defer.Deferred()

            def get_state_ok(_):
                self.logger.info('Successfully got the state from {0}:{1}'.format(host, port))
                self.status = STATUS_READY
            protocol.d.addCallback(get_state_ok)

            def get_state_error(reason):
                error_message = reason.getErrorMessage()
                self.logger.error('Error when getting state from {0}:{1}: {2}'.format(host, port, error_message))
                protocol.close_connection()
                self.callLater(0, lambda: self.download_state_from_random_peer())
            protocol.d.addErrback(get_state_error)

            protocol.send_get_state()
        d.addCallback(connection_ok)

        # in case of connection error show in debug and try again
        def connection_error(reason):
            # in case of error remove the peer from the database
            addr = random_peer['host'] + ':' + str(random_peer['port'])
            self.logger.debug('Error while connecting to {0}: {1}'.format(addr, reason.getErrorMessage()))
            Prisma().db.delete_peer(random_peer['_id'])
            # then call later again
            self.callLater(0, lambda: self.download_state_from_random_peer())
        d.addErrback(connection_error)

    def get_peers_from_random_peer(self):
        """
        Gets a random a peer from the database and connects to it and asks for peers.
        """
        # get a random peer from database
        random_peer = Prisma().db.get_random_peer()

        # if list is empty
        if not random_peer:
            self.logger.info('No peers to connect to. Wait to some peer to connect with you or restart with a peer.')
            return

        random_peer = random_peer.pop()
        host = random_peer['host']
        port = random_peer['port']
        client = TCP4ClientEndpoint(self.reactor, host, port, self.timeout)
        d = client.connect(self.factory)

        # in case of connection ok, add the callbacks for get_peers and call send_get_peers
        def connection_ok(protocol):
            protocol.d = defer.Deferred()

            def get_peers_ok(_):
                self.logger.info('Successfully got peers from {0}:{1}'.format(host, port))
            protocol.d.addCallback(get_peers_ok)

            def get_peers_error(reason):
                error_message = reason.getErrorMessage()
                self.logger.error('Error when getting peers from {0}:{1}: {2}'.format(host, port, error_message))
                protocol.close_connection()
                self.get_peers_lc.reset()
                self.get_peers_from_random_peer()
            protocol.d.addErrback(get_peers_error)

            protocol.send_get_peers()
        d.addCallback(connection_ok)

        # in case of connection error show in debug and try again
        def connection_error(reason):
            # in case of error remove the peer from the database
            addr = random_peer['host'] + ':' + str(random_peer['port'])
            self.logger.debug('Error while connecting to {0}: {1}'.format(addr, reason.getErrorMessage()))
            Prisma().db.delete_peer(random_peer['_id'])
            # then restart timer and try again get_peers_from_random_peer
            self.get_peers_lc.reset()
            self.get_peers_from_random_peer()
        d.addErrback(connection_error)

    def get_events_from_random_peer(self):
        """
        Gets a random a peer from the database and connects to it and asks for events.
        """
        # check first if ready
        if self.status != STATUS_READY:
            self.logger.info('Not ready, still bootstrapping.')
            return

        # check that we have enough peers
        peer_count = Prisma().db.count_peers()

        if peer_count < 3:
            if not CONFIG.getboolean('developer', 'developer_mode') or peer_count < 1:
                self.logger.debug('Not enough peers found in the network, skipping...')
                return

        random_peer = Prisma().db.get_random_peer().pop()
        host = random_peer['host']
        port = random_peer['port']
        client = TCP4ClientEndpoint(self.reactor, host, port, self.timeout)
        d = client.connect(self.factory)

        # in case of connection ok, add the callbacks for get_peers and call send_get_peers
        def connection_ok(protocol):
            protocol.d = defer.Deferred()

            def get_events_ok(_):
                self.logger.info('Successfully got events from {0}:{1}'.format(host, port))
            protocol.d.addCallback(get_events_ok)

            def get_events_error(reason):
                error_message = reason.getErrorMessage()
                self.logger.error('Error when getting events from {0}:{1}: {2}'.format(host, port, error_message))
                protocol.close_connection()
                self.get_events_lc.reset()
                self.get_events_from_random_peer()
            protocol.d.addErrback(get_events_error)

            protocol.send_get_events()
        d.addCallback(connection_ok)

        # in case of connection error show in debug and try again
        def connection_error(reason):
            # in case of error remove the peer from the database
            addr = random_peer['host'] + ':' + str(random_peer['port'])
            self.logger.debug('Error while connecting to {0}: {1}'.format(addr, reason.getErrorMessage()))
            Prisma().db.delete_peer(random_peer['_id'])
            # then restart timer and try again get_peers_from_random_peer
            self.get_events_lc.reset()
            self.get_events_from_random_peer()
        d.addErrback(connection_error)

    @staticmethod
    def get_node_id():
        """
        Generate a node id based on public key.

        :return: string
        """
        crypto = Crypto()
        pub_key_sha = crypto.sha256(str(Prisma().graph.keystore['publicKey']))
        node_id = pub_key_sha[:10]
        return hexlify(node_id).decode('utf-8')
