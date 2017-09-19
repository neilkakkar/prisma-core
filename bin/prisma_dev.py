import sys
import json
import collections

from time import time
from json import dumps, dump, load
from pymongo import MongoClient

from prisma.manager import Prisma
from prisma.crypto.crypto import Crypto


class PrismaDev:
    def __init__(self):
        self.genesis_balances_file = 'bin/balances.json'
        self.genesis_output_file = 'prisma/cryptograph/genesis.json'
        self.db_connection = MongoClient(serverSelectionTimeoutMS=2000, connect=False)

    def write_JSON_to_file(self, path, data):
        try:
            with open(path, "w") as storage:
                dump(data, storage)
                print('Successfully wrote genesis event.')
        except Exception as e:
            print('Could not write genesis event . Reason: ', e)
        return False

    def read_JSON_from_file(self, path):
        try:
            with open(path) as genesis_file:
                res = load(genesis_file)
            return res
        except Exception as e:
            print('Could not read from file, path:', path, e)
        return False

    def main(self):
        if len(sys.argv) == 1:
            print('Run: prisma_dev.py drop|genesis')
            exit()
        elif sys.argv[1] == 'drop':
            database_list = self.db_connection.database_names()
            for database in database_list:
                if database != 'local':
                    self._destroy_db(database)
        elif sys.argv[1] == 'genesis':
            balances = self.read_JSON_from_file(self.genesis_balances_file)
            # generate random wallet issuer of the genesis event
            balance = collections.OrderedDict(sorted(balances.items()))

            state = {'balance': balance}
            state_hash = Crypto().blake_hash(bytes(dumps(state).encode('utf-8')))

            genesis = {
                'state': state,
                'round': -1,
                'hash': state_hash,
                'signed': True
            }

            print(genesis)
            self.write_JSON_to_file(self.genesis_output_file, genesis)

    def _destroy_db(self, database):
        self.db_connection.drop_database(database)

# if this module is called directly then go to the entry point
if __name__ == '__main__':
    prisma_dev = PrismaDev()
    prisma_dev.main()
