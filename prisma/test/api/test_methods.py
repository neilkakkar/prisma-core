from prisma.test.testutils.testcase import PrismaTestCase

from prisma.api.methods import ApiMethods


class PrismaApiMethods(PrismaTestCase):
    """
    Test cases for Api methods.
    """
    def test_last_event_time(self):
        r = ApiMethods.last_event_time()
        self.assertTrue('latest_event_time' in r)
