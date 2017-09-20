# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

from collections import namedtuple
import logging
import os.path
from json import loads, load, dumps
import nacl.hash

from prisma.manager import Prisma


class Common(object):
    def __init__(self):
        self.logger = logging.getLogger('Common')

    @staticmethod
    def get_timestamp():
        from time import time
        return int(round(time() * 1000))

    def tuple_to_dict(self, event_tuple):
        """
        Converts a tuple of type Event to a dictionary.

        :param event_tuple: (namedtuple('Event', 'd p t c s'))
        :return: event_dict
        :rtype: tuple ( bool on error )
        """
        try:
            event_dict = loads(dumps(event_tuple._asdict()))
            return event_dict
        except Exception as e:
            self.logger.error("Could not convert named event tuple to dict. Reason:", e)
        return False

    def dict_to_tuple(self, event_dict):
        """
        Converts a list dictionaries to a named tuples of type Event.
        this returns a tuple without the key which is the blake2bhash.
        We can calculate this again by calling that function in crypto.

        :param event_dict: list of dictionaries of events. See documentation
        :return: dict of tuples
        :rtype: tuples ( 'Event', 'd p t c s')
        """
        evtuple_dict = {}

        if len(event_dict) > 0:
            for event in event_dict:
                try:
                    # Restore the original ordering in named tuple.
                    # We will do a blake2b hash on this bytes(tuple) and
                    # is therefore important. """
                    ev = namedtuple('Event_', 'd p t c s')
                    evtuple = ev(
                        event_dict[event]['d'],
                        tuple(event_dict[event]['p']),
                        event_dict[event]['t'],
                        event_dict[event]['c'],
                        event_dict[event]['s'])
                    if evtuple:
                        evtuple_dict[event] = evtuple

                except Exception as e:
                    self.logger.error("Could not convert dict to named tuple. Reason:", e)
                    return False
        return evtuple_dict

    def read_genesis_state(self):
        """
        Read genesis event from json file.

        :returns: genesis event dictionary
        :rtype: res: dictionary
        """
        try:
            genesis_filename = 'genesis.json'
            if Prisma().config.get('general', 'network') == 'testnet':
                genesis_filename = 'genesis-testnet.json'
            with open('{0}/cryptograph/{1}'.format(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                                   genesis_filename)) as genesis_file:
                res = load(genesis_file)
            return res
        except Exception as e:
            self.logger.critical('Could not read genesis event. Reason: {0}'.format(e))
        return False

    @staticmethod
    def get_mini_hash(text):
        """
        Creates a hash of anything and returns the first 8 characters like in git.
        This is very helpful specially when debugging purposes.

        It's much easier to identify a 7 character hex string than a hash, hex or random numbers.

        :param text: string to hash
        :return: string
        """
        hashed_string = nacl.hash.sha256(text.encode('utf-8')).decode('utf-8')
        return hashed_string[:8]
