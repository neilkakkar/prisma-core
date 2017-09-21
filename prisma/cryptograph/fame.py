
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


class Fame(object):
    """
    Fame
    """
    def __init__(self, graph):
        """
        Create class instance

        :param graph: instance of cryptograph class
        :type graph: object
        :returns instance of Fame class
        :rtype: object
        """
        self.graph = graph
        self.logger = logging.getLogger('Fame')
        """ TODO: what is C? In the default implementation C = 6."""
        self.C = 6

    @staticmethod
    def majority(it):
        """
        Specifies which type of vote(True or False) is major

        :param it: len(int) of s(described in decide_fame), votes(bool)
        :type it: generator object
        :return: v - majority vote in s, t - number of events in s with a vote of v
        :rtype: v: bool, t: int
        """
        hits = [0, 0]
        for s, x in it:
            hits[int(x)] += s
        if hits[0] > hits[1]:
            return False, hits[0]
        else:
            return True, hits[1]

    def decide_fame(self):
        """
        For each witness, decide whether it is famous

        :var: max_r: Last round saved in db
        :type: max_r: int
        :var: max_c: Count of consensus saved in db
        :type max_c: int
        :var: s: witness events in round r - 1 that y can strongly see
        :type s: set
        :returns: new consensus
        :rtype: list
        """
        max_r = Prisma().db.get_witness_max_round()
        max_c = Prisma().db.get_last_consensus()


        self.logger.debug("max_r %s", str(max_r))
        self.logger.debug("max_c %s", str(max_c))

        # helpers to keep code clean
        def iter_undetermined(r_):
            """
            For each round in range (max_c; r)
            get from db witnesses than add
            witness to result list if it is not famous

            :param r_: current iteration round
            :type r_: int
            :return: witnesses in format (round, witness hash)
            :rtype: generator
            """
            for r in range(max_c, r_):
                self.logger.debug("Start cycle with r = %s", str(r))
                if not Prisma().db.check_consensus(r):
                    self.logger.debug("r is not in consensus")
                    witness = Prisma().db.get_witness(r)
                    self.logger.debug("self.node.witnesses[r] %s", str(witness))
                    for w in witness.values():
                        self.logger.debug("Start cycle with w = %s", str(w))
                        if not Prisma().db.check_famous(w):
                            self.logger.debug("w is not in famous")
                            yield r, w

        def iter_voters():
            """
            For each event round in range (max_c; max_r]
            get witness from db
            (order is from earlier rounds to later)

            :return: witnesses in format (round, witness hash)
            :rtype: generator
            """

            self.logger.debug("MAX_C value = %s", str(max_c))
            for _r in range(max_c + 1, max_r + 1):
                self.logger.debug("X value = %s", str(_r))
                witness = Prisma().db.get_witness(_r)
                for w in witness.values():
                    yield _r, w

        done = set()

        # Note: r_ -- witness round
        #       y -- witness hash
        for r_, y in iter_voters():
            self.logger.debug("iter_y %s", str(y))
            self.logger.debug("Fame strongly see start")
            s = {Prisma().db.get_witness(r_ - 1)[c] for c in self.graph._cgc.strongly_see(y, r_ - 1)}
            self.logger.debug("fame_s %s", str(list(s)))

            # Note:    r -- witness round
            #          x -- witness hash
            for r, x in iter_undetermined(r_):
                self.logger.debug("r_ %s", str(r_))
                self.logger.debug("fame_r %s", str(r))

                if r_ - r == 1: # ﬁrst round of the election
                    self.logger.debug("y %s", str(y))
                    self.logger.debug("x %s", str(x))

                    new_votes = {y: {x: x in s}}
                    self.logger.debug("new_votes %s", new_votes)
                    Prisma().db.insert_vote(new_votes)
                else:
                    v, t = self.majority((len(s), Prisma().db.get_vote(w)[x]) for w in s)
                    self.logger.debug("fame_v %s", str(v))
                    self.logger.debug("round = %s fame_t %s", str(r), str(t))

                    if (r_ - r) % self.C != 0: # this is a normal round
                        if t >= self.graph.min_s:  # if supermajority, then decide
                            Prisma().db.insert_famous({x: v})
                            self.logger.debug("Add to done famous, round = %s", str(r))
                            done.add(r)
                        else: # else, just vote
                            Prisma().db.insert_vote({y: {x: v}})
                            self.logger.debug("[just vote] y %s vote for x %s %s", str(y), str(x), str(v))
                    else:  # this is a coin round
                        if t >= self.graph.min_s:  # if supermajority, then vote
                            Prisma().db.insert_vote({y: {x: v}})
                            self.logger.debug("[coin round] y %s vote for x %s %s", str(y), str(x), str(v))
                        else: # else ﬂip a coin
                            # the 1st bit is same as any other bit right?
                            hg = Prisma().db.get_event(y)
                            Prisma().db.insert_vote({y: {x: bool(ord(hg.s[0]) & 1)}})
                            self.logger.debug("[ﬂip a coin] y %s vote for x %s %s", str(y), str(x), str(bool(ord(hg.s[0]) & 1)))

        self.logger.debug("Famous_done %s", str(done))
        new_c = {r for r in done
                 if all(Prisma().db.check_famous(w) for w in Prisma().db.get_witness(r).values())}
        new_c = sorted(list(new_c))

        self.logger.debug("new_c %s", str(new_c))
        Prisma().db.insert_consensus(new_c)
        return new_c
