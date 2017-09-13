# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import sys
import logging
import json
from binascii import hexlify, unhexlify

from prisma.manager import Prisma
from prisma.utils.common import Common
from prisma.crypto.crypto import Crypto
from prisma.validation.transaction import TxValidator

TYPE_MONEY_TRANSFER = 0
TYPE_SIGNED_STATE = 1


class Transaction(object):
    """
    Transaction
    """
    def __init__(self):
        self.common_functions = Common()
        self.crypto = Crypto()
        self.validator = TxValidator()
        self.logger = logging.getLogger('Transaction')
        self.genesis_event_hash = self.get_genesis_event_hash()
        self.logger.debug("genesis_event_hash %s", str(self.genesis_event_hash))

    def get_genesis_event_hash(self):
        genesis_event = self.common_functions.read_genesis_event()
        if not genesis_event:
            sys.exit(1)
        return list(genesis_event.keys())[0]

    def hexlify_transaction(self, tx):
        """
        Hexifies a transaction.

        :param tx:
        :return: Success:
        :return: False: Failed to hexlify tx
        :rtype: string or bool
        """
        try:
            return hexlify(bytes(json.dumps(tx).encode('utf-8'))).decode('utf-8')
        except Exception as e:
            self.logger.error("Failed to hexlify transaction. Reason: {0}".format(e))
        return False

    @staticmethod
    def unhexlify_transaction(tx_hex):
        """
        From a tx_hex returns the original dictionary.

        :param tx_hex:
        :return: dict
        """
        try:
            return json.loads(unhexlify(tx_hex).decode('utf-8'))
        except Exception as e:
            self.logger.error("Failed to unhexlify transaction. Reason: {0}".format(e))
        return False

    def form_funds_tx(self, keys, recipient_id, amount):
        """
        Wraps a transaction in an object.

        :param keys:
        :param recipient_id:
        :param amount:
        :return: self.finalize_transaction():
        """
        if amount and keys and 'address' in keys and \
                'publicKey' in keys and recipient_id:

            tx = {
                "type": str(TYPE_MONEY_TRANSFER),
                "amount": amount,
                "senderPublicKey": keys['publicKey'].decode(),
                "senderId": keys['address'],
                "recipientId": recipient_id,
                "timestamp": self.common_functions.get_timestamp()
            }
        else:
            self.logger.error("Missing values in form transaction.")
            return False

        if not self.validator.transaction(tx):
            return False

        return self.hexlify_transaction(tx)

    def generate_transaction_id(self, tx_hex):
        """
        Generates a transaction ID

        :param tx_hex:
        :return: Success: tx_id: Transaction ID
        :rtype: int
        :return: False: Could not generate transaction id.
        :rtype: bool
        """
        try:
            tx_hash = self.crypto.sha256_tx(tx_hex)
            tx_id = int.from_bytes(tx_hash[:10], byteorder='big')
        except Exception as e:
            self.logger.error("Could not generate transaction id. Reason:", e)
            return False
        return tx_id

    @staticmethod
    def get_transaction_fee():
        """
        Returns transaction fee.

        :return: 10
        :rtype: int
        """
        return 10

    def parse_transaction_hex(self, tx_hex, ev_hash=''):
        """
        Parse hex to a transaction dict.

        :param tx_hex:
        :param ev_hash:
        :return: tx
        """
        try:
            tx = self.unhexlify_transaction(tx_hex)
            if ev_hash == self.genesis_event_hash:
                return tx
            if int(tx['type']) == TYPE_MONEY_TRANSFER:
                sender_balance = Prisma().db.get_account_balance(tx['senderId'])
                if tx['amount'] > sender_balance:
                    raise Exception('Money transfer without enough balance.')
            return tx
        except Exception as e:
            self.logger.debug('Could not parse transaction: ' + str(e))
        return False

    def insert_transactions_into_pool(self, tx_list):
        """
        Prepares and inserts transactions into tx pool.
        They will be inserted into event as soon as
        it will be created.

        :param tx_list: list of finalized transactions
        :type tx_list: list
        :return: insertion result
        :rtype: bool
        """
        if tx_list:
            prepared_tx_list = []
            for tx_hex in tx_list:
                tx = self.parse_transaction_hex(tx_hex)
                if tx:
                    tx['tx_dict_hex'] = tx_hex
                    self.logger.debug("Prepared for pool tx %s", str(tx))
                    prepared_tx_list.append(tx)
                else:
                    self.logger.error("Skipping inserting malformed transaction %s", str(tx))
                    continue
            return Prisma().db.insert_transactions(prepared_tx_list)
        return False

    def insert_processed_transaction(self, ev_hash_list, round, private_key_seed):
        """
        Inserts processed tx (the one, that was included in final tx order) by event hash
        Should be used only in order.py

        :param ev_hash_list: list of events for which final order was found
        :type ev_hash_list: list
        :param round: round of all events, used later to generate state and clean db
        :type round: int
        :param private_key_seed: node private key seed needed to create and afterwards to check verify key
        :type private_key_seed: str
        :return:
        """
        self.logger.debug("insert_processed_transaction input ev_hash_list = %s, round = %s, pk = %s",
                          str(ev_hash_list), str(round), str(private_key_seed))
        self_verify_key = self.crypto.get_verify_key(private_key_seed)

        tx_list = []
        for event_hash in ev_hash_list:
            self.logger.debug("insert_processed_transaction for ev with hash %s", str(event_hash))
            event = Prisma().db.get_event(event_hash)
            self.logger.debug("insert_transaction_by_ev_hash event %s", str(event))
            if not len(event):
                self.logger.error("Could not insert tx, event there is no event !")
                return False

            if len(event.d) > 0:
                if event.c != self_verify_key:
                    for tx_hex in event.d:
                        tx = self.parse_transaction_hex(tx_hex, event_hash)
                        # Money transfer
                        if (tx and 'type' in tx and int(tx['type']) == TYPE_MONEY_TRANSFER and
                                'amount' in tx and 'senderId' in tx and 'recipientId' in tx):
                            tx['tx_dict_hex'] = tx_hex
                            tx['ev_hash'] = event_hash
                            tx['round'] = round
                            tx_list.append(tx)
                            self.logger.debug("Insert money transfer tx %s", str(tx))
                        # State signature
                        elif tx and 'type' in tx and int(tx['type']) == TYPE_SIGNED_STATE:
                            # Handle new signatures that was crated by remote node
                            self.logger.debug("Handle remote sign %s", str(tx))
                            Prisma().state_manager.handle_new_sign(tx)
                        # Error
                        else:
                            self.logger.error("Skipping malformed transaction data for event hash: %s", str(tx))
                else:
                    Prisma().db.set_transaction_round(event_hash, round)
        return Prisma().db.insert_transactions(tx_list)
