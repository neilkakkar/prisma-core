# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging
import collections
from json import dumps, loads

from prisma.manager import Prisma
from prisma.crypto.crypto import Crypto
from prisma.cryptograph.transaction import Transaction, TYPE_SIGNED_STATE


class SignedStateManager(object):
    """
    Signed state manager
    """
    def __init__(self, graph):
        """
        Create class instance

        :param graph: instance of Graph class
        :type graph: object
        :returns instance of SignedStateManager class
        :rtype: object
        """
        self.graph = graph
        self.crypto = Crypto()
        self.transaction = Transaction()
        self.logger = logging.getLogger('SignedStateManager')

    def get_ordered_state(self, last_round, prev_hash, balance):
        """ Gets ordered dict of state
        
        :param last_round: last round of state
        :type last_round: int 
        :param prev_hash: hash of previous state
        :type prev_hash: str
        :param balance: sorted balance of all nodes  
        :type balance: sorted dict
        :return: ordered state
        :rtype: ordered dict
        """
        state = collections.OrderedDict([
            ('_id', last_round),
            ('prev_hash', prev_hash),
            ('balance', balance)
        ])

        return state

    def create_state(self, start_round, last_round):
        """ Generate state for given round range
        
        :param start_round: 
        :param last_round:
        :return: hash of newly created state
        :rtype: str
        """
        # Gets Prev_hash
        prev_hash = Prisma().db.get_last_state()['hash']

        # Gets and sort Balance
        balance_dict = Prisma().db.get_account_balance_many(
            [start_round, last_round])
        balance = collections.OrderedDict(sorted(balance_dict.items()))

        state = self.get_ordered_state(last_round, prev_hash, balance)
        state_hash = self.crypto.blake_hash(bytes(dumps(state).encode('utf-8')))

        # Result of all old transactions is saved in newly created state, so we can drop tx
        Prisma().db.delete_money_transfer_transaction_less_than(last_round)
        Prisma().db.insert_state(state, state_hash)
        return state_hash

    def create_state_sign(self):
        """
        Gets unsent state from db or create if it is not exit, 
        then gets its hash, and finally signs hash and 
        last round of this state by nodes secret key

        :returns: transaction with state signature
        :rtype: str
        """
        # Get rounds where famousness is fully decided
        consensus = Prisma().db.get_consensus_greater_than(
            Prisma().db.get_consensus_last_created_sign(),
            lim=self.graph.to_sign_count)
        self.logger.debug("State consensus %s", str(consensus))

        if len(consensus) != self.graph.to_sign_count:
            raise ValueError("Not enough rounds where famousness is fully decided!")

        state_db = Prisma().db.get_state(consensus[-1])
        if not state_db:
            state_hash = self.create_state(consensus[0], consensus[-1])
        else:
            # State was generated before
            state_hash = state_db['hash']

        data = {'last_round': consensus[-1], 'hash': state_hash}
        self.logger.debug("State signature data %s", str(data))
        sign_data = self.crypto.sign_data(dumps(data), self.graph.keystore['privateKeySeed'])

        # Form transaction
        sign_data['type'] = TYPE_SIGNED_STATE
        hex_str = self.transaction.hexlify_transaction(sign_data)

        Prisma().db.set_consensus_last_created_sign(consensus[-1])
        # Save our signature in orrder to send it to new node
        data['sign'] = sign_data
        Prisma().db.insert_signature(data)

        return hex_str

    def try_create_state_signatures(self):
        """
        While there are enough rounds where famousness is fully decided,
        creates state and than digitally sign this
        and pushes this signature to list. Afterwards, all created
        signatures are inserted into the pool.

        :returns: None
        """
        state_signatures = []

        while self.graph.unsent_count >= self.graph.to_sign_count:
            self.logger.debug("Signed state unsent count %s", str(self.graph.unsent_count))
            try:
                new_signature = self.create_state_sign()
            except ValueError as e:
                self.logger.error("Error with get state signature %s", str(e))
                break

            if new_signature:
                state_signatures.append(new_signature)
                self.graph.unsent_count -= self.graph.to_sign_count
                self.logger.debug("State signature was generated %s", str(new_signature))

        self.logger.debug("Consensus sign response = %s", str(state_signatures))
        self.transaction.insert_transactions_into_pool(state_signatures)

    def handle_new_sign(self, tx_dict):
        """
        If transaction if valid, stores it
        as unchecked to db (that means that we have not
        compared this remote hash with our local),
        also checks whether there are enough rounds for which
        all famous events are completely determined
        in order to create the signature of state
        On success, sign so many state as we can.

        :param tx_dict: parsed transaction dict
        :type tx_dict: dict
        :returns: None
        """
        if tx_dict:
            # Validates signature
            self.logger.debug("tx_dict: %s", str(tx_dict))
            sign_data = self.crypto.validate_state_sign(tx_dict)

            del tx_dict['type']
            sign_data['sign'] = tx_dict
            self.logger.debug("sign_data: %s", str(sign_data))

            if (sign_data and sign_data['last_round'] > self.graph.last_signed_state and
                sign_data['sign']['verify_key'] != self.graph.keystore['publicKey'].decode('utf-8')):
                # Inserts signature as unchecked
                Prisma().db.insert_signature_unchecked(sign_data)

                # Try to sign local state
                while True:
                    self.logger.debug("Handle state signatures last_signed_state %s", str(self.graph.last_signed_state))
                    local_consensus = Prisma().db.get_consensus_greater_than(
                        self.graph.last_signed_state, lim=self.graph.to_sign_count)

                    # if there is enough consensus to sign
                    if (len(local_consensus) != self.graph.to_sign_count or
                            not self.update_state_sign(local_consensus)):
                            break

    def update_state_sign(self, local_consensus):
        """
        Handles signatures of state stored in db

        :param local_consensus: local stored rounds where famousness is fully decided
        :type local_consensus: tuple
        :return: True if signed state is reached and False in opposite case
        :rtype: bool
        """
        local_signatures = Prisma().db.get_signature(local_consensus[-1])
        self.logger.debug("Local signatures %s", str(local_signatures))

        if not local_signatures:
            self.logger.debug("There is no local signatures")
            return False

        # Hash of local state
        local_hash = Prisma().db.get_state(local_signatures['_id'])['hash']

        # Count of successfully checked signatures
        unchecked_len = 0

        ''' Checks if hash of pair is equal to local, on success inserts 
            signature to db as checked and increments sign count. 
            Note: pair consists of hash of consensus and its sign. '''

        if 'unchecked_pair' in local_signatures:
            for pair in local_signatures['unchecked_pair']:
                for h, sign in pair.items():
                    self.logger.debug("Local con hash %s", str(local_hash))
                    self.logger.debug("Remote hash %s", str(h))

                    if h == local_hash and ('sign' not in local_signatures or sign not in local_signatures['sign']):
                        self.logger.debug("Consensus hash is equal.")
                        data = {'last_round': local_signatures['_id'], 'sign': sign, 'hash': h}
                        Prisma().db.insert_signature(data)
                        unchecked_len += 1
                    else:
                        self.logger.error("Consensus hash is NOT equal or that signature is already saved.")
            # All stored unchecked signatures are processed now, so we can delete them
            Prisma().db.unset_unchecked_signature(local_signatures['_id'])

        ''' There are no new valid signatures '''
        if not unchecked_len:
            return False

        ''' Calculates total count of valid signatures '''
        sign_count = unchecked_len
        if 'sign' in local_signatures:
            sign_count += len(local_signatures['sign'])

        ''' If there are enough signatures, signs consensus and cleans db '''
        if sign_count >= self.graph.min_s:
            self.logger.debug("Signs consensus")

            Prisma().db.sign_consensus(self.graph.to_sign_count)

            self.graph.last_signed_state = local_consensus[-1]
            self.logger.debug("self.graph.last_signed_state %s", str(self.graph.last_signed_state))

            # Start cleaning database
            self.clean_database(self.graph.last_signed_state)
            Prisma().db.set_state_signed(local_signatures['_id'])
            return True
        else:
            return False

    def clean_database(self, last_signed):
        """
        Deletes signed data from db, so there will never be a huge number of data stored

        :param last_signed: last round for which signed state was reached
        :type last_signed: int
        :return: None
        """
        Prisma().db.delete_transaction_less_than(last_signed)
        Prisma().db.delete_witnesses_less_than(last_signed)

        # Gets list of signed events
        hash_list = Prisma().db.get_rounds_hash_list(last_signed)
        for _hash in hash_list:
            Prisma().db.delete_event(_hash)
            Prisma().db.delete_can_see(_hash)
            Prisma().db.delete_votes(_hash)
            Prisma().db.delete_famous(_hash)

        ''' We should clear references after removing documents by hash.
            In this case we will get much better performance '''
        # Delete each link to signed events
        Prisma().db.delete_references_can_see(hash_list)

    def handle_received_state(self, state, signatures):
        """ Validates state received via connection
        
        :param state: state to validate
        :type state: dict
        :param signatures: list of signatures from more than 1/3 voting power
        :type signatures: list
        :return: is handling operation successful 
        """
        last_state_hash = Prisma().db.get_last_state()['hash']

        if last_state_hash != state['prev_hash']:
            self.logger.error("Recived state have bad hash of prev state")
            return False

        '''balance = collections.OrderedDict(sorted(state['balance'].items()))
        ordered_state = self.get_ordered_state(state['_id'], state['prev_hash'], balance)
        self.logger.debug("ordered_state: %s", str(ordered_state))

        state_hash = self.crypto.blake_hash(bytes(dumps(ordered_state).encode('utf-8')))'''
        state_hash = self.crypto.blake_hash(bytes(dumps(state).encode('utf-8')))

        # TODO improve signature storing and validation
        signature_list = []
        proof_sign_count = 0
        for verify_key in signatures:
            # Verifies signed data
            temp_dict = {'verify_key': verify_key, 'signed': signatures[verify_key]}
            sign_data = self.crypto.validate_state_sign(temp_dict)

            if not sign_data:
                # Incorrect verify_key
                return False

            node_addr = Prisma().wallet.addr_from_public_key(bytes(verify_key.encode('utf-8')))

            self.logger.debug("node_addr: %s", str(node_addr))
            self.logger.debug("node ballance: %s", str(Prisma().db.get_state_balance(node_addr)))
            self.logger.debug("sign_data['last_round'] = %s, state['_id'] = %s", str(sign_data['last_round']), str(state['_id']))
            self.logger.debug("sign_data['hash'] = %s, state_hash = %s", str(sign_data['hash']), str(state_hash))

            if (Prisma().db.get_state_balance(node_addr) and
                sign_data['last_round'] == state['_id'] and
                sign_data['hash'] == state_hash):

                # All is good add signature to valid list and count it as proof
                sign_data['sign'] = temp_dict
                signature_list.append(sign_data)
                proof_sign_count += 1
            else:
                self.logger.error("Recived state have bad signature")

        # Checks if we get enough signatures
        if proof_sign_count >= self.graph.min_s:
            Prisma().db.insert_state(state, state_hash, True)
            for sign in signature_list:
                Prisma().db.insert_signature(sign)
            return True
        else:
            self.logger.error("Recived state have not enough proof signatures")
            return False

    def handle_received_state_chain(self, chain):
        """ 
        
        :param chain: Chain of states and signatures as proof
        :type chain: list
        :return: is handling successful 
        """
        for stateunit in chain:
            if not self.handle_received_state(stateunit['state'], stateunit['signatures']):
                return False
        return True
