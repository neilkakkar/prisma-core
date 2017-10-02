# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging
import sys
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError

from prisma.utils.common import Common

class events(object):

    def __init__(self, prismaDB, super):
        self.logger = logging.getLogger('PrismaDB-Events')
        self.db = prismaDB
        self.super = super
        

    def get_event(self, event_id, as_tuple=True, clear_parent=False):
        """
        Gets one event from db
        :param event_id: event id (hash)
        :type event_id: str
        :param as_tuple: returns result as named tuple or as dict
        :type as_tuple: bool
        :param clear_parent: removes parents if they were signed or doesn't remove them
        :type clear_parent: bool
        :return: Event or False if error
        :rtype:     * dict of events
                    * dict of named tuple
                    * bool
        """
        try:
            cg_dict = {}

            _event = self.db.events.find_one({'_id': event_id})

            if _event and '_id' in _event and 'event' in _event:
                cg_dict[_event['_id']] = _event['event']

                if clear_parent:
                    new_parents_list = []
                    last_signed = self.super.get_consensus_last_signed()
                    for p in cg_dict[event_id]['p']:
                        rnd = self.super.get_round(p)
                        if rnd == -1:
                            self.logger.error("Could not find hash in rounds !")
                            return False

                        if rnd > last_signed:
                            new_parents_list.append(p)
                    cg_dict[event_id]['p'] = new_parents_list

            self.logger.debug("Get from Events %s", str(cg_dict))
            if as_tuple and len(_event) > 0:
                return self.super.common.dict_to_tuple(cg_dict)[event_id]
            return cg_dict
        except Exception as e:
            self.logger.error("Could not get event. Reason: %s", str(e))
            self.logger.debug("Event: %s", str(event_id))
        return False

    def get_events_many(self, as_tuple=True):
        """
        Gets many events from db
        :param as_tuple: returns result as named tuple or as dict
        :type as_tuple: bool
        :return: Events
        :rtype:     * dict of events
                    * dict of named tuple
        """
        cg_dict = {}
        try:
            for event in self.db.events.find().sort('event.t', ASCENDING):
                if '_id' in event and 'event' in event:
                    cg_dict[event['_id']] = event['event']
        except Exception as e:
            self.logger.error("Could not get events. Reason: %s", str(e))
            return cg_dict

        self.logger.debug("Get from Events %s", str(cg_dict))
        if as_tuple and len(cg_dict) > 0:
            return self.super.common.dict_to_tuple(cg_dict)
        return cg_dict

    def get_latest_event_time(self):
        """
        Gets latest (largest) time of event stored in db
        :return:    * latest event time - if it is possible to find event
                    * 0.0 - if the collection is empty
                    * False - if error
        :rtype: float or bool
        """
        ev_time_list = []
        try:
            for event in self.db.events.find().sort('event.t', -1).limit(1):
                ev_time_list.append(event)
            if len(ev_time_list) > 0 and 'event' in ev_time_list[0]:
                return ev_time_list[0]['event']['t']
            return 0.0
        except Exception as e:
            self.logger.error("Could not retrieve latest event timestamp. Reason:", str(e))
        return False

    def insert_event(self, event):
        """
        Inserts one event into db
        :param event: event info including blake2 hash as a key
        :type event: dict
        :return: was the insertion successful
        :rtype: bool
        """
        try:
            if event:
                self.logger.debug("Inserting into events collection: %s", str(event))
                for ev_id in event:
                    self.logger.debug("result %s", str(self.db.events.insert_one(
                        {'_id': ev_id, 'event': self.super.common.tuple_to_dict(event[ev_id])})))
                return True
        except DuplicateKeyError:
            self.logger.error("Could not insert event. Reason: duplicate (_id) event id.")
        except Exception as e:
            self.logger.error("Could not insert event(s). Reason: %s", str(e))
        return False

    def delete_event(self, h):
        """
        Deletes one event
        :param h: event hash
        :type h: str
        :return: was the delete operation successful
        """
        try:
            self.logger.debug("Delete from Events %s", str(h))
            self.db.events.remove(
                {'_id': h},
                {'justOne': True})
            return True
        except Exception as e:
            self.logger.error("Delete from Event. Reason: %s", str(e))
        return False
