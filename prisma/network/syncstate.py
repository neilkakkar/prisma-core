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
            'method': 'get_state',
            'last_round': Prisma().db.get_last_state()['_id']
        }
        protocol.send_data(request_data)

    @staticmethod
    def handle_get_state(protocol, last_round):
        """
        Send our state
        
        :param last_round: last round of state that remote has
        :type last_round: int
        """
        local_round = Prisma().db.get_last_state()['_id']
        if local_round > last_round:
            # Gets data for new node start from db
            rounds = Prisma().db.get_rounds_many(local_round)
            witnesses = {local_round: Prisma().db.get_witness(local_round),
                         local_round-1: Prisma().db.get_witness(local_round-1)}
            height = Prisma().db.get_heights_many()

            # Formats response dict
            response_data = {
                'method': 'get_state_response',
                'states':  Prisma().db.get_state_with_proof_many(last_round),
                'start_data': {
                    'rounds': rounds,
                    'witnesses': witnesses,
                    'heights': height
                }
            }
        else:
            # Nothing to send
            response_data = {
                'method': 'get_state_response',
                'states': None,
                'start_data': None
            }
        protocol.send_data(response_data)

    @staticmethod
    def handle_get_state_response(protocol, states, start_data):
        """
        Adds state from the response to the database. Then closes connection.

        :param protocol:
        :param data:
        """
        protocol.logger.debug("sync_state states = %s, start_data = %s", str(states), str(start_data))
        # state is empty, we are before the first state creation!
        if not states:
            protocol.d.callback(None)
            protocol.close_connection()
            return

        # Checks if last of received states has last round greater than local one
        last_state_id = Prisma().db.get_last_state()['_id']
        if last_state_id < states[-1]['state']['_id']:
            state_handle_res = Prisma().state_manager.handle_received_state_chain(states)

            # If received states are successfuly validated, then inserts start_data and starts working
            if state_handle_res:
                # After handling received states at least one state should be inserted
                last_state_id = Prisma().db.get_last_state()['_id']

                # Clear db
                Prisma().db.drop_collections_many(['events', 'height', 'rounds', 'head', 'state', 'signature'])
                Prisma().db.delete_round_greater_than(last_state_id)

                # Inserts start data and sets some initial values
                Prisma().db.insert_round(start_data['rounds'])
                Prisma().db.insert_height(start_data['heights'])
                Prisma().db.insert_consensus([last_state_id], True)
                Prisma().db.set_consensus_last_sent(last_state_id)
                Prisma().graph.last_signed_state = last_state_id
                Prisma().graph.unsent_count = 0
                Prisma().db.insert_witness(start_data['witnesses'])
            else:
                protocol.logger.error("Could not validate recived states, states = %s", str(states))
                # TODO everything is NOT ok what shall we do ?

        # everything ok, so do the callback and close connection
        protocol.d.callback(None)
        protocol.close_connection()
