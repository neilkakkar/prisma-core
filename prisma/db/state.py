# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging

class State(object):
    def __init__(self, prismaDB, super):
        self.logger = logging.getLogger('PrismaDB-state')
        self.db = prismaDB
        self.super = super

    def get_state(self, r, exclude_hash=False):
        """
        Gets state by last_round

        :param r: last_round for state
        :type r: int
        :param exclude_hash: remove hash from result or not
        :type exclude_hash: bool
        :return: state (balance of all wallets)
        :rtype: dict
        """
        try:
            projection = None
            if exclude_hash:
                projection = {'hash': False}

            state = self.db.state.find_one({'_id': r}, projection)
            self.logger.debug("Get state %s", str(state))
            return state
        except Exception as e:
            self.logger.error("Could not get state for round %s. Reason: %s", r, str(e))
        return False

    def get_last_state(self):
        """
        Gets the last state and round of the state.

        :return:
        """
        try:
            state = list(self.db.state.find().sort('_id', -1).limit(1))
            if not state:
                return False
            return state[0]
        except Exception as e:
            self.logger.error("Could not get the last state. Reason: %s", str(e))
            return False

    def get_state_many(self, gt=0, signed=True, exclude_hash=True):
        """
        Gets all state stored in db
        
        :param gt: state round for greater than
        :type gt: int
        :param signed: get only signed or not
        :type signed: bool
        :param exclude_hash: remove hash from result or not
        :type exclude_hash: bool
        :return: list of states
        :rtype: list
        """
        state = []
        try:
            query = {'_id': {'$gt': gt}}
            if signed:
                query['signed'] = True

            projection = None
            if exclude_hash:
                projection = {'hash': False}

            db_res = self.db.state.find(query, projection)
            if db_res:
                for s in db_res:
                    state.append(s)
            self.logger.debug("Get state MANY %s", str(state))
            return state
        except Exception as e:
            self.logger.error("Could not get state. Reason: %s", str(e))
        return False

    def get_state_balance(self, address):
        """
        Gets wallet balance by address from last state

        :param address: address of wallet
        :type address: str
        :return: wallet balance
        :rtype: int
        """
        try:
            db_res = self.db.state.find({'balance.' + address: {'$exists': True}},
                                           {'_id': 0, 'balance.' + address: 1}).limit(1).sort('_id', -1)
            if db_res:
                for balance in db_res:
                    self.logger.debug("Get balance for address %s from state result = %s", str(address), str(balance['balance'][address]))
                    return balance['balance'][address]
                else:
                    self.logger.debug("No balance for address %s, return 0", str(address))
                    return 0
        except Exception as e:
            self.logger.error("Could not get state balance. Reason: %s", str(e))
            self.logger.debug("Address: %s", address)
        return False

    def get_wallets_state(self):
        """
        Gets all unique wallets in state

        :return:unique wallets
        :rtype: set
        """
        try:
            db_res = self.db.state.find().limit(1).sort('_id', -1)
            if db_res:
                for res in db_res:
                    self.logger.debug("Get wallets from state %s", str(res))
                    wallets = set(res['balance'].keys())
                    return wallets
            return set()
        except Exception as e:
            self.logger.error("Could not get state. Reason: %s", str(e))
        return False

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
        try:
            self.db.state.insert({'_id': state['_id'], 'prev_hash': state['prev_hash'],
                                  'balance': state['balance'], 'hash': hash, 'signed': signed})
            self.logger.debug("Insert into state balance = %s, hash = %s, signed = %s",
                              str(state), str(hash), str(signed))
            return True
        except Exception as e:
            self.logger.error("Could not insert state. Reason: %s", str(e))
        return False

    def set_state_signed(self, round):
        """
        Sets signed flag to state with last_round equal to given round

        :param round: last_round of state to sign
        :type round: int
        :return: was the setting operation successful
        :rtype: bool
        """
        try:
            self.db.state.update({'_id': round}, {'$set': {'signed': True}})
            self.logger.debug("Set state signed %s", str(round))
            return True
        except Exception as e:
            self.logger.error("Could set state signed. Reason: %s", str(e))
            self.logger.debug("Round:", round)
        return False

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
        try:
            self.logger.debug("Delete from state less than round %s", str(round))
            result = self.db.state.remove({'_id': {'$lt': round}, 'signed': True})
            self.logger.debug("Delete from state result %s", str(result))
            return True
        except Exception as e:
            self.logger.error("Could not delete from state. Reason: %s", str(e))
        return False

    def get_state_with_proof_many(self, gt):
        db_states = self.get_state_many(gt)
        stateunit_list = []
        for state in db_states:
            signatures = {}
            for sign in self.super.get_signature(state['_id'])['sign']:
                signatures[sign['verify_key']] = sign['signed']

            stateunit = {
                'state': state,
                'signatures': signatures
            }
            stateunit_list.append(stateunit)
        return stateunit_list

    def get_state_with_proof(self, r):
        db_state = self.get_state(r, True)

        signatures = {}
        for sign in self.super.get_signature(r)['sign']:
            signatures[sign['verify_key']] = sign['signed']

        stateunit = {
            'state': db_state,
            'signatures': signatures
        }

        return stateunit
