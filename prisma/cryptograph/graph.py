# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import sys
import logging
import json

from prisma.manager import Prisma
from prisma.crypto.crypto import Crypto
from prisma.cryptograph.common import CryptographCommon
from prisma.cryptograph.event import Event
from prisma.cryptograph.fame import Fame
from prisma.cryptograph.order import Order
from prisma.cryptograph.rounds import Rounds
from prisma.utils.common import Common
from prisma.crypto.wallet import Wallet


class Graph:
    """
    Graph
    """
    def __init__(self):
        """
        Create class instance

        :returns instance of Graph class
        :rtype: object
        """
        self.wallet = Wallet()
        self.keystore = self.wallet.prompt_unlock()
        if not self.keystore:
            sys.exit(1)
        self.logger = logging.getLogger('Graph')
        self.logger.debug("Node address %s", str(self.keystore['address']))
        self.stake = 1
        self.tot_stake = 4  # TODO: It should change dynamically
        self.min_s = int(2 * self.tot_stake / 3 + 1) # min stake amount
        self.to_sign_count = 10
        self.last_signed_state = 0
        self.unsent_count = 0
        self._cgc = CryptographCommon(graph=self)
        self.common = Common()
        self.crypto = Crypto()
        self.head = None
        self.round = {}
        self.tbd = set()
        self._event = Event(graph=self)
        self._fame = Fame(graph=self)
        self._order = Order(graph=self)
        self._round = Rounds(graph=self)

    def init_graph(self):
        self.last_signed_state = Prisma().db.get_consensus_last_signed()
        self.logger.debug("INIT last_signed_state: %s", str(self.last_signed_state))

        is_cg_empty = self.init_events()
        self.restore_invariants(is_cg_empty)

        if is_cg_empty:
            self.sync_genesis()

        self.unsent_count = len(Prisma().db.get_consensus_greater_than(
            Prisma().db.get_consensus_last_created_sign()))

    def init_events(self):
        """
        Verifying events stored in database

        :return: is cg empty
        :rtype: bool
        """
        cg = Prisma().db.get_events_many()

        if cg:
            self.logger.info("Verifying events stored in database.")
            for event in cg:
                if not self._event.is_valid_event(event, cg[event]):
                    self.logger.error("Could not verify event with blake2b hash %s",
                                      str(event))
                    """ Todo: what will we do here if we can not validate an event in database? """
                    exit()
            return False
        else:
            return True

    def restore_invariants(self, is_cg_empty):
        """
        Initializes cryptograph if it is empty

        :param  is_cg_empty: is cryptograph empty
                (this arg func get from init_events)
        :return: None
        """
        if is_cg_empty:
            h, ev = self._event.new_event([], ())
            self._event.add_event(h, ev)
            Prisma().db.insert_round({h: 0})
            Prisma().db.insert_witness({0: {ev.c: h}})
            Prisma().db.insert_can_see({h: {ev.c: h}})
            Prisma().db.insert_head(h)
        else:
            self.logger.debug("Reconnect")

    def sync_genesis(self):
        """
        Insert genesis state if it is not exist
        """
        if not Prisma().db.get_state(-1):
            gen_state = Common().read_genesis_state()
            self.logger.debug("genesis_state: %s", str(gen_state))
            Prisma().db.insert_state(gen_state['state'], gen_state['hash'], gen_state['signed'])

    def signed_event_response(self):
        """
        Sends the events we know about without actually sending the events.
        As a response we shall get the events in full which we don't know about.
        The remote peer will call local_cryptograph_response() and create a subset based
        on this information. signed_events contains two parents and their heights.

        :returns: signed events
        :rtype: dict
        """
        head = Prisma().db.get_head()

        if head:
            signed_events = self.crypto.sign_data(
                json.dumps({c: Prisma().db.get_height(h) for c, h in Prisma().db.get_can_see(head).items()}),
                self.keystore['privateKeySeed'])
            if signed_events:
                return signed_events
        return None

    def get_clean_remote_cg(self, remote_cg):
        """
        Removes events from remote cg we have already signed or know.

        :param: remote cryptograph with events that we might know
        :type remote_cg: tuple
        :returns: remote cg without events that we have already sign or know
        :rtype: dict
        """
        remote_cg = self._event.restore(remote_cg)

        for event_hash in list(remote_cg):
            event_round = Prisma().db.get_round(event_hash)

            if event_round == -1:
                self.logger.error("Could not clean remote cg: get event round ERROR !")
                return False

            if (event_round and event_round <= self.last_signed_state) \
                    or Prisma().db.get_event(event_hash, as_tuple=False):
                self.logger.debug("CLEANING DELETE hash = %s", str(event_hash))
                del remote_cg[event_hash]

        self.logger.debug("Clean remote HG %s", str(remote_cg))
        return remote_cg

    def validate_add_event(self, events_sign):
        """
        Gets remote events signature, and validate than delete events that we already know

        :param events_sign: signature of remote cryptograph
        :type events_sign: dict
        :returns: remote cryptograph without events that we already know and remote head
        :rtype: dict and str
        """
        msg = self.crypto.verify_concatenated(events_sign)
        remote_head, remote_cg = json.loads(msg.decode('utf-8'))

        self.logger.debug("VALIDATE remote_cg %s", str(remote_cg))
        self.logger.debug("VALIDATE remote_head %s", str(remote_head))

        remote_cg = self.get_clean_remote_cg(remote_cg)
        return remote_cg, remote_head

    def insert_new_events(self, remote_cg, remote_head, payload):
        """
        Inserts new remote events into db and create new event of that sync

        :param remote_cg: remote cryptograph
        :type remote_cg: dict
        :param remote_head: hash of head of remote cryptograph
        :type remote_head: str
        :param payload: data (transaction) that will be inserted into the new event
        :type payload: dict or tuple
        :returns: topologicaly sorted sequence of new events to process.
        :rtype: events: set
        """
        new = tuple(self._cgc.toposort(remote_cg.keys(), lambda u: remote_cg[u].p))

        self.logger.debug("remote_cg %s", str(remote_cg))
        self.logger.debug("remote_head %s", str(remote_head))
        self.logger.debug("payload %s", str(payload))
        self.logger.debug("new %s", str(new))

        for h in new:
            ev = remote_cg[h]
            self.logger.debug("h %s", str(h))
            self.logger.debug("ev %s", str(ev))
            if self._event.is_valid_event(h, ev):
                self._event.add_event(h, ev)
            else:
                self.logger.debug("Event not valid: %s", str(ev))

        if self._event.is_valid_event(remote_head, remote_cg[remote_head]):
            h, ev = self._event.new_event(payload, (Prisma().db.get_head(), remote_head))
            self.logger.debug("new_event_event_part %s", str(ev))
            assert self._event.is_valid_event(h, ev)

            if self._event.add_event(h, ev):
                Prisma().db.insert_head(h)
                return new + (h,)
        return False

    def local_cryptograph_response(self, signed_event_response):
        """
        Based on the get_event_response and the data generated in signed_event_response()
        on the remote peer we calculate a subset of events that the asking node does not
        know about. The two parents and their height are used below. Returns a dict;
        see crypto.py

        :param signed_event_response: signed remote events and last remote event time
        :type signed_event_response: dict
        :returns: signed local events or False if error
        :rtype: dict or bool
        """
        head = Prisma().db.get_head()

        self.logger.debug("signed_event_response %s", str(signed_event_response))
        self.logger.debug("head %s", str(head))
        # cg is a list of event tuples, it should be a dict of tuples

        if head:
            cs = json.loads((self.crypto.verify_concatenated(signed_event_response)).decode('utf-8'))
            # cs are a dict
            subset = {h: Prisma().db.get_event(h)
                      for h in self._cgc.bfs((head,),
                                                   lambda u: (p for p in
                                                              Prisma().db.get_event(u, clear_parent=True).p
                                                              if Prisma().db.get_event(p).c not in cs or
                                                              Prisma().db.get_height(p) > cs[Prisma().db.get_event(p).c]))}
            response = json.dumps((head, subset))
            local_cryptograph_response_res = self.crypto.sign_data(response, self.keystore['privateKeySeed'])
            self.logger.debug("local_cryptograph_response_res %s", str(local_cryptograph_response_res))
            return local_cryptograph_response_res
        return False

