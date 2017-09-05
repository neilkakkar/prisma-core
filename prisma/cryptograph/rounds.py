# -*- coding: utf-8 -*-
"""
The following copyright notice does not apply to the files: event.py, order.py, fame.py and rounds.py

Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging
from collections import defaultdict

from prisma.manager import Prisma


class Rounds(object):
    """
    Rounds
    """
    def __init__(self, graph):
        """
        Create class instance

        :param graph: instance of cryptograph class
        :type graph: object
        :returns instance of Rounds class
        :rtype: object
        """
        self.graph = graph
        self.logger = logging.getLogger('Rounds')

    def divide_rounds(self, events):
        """
        Divide all events into rounds

        :param events: topologicaly sorted sequence of new event to process.
        :type events: set
        """
        self.logger.debug("DIVIDE ROUNDS: %s", str(events))
        for h in events:
            ev = Prisma().db.get_event(h)

            if ev.p == ():  # this is a root event
                Prisma().db.insert_round({h: 0})
                Prisma().db.insert_witness({0: {ev.c: h}})
                Prisma().db.insert_can_see({h: {ev.c: h}})
            else:
                # r -- last round stored in db
                r =  max(Prisma().db.get_round(p) for p in ev.p)
                self.logger.debug("RMAX %s", str(r))

                # Recurrence relation to update can_see

                p0, p1 = (Prisma().db.get_can_see(p) for p in ev.p)
                value = {c: self.graph._cgc.maxi(p0.get(c), p1.get(c)) for c in p0.keys() | p1.keys()}
                self.logger.debug("p0 %s", str(p0))
                self.logger.debug("p1 %s", str(p1))
                self.logger.debug("vaule %s", str(value))
                Prisma().db.insert_can_see({h: value})

                self.logger.debug("self.graph.min_s %s", str(self.graph.min_s))

                self.logger.debug("Round strongly see start")
                if len(self.graph._cgc.strongly_see(h, r)) >= self.graph.min_s:
                    Prisma().db.insert_round({h: r + 1})
                    self.logger.debug("Hash %s has round + 1 ", h)
                    self.logger.debug("Decide round for event with hash = %s, round = %s", str(h), str(r+1))
                else:
                    Prisma().db.insert_round({h: r})
                    self.logger.debug("Decide round for event with hash = %s, round = %s", str(h), str(r))

                    Prisma().db.insert_can_see({h: {ev.c: h}})

                # Get round for x by hash and get round for x parent if first is bigger we can insert witness for x
                x_round = Prisma().db.get_round(h)
                if x_round > Prisma().db.get_round(ev.p[0]):
                    Prisma().db.insert_witness({x_round: {ev.c: h}})
