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

    def sign_data(self, data, private_key_seed, separated=False):
        """
        Sign given data with node private key.

        :param data: any data to sign
        :type data: dict
        :param private_key_seed: seed of node private key
        :type private_key_seed: str
        :param separated:   saves signed message and signature
                            separated or concatenates them
        :type separated: bool
        :return: verify_key and only signature (separated = True)
        :return: verify_key and signature concatenated with signed message (separated = False)
        :rtype: dict
        """
        try:
            keypair = nacl.signing.SigningKey(unhexlify(private_key_seed))
            signed_event = keypair.sign(bytes(data.encode('utf-8')))
        except Exception as e:
            self.logger.error("Could not sign data. Reason: %s", str(e))
            return False

        result = {'verify_key': (keypair.verify_key.encode(encoder=nacl.encoding.HexEncoder)).decode('utf-8')}

        if separated:
            result['sig_detached'] = hexlify(signed_event.signature).decode('utf-8')
        else:
            result['signed'] = hexlify(signed_event).decode('utf-8')

        return result

    def verify_signature(self, data, verify_key_hex, sig_detached=None):
        """
        Verifies signature for given data

        :param verify_key_hex: verifies key for data (public key)
        :type verify_key_hex: byte string
        :param data: data to verify
        :type data: byte string
        :param sig_detached: provided if signature store is separated from data otherwise None
        :type sig_detached: byte string or None
        :return: the message if successfully verified
        """
        try:
            verify_key = nacl.signing.VerifyKey(verify_key_hex, encoder=nacl.encoding.HexEncoder)
            res_verify = verify_key.verify(data, signature=sig_detached)
        except Exception as e:
            self.logger.error("Could not verify remote event. Reason: %s", str(e))
            return False
        return res_verify

    def verify_local_event(self, ev):
        """
        Verifies a signed Event.

        :param ev: A named event tuple with the type, Event_('d p t c s') where:

            * d: Data/payload!
            * p: event-hash of 2 parents (the latest events) of the event
            * t: time of event creation
            * c: identifying key of the first parent
            * s: digital sign of event by the first parent (using its secret key)

        :return: True: Successfully verified event.
        :return: False: Unsuccessfully verified event.
        :rtype: bool
        """
        verify_key_hex = bytes(ev.c.encode('utf-8'))
        data = bytes(dumps(ev.d, ev.p, ev.t, ev.c).encode('utf-8'))
        event_sig = unhexlify(ev.s.encode('utf-8'))

        if self.verify_signature(data, verify_key_hex, event_sig):
            return True
        else:
            return False

    def verify_concatenated(self, data):
        """
        Verifies data that contain signature concatenated with message

        :param data: dictionary containing the keys,
                        signed: concatenated data and signature for it
                        verify_key: verifies key (public key) to verify signature
        :return: The message: Successfully verified data.
        :return: False: Unsuccessfully verified data.
        """
        verify_key_hex = data['verify_key'].encode('utf-8')
        data_bytes = unhexlify(data['signed'].encode('utf-8'))

        return self.verify_signature(data_bytes, verify_key_hex)

    def validate_state_sign(self, sign):
        """
        Validates state signature

        :param sign: state signature
        :type sign: dict
        :return: data or False if error
        :rtype: dict or bool
        """
        if sign and 'signed' in sign:
            verify_res = self.verify_concatenated(sign).decode('utf-8')
            if verify_res:
                return loads(verify_res)

        # it is not a signature or could not validate signature
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
