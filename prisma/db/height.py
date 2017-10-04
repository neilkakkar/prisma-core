# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging

class Height(object):
    def __init__(self, prismaDB, super):
        self.logger = logging.getLogger('PrismaDB-Height')
        self.db = prismaDB
        self.super = super

    def get_height(self, event_id):
        """
        Gets height of given event (hash) from db

        :param event_id: event hash
        :type event_id: str
        :return:    * height
                    * False if error
        :rtype: int or bool
        """
        try:
            if event_id:
                _height = self.db.height.find_one({'_id': event_id})
                if _height and 'height' in _height:
                    self.logger.debug("Get from Heights %s", str(_height['height']))
                    return _height['height']
        except Exception as e:
            self.logger.error("Could not get round. Reason: %s", str(e))
            self.logger.debug("Event:", event_id)
        return False

    def get_heights_many(self):
        """
        Gets all heights info

        :return: height in format {hash: height}
        :rtype: dict
        """
        heights_dict = {}
        try:
            _heights = self.db.height.find()
            if _heights:
                for event in _heights:
                    if '_id' in event and 'height' in event:
                        heights_dict[event['_id']] = event['height']
                self.logger.debug("Get from Heights %s", str(heights_dict))
            return heights_dict
        except Exception as e:
            self.logger.error("Could not get heights. Reason: %s", str(e))
        return False

    def insert_height(self, height_info):
        """
        Inserts height of event to db

        :param height_info: data in format {hash: height}
        :type height_info: dict
        :return: was the insertion successful
        :rtype: bool
        """
        try:
            if height_info:
                self.logger.debug("Insert into Height %s", str(height_info))
                for height_id in height_info:
                    self.logger.debug("Result %s", str(self.db.height.update(
                        {'_id': height_id},
                        {'_id': height_id, 'height': int(height_info[height_id])},
                        upsert=True
                    )))
                return True
        except Exception as e:
            self.logger.error("Could not insert height. Reason: %s", str(e))
            self.logger.debug("Height:", height_info)
        return False

    def delete_height(self, h):
        """
        Deletes height by event hash

        :param h: event hash
        :type h: str
        :return: was the delete operation successful
        :rtype: bool
        """
        try:
            self.logger.debug("Delete from Height %s", str(h))
            self.db.height.remove(
                {'_id': h},
                {'justOne': True})
            return True
        except Exception as e:
            self.logger.error("Could not delete from Height. Reason: %s", str(e))
        return False
