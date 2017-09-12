import logging

TYPE_MONEY_TRANSFER = 0
TYPE_SIGNED_STATE = 1


class TxValidator(object):

    def __init__(self):
        self.logger = logging.getLogger('Transaction validator')

    def transaction(self, tx):
        """ Validate a dictionary of a formed transaction.

        :param tx: transaction dictionary
        :type tx: dict
        :rtype: bool
        """

        if self.wallet_address(tx['recipientId']) and \
                self.wallet_address(tx['senderId']) and \
                self.amount(tx['amount']) and \
                self.public_key(tx['senderPublicKey']) and \
                self.tx_type(tx['type']):
            return True
        return False

    def wallet_address(self, address):
        """
        Validate senderId or recipientId (wallet address).
        
        :param address: address
        :type address: string
        :rtype: bool
        """

        if address and len(address) == 21:
            try:
                isinstance(int(address[:-2]), int)
                return True
            except Exception as e:
                self.logger.error("Wallet address not valid. Reason: {0}".format(e))
        self.logger.error("Wallet address not valid.")
        return False

    def amount(self, _amount):
        """
        Validate funds amount.
        
        :param _amount: amount of funds
        :type _amount: int
        :rtype: bool
        """

        if isinstance(_amount, int) and _amount > 0:
            if not _amount > 9223372036854775807: # to be made decimal
                return True
            else:
                self.logger.error("Amount succeeds maximal transfer unit.")
        self.logger.error("Invalid transaction amount.")
        return False

    def public_key(self, public_key):
        """
        Validate public key.
        
        :param public_key: public key
        :type public_key: hex string
        :rtype: bool
        """

        if len(public_key) == 64:
            try:
                int(public_key, 16)
                return True
            except Exception as e:
                self.logger.error("Invalid public key. Reason: {0}".format(e))
        self.logger.error("Invalid public key.")
        return False

    def tx_type(self, _type):
        """
        Validate transaction types

        :param _type: funds transfer or signed state
        :type _type: string
        :rtype: bool
        """

        # TODO: Should not use string as tx type. Now we have to type cast. 
        if isinstance(_type, str) and int(_type) == TYPE_MONEY_TRANSFER or int(_type) == TYPE_SIGNED_STATE:
            return True
        self.logger.error("Invalid transaction type.")
        return False
