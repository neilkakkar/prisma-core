# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging

class Votes(object):
    def __init__(self, prismaDB, super):
        self.logger = logging.getLogger('PrismaDB-votes')
        self.db = prismaDB
        self.super = super

    def get_vote(self, vote_id):
        """
        Gets vote from db by event id

        :param vote_id: hash events the votes of which we are looking for
        :type vote_id: str
        :return:    * votes dict in format {hash: vote(T/F)}
                    * False - if error
        """
        try:
            if vote_id:
                _vote = self.db.votes.find_one({'_id': vote_id})
                if _vote and 'vote' in _vote:
                    self.logger.debug("Get from Vote %s", str(_vote['vote']))
                    return _vote['vote']
        except Exception as e:
            self.logger.error("Could not get vote. Reason: %s", str(e))
        return False

    def insert_vote(self, vote):
        """
        Inserts vote to db

        :param vote: vote info in format {who vote(hash):{for whom(hash): vote(T/F)}}
        :type vote: dict
        :return: was the insertion successful
        :rtype: bool
        """
        try:
            if vote:
                for vote_id in vote:
                    for key, val in vote[vote_id].items():
                        self.logger.debug("Result %s", self.db.votes.update(
                            {'_id': vote_id},
                            {'$set': {'_id': vote_id, 'vote.' + key: val}}, upsert=True
                        ))
                return True
        except Exception as e:
            self.logger.error("Could not insert Vote. Reason: %s", str(e))
            self.logger.debug("Vote:", vote)
        return False

    def delete_votes(self, h):
        """ Deletes votes from db by given hash

        :param h: event hash to be found
        :type h: str
        :return: was the delete operation successful
        :rtype: bool
        """
        try:
            self.logger.debug("Delete from Votes %s", str(h))
            self.db.votes.remove(
                {'_id': h},
                {'justOne': True})
            return True
        except Exception as e:
            self.logger.error("Could not delete from Votes. Reason: %s", str(e))
        return False

    # Famous

    def get_famous(self, witness):
        """
        Gets whether the witness is famous or not from db

        Return None here? We can check the return value of None (if not None:).
        The return value will be either False or True when it comes to a famous witness,
        so we can not do a simple if statement to check the return value from this function.

        :param witness: event hash
        :type witness: str
        :return:    * True/False - if it was found in db
                    * None  - if the hash does not exist
        :rtype: bool or None
        """
        try:
            if witness:
                _witness = self.db.famous.find_one({'_id': witness})
                if _witness:
                    self.logger.debug("Get from Famous hash = %s, result =  %s", str(witness), str(_witness['famous']))
                    return [_witness['famous']]
        except Exception as e:
            self.logger.error("Could not get famous witness. Reason: %s", str(e))

        self.logger.debug("Get from Famous hash = %s, result =  None", str(witness))
        return None

    def get_famous_many(self):
        """
        Gets all famous witnesses from db

        :return:    * famous info in format {hash: is famous(T/F)}
                    * False - if error
        :rtype: dict or bool
        """
        mfamous_dict = {}
        try:
            _mfamous = self.db.famous.find()
            if _mfamous:
                for famous in _mfamous:
                    if '_id' in famous and 'famous' in famous:
                        mfamous_dict[famous['_id']] = famous['famous']
            return mfamous_dict
        except Exception as e:
            self.logger.error("Could not get famous witnesses. Reason: %s", str(e))
        return False

    def insert_famous(self, famous_info):
        """
        Inserts famous info into db
        
        :param famous_info: data in format {hash: is famous(T/F)}
        :type famous_info: dict
        :return: was the insertion successful
        :rtype: bool
        """
        try:
            if famous_info:
                self.logger.debug("Insert into Famous %s", str(famous_info))
                for wit_id in famous_info:
                    self.logger.debug("Result Famous %s", str(self.db.famous.update(
                        {'_id': wit_id},
                        {'$set': {'_id': wit_id, 'famous': famous_info[wit_id]}}, upsert=True
                    )))
                return True
        except Exception as e:
            self.logger.error("Could not insert Famous. Reason: %s", str(e))
            self.logger.debug("Witnesses:", famous_info)
        return False

    def check_famous(self, h):
        """
        Checks if hash is present in famous

        :param h: event hash
        :type h: str
        :return: is present or not
        :rtype: int
        """
        try:
            is_famous = self.db.famous.find({'_id': h}, {'_id': 1}).limit(1).count()
            self.logger.debug("Check famous for hash = %s, result = %s", str(h), str(is_famous))
            return is_famous
        except Exception as e:
            self.logger.error("Could not check famous. Reason: %s", str(e))
        return False

    def delete_famous(self, h):
        """ Deletes famous info with given hash from db

        :param h: event hash
        :type h: str
        :return: was the delete operation successful
        :rtype: bool
        """
        try:
            self.logger.debug("Delete from Famous %s", str(h))
            self.db.famous.remove(
                {'_id': h},
                {'justOne': True})
            return True
        except Exception as e:
            self.logger.error("Could not delete from Famous. Reason: %s", str(e))
        return False
