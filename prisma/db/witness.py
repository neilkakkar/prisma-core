# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging

class Witness(object):

    def __init__(self, prismaDB, super):
        self.logger = logging.getLogger('PrismaDB-Witness')
        self.db = prismaDB
        self.super = super

    def get_witness(self, r):
        """
        Gets witnesses for given round

        :param r: round num for witnesses to be found
        :type r: int
        :return:    * all witnesses with given round
                    * False - if error
        :rtype: dict or bool
        """
        try:
            self.logger.debug("GET FROM WIT, WIT = %s", str(r))
            _witness = self.db.witness.find_one({'_id': r})
            if _witness and 'witness' in _witness:
                self.logger.debug("Get from Witness %s", str(_witness['witness']))
                return _witness['witness']
            return {}
        except Exception as e:
            self.logger.error("Could not get witness. Reason: %s", str(e))
            self.logger.debug("Witness:", r)
        return False

    def get_witness_max_round(self):
        """
        Gets max round stored in witness

        :return:    * max round - if it was found
                    * 0 - if the collection is empty
                    * False - if error
        :rtype: int or bool
        """
        try:
            _witness = self.db.witness.find().sort('_id', -1).limit(1)
            if _witness:
                for wit in _witness:
                    if '_id' in wit:
                        self.logger.debug("Get max round from Witness %s", str(wit['_id']))
                        return wit['_id']
            return 0
        except Exception as e:
            self.logger.error("Could not get max round  from Witness. Reason: %s", str(e))
        return False

    def insert_witness(self, witness_info):
        """
        Inserts one witness to db

        :param witness_info: witness data in format {round:{hash:hash}}
        :type witness_info: dict
        :return: was the insertion successful
        :rtype: bool
        """

        try:
            if witness_info:
                self.logger.debug("Insert into witness collection %s", str(witness_info))
                for r in witness_info:
                    for key, val in witness_info[r].items():
                        res = self.db.witness.update(
                            {'_id': int(r)},
                            {'$set': {'witness.' + key: val}},
                            upsert=True
                        )
                        #self.logger.debug("Insert into witness collection result %s", str(res))
                return True
        except Exception as e:
            self.logger.error("Could not insert witness. Reason: %s", str(e))
            self.logger.debug("Witness:", witness_info)
        return False

    def delete_witnesses_less_than(self, r):
        """
        Deletes witnesses with round less than given

        :param r: start round num
        :type r: int
        :return: was the delete operation successful
        :rtype: bool
        """
        try:
            self.logger.debug("Delete from Witnesses %s", str(r))
            self.db.witness.remove({'_id': {'$lt': r}})
            return True
        except Exception as e:
            self.logger.error("Could not delete from Witnesses. Reason: %s", str(e))
        return False