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
from json import dumps, loads

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

    def sign_data(self, data, private_key_seed):
        """
        Sign given data with node private key.

        :param data: data to be signed
        :type data: dict
        :param private_key_seed: deterministic private key seed
        :type private_key_seed: hexadecimal string
        :rtype: dict
        """

        try:
            keypair = nacl.signing.SigningKey(unhexlify(private_key_seed))
            signed_event = keypair.sign(bytes(data.encode('utf-8')))
        except Exception as e:
            self.logger.error("Could not sign data. Reason: %s", str(e))
            return False

       	return {'signed': hexlify(signed_event.message).decode('utf-8'),
               	'sig_detached': hexlify(signed_event.signature).decode('utf-8'),
               	'verify_key': (keypair.verify_key.encode(encoder=nacl.encoding.HexEncoder)).decode('utf-8')}


    def verify_signature(self, data):
        """
        Verifies signature for given data

        :param data: Data to verify
        :type data: A dictionary of byte strings.
        :return: Verified data.
        :rtype: Byte string or a marshalled byte string of dicts in our case.
        :return: False: Could not verify data
        :rtype: bool
        """

        try:
            verify_key = nacl.signing.VerifyKey(data['verify_key'], encoder=nacl.encoding.HexEncoder)
            res_verify = verify_key.verify(data['signed'], signature=data['sig_detached'])
            return res_verify
        except Exception as e:
            self.logger.error("Could not verify data with signature. Reason: %s", str(e))
        return False

    def verify_local_event(self, event):
        """
        Verifies a signed Event.

        :param event: A named event tuple with the type, Event_('d p t c s') where:

            # Signed data
                * d: Data/payload!
                * p: Event-hash of 2 parents (the latest events) of the event
                * t: Time of event creation

            # Keys
                * c: Identifying key of the first parent.
                     This is the verify key.
                * s: Digital sign of event by the first parent (using its secret key).
                     This is the detached signature.

        :return: True: Successfully verified event.
        :return: False: Unsuccessfully verified event.
        :rtype: bool
        """

        try:
            event_data = {'verify_key': bytes(event.c.encode('utf-8')),
                          'signed': bytes(dumps(event.d, event.p, event.t).encode('utf-8')),
                          'sig_detached': unhexlify(event.s.encode('utf-8'))}
            return self.verify_signature(event_data)
        except Exception as e:
            self.logger.error("Could not extract event data. Reason: {0}".format(e))
        return False

    def validate_state_sign(self, data):
        """
        Validates state signature

        :param data: state signature
        :type data: dict
        :return: dict or False if error
        :rtype: dict or bool
        """

        if 'verify_key' in data and 'signed' in data:
            state_data = {'verify_key': data['verify_key'].encode('utf-8'),
                          'signed': unhexlify(data['signed'].encode('utf-8'))}
            verify_res = self.verify_signature(sign).decode('utf-8')
            if verify_res:
                return loads(verify_res)
        self.logger.error("Failed to validate state sign")
        return False

    def blake_hash(self, byte_string):
        """
        Generates a blake2b hash of a byte string.

        :param byte_string:
        :return: a byte string of the generated blake2b hash or false
        """
        try:
            return nacl.hash.blake2b(byte_string).decode()
        except Exception as e:
            self.logger.error("Could not generate generic blake2 hash. Reason:", e)
        return False

    def sha256(self, string):
        """
        Generates a sha256 hash sum of a string.

        :param string:
        :return: Success: a byte string of the generated sha256 hash.
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
        Generates a sha256 hash sum of a byte string.

        :param tx_hex: a hex decimal string of the json serialized transaction.
        :return: a byte string of the generated sha256 hash, false: could not generate the blake2 hash of the byte string
        """
        try:
            hashed_string = nacl.hash.sha256(tx_hex)
        except Exception as e:
            self.logger.error("Could not hash transaction data. Reason:", e)
            return False
        return hashed_string

    def generate_random_string(self):
        """
        Generates a random hex string with the size of 32 bytes.

        :return: Success: a hex decimal string
        :return: False: could not generate the random string.
        :rtype: string or bool
        """
        try:
            rand_hash = hexlify(hexlify(nacl.utils.random(size=32))).decode('utf-8')
        except Exception as e:
            self.logger.error("Could generate random string. Reason:", e)
            return False
        return rand_hash
