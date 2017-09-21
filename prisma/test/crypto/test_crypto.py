from binascii import hexlify

from prisma.test.testutils.testcase import PrismaTestCase


class PrismaCryptoCryptoTestCase(PrismaTestCase):
    """
    Test cases for crypto.
    """
    def test_generate_keypair(self):
        key_pair = self.prisma.wallet.crypto.generate_keypair()
        sk = hexlify(bytes(key_pair))
        sk2 = hexlify(bytes(key_pair))
        self.assertTrue(sk == sk2)
        sk_curve25519 = hexlify(bytes(key_pair.to_curve25519_private_key()))
        pk = hexlify(bytes(key_pair.verify_key))
        pk_curve25519 = hexlify(bytes(key_pair.verify_key.to_curve25519_public_key()))
        self.assertTrue(len(sk) == 64)  # 32 bytes, 256 bits
        self.assertTrue(len(sk_curve25519) == 64)
        self.assertTrue(len(pk) == 64)
        self.assertTrue(len(pk_curve25519) == 64)
