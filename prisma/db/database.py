# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging
import sys
from pymongo import DESCENDING
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid
from pymongo.errors import ConnectionFailure
from bson import CodecOptions
from collections import OrderedDict

from prisma.utils.common import Common
from prisma.config import CONFIG

from prisma.db.events import Events
from prisma.db.rounds import Rounds
from prisma.db.visible import Visible
from prisma.db.votes import Votes
from prisma.db.peer import Peer
from prisma.db.state import State
from prisma.db.head import Head
from prisma.db.consensus import Consensus
from prisma.db.height import Height
from prisma.db.sign import Sign
from prisma.db.transactions import Transactions
from prisma.db.witness import Witness

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

        opts = CodecOptions(document_class = OrderedDict)
        self.db.state = self.db.state.with_options(codec_options=opts)

        if not self.is_running():
            self.logger.error("MongoDB is not started, exiting.")
            sys.exit(1)

        self.logger.info('MongoDB v%s, using database "%s".', self.get_version(), self.get_db_name())
        self.collections_list = ['events', 'rounds', 'can_see', 'height', 'head', 'peers', 'witness', 'famous',
                                 'votes', 'transactions', 'consensus', 'signature', 'state']
        self.create_collections()
        self.create_indexes()


        self.events = Events(self.db, self)
        self.rounds = Rounds(self.db, self)
        self.visible = Visible(self.db, self)
        self.votes = Votes(self.db, self)
        self.peer = Peer(self.db, self)
        self.state = State(self.db, self)
        self.head = Head(self.db, self)
        self.consensus = Consensus(self.db, self)
        self.height = Height(self.db, self)
        self.sign = Sign(self.db, self)
        self.transactions = Transactions(self.db, self)
        self.witness = Witness(self.db, self)

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
        return self.events.get_event(event_id, as_tuple, clear_parent)

    def get_events_many(self, as_tuple=True):
        """
        Gets many events from db

        :param as_tuple: returns result as named tuple or as dict
        :type as_tuple: bool
        :return: Events
        :rtype:     * dict of events
                    * dict of named tuple
        """
        return self.events.get_events_many(as_tuple)

    def get_latest_event_time(self):
        """
        Gets latest (largest) time of event stored in db

        :return:    * latest event time - if it is possible to find event
                    * 0.0 - if the collection is empty
                    * False - if error
        :rtype: float or bool
        """
        return self.events.get_latest_event_time()

    def insert_event(self, event):
        """
        Inserts one event into db

        :param event: event info including blake2 hash as a key
        :type event: dict
        :return: was the insertion successful
        :rtype: bool
        """
        return self.events.insert_event(event)

    def delete_event(self, h):
        """
        Deletes one event

        :param h: event hash
        :type h: str
        :return: was the delete operation successful
        """
        return self.events.delete_event(h)

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
        return self.rounds.get_round(h)
        
    def get_rounds_many(self, less_than=False):
        """
        Gets all rounds from db

        :param less_than: limitation for round num
        :type less_than: int/bool(by default)
        :return: round for every hash or False if error
        :rtype: dict or bool
        """
        return self.rounds.get_rounds_many(less_than)

    def get_rounds_max(self):
        """
        Gets max round stored in db

        :return:    * round - if the document was found in collection
                    * 0 - if the collection is empty
                    * False -  in the case of error
        :rtype: int
        """
        return self.rounds.get_rounds_max()
        

    def get_rounds_hash_list(self, value):
        """
        Gets hashes of events with round less than given value

        :param value: start round num
        :type value: int
        :return: id (hash) values from all documents with round less than given value
        :rtype: list
        """
        return self.rounds.get_rounds_hash_list(value)
        

    def get_rounds_less_than(self, r):
        """
        Gets documents with round less than given one

        :param r: round num
        :type r: int
        :return: documents with round less than given one
        :rtype: list
        """
        return self.rounds.get_rounds_less_than(r)

    def insert_round(self, round_info):
        """
        Inserts one round into db

        :param round_info: dict in format {hash:round}
        :type round_info: dict
        :return: was the insertion successful
        :rtype: bool
        """
        return self.rounds.insert_round(round_info)

    def set_round_handled(self, round_info):
        """
        Set round when event was handled

        :param round_info: dict in format {hash:round}
        :type round_info: dict
        :return: was the insertion successful
        :rtype: bool
        """
        return self.rounds.set_round_handled(round_info)

    def delete_round_less_than(self, value):
        """
        Deletes all documents with round less than value

        :param value: start round num
        :type value: int
        :return: was the delete operation successful
        :rtype: bool
        """
        return self.rounds.delete_round_less_than(value)

    def delete_round_greater_than(self, value):
        """
        Deletes all documents with round greater than value

        :param value: start round num
        :type value: int
        :return: was the delete operation successful
        :rtype: bool
        """
        return self.rounds.delete_round_greater_than(value)

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
        return self.visible.get_can_see(event_id)

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
        return self.visible.insert_can_see(can_see)

    def delete_can_see(self, h):
        """
        Deletes document that can be seen by event hash

        :param h: event hash
        :type h: str
        :return: was the delete operation successful
        :rtype: bool
        """
        return self.visible.delete_can_see(h)

    def delete_references_can_see(self, hash_list):
        """
        Deletes all references to signed hashes

        :param hash_list: list of signed events
        :type hash_list: tuple
        :return: was the delete operation successful
        :rtype: bool
        """
        return self.visible.delete_references_can_see(hash_list)

    # Head

    def get_head(self):
        """
        Gets cryptograph head from db

        :return:    * hash of head event
                    * False if error
        :rtype: str or bool
        """
        return self.head.get_head()

    def insert_head(self, head):
        """
        Inserts cryptograph head to db

        :param head: hash of head event
        :type head: str
        :return: was the insertion successful
        :rtype: bool
        """
        return self.head.insert_head(head)

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
        return self.height.get_height(event_id)

    def get_heights_many(self):
        """
        Gets all heights info

        :return: height in format {hash: height}
        :rtype: dict
        """
        return self.height.get_heights_many()

    def insert_height(self, height_info):
        """
        Inserts height of event to db

        :param height_info: data in format {hash: height}
        :type height_info: dict
        :return: was the insertion successful
        :rtype: bool
        """
        return self.height.insert_height(height_info)

    def delete_height(self, h):
        """
        Deletes height by event hash

        :param h: event hash
        :type h: str
        :return: was the delete operation successful
        :rtype: bool
        """
        return self.height.delete_height(h)

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
        return self.witness.get_witness(r)

    def get_witness_max_round(self):
        """
        Gets max round stored in witness

        :return:    * max round - if it was found
                    * 0 - if the collection is empty
                    * False - if error
        :rtype: int or bool
        """
        return self.witness.get_witness_max_round()

    def insert_witness(self, witness_info):
        """
        Inserts one witness to db

        :param witness_info: witness data in format {round:{hash:hash}}
        :type witness_info: dict
        :return: was the insertion successful
        :rtype: bool
        """
        return self.witness.insert_witness(witness_info)

    def delete_witnesses_less_than(self, r):
        """
        Deletes witnesses with round less than given

        :param r: start round num
        :type r: int
        :return: was the delete operation successful
        :rtype: bool
        """
        return self.witness.delete_witnesses_less_than(r)

    # Transactions

    def get_transactions_many(self):
        """
        Gets all transactions from db

        :return: list of all transactions stored in db (without round)
        :rtype: tuple
        """
        return self.transactions.get_transactions_many()

    def get_unsent_transactions_many(self, account_id):
        """
        Gets all unsent transactions from db.
        Unsent mean that event for that tx was not created

        :param account_id: our local account id
        :type account_id: str
        :return: list of all unsent transactions stored in db, and list of their ids
        :rtype: tuple
        """
        return self.transactions.get_unsent_transactions_many(account_id)

    def get_all_known_wallets(self):
        """
        Finds and returns all unique wallets in transactions and last state

        :return: unique wallets stored in db
        :rtype: set
        """
        return self.transactions.get_all_known_wallets()

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
        return self.transactions.get_account_balance(account_id, r)

    def get_account_balance_many(self, range=False):
        """
        Gets balance for all known wallets

        :param range: range of rounds
        :type range: list
        :return: balance for all known wallets in format {address: amount}
        :rtype: dict
        """
        return self.transactions.get_account_balance_many(range)

    def insert_transactions(self, tx_list):
        """
        Inserts prepared tx into db.
        Should not be invoked directly, only from transaction class

        :param tx_list: list of transactions to be inserted
        :type tx_list: list
        :return: was the insertion successful
        :rtype: bool
        """
        return self.transactions.insert_transactions(tx_list)

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
        return self.transactions.set_transaction_hash(tx_list)

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
        return self.transactions.set_transaction_round(ev_hash, r)

    def delete_transaction_less_than(self, r):
        """
        Deletes transaction with round less than given value

        :param r: start round num
        :type r: int
        :return: was the delete operation successful
        :rtype: bool
        """
        return self.transactions.delete_transaction_less_than(r)

    def delete_money_transfer_transaction_less_than(self, r):
        """
        Deletes transactions that contain money transfer and round <= than given one
        Should be invoked after the creation of state

        :param r: round
        :type r: int
        :return: was the delete operation successful
        :rtype: bool
        """
        return self.transactions.delete_money_transfer_transaction_less_than(r)

    # Votes

    def get_vote(self, vote_id):
        """
        Gets vote from db by event id

        :param vote_id: hash events the votes of which we are looking for
        :type vote_id: str
        :return:    * votes dict in format {hash: vote(T/F)}
                    * False - if error
        """
        return self.votes.get_vote(vote_id)

    def insert_vote(self, vote):
        """
        Inserts vote to db

        :param vote: vote info in format {who vote(hash):{for whom(hash): vote(T/F)}}
        :type vote: dict
        :return: was the insertion successful
        :rtype: bool
        """
        return self.votes.insert_vote(vote)

    def delete_votes(self, h):
        """ Deletes votes from db by given hash

        :param h: event hash to be found
        :type h: str
        :return: was the delete operation successful
        :rtype: bool
        """
        return self.votes.delete_votes(h)

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
        return self.votes.get_famous(witness)

    def get_famous_many(self):
        """
        Gets all famous witnesses from db

        :return:    * famous info in format {hash: is famous(T/F)}
                    * False - if error
        :rtype: dict or bool
        """
        return self.votes.get_famous_many()

    def insert_famous(self, famous_info):
        """
        Inserts famous info into db
        
        :param famous_info: data in format {hash: is famous(T/F)}
        :type famous_info: dict
        :return: was the insertion successful
        :rtype: bool
        """
        return self.votes.insert_famous(famous_info)

    def check_famous(self, h):
        """
        Checks if hash is present in famous

        :param h: event hash
        :type h: str
        :return: is present or not
        :rtype: int
        """
        return self.votes.check_famous(h)

    def delete_famous(self, h):
        """ Deletes famous info with given hash from db

        :param h: event hash
        :type h: str
        :return: was the delete operation successful
        :rtype: bool
        """
        return self.votes.delete_famous(h)

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
        return self.consensus.get_consensus_many(lim, sign, sort)

    def get_consensus_count(self):
        """
        Gets how many consensus are stored in db

        :return: consensus count or 0 if the collection is empty
        :rtype: int
        """
        return self.consensus.get_consensus_count()

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
        return self.consensus.get_consensus_greater_than(value, lim)

    def get_consensus_last_sent(self):
        """
        Gets consensus with last sent flag

        :return:    * Last sent consensus - if found
                    * -1 - if it does not exist
                    * False - if error
        :rtype: int or bool
        """
        return self.consensus.get_consensus_last_sent()

    def get_consensus_last_created_sign(self):
        """
        Gets consensus with last created signature flag

        :return:    * Last created signature - if it was found
                    * -1 - if it does not exist
                    * False - if error
        :rtype: int or bool
        """
        return self.consensus.get_consensus_last_created_sign()

    def get_consensus_last_signed(self):
        """
        Gets last signed round from db

        :return: last signed round or -1 if it does not exist
        :rtype: int
        """
        return self.consensus.get_consensus_last_signed()

    def get_last_consensus(self):
        """
        Get last consensus round

        :return: last consensus round
        :rtype: int
        """
        return self.consensus.get_last_consensus()

    def insert_consensus(self, consensus, signed=False):
        """
        Inserts consensus into db

        :param consensus: consensus (Note: by default, consensus is unsigned)
        :type consensus: int
        :return: was the insertion successful
        :rtype: bool
        """
        return self.consensus.insert_consensus(consensus, signed)

    def check_consensus(self, r):
        """
        Checks if round is present in consensus

        :param h: round to check
        :type h: str
        :return: is present or not
        :rtype: int
        """
        return self.consensus.check_consensus(r)

    def sign_consensus(self, count):
        """
        Signs some consensus

        :param count: how many consensuses should be signed
        :type count: int
        :return: was the sign operation successful
        :rtype: bool
        """
        return self.consensus.sign_consensus(count)

    def set_consensus_last_sent(self, consensus):
        """
        Sets the last sent flag to consensus

        :param consensus: consensus value
        :type consensus: int
        :return: was the setting operation successful
        :rtype: bool
        """
        return self.consensus.set_consensus_last_sent(consensus)

    def set_consensus_last_created_sign(self, consensus):
        """
        Sets the last created signature flag to consensus

        :param consensus: consensus value
        :type consensus: int
        :return: was the setting operation successful
        :rtype: bool
        """
        return self.consensus.set_consensus_last_created_sign(consensus)

    # Signature

    def get_signature(self, last_round):
        """
        Gets signatures for last round

        :param last_round: last round of state
        :type last_round: int
        :return: signatures or False if error
        :rtype: dict or bool
        """
        return self.sign.get_signature(last_round)

    def get_signature_grater_than(self, last_round):
        """
        Gets signatures with start greater than the given one

        :param last_round: last round of state
        :type last_round: int
        :return: signatures or False if error
        :rtype: dict or bool
        """
        return self.sign.get_signature_grater_than(last_round)

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
        return self.sign.check_if_signature_present(last_round, ver_key)

    def insert_signature(self, signature):
        """
        Inserts signature into db

        :param signature: sign - contain: signature itself, start value and consensus hash
        :type signature: dict
        :return: was the insertion successful
        :rtype: bool
        """
        return self.sign.insert_signature(signature)

    def unset_unchecked_signature(self, last_round):
        """
        Deletes all unchecked signatures
        (unchecked means that we have not compared this remote hash with our local)

        :param last_round: last round of state
        :type last_round: int
        :return: was the delete operation successful
        :rtype: bool
        """
        return self.sign.unset_unchecked_signature(last_round)

    def insert_signature_unchecked(self, signature):
        """
        Inserts signature as unchecked
        (unchecked means that we have not compared this remote hash with our local)

        :param signature: sign - contains: sign itself, start value and consensus hash
        :type signature: dict
        :return: was the insertion successful
        :rtype: bool
        """
        return self.sign.insert_signature_unchecked(signature)

    # State

    def get_state(self, r, for_sync=False):
        """
        Gets state by last_round

        :param r: last_round for state
        :type r: int
        :param for_sync: remove hash and signed flag from result or not
        :type for_sync: bool
        :return: state (balance of all wallets)
        :rtype: dict
        """

        return self.state.get_state(r, for_sync)

    def get_last_state(self):
        """
        Gets the last state and round of the state.

        :return:
        """
        return self.state.get_last_state()

    def get_state_many(self, gt=0, signed=True, for_sync=True):
        """
        Gets all state stored in db
        
        :param gt: state round for greater than
        :type gt: int
        :param signed: get only signed or not
        :type signed: bool
        :param for_sync: remove hash and signed flag from result or not
        :type for_sync: bool
        :return: list of states
        :rtype: list
        """

        return self.state.get_state_many(gt, signed, exclude_hash)

    def get_state_balance(self, address):
        """
        Gets wallet balance by address from last state

        :param address: address of wallet
        :type address: str
        :return: wallet balance
        :rtype: int
        """
        return self.state.get_state_balance(address)

    def get_wallets_state(self):
        """
        Gets all unique wallets in state

        :return:unique wallets
        :rtype: set
        """
        return self.state.get_wallets_state()

    def insert_state(self, state, hash, signed=False):
        """
        Inserts state into db

        :param state: state itself
        :type state: dict
        :param hash: state hash
        :type hash: str
        :param signed: is state already signed
        :type signed: bool
        :return: was the insertion successful
        :rtype: bool
        """

        return self.state.insert_state(state, hash, signed)

    def set_state_signed(self, round):
        """
        Sets signed flag to state with last_round equal to given round

        :param round: last_round of state to sign
        :type round: int
        :return: was the setting operation successful
        :rtype: bool
        """
        return self.state.set_state_signed(round)

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
        return self.state.delete_state_less_than(round)

    def get_state_with_proof_many(self, gt):
        return self.state.get_state_with_proof_many(gt)

    def get_state_with_proof(self, r):
        return self.state.get_state_with_proof(r)

    # Peer

    def get_peer(self, ip):
        # No usage
        return self.peer.get_peer(ip)

    def get_peers_many(self):
        """
        Gets all peers stored in db

        :return: peer list or False if error
        :rtype: tuple or bool
        """
        return self.peer.get_peers_many()

    def count_peers(self):
        """
        Counts number of peers before the start of events syncing.
        Consensus states that at least 3 node should be online.

        :return: peer count
        :rtype: int
        """
        return self.peer.count_peers()

    def insert_peer(self, peer):
        """
        Inserts peer into db

        :param peer: peer info
        :type peer: dict
        :return: was the insertion successful
        :rtype: bool
        """
        return self.peer.insert_peer(peer)

    def delete_peers(self):
        """
        Deletes all peers stored in db

        :return: was the delete operation successful
        :rtype: bool
        """
        return self.peer.delete_peers()

    def delete_peer(self, ip):
        # No usage
        return self.peer.delete_peer(ip)

    def get_random_peer(self):
        # No usage
        return self.peer.get_random_peer()

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
