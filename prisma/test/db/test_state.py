from prisma.test.testutils.testcase import PrismaTestCase


class PrismaDbHeights(PrismaTestCase):
    def _add_example_states(self):
        self.prisma.db.insert_state(
            {
                "3558462963507083618PR": 100000,
                "3832901052830737971PR": -500000,
                "3918807197700602162PR": 100000,
                "7306589250910697267PR": 300000
            },
            9,
            'cace9158277350b011a7336fc2ded9466a37f9119912909f693973e74231f5ab'
        )
        self.prisma.db.insert_state(
            {
                "3558462963507083618PR": 100000,
                "3761975960047924065PR": 1,
                "3832901052830737971PR": -500000,
                "3918807197700602162PR": 99999,
                "7306589250910697267PR": 300000
            },
            14,
            'bb423e2c04ede3e3fe7091ff56810c4b0d0bd1fa9ee472271b642adb3c7dec3e'
        )
        self.prisma.db.insert_state(
            {
                "3558462963507083618PR": 100000,
                "3832901052830737971PR": -500000,
                "3918807197700602162PR": 100000,
                "7306589250910697267PR": 300000
            },
            4,
            'cace9158277350b011a7336fc2ded9466a37f9119912909f693973e74231f5ab'
        )

    def test_get_last_state(self):
        """
        Tests the last state.
        """
        last_state = self.prisma.db.get_last_state()
        self.assertFalse(last_state)
        self._add_example_states()
        last_state = self.prisma.db.get_last_state()
        self.assertTrue(last_state['_id'] == 14)
