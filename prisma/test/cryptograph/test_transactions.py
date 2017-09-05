import json
from binascii import unhexlify

from prisma.test.testutils.testcase import PrismaTestCase


class PrismaCryptographTransactions(PrismaTestCase):
    """
    Test cases for Api methods.
    """
    def _create_test_keystore(self):
        return {
            'privateKeySeed': self.SK,
            'publicKey': self.PK,
            'address': self.PK_ADDRESS
        }

    def test_insert_transaction(self):
        keystore = self.prisma.graph.keystore
        keystore_genesis = self._create_test_keystore()

        # create transaction for main account to have some money
        transaction_hex = self.prisma.wallet.transaction.form_transaction(keystore_genesis, keystore['address'], 1000)
        transaction = self.prisma.wallet.transaction.unhexify_transaction(transaction_hex)
        transaction_dict = json.loads(unhexlify(transaction['tx_hex']).decode('utf-8'))
        transaction_dict['tx_dict_hex'] = transaction_hex
        self.prisma.db.insert_transactions([transaction_dict])

        self.assertTrue(self.prisma.db.get_account_balance(keystore['address']) == 1000)

        # create a transaction to alt
        recipient_address = '3558462963507083618PR'
        transaction_hex = self.prisma.wallet.transaction.form_transaction(keystore, recipient_address, 1)
        self.prisma.wallet.transaction.insert_transactions_into_pool([transaction_hex])

        self.assertTrue(self.prisma.db.get_account_balance(keystore['address']) == 999)
        self.assertTrue(self.prisma.db.get_account_balance(recipient_address) == 1)
