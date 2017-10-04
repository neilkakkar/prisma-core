# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging

from pymongo.errors import DuplicateKeyError

class Rounds(object):

    def __init__(self, prismaDB, super):
        self.logger = logging.getLogger('PrismaDB-Rounds')
        self.db = prismaDB
        self.super = super

    def get_round(self,h):
        """
        Gets one round from db

        :param h: event hash(key)
        :type h: str
        :return:    * round -  if the document was found in collection
                    * False   - if the document was not found in collection OR in the case of error
        :rtype: int
        """

        if h:
            try:
                _round = self.db.rounds.find_one({'_id': h})
                if _round and 'round' in _round:
                    self.logger.debug("Get from Rounds for hash %s, round = %s", str(h), str(_round['round']))
                    return _round['round']
                """ If the round data does not exist, is it safe to assume its round is 0? """
            except Exception as e:
                self.logger.error("Could not get round. Reason: %s", str(e))
                self.logger.debug("Event:", h)
        return False

    def get_rounds_many(self, less_than):
        """
        Gets all rounds from db

        :param less_than: limitation for round num
        :type less_than: int/bool(by default)
        :return: round for every hash or False if error
        :rtype: dict or bool
        """
        rounds_dict = {}
        try:
            if less_than:
                _rounds = self.db.rounds.find({'round': {'$lte': less_than}})
            else:
                _rounds = self.db.rounds.find()
            if _rounds:
                for r in _rounds:
                    if '_id' in r and 'round' in r:
                        rounds_dict[r['_id']] = r['round']
                    self.logger.debug("Get from Rounds %s", str(rounds_dict))
            return rounds_dict
        except Exception as e:
            self.logger.error("Could not get rounds. Reason: %s", str(e))
        return False

    def get_rounds_max(self):
        """
        Gets max round stored in db

        :return:    * round - if the document was found in collection
                    * 0 - if the collection is empty
                    * False -  in the case of error
        :rtype: int
        """

        try:
            _rounds = self.db.rounds.find().sort('round', -1).limit(1)
            if _rounds:
                for r in _rounds:
                    if 'round' in r:
                        self.logger.debug("Get max round from Round %s", str(r['round']))
                        return r['round']
            return 0
        except Exception as e:
            self.logger.error("Could not get max round from Round. Reason: %s", str(e))
        return False

    def get_rounds_hash_list(self, value):
        """
        Gets hashes of events with round less than given value

        :param value: start round num
        :type value: int
        :return: id (hash) values from all documents with round less than given value
        :rtype: list
        """

        hash_list = []
        try:
            _hashes = self.db.rounds.find({'round_handled': {'$lte': value}})
            if _hashes:
                for h in _hashes:
                    if '_id' in h and 'round' in h:
                        hash_list.append(h['_id'])
                    self.logger.debug("Get from Rounds less than %s", str(value))
            return hash_list
        except Exception as e:
            self.logger.error("Could not get from rounds less than %s. Reason: %s", str(value), str(e))
        return False

    def get_rounds_less_than(self,r):
        """
        Gets documents with round less than given one

        :param r: round num
        :type r: int
        :return: documents with round less than given one
        :rtype: list
        """
        try:
            res_dict = {}
            _hashes = self.db.rounds.find({'round': {'$lt': r}})
            if _hashes:
                for h in _hashes:
                    if '_id' in h and 'round' in h:
                        res_dict[h['_id']] = h['round']
                    self.logger.debug("Get hash list from Rounds, round = %s", str(r))
            return res_dict
        except Exception as e:
            self.logger.error("Could not get hash list from Rounds. Reason: %s", str(e))
            return False

    def insert_round(self, round_info):
        """
        Inserts one round into db

        :param round_info: dict in format {hash:round}
        :type round_info: dict
        :return: was the insertion successful
        :rtype: bool
        """
        try:
            if round_info:
                self.logger.debug("Insert into Rounds %s", str(round_info))
                for round_id in round_info:
                    res = self.db.rounds.update({'_id': round_id},
                                                {'$set':{'_id': round_id, 'round': int(round_info[round_id])}}, upsert=True)
                    self.logger.debug("Insert into Rounds collection result %s", str(res))
                return True
        except DuplicateKeyError:
            self.logger.error("Could not insert round. Reason: duplicate (_id) round id.")
        except Exception as e:
            self.logger.error("Could not insert round. Reason: %s", str(e))
            self.logger.debug("Round:", round_info)
        return False

    def set_round_handled(self, round_info):
        """
        Set round when event was handled

        :param round_info: dict in format {hash:round}
        :type round_info: dict
        :return: was the insertion successful
        :rtype: bool
        """
        try:
            if round_info:
                self.logger.debug("Set round handled %s", str(round_info))
                for round_id in round_info:
                    self.db.rounds.update({'_id': round_id},
                                                {'$set': {'round_handled': int(round_info[round_id])}}
                                                , upsert=False)
                return True
        except DuplicateKeyError:
            self.logger.error("Could not set handled round. Reason: duplicate (_id) round id.")
        except Exception as e:
            self.logger.error("Could not set handled round. Reason: %s", str(e))
            self.logger.debug("Round info:", round_info)
        return False

    def delete_round_less_than(self, value):
        """
        Deletes all documents with round less than value

        :param value: start round num
        :type value: int
        :return: was the delete operation successful
        :rtype: bool
        """
        try:
            self.logger.debug("Delete from Rounds less than %s", str(value))
            self.db.rounds.remove({'round': {'$lt': value}})
            return True
        except Exception as e:
            self.logger.error("Could not delete round. Reason: %s", str(e))
        return False

    def delete_round_greater_than(self, value):
        """
        Deletes all documents with round greater than value

        :param value: start round num
        :type value: int
        :return: was the delete operation successful
        :rtype: bool
        """
        try:
            self.logger.debug("Delete from Rounds greater than %s", str(value))
            self.db.rounds.remove({'round': {'$gt': value}})
            return True
        except Exception as e:
            self.logger.error("Could not delete round. Reason: %s", str(e))
        return False
