import logging
from twisted.internet import reactor, error

from prisma import __version__


def Prisma():
    """
    Returns PrismaApp instance. This must be defined here, otherwise the program won't run
    because of circular dependencies.

    :return: PrismaApp instance.
    """
    return PrismaManager.Instance()


from prisma.config import CONFIG
from prisma.utils.singleton import Singleton
from prisma.db.database import PrismaDB
from prisma.client.prompt import Prompt
from prisma.crypto.crypto import Crypto
from prisma.crypto.wallet import Wallet
from prisma.cryptograph.graph import Graph
from prisma.cryptograph.signed_state import SignedStateManager
from prisma.api.service import ApiService
from prisma.network.service import NetworkService
from prisma.utils.common import Common


@Singleton
class PrismaManager:
    """
    PrismaApp setups the applications and also contains variables and functions that
    can be called from anywhere the code.
    """
    def __init__(self):
        self.logger = logging.getLogger('Prisma')
        self.config = CONFIG
        self.db = None
        self.wallet = None
        self.crypto = None
        self.common = None
        self.graph = None
        self.callLater = reactor.callLater  # this is because when testing we're not using reactor
        self.api = None
        self.network = None
        self.version = __version__

    def start(self, is_prompt):
        """
        Start the app.

        :param is_prompt:
        :return:
        """
        self.logger.info('Starting Prisma v{0}'.format(self.version))
        try:
            self.common = Common()
            self.db = PrismaDB(self.config.get('general', 'database'))
            self.wallet = Wallet()
            self.crypto = Crypto()

            self.graph = Graph()
            self.state_manager = SignedStateManager(self.graph)
            is_cg_empty = self.graph.init_events()
            self.graph.restore_invariants(is_cg_empty)

            if is_cg_empty:
                self.graph.sync_genesis()

            self.api = ApiService()
            self.network = NetworkService()
            self.network.start()
            self.api.start()
            if is_prompt:
                # set prompt with a thread
                prompt = Prompt()
                reactor.callInThread(prompt.run)  # callInThread will make input non-blocking
        except error.CannotListenError as e:
            self.logger.critical('Port %i is already in use.', e.port)
        except Exception as e:
            self.logger.exception('Error: ' + str(e))
            exit(1)

    def stop(self):
        """
        Called when stopping the app.

        :return:
        """
        self.logger.debug('Stopping Prisma')
        self.network.stop()
        self.api.stop()
        # reactor is not running while running tests, that's why checks status
        if reactor.running:
            reactor.stop()
