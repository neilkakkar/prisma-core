# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging

from prisma.cryptograph.transaction import TYPE_SIGNED_STATE, TYPE_MONEY_TRANSFER

class Transactions(object):
    
    def __init__(self, prismaDB,super):
        self.logger = logging.getLogger('PrismaDB-Witness')
        self.db = prismaDB
        self.super = super


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
                wallets |= self.super.get_wallets_state()
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
        bal_res = tx_balance + self.super.get_state_balance(account_id)
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
            event_hash = self.super.get_head()
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
