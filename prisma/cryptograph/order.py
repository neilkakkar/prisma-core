# -*- coding: utf-8 -*-
"""
The following copyright notice does not apply to the files: event.py, order.py, fame.py and rounds.py

Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging
from functools import reduce

from prisma.manager import Prisma
from prisma.cryptograph.transaction import Transaction


class Order(object):
    """
    Order
    """
    def __init__(self, graph):
        """
        Create class instance

        :param graph: instance of cryptograph class
        :type graph: object
        :returns instance of Order class
        :rtype: object
        """
        self.graph = graph
        self.transaction = Transaction()
        self.logger = logging.getLogger('Order')

    def find_order(self, new_c):
        """
        Assign earlier events a round received and consensus timestamp

        :param new_c: new consensus
        :type new_c: list
        :return: None
        """
        # @var to_int function to get int value from event signature by its hash
        # @var f_w function to get int value from event signature by its hash

        to_int = lambda x: int.from_bytes(Prisma().db.get_event(x).s.encode('utf-8'), byteorder='big')

        for r in new_c:
            f_w = {w for w in Prisma().db.get_witness(r).values() if
                   Prisma().db.get_famous(w)}

            white = reduce(lambda a, b: a ^ to_int(b), f_w, 0)
            self.logger.debug("white %s", str(white))

            ts = {}  # timestamps dict
            seen = set()
            for x in Prisma().graph._cgc.bfs(filter(Prisma().graph.tbd.__contains__, f_w),
                                         lambda u: (p for p in
                                                    Prisma().db.get_event(u, clear_parent=True).p
                                                    if p in Prisma().graph.tbd)):

                self.logger.debug("order_x: %s", str(x))

                c = Prisma().db.get_event(x).c  # key of first parent

                s = set()
                for w in f_w:
                    can_see_w = Prisma().db.get_can_see(w)
                    if c in can_see_w and Prisma().graph._cgc.higher(can_see_w[c], x):
                       s.add(w)
                self.logger.debug("Order s %s", str(s))

                if sum(1 for w in s) > self.graph.tot_stake / 2:
                    Prisma().graph.tbd.remove(x)
                    seen.add(x)

                    """ Calculate median of the timestamps of all the events in s"""
                    times = []
                    for w in s:
                        a = w
                        can_see_a = Prisma().db.get_can_see(a)
                        while (c in can_see_a
                               and Prisma().graph._cgc.higher(can_see_a[c], x)
                               and Prisma().db.get_event(a, clear_parent=True).p):
                            a = Prisma().db.get_event(a, clear_parent=True).p[0]
                            can_see_a = Prisma().db.get_can_see(a)
                        times.append(Prisma().db.get_event(a).t)
                    times.sort()

                    times_len = len(times)
                    if times_len % 2 == 0:
                        ts[x] = .5 * (times[times_len // 2] + times[(times_len - 1) // 2])
                    else:
                        ts[x] = .5 * (times[times_len // 2])

            final = sorted(seen, key=lambda x: (ts[x], white ^ to_int(x)))
            self.logger.debug("Seen: %s", str(seen))
            self.logger.debug("Transaction dictL %s", str(ts))
            self.logger.debug("Final: %s", str(final))

            self.logger.debug("Before inserting new_c %s", str(new_c))
            self.transaction.insert_processed_transaction(final, r, self.graph.keystore['privateKeySeed'])
