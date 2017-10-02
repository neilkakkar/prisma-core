# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging

class sign(object):
    def __init__(self, prismaDB, super):
        self.logger = logging.getLogger('PrismaDB-sign')
        self.db = prismaDB
        self.super = super

    def get_signature(self, last_round):
        """
        Gets signatures for last round

        :param last_round: last round of state
        :type last_round: int
        :return: signatures or False if error
        :rtype: dict or bool
        """
        try:
            self.logger.debug("Get signatures for last_round = %s", str(last_round))
            sign = self.db.signature.find({'_id': last_round}).limit(1)
            if sign:
                for sg in sign:
                    return sg
        except Exception as e:
            self.logger.error("Could not signature for last_round = %s. Reason: %s", str(last_round), str(e))
        return False

    def get_signature_grater_than(self, last_round):
        """
        Gets signatures with start greater than the given one

        :param last_round: last round of state
        :type last_round: int
        :return: signatures or False if error
        :rtype: dict or bool
        """
        try:
            sign = self.db.signature.find({'_id': {'$gt': last_round}}).limit(1)
            if sign:
                for sg in sign:
                    return sg
        except Exception as e:
            self.logger.error("Could not signature grater than %s witness. Reason: %s", str(last_round), str(e))
        return False

    def check_if_signature_present(self, last_round, ver_key):
        """
        Checks whether a signature with that verify_key key is present in db

        :param last_round: last round of state
        :type last_round: int
        :param ver_key: verify_key of sign
        :type ver_key: str
        :return: False if it was found, True if was not found or error
        :rtype: bool
        """
        try:
            sign = self.db.signature.find({'_id': last_round, 'sign.verify_key': ver_key}).count()
            if sign:
                return True
            else:
                return False
        except Exception as e:
            self.logger.error("Could not check if signature present. Reason: %s", str(e))
        return True

    def insert_signature(self, signature):
        """
        Inserts signature into db

        :param signature: sign - contain: signature itself, start value and consensus hash
        :type signature: dict
        :return: was the insertion successful
        :rtype: bool
        """
        try:
            if signature and not self.check_if_signature_present(signature['last_round'], signature['sign']['verify_key']):
                self.db.signature.update({'_id': signature['last_round']},
                                         {'$addToSet': {'sign': signature['sign']},
                                          '$set': {
                                              '_id': signature['last_round'],
                                              'hash': signature['hash']
                                          }}, upsert=True)
                return True
        except Exception as e:
            self.logger.error("Could not insert signature. Reason: %s", str(e))
            self.logger.debug("Signature:", signature)
        return False

    def unset_unchecked_signature(self, last_round):
        """
        Deletes all unchecked signatures
        (unchecked means that we have not compared this remote hash with our local)

        :param last_round: last round of state
        :type last_round: int
        :return: was the delete operation successful
        :rtype: bool
        """
        try:
            self.db.signature.update({'_id': last_round},
                                     {'$unset': {'unchecked_pair': ''}})
            return True
        except Exception as e:
            self.logger.error("Could not unset unchecked in signature. Reason: %s", str(e))
            self.logger.debug("Start:", last_round)
        return False

    def insert_signature_unchecked(self, signature):
        """
        Inserts signature as unchecked
        (unchecked means that we have not compared this remote hash with our local)

        :param signature: sign - contains: sign itself, start value and consensus hash
        :type signature: dict
        :return: was the insertion successful
        :rtype: bool
        """
        try:
            self.logger.debug("Insert signature as unchecked %s", str(signature))
            if signature:
                self.db.signature.update({'_id': signature['last_round']},
                                         {'$addToSet': {'unchecked_pair': {signature['hash']: signature['sign']}},
                                          '$set': {
                                              '_id': signature['last_round']
                                          }}, upsert=True)
                return True
        except Exception as e:
            self.logger.error("Could not insert unchecked signature. Reason: %s", str(e))
            self.logger.debug("Unchecked Signature: %s", str(signature))
        return False