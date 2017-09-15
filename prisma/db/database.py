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

from prisma.utils.common import Common
from prisma.config import CONFIG
from prisma.cryptograph.transaction import TYPE_SIGNED_STATE, TYPE_MONEY_TRANSFER


class PrismaDB(object):
    """
    Database class.
    """
    def __init__(self, db_name):
        """
        Creates class instance

        :returns instance of PrismaDB class
        :rtype: object
        """
        self.logger = logging.getLogger('PrismaDB')
        self.common = Common()

        try:
            self.connection = MongoClient(serverSelectionTimeoutMS=2000, connect=False)
        except Exception as e:
            self.logger.error('%s.', str(e))
            sys.exit(1)

        self.logger.info('Connecting to MongoDB on localhost.')
        self.db = self.connection[db_name]

        if not self.is_running():
            self.logger.error("MongoDB is not started, exiting.")
            sys.exit(1)

        self.logger.info('MongoDB v%s, using database "%s".', self.get_version(), self.get_db_name())
        self.collections_list = ['events', 'rounds', 'can_see', 'height', 'head', 'peers', 'witness', 'famous',
                                 'votes', 'transactions', 'consensus', 'signature', 'state']
        self.create_collections()
        self.create_indexes()

    def create_indexes(self):
        """
        Creates index based on event time.
        This will be useful for remote graphs that want to sync events between particular time stamps.

        :returns: None
        """
        try:

            self.logger.debug("Creating index in descending order for events.")
            self.db.events.create_index([("event.t", DESCENDING)], background=True)
        except Exception as e:
            self.logger.error("Could not create index on events collection. Reason:", str(e))
            self.logger.warning("Running a database collection without an index might impact performance.")

        if not CONFIG.getboolean('developer', 'developer_mode'):
            try:
                self.logger.debug("Creating indexes for peers.")
                self.db.peers.create_index([("host", DESCENDING)], background=True, unique=True)
            except Exception as e:
                self.logger.error("Could not create index on peers collection. Reason:", str(e))
                self.logger.warning("Running a database collection without an index might impact performance.")

    def destroy_db(self, name=None):
        """
        Destroys database

        :param name: database name
        :type name: str or None
        :return: was the destruction successful
        :rtype: bool
        """
        try:
            name = name or self.get_db_name()
            self.connection.drop_database(name)
            self.logger.info('Deleted database: %s.', str(name))
            return True
        except Exception as e:
            self.logger.error("Could not delete database: %s. Reason: %s", str(name), str(e))
        return False

    def create_collections(self):
        """
        Creates all collections

        :return: was the creation successful
        :rtype: bool
        """
        for collection in self.collections_list:
            try:
                self.db.create_collection(collection)
            except CollectionInvalid:
                pass
            except Exception as e:
                self.logger.error('Could not create collection: %s. Reason: %s', collection, str(e))
                return False

        return True

    def drop_collections_many(self, exceptions=[]):
        """
        Drop all collections exept given ones

        :param exceptions: collections that should not be deleted
        :type exceptions: list
        :return: was the drop operation successful
        :rtype: bool
        """
        for collection_name in self.collections_list:
            if collection_name not in exceptions:
                if not self.drop_collection(collection_name):
                    return False
        return True

    def drop_collection(self, collection_name):
        """
        Drop one collection from db

        :param collection_name: name of collection to drop
        :type collection_name: str
        :return: was the drop operation successful
        :rtype: bool
        """
        try:
            getattr(self.db, collection_name).drop()
        except Exception as e:
            self.logger.error('Could not delete collection: %s. Reason: %s', collection_name, str(e))
            return False

        return True

    # Events

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
                    last_signed = self.get_consensus_last_signed()
                    for p in cg_dict[event_id]['p']:
                        rnd = self.get_round(p)
                        if rnd == -1:
                            self.logger.error("Could not find hash in rounds !")
                            return False

                        if rnd > last_signed:
                            new_parents_list.append(p)
                    cg_dict[event_id]['p'] = new_parents_list

            self.logger.debug("Get from Events %s", str(cg_dict))
            if as_tuple and len(_event) > 0:
                return self.common.dict_to_tuple(cg_dict)[event_id]
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
            return self.common.dict_to_tuple(cg_dict)
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
                        {'_id': ev_id, 'event': self.common.tuple_to_dict(event[ev_id])})))
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

    # Rounds

    def get_round(self, h):
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

    def get_rounds_many(self, less_than=False):
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

    def get_rounds_less_than(self, r):
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

    # Can see

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

    # Head

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

    # Height

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

    # Witness

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

    # Transactions

    def get_transactions_many(self):
        """
        Gets all transactions from db

        :return: list of all transactions stored in db (without round)
        :rtype: tuple
        """
        transaction_list = []
        try:
            _transactions = self.db.transactions.find()
            if _transactions:
                for tx in _transactions:
                    if tx and '_id' in tx:
                        transaction_list.append(tx['_id'])
        except Exception as e:
            self.logger.error("Could not get transactions. Reason: %s", str(e))
        return transaction_list

    def get_unsent_transactions_many(self, account_id):
        """
        Gets all unsent transactions from db.
        Unsent mean that event for that tx was not created

        :param account_id: our local account id
        :type account_id: str
        :return: list of all unsent transactions stored in db, and list of their ids
        :rtype: tuple
        """
        transaction_list = []
        id_list = []
        try:
            transactions = self.db.transactions.find({
                'event_hash': {'$exists': False},
                '$or': [{'senderId': account_id}, {'type': TYPE_SIGNED_STATE}]
            })
            if transactions:
                for tx in transactions:
                    self.logger.debug("get_unsent_transactions_many item %s", str(tx))
                    if '_id' in tx and 'tx_dict_hex' in tx:
                        id_list.append(tx['_id'])
                        transaction_list.append(tx['tx_dict_hex'])
                    else:
                        self.logger.error("Incorrect tx in db !")
                        continue
        except Exception as e:
            self.logger.error("Could not get transactions. Reason: %s", str(e))
        return id_list, transaction_list

    def get_all_known_wallets(self):
        """
        Finds and returns all unique wallets in transactions and last state

        :return: unique wallets stored in db
        :rtype: set
        """
        wallets = set()
        try:
            # Gets all wallets in transactions
            db_res = self.db.transactions.aggregate([
                {'$group': {'_id': 0,
                            'sender_wallets': {'$addToSet': '$senderId'},
                            'recipient_wallets': {'$addToSet': '$recipientId'}}},
                {'$project': {'balance': {'$setUnion': ['$sender_wallets', '$recipient_wallets']}}}])
            if db_res:
                for wal in db_res:
                    self.logger.debug("TX_WAL %s", str(wal))
                    wallets |= set(wal['balance'])

                # Gets all wallets saved in state
                wallets |= self.get_wallets_state()
        except Exception as e:
            self.logger.error("Could not get all known wallets. Reason: %s", str(e))
        return wallets

    def get_account_balance(self, account_id, r=False):
        """
        Gets account balance from transactions and last state

        :param account_id: wallet id to search
        :type account_id: str
        :param r: range of rounds
        :type r: list
        :return: account balance
        :rtype: int
        """
        sent = 0
        received = 0

        round_check = None
        if r:
            round_check = {'$gte': r[0], '$lte': r[1]}

        try:
            match_dict = {'senderId': account_id}
            if round_check:
                match_dict['round'] = round_check

            pipe_sent = [{'$match': match_dict},
                         {'$group': {'_id': None, 'amount': {'$sum': '$amount'}}}]
            for i in self.db.transactions.aggregate(pipeline=pipe_sent):
                if 'amount' in i:
                    sent = i['amount']
        except Exception as e:
            self.logger.debug("Could not retrieve account balance. Reason: %s", str(e))
            return False

        try:
            match_dict = {'recipientId': account_id}
            if round_check:
                match_dict['round'] = round_check

            pipe_rec = [{'$match': match_dict},
                        {'$group': {'_id': None, 'amount': {'$sum': '$amount'}}}]
            for i in self.db.transactions.aggregate(pipeline=pipe_rec):
                if 'amount' in i:
                    received = i['amount']
        except Exception as e:
            self.logger.debug("Could not retrieve account balance. Reason: %s", str(e))
            return False

        tx_balance = received - sent
        bal_res = tx_balance + self.get_state_balance(account_id)
        self.logger.debug("BAl_RES %s", str(bal_res))
        return bal_res

    def get_account_balance_many(self, range=False):
        """
        Gets balance for all known wallets

        :param range: range of rounds
        :type range: list
        :return: balance for all known wallets in format {address: amount}
        :rtype: dict
        """
        wallets_balance = {}
        for w_id in self.get_all_known_wallets():
            bal = self.get_account_balance(w_id, range)

            if bal:
                wallets_balance[w_id] = bal
        return wallets_balance

    def insert_transactions(self, tx_list):
        """
        Inserts prepared tx into db.
        Should not be invoked directly, only from transaction class

        :param tx_list: list of transactions to be inserted
        :type tx_list: list
        :return: was the insertion successful
        :rtype: bool
        """
        try:
            self.logger.debug("TX LSIT : %s", str(tx_list))
            if len(tx_list) > 0:
                self.db.transactions.insert_many(tx_list)
            return True
        except Exception as e:
            self.logger.error("Could not insert transactions. Reason: %s", str(e))
        return False

    def set_transaction_hash(self, tx_list):
        """
        Sets event_hash to transaction
        When event will be created and tx will be inserted,
        we should mark tx as sent, and store event hash

        :param tx_list: transaction to be set
        :type tx_list: tuple
        :return: was the setting operation successful
        :rtype: bool
        """
        try:
            event_hash = self.get_head()
            if event_hash:
                for tx_id in tx_list:
                    self.logger.debug("Set event hash to transaction with id = %s", str(tx_id))
                    self.db.transactions.update({'_id': tx_id}, {'$set': {'event_hash': event_hash}})
                return True
        except Exception as e:
            self.logger.error("Could not set event hash to transaction. Reason: %s", str(e))
            self.logger.debug("Tx list:", str(tx_list))
        return False

    def set_transaction_round(self, ev_hash, r):
        """
        When final order of transactions was found we should
        store round of transaction to create state later only
        from tx with round <= than last_round of state

        :param ev_hash: event hash for the round to be set
        :type ev_hash: str
        :param r: round of event
        :type r: int
        :return: was the setting operation successful
        :rtype: bool
        """
        try:
            res = self.db.transactions.update({'event_hash': ev_hash}, {'$set': {'round': r}},
                                              upsert=False, multi=True)
            self.logger.debug("Set round for our tx ev_hash = %s, round = %s, result = %s", str(ev_hash),
                              str(r), str(res))
            return True
        except Exception as e:
            self.logger.error("Could not set round for transaction. Reason: %s", str(e))
            self.logger.debug("Ev_hash:", str(ev_hash))
        return False

    def delete_transaction_less_than(self, r):
        """
        Deletes transaction with round less than given value

        :param r: start round num
        :type r: int
        :return: was the delete operation successful
        :rtype: bool
        """
        try:
            self.logger.debug("Delete from Transaction less than %s", str(r))
            result = self.db.transactions.remove({'round': {'$lte': r}})
            self.logger.debug("Delete from Transaction result %s", str(result))
            return True
        except Exception as e:
            self.logger.error("Could not delete transaction. Reason: %s", str(e))
            self.logger.debug("Round:", r)
        return False

    def delete_money_transfer_transaction_less_than(self, r):
        """
        Deletes transactions that contain money transfer and round <= than given one
        Should be invoked after the creation of state

        :param r: round
        :type r: int
        :return: was the delete operation successful
        :rtype: bool
        """
        try:
            self.logger.debug("Delete from money transfer transaction less than %s", str(r))
            result = self.db.transactions.remove({'round': {'$lte': r}, 'type': str(TYPE_MONEY_TRANSFER)})
            self.logger.debug("Delete from money transfer transaction result %s", str(result))
            return True
        except Exception as e:
            self.logger.error("Could not delete transaction. Reason: %s", str(e))
            self.logger.debug("Round:", r)
        return False

    # Votes

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

    # Consensus

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

    # Signature

    def get_signature(self, last_round):
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

    # State

    def get_last_state(self):
        """
        Gets the last state and round of the state.

        :return:
        """
        try:
            state = list(self.db.state.find().sort('_id', -1).limit(1))
            if not state:
                return False
            return state[0]
        except Exception as e:
            self.logger.error("Could not get the last state. Reason: %s", str(e))
            return False

    def get_state(self, r):
        """
        Gets state by last_round

        :param r: last_round for state
        :type r: int
        :return: state (balance of all wallets)
        :rtype: dict
        """
        try:
            state = self.db.state.find_one({'_id': r})
            self.logger.debug("Get state %s", str(state))
            return state
        except Exception as e:
            self.logger.error("Could not get state for round %s. Reason: %s", r, str(e))
        return False

    def get_state_many(self, sort=False, lim=0):
        """
        Gets all state stored in db

        :return: list of states
        :rtype: list
        """
        state = []
        try:
            if sort:
                db_res = self.db.state.find({}).sort('_id', sort).limit(lim)
            else:
                db_res = self.db.state.find({}).limit(lim)
            if db_res:
                for s in db_res:
                    state.append(s)
            self.logger.debug("Get state MANY %s", str(state))
            return state
        except Exception as e:
            self.logger.error("Could not get state. Reason: %s", str(e))
        return False

    def get_state_balance(self, address):
        """
        Gets wallet balance by address from last state

        :param address: address of wallet
        :type address: str
        :return: wallet balance
        :rtype: int
        """
        try:
            db_res = self.db.state.find({'balance.' + address: {'$exists': True}},
                                           {'_id': 0, 'balance.' + address: 1}).limit(1).sort('_id', -1)
            if db_res:
                for balance in db_res:
                    self.logger.debug("Get balance for address %s from state result = %s", str(address), str(balance['balance'][address]))
                    return balance['balance'][address]
                else:
                    self.logger.debug("No balance for address %s, return 0", str(address))
                    return 0
        except Exception as e:
            self.logger.error("Could not get state balance. Reason: %s", str(e))
            self.logger.debug("Address: %s", address)
        return False

    def get_wallets_state(self):
        """
        Gets all unique wallets in state

        :return:unique wallets
        :rtype: set
        """
        try:
            db_res = self.db.state.find().limit(1).sort('_id', -1)
            if db_res:
                for res in db_res:
                    self.logger.debug("Get wallets from state %s", str(res))
                    wallets = set(res['balance'].keys())
                    return wallets
            return set()
        except Exception as e:
            self.logger.error("Could not get state. Reason: %s", str(e))
        return False

    def insert_state(self, state, round, hash, signed=False):
        """
        Inserts state into db

        :param state: state itself
        :type state: dict
        :param round: last round of state
        :type round: int
        :param hash: state hash
        :type hash: str
        :param signed: is state already signed
        :type signed: bool
        :return: was the insertion successful
        :rtype: bool
        """
        try:
            self.db.state.insert({'_id': round, 'balance': state['balance'], 'hash': hash, 'signed': signed})
            self.logger.debug("Insert into state balance = %s, round = %s, hash = %s, signed = %s",
                              str(state), str(round), str(hash), str(signed))
            return True
        except Exception as e:
            self.logger.error("Could not insert state. Reason: %s", str(e))
        return False

    def set_state_signed(self, round):
        """
        Sets signed flag to state with last_round equal to given round

        :param round: last_round of state to sign
        :type round: int
        :return: was the setting operation successful
        :rtype: bool
        """
        try:
            self.db.state.update({'_id': round}, {'$set': {'signed': True}})
            self.logger.debug("Set state signed %s", str(round))
            return True
        except Exception as e:
            self.logger.error("Could set state signed. Reason: %s", str(e))
            self.logger.debug("Round:", round)
        return False

    def delete_state_less_than(self, round):
        """
        Deletes all signed states with round less than given.
        We should not store all signed states, so we delete existing, when
        we get new one.

        :param round: last_round of state
        :type round: int
        :return: was the delete operation successful
        :rtype: bool
        """
        try:
            self.logger.debug("Delete from state less than round %s", str(round))
            result = self.db.state.remove({'_id': {'$lt': round}, 'signed': True})
            self.logger.debug("Delete from state result %s", str(result))
            return True
        except Exception as e:
            self.logger.error("Could not delete from state. Reason: %s", str(e))
        return False

    # Peer

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

    def get_events_by_time(self, time):
        ev_list = []
        try:
            for event in self.db.events.find({'event.t': {'$gt': time}}):
                ev_list.append(event)
            return ev_list
        except Exception as e:
            self.logger.error("Could not retrieve events based on time. Reason:", str(e))
        return False

    def get_db(self):
        return self.db

    def get_db_name(self):
        return self.db.name

    def get_version(self):
        return self.db.client.server_info()['version']

    def is_running(self):
        try:
            self.db.client.admin.command('ismaster')
        except ConnectionFailure:
            return False
        return True

    def disconnect(self):
        # No usage
        self.connection.close()
        self.logger.info('Database connection closed.')
