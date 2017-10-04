# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging
import sys
from pymongo import ASCENDING, DESCENDING
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from pymongo.errors import CollectionInvalid
from pymongo.errors import ConnectionFailure

from prisma.config import CONFIG


class Peer(object):
    def __init__(self, prismaDB, super):
        self.logger = logging.getLogger('PrismaDB-Peer')
        self.db = prismaDB
        self.super = super

    def get_peer(self, ip):
        # No usage
        try:
            if ip:
                _peer = self.db.peers.find_one({'_id': ip})
                return _peer
        except Exception as e:
            self.logger.error("Could not get peer. Reason: %s", str(e))
            self.logger.debug("Peer:", ip)
        return False

    def get_peers_many(self):
        """
        Gets all peers stored in db

        :return: peer list or False if error
        :rtype: tuple or bool
        """
        peer_list = []
        try:
            _peers = self.db.peers.find()
            if _peers:
                for _peer in _peers:
                    peer_list.append(_peer)
            return peer_list
        except Exception as e:
            self.logger.error("Could not get peers. Reason: %s", str(e))
        return False

    def count_peers(self):
        """
        Counts number of peers before the start of events syncing.
        Consensus states that at least 3 node should be online.

        :return: peer count
        :rtype: int
        """
        try:
            return self.db.peers.count()
        except Exception as e:
            self.logger.error("Could not get peer count. Reason: %s", str(e))
        """ Note: 0 can also mean False in python."""
        return 0

    def insert_peer(self, peer):
        """
        Inserts peer into db

        :param peer: peer info
        :type peer: dict
        :return: was the insertion successful
        :rtype: bool
        """
        try:
            if peer and '_id' in peer:
                # host is forced to 8000 unless it's in developer mode
                port = 8000
                if CONFIG.getboolean('developer', 'developer_mode'):
                    port = peer['port']
                self.db.peers.update({'_id': peer['_id']}, {'$set':  {'seen': peer['seen'],
                                                                      'latest_event': peer['latest_event'],
                                                                      'host': peer['host'],
                                                                      'port': port}}, upsert=True)
            return True
        except Exception as e:
            self.logger.error("Could not insert peer. Reason: %s", str(e))
            self.logger.debug("Peer:", peer)
        return False

    def delete_peers(self):
        """
        Deletes all peers stored in db

        :return: was the delete operation successful
        :rtype: bool
        """
        try:
            if self.db.peers.remove({}):
                return True
        except Exception as e:
            self.logger.error("Could not delete peer table. Reason: %s", str(e))
        return False

    def delete_peer(self, ip):
        # No usage
        try:
            if ip and self.db.peers.remove({'_id': ip}):
                return True
        except Exception as e:
            self.logger.error("Could not delete peer %s from peer table: %s", str(ip), str(e))
        return False

    def get_random_peer(self):
        # No usage
        try:
            peer_list = []
            peer = self.db.peers.aggregate([{"$sample": {'size': 1}}])
            for p in peer:
                peer_list.append(p)
            return peer_list
        except Exception as e:
            self.logger.error("Could not retrieve a random peer from database. Reason:", str(e))
        return False