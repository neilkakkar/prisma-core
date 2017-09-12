# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging
from binascii import hexlify, unhexlify
import nacl.encoding
import nacl.hash
import nacl.signing
import nacl.utils
from json import loads


class Crypto(object):
    """
    Crypto
    """
    def __init__(self):
        self.logger = logging.getLogger('Crypto')

    def generate_keypair(self):
        """
        Generates a random public and private key.

        :return: Instance of Signing Key: Contains the public and private key.
            This instance can be called from external functions.
        """
        try:
            keypair = nacl.signing.SigningKey.generate()
        except Exception as e:
            self.logger.error("Could not generate keypair. Reason:", e)
            return False
        return keypair

    def get_verify_key(self, private_key):
        keypair = nacl.signing.SigningKey(unhexlify(private_key))
        res = (keypair.verify_key.encode(encoder=nacl.encoding.HexEncoder)).decode('utf-8')
        self.logger.debug("Get verify key %s", str(res))
        return res

    def sign_event(self, event, private_key_seed):
        """
        Signs event(s) in the hash graph.
            
        :param event: a json serialized tuple of dicts.
        :param private_key_seed: Decrypted private key as byte string.
        :return: sig_detached: hex formatted byte string of the signature without the signed message
        :return: verify_key: hex formatted byte string of the verify key.
        :rtype: string (hex formatted) or bool
        """
        try:
            keypair = nacl.signing.SigningKey(unhexlify(private_key_seed))
            signed_event = keypair.sign(bytes(event.encode('utf-8')))
        except Exception as e:
            self.logger.error("Could not sign event. Reason:", e)
            return False
        return {'signed': hexlify(signed_event).decode('utf-8'),
                'sig_detached': hexlify(signed_event.signature).decode('utf-8'),
                'verify_key': (keypair.verify_key.encode(encoder=nacl.encoding.HexEncoder)).decode('utf-8')}

    def verify_local_event(self, ev):
        """
        Verifies a signed Event.

        :param ev: A named event tuple with the type, Event_('d p t c s') where;

            * d: Data/payload!
            * p: event-hash of 2 parents (latest events) of event
            * t: time of event creation
            * c: identifying key of first parent
            * s: digital sign of event by first parent (using his secret key)

        :return: True: Successfully verified event.
        :return: False: Unsuccessfully verified event.
        :rtype: bool
        """
        try:
            verify_key = nacl.signing.VerifyKey(bytes(ev.c.encode('utf-8')), encoder=nacl.encoding.HexEncoder)
            verify_key.verify(unhexlify(ev.s.encode('utf-8')))  # throws an exception if not verified
        except Exception as e:
            self.logger.error("Could not verify local event. Reason: %s", e)
            return False
        return True

    def verify_event(self, ev):
        """
        Verifies a serialized event from a remote host.

        :param ev: dictionary containing the keys,
                        signed_event: hex formatted byte string of the signature without the signed message.
                        event: the serialized event.
                        verify_key_hex: hex formatted byte string of the public key
        :return: True: Successfully verified Event.
        :return: False: Unsuccessfully verified Event.
        """
        event = unhexlify(ev['signed'].encode('utf-8'))
        verify_key_hex = ev['verify_key'].encode('utf-8')

        try:
            verify_key = nacl.signing.VerifyKey(verify_key_hex, encoder=nacl.encoding.HexEncoder)
            res_verify = verify_key.verify(event)
        except Exception as e:
            self.logger.error("Could not verify remote event. Reason:", e)
            return False
        return res_verify

    def validate_sign_consensus(self, data):
        """
        Validates consenss signature

        :param data: consensus signature
        :type data: dict
        :return: decrypted data and signature itself or False if error
        :rtype: dict or bool
        """
        if data:
            try:
                if data and 'signed' in data:
                    remote_consensus = loads(self.verify_event(data).decode('utf-8'))
                    self.logger.debug("remote_consensus %s", str(remote_consensus))
                    if remote_consensus:
                        remote_consensus['sign'] = data
                        return remote_consensus
            except Exception as e:
                self.logger.error("Failed to validate consensus sign msg: %s", str(e))
        # it is not a signature or could not validate signatureGs
        return False

    def sign_tx(self, private_key_seed, tx_hash):
        """
        Signs a sha256 hash sum of the json serialized transaction dictionary.

        :param private_key_seed: byte string of a hex decimal private key.
        :param tx_hash: sha256 hash of the json serialized transaction dictionary.
        :return: False: could not sign the transaction.
        :return: Success: a dict with a hex encoded detached signature and verify key.
        :rtype: dict or bool
        """
        try:
            keypair = nacl.signing.SigningKey(unhexlify(private_key_seed))
            signed_tx = keypair.sign(tx_hash)
        except Exception as e:
            self.logger.error("Could not sign data. Reason:", e)
            return False
        return {'sig_detached': hexlify(signed_tx.signature),
                'verify_key': keypair.verify_key.encode(encoder=nacl.encoding.HexEncoder)}

    def blake_hash(self, byte_string):
        """
        Generate a blake2b hash of a byte string.

        :param byte_string:
        :return: byte string of the generated blake2b hash or false
        """
        try:
            return nacl.hash.blake2b(byte_string).decode()
        except Exception as e:
            self.logger.error("Could not generate generic blake2 hash. Reason:", e)
        return False

    def sha256(self, string):
        """
        Generate a sha256 hash sum of a string.

        :param string:
        :return: Success: byte string of the generated sha256 hash.
        :return: False: could not generate the blake2 hash of the byte string
        :rtype: string or bool
        """
        try:
            hashed_string = unhexlify(nacl.hash.sha256(bytes(string.encode('utf-8'))))
        except Exception as e:
            self.logger.error("Could not hash data. Reason:", e)
            return False
        return hashed_string

    def sha256_tx(self, tx_hex):
        """
        Generate a sha256 hash sum of a byte string.

        :param tx_hex: hex decimal string of the json serialized transaction.
        :return: byte string of the generated sha256 hash, false: could not generate the blake2 hash of the byte string
        """
        try:
            hashed_string = nacl.hash.sha256(tx_hex)
        except Exception as e:
            self.logger.error("Could not hash transaction data. Reason:", e)
            return False
        return hashed_string

    def generate_random_string(self):
        """
        Generate a random hex string with the size of 32 bytes.

        :return: Success: hex decimal string
        :return: False: could not generate the random string.
        :rtype: string or bool
        """
        try:
            rand_hash = hexlify(hexlify(nacl.utils.random(size=32))).decode('utf-8')
        except Exception as e:
            self.logger.error("Could generate random string. Reason:", e)
            return False
        return rand_hash
