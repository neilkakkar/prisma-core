# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging

class Head(object):
    def __init__(self, prismaDB, super):
        self.logger = logging.getLogger('PrismaDB-Head')
        self.db = prismaDB
        self.super = super

    def get_head(self):
        """
        Gets cryptograph head from db

        :return:    * hash of head event
                    * False if error
        :rtype: str or bool
        """
        head_list = []
        try:
            _heads = self.db.head.find()
            if _heads:
                for _head in _heads:
                    head_list.append(_head)
                if len(head_list) > 0 and 'head' in head_list[0]:
                    self.logger.debug("Get from Head %s", str(head_list[0]['head']))
                    return head_list[0]['head']
            return head_list
        except Exception as e:
            self.logger.error("Could not get head. Reason: %s", str(e))
        return False

    def insert_head(self, head):
        """
        Inserts cryptograph head to db

        :param head: hash of head event
        :type head: str
        :return: was the insertion successful
        :rtype: bool
        """
        try:
            if head:
                self.logger.debug("Insert Head %s", str(self.db.head.update({}, {"$set": {'head': head}}, upsert=True)))
                return True
        except Exception as e:
            self.logger.error("Could not insert head. Reason: %s", str(e))
            self.logger.debug("Head:", head)
        return False
