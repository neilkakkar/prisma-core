# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging

class visible(object):
    def __init__(self, prismaDB, super):
        self.logger = logging.getLogger('PrismaDB-visible')
        self.db = prismaDB
        self.super = super

    def get_can_see(self, event_id):
        """
        Gets events that can be seen based on event hash
        Note: parent is actually parent hash

        :param event_id: event hash
        :type event_id: str
        :return:    * events that event with given hash can see
                    * False - if error
        :rtype: dict or bool
        """
        try:
            if event_id:
                _can_see = self.db.can_see.find_one({'_id': event_id})
                if _can_see and 'can_see' in _can_see:
                    result_dict = {}
                    for item in _can_see['can_see']:
                        if 'parent' in item and 'event' in item:
                            result_dict[item['parent']] = item['event']
                    self.logger.debug("Get from Can_see %s", str(result_dict))
                    return result_dict
                return {}
        except Exception as e:
            self.logger.error("Could not get can_see. Reason: %s", str(e))
            self.logger.debug("Event:", event_id)
        return False

    def insert_can_see(self, can_see):
        """
        Inserts can see info
        Note: parent is actually parent hash

        :param can_see: event hash and hash of event that can see it
                        format {event:{node_id:event}}
        :type can_see: dict
        :return: was the insertion successful
        :rtype: bool
        """
        try:
            if can_see:
                for see_id in can_see:
                    for parent, val in can_see[see_id].items():
                        self.logger.debug("result %s", str(self.db.can_see.update(
                            {'_id': see_id},
                            {'$addToSet': {'can_see': {'parent': parent, 'event': val}}},
                            upsert=True
                        )))
                return True
        except Exception as e:
            self.logger.error("Could not insert can_see. Reason: %s", str(e))
            self.logger.debug("Can_see:", can_see)
        return False

    def delete_can_see(self, h):
        """
        Deletes document that can be seen by event hash

        :param h: event hash
        :type h: str
        :return: was the delete operation successful
        :rtype: bool
        """
        try:
            self.logger.debug("Delete from Can_see %s", str(h))
            self.db.can_see.remove(
                {'_id': h},
                {'justOne': True})
            return True
        except Exception as e:
            self.logger.error("Could not delete from Can_see. Reason: %s", str(e))
        return False

    def delete_references_can_see(self, hash_list):
        """
        Deletes all references to signed hashes

        :param hash_list: list of signed events
        :type hash_list: tuple
        :return: was the delete operation successful
        :rtype: bool
        """
        try:
            for h in hash_list:
                self.logger.debug("Delete reference from Can_see hash = %s", str(h))
                self.db.can_see.update({}, {
                    '$pull': {'can_see': {'$or': [{'parent': h}, {'event': h}]}}
                }, upsert=False, multi=True)
            return True
        except Exception as e:
            self.logger.error("Could not delete from Can_see. Reason: %s", str(e))
        return False