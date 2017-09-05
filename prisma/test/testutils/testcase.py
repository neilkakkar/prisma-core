from twisted.trial.unittest import TestCase
from twisted.internet import task
from pymongo import MongoClient

from prisma.manager import Prisma
from prisma.config import CONFIG


class PrismaTestCase(TestCase):
    """
    This class is made to speedup things when testing. Basically already implements a setUp and tearDown functions.
    """
    DATABASE_NAME = 'prisma_testing'

    PK_ADDRESS = '7076333928921313840PR'
    SK = b'0ff8f749918a1cfd5278c50e5b36002aea8f466b4ec92b0a6593e6c531d35dd6'
    PK = b'b407af205207a9ab341a01e96456caf27f3d6455649dc2fe069953c9981805e2'
    SK_CURVE25519 = b'48a73ba86cb5d650b4d24f142d07917f1726bd3ddb07fb1cc865b24a28c1135c'
    PK_CURVE25519 = b'6f44f4d07c1ec3c68f32873e9a76803841d2a1154d14025f21c372fe5edb6006'

    def setUp(self):
        self._set_up()

    def _set_up(self):
        self._destroy_db()
        CONFIG.set('general', 'database', self.DATABASE_NAME)
        CONFIG.set('general', 'network', 'testnet')
        CONFIG.set('general', 'wallet_address', '3918807197700602162PR')
        CONFIG.set('bootstrap', 'bootstrap_nodes', '[]')
        CONFIG.set('developer', 'wallet_password', 'test1')
        self.clock = task.Clock()
        self.prisma = Prisma()
        self.prisma.callLater = self.clock.callLater
        self.prisma.start(False)

    def _destroy_db(self):
        connection = MongoClient(serverSelectionTimeoutMS=2000, connect=False)
        connection.drop_database(self.DATABASE_NAME)

    def tearDown(self):
        self._tear_down()

    def _tear_down(self):
        self.prisma.stop()
