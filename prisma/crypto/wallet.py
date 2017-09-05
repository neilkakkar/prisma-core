# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

from os import path
from os import makedirs
import logging
import nacl.secret
import nacl.utils
import nacl.hash
import nacl.encoding
from getpass import getpass
from json import dump, load
from sys import platform
from binascii import hexlify, unhexlify

from prisma.config import CONFIG
from prisma.crypto.crypto import Crypto
from prisma.cryptograph.transaction import Transaction


class Wallet(object):
    """
    Wallet
    """
    def __init__(self):
        self.logger = logging.getLogger('Wallet')
        self.crypto = Crypto()
        self.transaction = Transaction()
        self.transaction_buffer = []

    def create_prisma_home_directory(self):
        """
        Creates or make sure that prisma root directory exists.

        :return: True: Prisma root directory exists.
        :return: False: Could not create prisma root directory.
        :rtype: bool
        """
        if platform == 'linux' or platform == 'linux2':
            storage_dir = path.expanduser('~/.prisma')
            if not path.isdir(storage_dir):
                try:
                    makedirs(storage_dir)
                    self.logger.debug("Created new prisma storage directory.")
                except OSError as e:
                    self.logger.error("Could not create prisma storage directory." +
                                      "Reason: %s", str(e))
                    return False
        else:
            self.logger.error("Could not create prisma storage directory. " +
                              "Operating system not supported.")
            return False
        return True

    def keystore_path(self):
        """
        Creates or make sure that prisma wallet key storage file exists.

        :return: True - Prisma wallet key storage file exists.
        :return: False - could not create prisma wallet key storage file.
        """
        if platform == 'linux' or platform == 'linux2':
            key_storage_file = path.expanduser('~/.prisma/keystore.json')
            if not path.exists(key_storage_file):
                try:
                    with open(key_storage_file, 'a') as key_storage:
                        dump([], key_storage)
                    self.logger.debug("Created new empty prisma key storage file.")
                except Exception as e:
                    self.logger.error("Could not create prisma key storage file." +
                                      "Reason: %s", str(e))
                    return False
            return key_storage_file
        else:
            self.logger.error("Could not open keystore. Operating system not supported.")
        return False

    def encrypt_keystore(self, account, password):
        """
        Encrypts the wallet private key.

        :param account: dictionary of unencrypted public and private keys.
        :param password: password string for encryption.
        :return: Success: dictionary of the encrypted private key, unencrypted public key and address
        :return: False: could not encrypt private key.
        :rtype: dict or bool
        """
        if 'privateKeySeed' in account and 'publicKey' in account and 'address' in account:
            try:
                key_storage = nacl.secret.SecretBox(self.crypto.sha256(password))
                encrypted_private_key_seed = key_storage.encrypt(account['privateKeySeed'])
            except Exception as e:
                self.logger.error("Could not create encrypted keystorage. Reason: %s", str(e))
                return False
            self.logger.debug("Created new encrypted key storage for public key: %s",
                              str(account['publicKey']))
            return {'encPrivateKeySeed': (hexlify(encrypted_private_key_seed)).decode(),
                    'publicKey': account['publicKey'].decode(),
                    'address': account['address']}
        return False

    def decrypt_keystore(self, address, password):
        """
        Decrypts the wallet private key.

        :param password: password string for decryption of the private key.
        :param address:
        :return: Success: dictionary of the unencrypted private key, unencrypted public key and address.
        :return: False: could not decrypt private key.
        :rtype: dict or bool
        """
        enc_pk = {}

        wallets = self.read_keystore()
        for wallet in wallets:
            if 'address' in wallet and wallet['address'] == address:
                enc_pk = wallet
                break

        if enc_pk:
            _enc_pk = unhexlify(bytes(enc_pk['encPrivateKeySeed'].encode('utf-8')))
            try:
                key_storage = nacl.secret.SecretBox(self.crypto.sha256(password))
                private_key_seed = key_storage.decrypt(ciphertext=_enc_pk)
            except Exception as e:
                self.logger.error("Could not decrypt key storage. Check password. Error: %s", str(e))
                return False
            return {'publicKey': bytes(enc_pk['publicKey'].encode('utf-8')),
                    'address': enc_pk['address'],
                    'privateKeySeed': private_key_seed}
        self.logger.error('Wallet with address {0} does not exist.'.format(address))
        return False

    def read_keystore(self):
        """
        Reads the json key storage file.

        :param none
        :return: Success: dictionary of the encrypted private key, unencrypted public key and address.
        :return: False: could not decrypt private key.
        :rtype: dict or bool
        """
        if self.create_prisma_home_directory() and self.keystore_path():
            try:
                with open(self.keystore_path()) as key_storage:
                    wallets = load(key_storage)
                if not isinstance(wallets, list):
                    # todo: validate wallet keys
                    self.logger.error("Invalid wallet format.")
                    return None
                return wallets
            except Exception as e:
                self.logger.error("Could not read key storage. Reason: %s", str(e))
        self.logger.error("No wallets exists.")
        return False

    def write_keystore(self, encrypted_json_array):
        """
        Writes the json key storage file.

        :param encrypted_json_array: dictionary with the encrypted private key, unencrypted public key and address
        :return: True: successfully wrote dictionary to key storage.
        :return: False: could not write dictionary to key storage.
        :rtype: bool
        """
        if self.create_prisma_home_directory() and self.keystore_path():
            wallets = self.read_keystore()
            if wallets is not None:
                wallets.append(encrypted_json_array)
                try:
                    with open(self.keystore_path(), "w") as key_storage:
                        dump(wallets, key_storage)
                        self.logger.debug("Successfully wrote keys to key storage.")
                except Exception as e:
                    self.logger.error("Could not write keys to key storage. Reason: %s", str(e))
                    return False
                return True
        return False

    def addr_from_public_key(self, public_key):
        """
        Converts the public key to a more readable wallet address.

        :param public_key: byte string with the public key
        :type public_key: byte string
        :return: Success: an int representation of the byte string plus suffix
        :return: False: could not convert the public key to an int representation
        :rtype: string or bool
        """
        try:
            address_as_int = int.from_bytes(public_key[:8], byteorder='big')
            address = str(address_as_int) + "PR"
        except Exception as e:
            self.logger.error("Could not generate address from public key. Reason:", str(e))
            return False
        return address

    def new_wallet(self, password, write=True):
        """
        Creates a new random public and private key. Encrypts the private key and writes it to wallet key storage.

        :param password: password string for encrypt and decrypt the private key.
        :param write:
        :return: True: successfully created a new wallet.
        :return: False: could not create a new wallet.
        :rtype: bool
        """
        kp = self.crypto.generate_keypair()
        keys = {"privateKeySeed": hexlify(bytes(kp)),
                "publicKey": hexlify(bytes(kp.verify_key))}

        if keys:
            keys['address'] = self.addr_from_public_key(bytes(keys['publicKey']))

        if not write:
            return keys

        if self.create_prisma_home_directory() and self.keystore_path():
            encrypted_keys = self.encrypt_keystore(keys, password)
            if encrypted_keys:
                if self.write_keystore(encrypted_keys):
                    return keys
        return False

    def list_wallets(self):
        """
        Lists existing wallet addresses. One address will be sent as an argument to decrypt_keystore().

        :return: List
        """
        address_list = []
        wallets = self.read_keystore()
        if wallets:
            for wallet in wallets:
                if 'address' in wallet:
                    address_list.append(wallet['address'])
        return address_list

    def create_wallet(self):
        """
        Creates a new wallet asking password in the prompt.

        :return: dict
        """
        password = getpass(prompt='New password: ')
        password_verification = getpass(prompt='Verify password: ')
        if password != password_verification:
            raise Exception('Passwords do not match.')
        keys = self.new_wallet(password)
        if not keys:
            raise Exception('Could not create wallet. Check ~/.prisma directory permissions.')
        return keys

    def prompt_unlock(self):
        """
        Prompt user for unlocking a certain wallet by its address.

        :return: success: keys dictionary, no success: False
        """
        try:
            # verify if there is not an existing wallet then create a new wallet and continue
            if len(self.list_wallets()) == 0:
                print('You don\'t have any wallets. Let\'s create your first wallet.')
                keys = self.create_wallet()
                print('Wallet created with address: ' + keys['address'])
                return keys

            # if wallet address is specified in the config file then just ask for a password, otherwise ask for an
            # address in the prompt
            if CONFIG.has_option('general', 'wallet_address'):
                wallet_address = CONFIG.get('general', 'wallet_address')
                if CONFIG.get('general', 'wallet_address') not in self.list_wallets():
                    raise Exception('Wallet provided in the config file does not exist.')
                self.logger.info('Unlocking wallet with address {0}'.format(wallet_address))
                # in case of dev mode we can have the password in the config file, otherwise ask for a password
                if CONFIG.getboolean('developer', 'developer_mode') and \
                        CONFIG.has_option('developer', 'wallet_password'):
                    keys = self.decrypt_keystore(wallet_address, CONFIG.get('developer', 'wallet_password'))
                    if keys:
                        return keys
                else:
                    while True:
                        password = getpass(prompt="Password: ")
                        if password:
                            keys = self.decrypt_keystore(wallet_address, password)
                            if keys:
                                return keys
                        else:
                            self.logger.error("Password can not be empty.")
            else:
                while True:
                    wallet_address = input("Wallet address: ")
                    if wallet_address and wallet_address in self.list_wallets():
                        password = getpass(prompt="Password: ")
                        if password:
                            keys = self.decrypt_keystore(wallet_address, password)
                            if keys:
                                return keys
                        else:
                            self.logger.error("Password can not be empty.")
                    else:
                        self.logger.info("Wallet address does not exist.")
                        break
        except Exception as e:
            self.logger.error('Error when unlocking wallet. Reason: {0}'.format(e))
        return False

    def transaction_buffer_add(self, transaction):
        """
        Saves a transaction in a buffer.

        :param transaction:
        """
        self.transaction_buffer.append(transaction)

    def clear_transaction_buffer(self):
        """
        Empties the transaction buffer.
        """
        del self.transaction_buffer[:]

    def insert_transaction_buffer_into_pool(self):
        """
        Gets all stored transactions and inserts them into the pool.
        """
        self.transaction.insert_transactions_into_pool(self.transaction_buffer)
        self.clear_transaction_buffer()
