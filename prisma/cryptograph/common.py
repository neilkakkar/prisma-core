# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging
import os
from collections import deque
from collections import namedtuple
from json import dumps, loads, load
from collections import defaultdict

from prisma.manager import Prisma


class CryptographCommon(object):
    """
    Common functions for the cryptograph module.
    """
    def __init__(self, graph):
        """
        Create class instance

        :param graph: instance of cryptograph class
        :type graph: object
        :returns instance of CryptographCommon class
        :rtype: object
        """
        self.graph = graph
        self.logger = logging.getLogger('HgCommon')

    def maxi(self, a, b):
        """
        Find hash with biggest height

        :param a: first event hash
        :type a: str
        :param b: second event hash
        :type b: str
        :return: hash with higher height
        :rtype: str
        """
        if self.higher(a, b):
            return a
        else:
            return b

    @staticmethod
    def higher(a, b):
        """
        Check if height of a bigger than height of b

        :param a: first event hash
        :type a: str
        :param b: second event hash
        :type b: str
        :return: is a higher
        :rtype: bool
        """
        return a is not None and (b is None or Prisma().db.get_height(a) >= Prisma().db.get_height(b))

    @staticmethod
    def toposort(graphs, parents):
        """
        Make topological sorting for remote cg

        :param graphs: remote cg hashes
        :type: list
        :param parents: func to get parents of current event
        :type: lambda
        :return: topologicaly sorted remote keys(hashes)
        :rtype: generator
        """
        seen = {}

        def visit(u):
            """
            Helper function for toposort

            :param u: Node hash
            :type u: str
            :return: Visited node hash
            :rtype: generator
            :raises: ValueError: if input is not directed acyclic graph
            """
            if u in seen:
                if seen[u] == 0:
                    raise ValueError('not a DAG')
            elif u in graphs:
                seen[u] = 0
                for v in parents(u):
                    yield from visit(v)
                seen[u] = 1
                yield u

        for u in graphs:
            yield from visit(u)

    @staticmethod
    def bfs(s, succ):
        """
        Breadth-first search

        :param s: graph root
        :type s: iterator or str(hash)
        :param succ: func to get adjacent nodes
        :type succ: lambda func
        :return: current node
        :rtype: generator
        """
        s = tuple(s)
        seen = set(s)
        q = deque(s)
        while q:
            u = q.popleft()
            yield u
            for v in succ(u):
                if v not in seen:
                    seen.add(v)
                    q.append(v)

    @staticmethod
    def dfs(s, succ):
        """
        Depth-first search

        :param s:
        :param succ:
        :return:
        """
        # No usage
        seen = set()
        q = [s]
        while q:
            u = q.pop()
            yield u
            seen.add(u)
            for v in succ(u):
                if v not in seen:
                    q.append(v)

    @staticmethod
    def randrange(n):
        # No usage
        a = (n.bit_length() + 7) // 8  # number of bytes to store n
        b = 8 * a - n.bit_length()  # number of shifts to have good bit number
        r = int.from_bytes(randombytes(a), byteorder='big') >> b
        while r >= n:
            r = int.from_bytes(randombytes(a), byteorder='big') >> b
        return r

    def tuple_to_dict(self, event_tuple):
        """
        Converts a tuple of type Event to a dictionary.

        :param event_tuple: (namedtuple('Event', 'd p t c s'))
        :return: Success event_dict
        :rtype: dict
        :return: False: Could not convert named event tuple to dict.
        :rtype: bool
        """
        try:
            event_dict = loads(dumps(event_tuple._asdict()))
            return event_dict
        except Exception as e:
            self.logger.error("Could not convert named event tuple to dict. Reason:", e)
        return False

    def dict_to_tuple(self, event):
        """
        Converts a dictionary to a named tuple of type Event.

        :param event:
        :type event: dict
        :return: Success: evtuple: List of tuples ('Event', 'd p t c s')
        :return: False: Could not convert dict to named event tuple.
        :rtype: bool
        """
        if len(event) > 0:
            try:
                """
                Restore the original ordering in named tuple. 
                We will do a blake2b hash on this bytes(tuple) and is therefore important.
                """
                ev = namedtuple('Event_', 'd p t c s')
                evtuple = ev(event['d'],
                             tuple(event['p']),
                             event['t'],
                             event['c'],
                             event['s'])
                return evtuple
            except Exception as e:
                self.logger.error("Could not convert dict to named event tuple. Reason:", e)
                return False
        return False

    def read_genesis_event(self):
        """
        Read genesis event from json file.

        :return: Success: genesis event dictionary
        :rtype: res: dictionary
        :return: False: Could not read genesis event.
        :rtype: bool
        """
        try:
            genesis_filename = 'genesis.json'
            if Prisma().config.get('general', 'network') == 'testnet':
                genesis_filename = 'genesis-testnet.json'
            with open('{0}/{1}'.format(os.path.dirname(os.path.abspath(__file__)), genesis_filename)) as genesis_file:
                res = load(genesis_file)
            return res
        except Exception as e:
            self.logger.critical('Could not read genesis event. Reason: {0}'.format(e))
        return False

    def strongly_see(self, h, r):
        """
        Get nodes that given event can strongly see

        :param h: event hash
        :type h: str
        :param r: round
        :type r: int
        :return: nodes that can strongly see that event
        :rtype: set
        """
        self.logger.debug("strongly_see start h = %s, r = %s", str(h), str(r))
        self.logger.debug("Witneeses on round r %s", str(Prisma().db.get_witness(r)))
        hits = defaultdict(int)
        for c, k in Prisma().db.get_can_see(h).items():
            self.logger.debug("strongly_see k = %s ", str(k))
            self.logger.debug("strongly_see k (round) = %s", str(Prisma().db.get_round(k)))
            if Prisma().db.get_round(k) == r:
                for c_, k_ in Prisma().db.get_can_see(k).items():
                    self.logger.debug("strongly_see k______ = %s ", str(k_))
                    self.logger.debug("strongly_see k______(round) = %s ", str(Prisma().db.get_round(k_)))
                    if Prisma().db.get_round(k_) == r:
                        # TODO change it to node stake
                        hits[c_] += 1

        self.logger.debug("strongly_see hits = %s", str(hits))
        res = set()
        for c, n in hits.items():
            if n >= self.graph.min_s:
                res.add(c)
        self.logger.debug("strongly_see res %s", str(res))
        return res
