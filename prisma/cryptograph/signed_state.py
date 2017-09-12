# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging
import collections
from json import dumps

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

    def get_con_sign_response(self):
        """
        Gets unsent state from db, then gets its hash,
        and finally signs hash and last round by secret key

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
            # Generate state for round
            balance = Prisma().db.get_account_balance_many(
                [consensus[0], consensus[-1]])
            state = collections.OrderedDict(sorted(balance.items()))
            state_hash = self.crypto.blake_hash(bytes(dumps(state).encode('utf-8')))
            Prisma().db.delete_money_transfer_transaction_less_than(consensus[-1])
            Prisma().db.insert_state(state, consensus[-1], state_hash)
        else:
            # State was generated before
            state_hash = state_db['hash']

        data = {'last_round': consensus[-1], 'hash': state_hash}
        self.logger.debug("State signature data %s", str(data))

        # Form transaction
        data['type'] = TYPE_SIGNED_STATE
        hex_str = self.transaction.hexlify_transaction(data)

        Prisma().db.set_consensus_last_created_sign(consensus[-1])
        return hex_str

    def get_con_signatures(self):
        """
        While there are enough rounds where famousness is fully decided,
        creates signature (size is defined as constant in graph class)
        and pushes this signature to list. Afterwards, all created
        signatures are inserted into the pool.

        :returns: None
        """
        consensus_signatures = []

        while self.graph.unsent_count >= self.graph.to_sign_count:
            self.logger.debug("Signed state unsent count %s", str(self.graph.unsent_count))
            try:
                res = self.get_con_sign_response()
            except ValueError as e:
                self.logger.error("Error with get con signature %s", str(e))
                break

            if res:
                consensus_signatures.append(res)
                self.graph.unsent_count -= self.graph.to_sign_count
                self.logger.debug("Consensus signature was generated %s", str(res))

        self.logger.debug("Consensus sign response = %s", str(consensus_signatures))
        self.transaction.insert_transactions_into_pool(consensus_signatures)

    def handle_new_sign(self, transaction_dict):
        """
        If transaction if valid, stores it
        as unchecked to db (that means that we have not
        compared this remote hash with our local),
        also checks whether there are enough rounds for which
        all famous events are completely determined
        in order to create the signature of state
        On success, sign so many state as we can.

        :param transaction_dict: parsed transaction dict
        :type transaction_dict: dict
        :returns: None
        """
        if transaction_dict:
            # Validates signature
            self.logger.debug("transaction_dict: %s", str(transaction_dict))
            sign_data = self.crypto.validate_sign_consensus(transaction_dict)
            self.logger.debug("sign_data: %s", str(sign_data))

            if (sign_data and sign_data['last_round'] > self.graph.last_signed_state
                and sign_data['sign']['verify_key'] != self.crypto.get_verify_key(self.graph.keystore['privateKeySeed'])):
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
                        self.logger.error("Consensus hash is NOT equal.")
            # All stored unchecked signatures are processed now, so we can delete them
            Prisma().db.unset_unchecked_signature(local_signatures['_id'])

        ''' Calculates total count of valid signatures '''
        sign_count = unchecked_len
        if 'sign' in local_signatures:
            sign_count += len(local_signatures['sign'])

        ''' If there are enough signatures, signs consensus and cleans db '''
        # sign + 1, for our self sign
        if (sign_count + 1) >= self.graph.min_s:
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
        hash_list = Prisma().db.get_rounds_less_than(last_signed)
        for _hash in hash_list:
            Prisma().db.delete_event(_hash)
            Prisma().db.delete_can_see(_hash)
            Prisma().db.delete_votes(_hash)
            Prisma().db.delete_height(_hash)
            Prisma().db.delete_famous(_hash)

        ''' We should clear references after removing documents by hash.
            In this case we will get much better performance '''
        # Delete each link to signed events
        Prisma().db.delete_round_less_than(last_signed)
        Prisma().db.delete_references_can_see(hash_list)

    def update_state(self):
        Prisma().db.set_consensus_last_sent(Prisma().db.get_consensus_last_created_sign())
