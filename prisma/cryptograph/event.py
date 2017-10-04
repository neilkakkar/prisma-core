# -*- coding: utf-8 -*-
"""
The following copyright notice does not apply to the files: event.py, order.py, fame.py and rounds.py

Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging
from collections import namedtuple
from json import dumps
from time import time

from prisma.manager import Prisma
from prisma.crypto.crypto import Crypto

"""
Event_ Tuple explanation:

* d- Data/payload!
* p- event-hash of 2 parents(latest events) of event
* t- time of event creation
* c- identifying key of first parent
* s- digital sign of event by first parent ( using his secret key)
"""
Event_ = namedtuple('Event_', 'd p t c s')


class Event(object):
    """
    Event
    """
    def __init__(self, graph):
        """
        Create class instance

        :param graph: instance of cryptograph class
        :type graph: object
        :returns instance of Event class
        :rtype: object
        """
        self.graph = graph
        self.crypto = Crypto()
        self.logger = logging.getLogger('Event')

    @staticmethod
    def restore(msg):
        """
        Restore Named tuple Event from tuple

        :param msg: event dict formatted as tuple(not named) with order that match with order in named Event
        :type msg: tuple
        :return: formated Event
        :rtype: named tuple(Event)
        """
        res = {}
        for h in msg.keys():
            list_event = msg[h]
            res[h] = Event_(list_event[0], tuple(list_event[1]), list_event[2], list_event[3], list_event[4])
        return res

    def new_event(self, d, p):
        """
        Create a new event (and also return it's hash)
        Events are vertices in the hash graph containing
        the info(hashes) about 2 parent graphs that synced/gossiped

        :param d: data/payload
        :type d: tuple
        :param p: event-hash of 2 parents
        :type p: set
        :return: hash of new event and event itself
        :rtype: str and named tuple
        """
        self.logger.debug("NEW_EVENT: %s %s", str(d), str(p))

        t = time()
        s = self.crypto.sign_data(dumps(d, p, t, self.graph.keystore['publicKey'].decode()),
                                       self.graph.keystore['privateKeySeed'])
        self.logger.debug("Sign: %s", s['sig_detached'])
        ev = Event_(d, p, t, s['verify_key'], s['sig_detached'])
        self.logger.debug("Created event : %s", str(ev))
        return self.crypto.blake_hash(bytes(dumps(ev).encode('utf-8'))), ev

    def is_valid_event(self, blake2hash, ev):
        """
        Validate event

        :param blake2hash: event hash
        :type blake2hash: str
        :param ev: Event = named tuple containing : d p c t s
        :type ev: named tuple
        :return: True if event valid and False otherwise
        :rtype: bool
        """
        if not self.crypto.verify_local_event(ev):
            return False

        self.logger.debug("VALID_CHECK %s %s", str(blake2hash), str(ev))
        self.logger.debug("self.hash %s", str(self.crypto.blake_hash(bytes(dumps(ev).encode('utf-8')))))
        if self.crypto.blake_hash(bytes(dumps(ev).encode('utf-8'))) == blake2hash:
            self.logger.debug("Event blake2b hash matches ")
        else:
            self.logger.debug("HASHES dont match.")

        self.logger.debug("Parents: %s", str(ev.p))
        if ev.p != ():
            rnd1 = Prisma().db.get_round(ev.p[0])
            rnd2 = Prisma().db.get_round(ev.p[1])
            first_parent = Prisma().db.get_event(ev.p[0], as_tuple=False)
            second_parent = Prisma().db.get_event(ev.p[1], as_tuple=False)
        if (self.crypto.blake_hash(bytes(dumps(ev).encode('utf-8'))) == blake2hash and (
                        ev.p == ()
                or (len(ev.p) == 2
                    and ((first_parent and first_parent[ev.p[0]]['c'] == ev.c) or
                                 rnd1 <= self.graph.last_signed_state)
                    and ((second_parent and second_parent[ev.p[1]]['c'] != ev.c) or
                                 rnd2 <= self.graph.last_signed_state)
                    ))):
            self.logger.debug("Event successfully validated: %s", str(ev))
            return True
        self.logger.debug("Event could not be successfully validated: %s", str(ev))
        return False

        # TODO: check if there is a fork (rly need reverse edges?)
        # and all(self.cg[x].c != ev.c
        # for x in self.preds[ev.p[0]]))))

    def add_event(self, blake2hash, ev):
        """
        Save event to database

        :param blake2hash: event hash
        :type blake2hash: str
        :param ev: Event = named tuple containing : d p c t s
        :type ev: named tuple
        :return: True if successfully added and False otherwise
        :rtype: bool
        """
        try:
            Prisma().graph.tbd.add(blake2hash)
            if ev.p == ():
                if not Prisma().db.insert_height({blake2hash: 0}):
                    self.logger.error("Could not add root event with blake2b hash %s.",
                                      str(blake2hash))
                    return False
            else:
                height_list = []
                for p in ev.p:
                    height_list.append(Prisma().db.get_height(p))
                if not Prisma().db.insert_height(
                        {blake2hash: max(height_list) + 1}):
                    self.logger.debug("Could not add new event with blake2b hash %s",
                                      str(blake2hash))
                    return False
            Prisma().db.insert_event({blake2hash: ev})
        except Exception as e:
            self.logger.error("Could not add new event. Reason:", e)
            return False
        return True
