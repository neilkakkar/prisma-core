import logging

TYPE_MONEY_TRANSFER = 0
TYPE_SIGNED_STATE = 1


class TxValidator(object):

    def __init__(self):
        self.logger = logging.getLogger('Transaction validator')

    def transaction(self, tx):
        if self.wallet_address(tx['recipientId']) and \
                self.wallet_address(tx['senderId']) and \
                self.amount(tx['amount']) and \
                self.public_key(tx['senderPublicKey']) and \
                self.tx_type(tx['type']):
            return True
        return False

    def wallet_address(self, address):
        if address and len(address) == 21:
            try:
                isinstance(int(address[:-2]), int)
                return True
            except Exception as e:
                self.logger.error("Wallet address not valid. Reason: {0}".format(e))
        self.logger.error("Wallet address not valid.")
        return False

    def amount(self, _amount):
        if isinstance(_amount, int) and _amount > 0:
            if not _amount > 9223372036854775807:
                return True
            else:
                self.logger.error("Amount succeeds maximal transfer unit.")
        self.logger.error("Invalid transaction amount.")
        return False

    def public_key(self, public_key):
        if len(public_key) == 64:
            try:
                int(public_key, 16)
                return True
            except Exception as e:
                self.logger.error("Invalid public key. Reason: {0}".format(e))
        self.logger.error("Invalid public key.")
        return False

    def tx_type(self, _type):
        if isinstance(_type, int) and _type == TYPE_MONEY_TRANSFER or _type == TYPE_SIGNED_STATE:
            return True
        self.logger.error("Invalid transaction type.")
        return False
