# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging

from prisma.manager import Prisma


class SyncEvents:
    """
    Methods for syncing events.
    This will use the protocol class to send and receive its data.
    """

    @staticmethod
    def send_get_events(protocol):
        """
        Alice tells Bob his event info.

        sendGetEvents is used to sync events with a remote peer
        running once on start. If syncing occurs in this stage, no
        remote node shall be able to sync from us.

        :param protocol:
        """
        latest_event = Prisma().db.get_latest_event_time()
        event_info = Prisma().graph.signed_event_response()

        if event_info and latest_event:
            get_events = {
                'method': 'get_events',
                'latest_event': latest_event,
                'event_info': event_info
            }
            protocol.send_data(get_events)

    @staticmethod
    def handle_get_events(protocol, latest_event, event_info):
        """
        Bob sends to Alice all events that Alice doesn't have.

        To be fixed. The event list should be sent in chunks, e.g a list of 30 events.
        For now we send each event.

        Here we respond with our local cryptograph and those events that the remote node does not know about.

        :param protocol:
        :param latest_event:
        :param event_info:
        """
        events = Prisma().graph.local_cryptograph_response(event_info)
        event_data = {
            'method': 'get_events_response',
            'events': events
        }
        protocol.send_data(event_data)

    @staticmethod
    def handle_get_events_response(protocol, data):
        """
        Alice adds the events, creates an event, and then divides rounds, decides fame and finds order.

        :param protocol:
        :type protocol: instance of protocol
        :param data: sign of remote hash graph
        :type data: dict
        """
        logger = logging.getLogger('Protocol')

        if not data:
            protocol.d.callback(None)
            protocol.close_connection()
            return

        remote_cg, remote_head = Prisma().graph.validate_add_event(data)
        protocol.logger.debug("sync_events_remote_cg %s", str(remote_cg))
        protocol.logger.debug("sync_events_remote_head %s", str(remote_head))

        if remote_cg and remote_head in remote_cg:
            id_list, transaction_list = Prisma().db.get_unsent_transactions_many(
                Prisma().graph.keystore['address'])

            # Pass signatures as payload argument to new event
            new_remote_events = Prisma().graph.insert_new_events(remote_cg, remote_head, transaction_list)
            logger.debug("new remote events: %s", str(new_remote_events))

            if new_remote_events:
                Prisma().state_manager.update_state()

                Prisma().graph._round.divide_rounds(new_remote_events)
                Prisma().db.set_transaction_hash(id_list)

                new_c = Prisma().graph._fame.decide_fame()
                Prisma().graph._order.find_order(new_c)

                # Control unsent signatures count
                if len(new_c):
                    logger.debug("New_c is not empty ! %s", str(new_c))

                Prisma().graph.unsent_count += len(new_c)

                # Get data(list of signatures) to send to remote
                Prisma().state_manager.get_con_signatures()

                logger.debug("[--->FINAL RESPONSE<---]")
        # Demo for tx pool and genesis event
        logger.debug("All NODES BALANCE: %s", str(Prisma().db.get_account_balance_many()))
        logger.debug("STATE: %s", str(Prisma().db.get_last_state()))

        # Maybe do the next line based on some config variable in the development section?
        # SyncEvents.send_get_events(protocol)

        # everything ok, so do the callback and close connection
        protocol.d.callback(None)
        protocol.close_connection()
