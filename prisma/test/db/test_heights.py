from prisma.test.testutils.testcase import PrismaTestCase


class PrismaDbHeights(PrismaTestCase):
    def test_get_heights_many(self):
        """
        Tests height by checking the genesis and not genesis.
        """
        heights = self.prisma.db.get_heights_many()
        events = self.prisma.db.get_events_many()
        for e in events:
            self.assertTrue(e in heights)
            if events[e].p == ():
                self.assertTrue(heights[e] == 0)
            else:
                self.assertTrue(heights[e] > 0)
