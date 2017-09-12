import sys
import json
from time import time
from pymongo import MongoClient

from prisma.manager import Prisma


class PrismaDev:
    def __init__(self):
        self.db_connection = MongoClient(serverSelectionTimeoutMS=2000, connect=False)

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
            Prisma().start(False)
            wallet = Prisma().wallet
            crypto = wallet.crypto
            genesis_tx = {
                '3918807197700602162PR': 100000,
                '3558462963507083618PR': 100000,
                '7306589250910697267PR': 300000
            }
            # generate random wallet issuer of the genesis event
            keys = wallet.new_wallet('password', False)
            if not keys:
                raise Exception('Error while generating wallet')
            # prepare tx
            tx_list = []
            for addr, amount in genesis_tx.items():
                tx_list.append(wallet.transaction.form_money_transfer_tx(keys, addr, amount))
            # create genesis
            t = time()
            s = crypto.sign_event(json.dumps((tx_list, (), t, keys['publicKey'].decode())), keys['privateKeySeed'])
            ev = [tx_list, (), t, s['verify_key'], s['signed']]
            genesis_json = {crypto.blake_hash(bytes(json.dumps(ev).encode('utf-8'))): ev}
            # print genesis_json
            print(json.dumps(genesis_json))

    def _destroy_db(self, database):
        self.db_connection.drop_database(database)

# if this module is called directly then go to the entry point
if __name__ == '__main__':
    prisma_dev = PrismaDev()
    prisma_dev.main()
