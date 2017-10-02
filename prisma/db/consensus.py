# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging

class consensus(object):
    def __init__(self, prismaDB, super):
        self.logger = logging.getLogger('PrismaDB-consensus')
        self.db = prismaDB
        self.super = super

    def get_consensus_many(self, lim=0, sign=False, sort=False):
        """
        Gets many consensus info from db

        :param lim: limit of documents to be found
        :type lim: int (Note: 0 - means there is no limit)
        :param sign: gets signed or unsigned
        :type sign: bool
        :param sort: how data should be sorted:
                        * False - by id
                        * 1 - Ascending
                        * -1 - Descending
        :type sort: bool or int
        :return: consensus list
        :rtype: tuple
        """
        result = []
        try:
            if not sort:
                _consensus = self.db.consensus.find({'signed': sign}).limit(lim)
            else:
                _consensus = self.db.consensus.find({'signed': sign}).sort('consensus', sort).limit(lim)
            if _consensus:
                for cs in _consensus:
                    if cs and 'consensus' in cs:
                        result.append(cs['consensus'])
                self.logger.debug("GetConsensus: {0}".format(result))
            return result
        except Exception as e:
            self.logger.error("Could not get consensus. Reason: %s", str(e))
            self.logger.debug("SORT: {0}".format(sort))
        return result

    def get_consensus_count(self):
        """
        Gets how many consensus are stored in db

        :return: consensus count or 0 if the collection is empty
        :rtype: int
        """
        try:
            count = self.db.consensus.find({}).count()
            self.logger.debug("Get consensus count: {0}".format(count))
            return count
        except Exception as e:
            self.logger.error("Could not get consensus. Reason: %s", str(e))
        return 0

    def get_consensus_greater_than(self, value, lim=0):
        """
        Gets all consensus with value greater than the given one

        :param value: value to start
        :type value: int
        :param lim: limit of documents to be found
        :type lim: int
        :return: consensus list
        :rtype: tuple
        """
        result = []
        try:
            _consensus = self.db.consensus.find({'consensus': {'$gt': value}}).limit(lim)
            self.logger.debug("value: {0}".format(value))
            self.logger.debug("limit: {0}".format(lim))
            self.logger.debug("GRATER THAN: {0} ".format(_consensus))
            if _consensus:
                for cs in _consensus:
                    self.logger.debug("cs: {0}".format(cs))
                    if cs and 'consensus' in cs:
                        result.append(cs['consensus'])
                self.logger.debug("Get from consensus greater than value: {0}, {1}".format(value, result))
        except Exception as e:
            self.logger.error("Could from consensus greater than value. Reason: %s", str(e))
        return result

    def get_consensus_last_sent(self):
        """
        Gets consensus with last sent flag

        :return:    * Last sent consensus - if found
                    * -1 - if it does not exist
                    * False - if error
        :rtype: int or bool
        """
        try:
            _consensus = self.db.consensus.find({'last_sent': {'$exists': True}})

            if _consensus:
                for item in _consensus:
                    self.logger.debug("CHECK = %s", str(item))
                    if 'consensus' in item:
                        self.logger.debug("Get consensus last sent %s", str(item['consensus']))
                        return item['consensus']
            self.logger.debug("Last sent not found return last signed consensus")
            return self.get_consensus_last_signed()
        except Exception as e:
            self.logger.error("Could not get last sent from consensus. Reason: %s", str(e))
        return False

    def get_consensus_last_created_sign(self):
        """
        Gets consensus with last created signature flag

        :return:    * Last created signature - if it was found
                    * -1 - if it does not exist
                    * False - if error
        :rtype: int or bool
        """
        try:
            _consensus = self.db.consensus.find({'last_created_sign': {'$exists': True}})

            if _consensus:
                for item in _consensus:
                    self.logger.debug("CHECK = %s", str(item))
                    if 'consensus' in item:
                        self.logger.debug("Get consensus last sent %s", str(item['consensus']))
                        return item['consensus']
            self.logger.debug("Last created signature not found return last sent sign")
            return self.get_consensus_last_sent()
        except Exception as e:
            self.logger.error("Could not get last sent from consensus. Reason: %s", str(e))
            return False

    def get_consensus_last_signed(self):
        """
        Gets last signed round from db

        :return: last signed round or -1 if it does not exist
        :rtype: int
        """
        con = self.get_consensus_many(sign=True, lim=1, sort=-1)
        if con:
            return con[0]
        else:
            return -1

    def get_last_consensus(self):
        """
        Get last consensus round

        :return: last consensus round
        :rtype: int
        """
        try:
            last_consensus = self.db.consensus.find({}).sort('consensus', -1).limit(1)
            for res in last_consensus:
                return res['consensus']
            return -1
        except Exception as e:
            self.logger.error("Could not get consensus. Reason: %s", str(e))
            return False

    def insert_consensus(self, consensus, signed=False):
        """
        Inserts consensus into db

        :param consensus: consensus (Note: by default, consensus is unsigned)
        :type consensus: int
        :return: was the insertion successful
        :rtype: bool
        """
        try:
            for con in consensus:
                self.db.consensus.insert({'consensus': con, 'signed': signed})
            return True
        except Exception as e:
            self.logger.error("Could not insert consensus. Reason: %s", str(e))
            self.logger.debug("Consensus:", consensus)
        return False

    def check_consensus(self, r):
        """
        Checks if round is present in consensus

        :param h: round to check
        :type h: str
        :return: is present or not
        :rtype: int
        """
        try:
            is_present = self.db.consensus.find({'consensus': r}, {'_id': 1}).limit(1).count()
            self.logger.debug("Check consensus for round = %s, result = %s", str(r), str(is_present))
            return is_present
        except Exception as e:
            self.logger.error("Could not check famous. Reason: %s", str(e))
        return False

    def sign_consensus(self, count):
        """
        Signs some consensus

        :param count: how many consensuses should be signed
        :type count: int
        :return: was the sign operation successful
        :rtype: bool
        """
        try:
            if count:
                for i in range(count):
                    self.logger.debug("Result of sign consensus %s",
                                      str(self.db.consensus.update({'signed': False}, {'$set': {'signed': True}})))
            return True
        except Exception as e:
            self.logger.error("Could not sign consensus. Reason: %s", str(e))
            self.logger.debug("Count:", count)
        return False

    def set_consensus_last_sent(self, consensus):
        """
        Sets the last sent flag to consensus

        :param consensus: consensus value
        :type consensus: int
        :return: was the setting operation successful
        :rtype: bool
        """
        try:
            self.logger.debug("Set consensus last sent con = %s", str(consensus))
            self.db.consensus.update({'last_sent': {'$exists': True}}, {'$unset': {'last_sent': ''}})
            self.db.consensus.update({'consensus': consensus},
                                     {'$set': {'last_sent': True}})
            return True
        except Exception as e:
            self.logger.error("Could not set consensus last sent. Reason: %s", str(e))
            self.logger.debug("Consensus:", consensus)
            return False

    def set_consensus_last_created_sign(self, consensus):
        """
        Sets the last created signature flag to consensus

        :param consensus: consensus value
        :type consensus: int
        :return: was the setting operation successful
        :rtype: bool
        """
        try:
            self.logger.debug("Set last created signature con = %s", str(consensus))
            self.db.consensus.update({'last_created_sign': {'$exists': True}}, {'$unset': {'last_created_sign': ''}})
            self.db.consensus.update({'consensus': consensus},
                                     {'$set': {'last_created_sign': True}})
            return True
        except Exception as e:
            self.logger.error("Could not set last created signature. Reason: %s", str(e))
            self.logger.debug("Consensus:", consensus)
            return False
    