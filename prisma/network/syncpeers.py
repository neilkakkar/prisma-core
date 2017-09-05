# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

from prisma.manager import Prisma
from prisma.utils.common import Common


class SyncPeers:
    """
    Methods for syncing peers.
    This will use the protocol class to send and receive its data.
    """

    @staticmethod
    def send_get_peers(protocol):
        """
        Prepare and send get_peers.

        :param protocol:
        """
        request_data = {
            'method': 'get_peers',
            '_id': Prisma().network.node_id,
            'port': Prisma().network.listen_port,
            'latest_event': Prisma().db.get_latest_event_time()
        }
        protocol.send_data(request_data)

    @staticmethod
    def handle_get_peers(protocol, _id, port, latest_event):
        """
        Add remote peer to database and send my peers.

        :param protocol:
        :param _id:
        :param port:
        :param latest_event:
        """
        # add peer to database
        data = {
            '_id': _id,
            'host': protocol.peer.host,
            'port': port,
            'latest_event': latest_event,
            'seen': Common.get_timestamp()
        }
        Prisma().db.insert_peer(data)
        # send the remote peer my known peers, including myself
        peers_response = Prisma().db.get_peers_many()
        peers_response.append({
            '_id': Prisma().network.node_id,
            'host': protocol.host.host,
            'port': Prisma().network.listen_port,
            'latest_event': Prisma().db.get_latest_event_time(),
            'seen': Common.get_timestamp()
        })
        response_data = {
            'method': 'get_peers_response',
            'peers': peers_response
        }
        protocol.send_data(response_data)

    @staticmethod
    def handle_get_peers_response(protocol, peers):
        """
        Add peers from the response to the database. Then close connection.

        :param protocol:
        :param peers:
        """
        for peer in peers:
            if Prisma().network.node_id != peer['_id'] and protocol.validate.is_valid_node_ip(peer['host']):
                Prisma().db.insert_peer(peer)

        # everything ok, so do the callback and close connection
        protocol.d.callback(None)
        protocol.close_connection()
