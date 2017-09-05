# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""
import json
import collections

from prisma.manager import Prisma


class SyncState:
    """
    Methods for syncing the state.
    This will use the protocol class to send and receive its data.
    """

    @staticmethod
    def send_get_state(protocol):
        """
        Prepare and send get_state.

        :param protocol:
        """
        request_data = {
            'method': 'get_state'
        }
        protocol.send_data(request_data)

    @staticmethod
    def handle_get_state(protocol):
        """
        Send our state
        """
        state = Prisma().db.get_last_state()
        # add peer to database
        response_data = {
            'method': 'get_state_response',
            'state': state
        }
        protocol.send_data(response_data)

    @staticmethod
    def handle_get_state_response(protocol, state):
        """
        Add state from the response to the database. Then close connection.

        :param protocol:
        :param state:
        """
        # state is empty, we are before the first state creation!
        if state is False:
            protocol.d.callback(None)
            protocol.close_connection()
            return

        # TODO the hash will have to be corroborated with 1/3 (half of the 2/3)
        wallets = collections.OrderedDict(sorted(state['wallets'].items()))
        h = Prisma().crypto.blake_hash(bytes(json.dumps(wallets).encode('utf-8')))
        if h != state['hash']:
            protocol.d.errback(Exception('State does not generate the same hash as the one received!'))

        # add to the database
        Prisma().db.insert_state(state['wallets'], state['_id'], state['hash'])

        # everything ok, so do the callback and close connection
        protocol.d.callback(None)
        protocol.close_connection()
