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
        if state and state['_id'] != -1:
            rounds = Prisma().db.get_rounds_many(state['_id'])
            witnesses = {state['_id']: Prisma().db.get_witness(state['_id']),
                         state['_id']-1: Prisma().db.get_witness(state['_id']-1)}
            height = Prisma().db.get_heights_many()

            # add peer to database
            response_data = {
                'method': 'get_state_response',
                'state': state,
                'rounds': rounds,
                'witnesses': witnesses,
                'heights': height
            }
        else:
            response_data = {
                'method': 'get_state_response',
                'state': state
            }
        protocol.send_data(response_data)

    @staticmethod
    def handle_get_state_response(protocol, data):
        """
        Add state from the response to the database. Then close connection.

        :param protocol:
        :param state:
        """
        protocol.logger.debug("sync_state %s", str(data))
        # state is empty, we are before the first state creation!
        if data['state'] is False:
            protocol.d.callback(None)
            protocol.close_connection()
            return

        # TODO the hash will have to be corroborated with 1/3 (half of the 2/3)

        last_local_state = Prisma().db.get_last_state()
        if not last_local_state or last_local_state['_id'] < data['state']['_id']:
            # Clear db
            Prisma().db.drop_collections_many(['events', 'height', 'rounds', 'head', 'state', 'signature'])
            Prisma().db.delete_round_greater_than(data['state']['_id'])

            # insert startup data
            Prisma().db.insert_state(data['state'], data['state']['_id'], data['state']['hash'])
            Prisma().db.insert_round(data['rounds'])
            Prisma().db.insert_height(data['heights'])
            Prisma().db.insert_consensus([data['state']['_id']], True)
            Prisma().db.set_consensus_last_sent(data['state']['_id'])
            Prisma().graph.last_signed_state = data['state']['_id']
            Prisma().graph.unsent_count = 0
            Prisma().db.insert_witness(data['witnesses'])

        # everything ok, so do the callback and close connection
        protocol.d.callback(None)
        protocol.close_connection()
