# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

from prisma.manager import Prisma


class ApiMethods:
    """
    List of methods that can be callable from the API.
    """

    @staticmethod
    def create_wallet(password):
        """
        Create a new wallet encrypted with the given password

        :param password:
        :return: the information of the new wallet
        """
        wallet = Prisma().graph.wallet.new_wallet(password)
        return {
            'address': wallet['address'],
            'public_key': wallet['publicKey'].decode('utf-8')
        }

    @staticmethod
    def decrypt_wallet(address, password):
        decrypted_wallet = Prisma().graph.wallet.decrypt_keystore(address, password)
        return {
            'address': decrypted_wallet['address'],
            'public_key': decrypted_wallet['publicKey'].decode('utf-8'),
            'private_key': decrypted_wallet['privateKeySeed'].decode('utf-8')
        }

    @staticmethod
    def list_wallets():
        """
        Returns a list of wallet addresses stored.

        :return: a list of wallet addresses
        """
        return {'addresses': Prisma().graph.wallet.list_wallets()}

    @staticmethod
    def peer_list():
        """
        Returns a list with all the peers in our database.

        :return: a list of peers
        """
        return {'peer_list': Prisma().db.get_peers_many()}

    @staticmethod
    def peer_count():
        """
        Returns the number of connected peers.

        :return: a list of peers
        """
        return {'peer_count': Prisma().db.count_peers()}

    @staticmethod
    def last_event_time():
        """
        Returns the latest event time.

        :return: last event
        """
        return {'latest_event_time': Prisma().db.get_latest_event_time()}

    @staticmethod
    def get_my_balance():
        """
        Get the balance in the current node keystore

        :return: my balance
        """
        address = Prisma().graph.keystore['address']
        my_balance = Prisma().db.get_account_balance(address)
        return {
            'my_address': address,
            'my_balance': my_balance
        }

    @staticmethod
    def get_address_balance(address):
        """
        Returns the balance in an address.

        :param address:
        :return: balance
        """
        balance = Prisma().db.get_account_balance(address)
        return {
            'address': address,
            'balance': balance
        }

    @staticmethod
    def create_transaction_and_send(to_address, amount):
        """
        Creates a transaction and inserts it to the pool.

        :param to_address: address
        :param amount: int
        """
        transaction = Prisma().wallet.transaction.form_money_transfer_tx(Prisma().graph.keystore, to_address, amount)
        Prisma().wallet.transaction.insert_transactions_into_pool([transaction])
        return {'transaction': Prisma().wallet.transaction.unhexify_transaction(transaction)}

    @staticmethod
    def create_transaction(to_address, amount, from_address=None, password=None):
        """
        Created a transaction and saves it.

        :param to_address:
        :param amount:
        :param from_address:
        :param password:
        :return: the transaction stored
        """
        if from_address:
            """
            keystore = Prisma().wallet.decrypt_keystore(from_address, password)
            if not keystore:
                raise Exception('The wallet provided is invalid or is not stored in the system.')
            """
            raise Exception('It\'s not possible to send from another wallet different than the main wallet atm. Sorry!')
        else:
            keystore = Prisma().graph.keystore
        transaction = Prisma().wallet.transaction.form_money_transfer_tx(keystore, to_address, amount)
        Prisma().wallet.transaction_buffer_add(transaction)
        return {'transaction_stored': Prisma().wallet.transaction.unhexify_transaction(transaction)}

    @staticmethod
    def clear_transactions():
        """
        Clear transactions in the buffer.
        """
        Prisma().wallet.clear_transaction_buffer()
        return {}

    @staticmethod
    def list_transactions():
        """
        Returns a list of buffered transactions.

        :return: the transaction buffer unhexified.
        """
        i = 0
        data = {}
        if len(Prisma().wallet.transaction_buffer) == 0:
            return {'message': 'The buffer is empty.'}
        for transaction in Prisma().wallet.transaction_buffer:
            data[i] = Prisma().wallet.transaction.unhexify_transaction(transaction)
            i += 1
        return data

    @staticmethod
    def send_transactions():
        """
        Inserts the transactions into pool for processing.
        """
        Prisma().wallet.insert_transaction_buffer_into_pool()
        return {}
