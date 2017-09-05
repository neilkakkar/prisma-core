import pytest
import collections
from prisma.cryptograph.graph import Graph
from prisma.cryptograph.signed_state import SignedStateManager
from prisma.db.database import PrismaDB
from prisma.cryptograph.transaction import Transaction
from prisma.crypto.crypto import Crypto

from_0_to_4_hash = "959877b44806b95933f5bc0ca550437ff1b038888b57e88ff27e60f136dad4e3"
from_5_to_10_hash = "cf6b07853ef5c4d232a663a69ba0b6da7f06ceb7fb9567ad2685ce91ab09be83"
our_from_0_to_4_sign_tx = "7b227665726966795f6b6579223a202237613139373163393966663166313261353030366531313539363366643961376463646133343561653961313032363433363830333664326435366639643338222c20227369676e6564223a202263353630666463353537353061343766613566333432633438383463616238313636343734626635636666653366636133376536373936333735346464383634336536366263326561396338363931373161356236643066653131363637653433383038343062636265396536623263366132626537653834333031613830393762323237333734363137323734323233613230333032633230323236383631373336383232336132303232333933353339333833373337363233343334333833303336363233393335333933333333363633353632363333303633363133353335333033343333333736363636333136323330333333383338333833383632333533373635333833383636363633323337363533363330363633313333333636343631363433343635333332323764222c20227369675f6465746163686564223a20226335363066646335353735306134376661356633343263343838346361623831363634373462663563666665336663613337653637393633373534646438363433653636626332656139633836393137316135623664306665313136363765343338303834306263626539653662326336613262653765383433303161383039227d"
remote_from_0_to_4_sign_tx = "7b227665726966795f6b6579223a202262623435616232343061373138383133353631616461366437633233326463323432343133336335306632303431653030383564656637303163663139353665222c20227369676e6564223a202231323431316565663237613464336464313630626337383666383932306633613565336139623838396130373432613063376463326134373963346332626337306263646530316662616365373537313639656632643731626538323839383361626666366531643934343234623834353065666462353163656233366230633762323236383631373336383232336132303232333933353339333833373337363233343334333833303336363233393335333933333333363633353632363333303633363133353335333033343333333736363636333136323330333333383338333833383632333533373635333833383636363633323337363533363330363633313333333636343631363433343635333332323263323032323733373436313732373432323361323033303764222c20227369675f6465746163686564223a20223132343131656566323761346433646431363062633738366638393230663361356533613962383839613037343261306337646332613437396334633262633730626364653031666261636537353731363965663264373162653832383938336162666636653164393434323462383435306566646235316365623336623063227d"
remote_from_5_to_9_sign_tx = "7b227665726966795f6b6579223a202262623435616232343061373138383133353631616461366437633233326463323432343133336335306632303431653030383564656637303163663139353665222c20227369676e6564223a202266636661653433626131376432636430383538383832633161373464393735323031643134643236636339343864343063613062646139346330376262343962376239653461386630363237613636396263356561343163366134383661316437343334313862393661343439653736306365356262393664346132643830303762323236383631373336383232336132303232363336363336363233303337333833353333363536363335363333343634333233333332363133363336333336313336333936323631333036323336363436313337363633303336363336353632333736363632333933353336333736313634333233363338333536333635333933313631363233303339363236353338333332323263323032323733373436313732373432323361323033353764222c20227369675f6465746163686564223a20226663666165343362613137643263643038353838383263316137346439373532303164313464323663633934386434306361306264613934633037626234396237623965346138663036323761363639626335656134316336613438366131643734333431386239366134343965373630636535626239366434613264383030227d"
remote_from_10_to_14_sign_tx = "7b227665726966795f6b6579223a202262623435616232343061373138383133353631616461366437633233326463323432343133336335306632303431653030383564656637303163663139353665222c20227369676e6564223a2022343339613635336364663837616331396131353337646235653663343235353537383139393238666333363833653065396464393137303138613563313133333230613963626466326234356465373831623264643161663431636436656336666238636263373038346136393736306163336137313436353931356437303437623232363836313733363832323361323032323632333136333339333133363636333333383332363633363631333636313338333533333336333236323334333036353338333933393333333133323335333833313338333333383337333536313339333033323335333133383333333836313334333036333636363533373337333036313636363333383330363633383337323232633230323237333734363137323734323233613230333133303764222c20227369675f6465746163686564223a20223433396136353363646638376163313961313533376462356536633432353535373831393932386663333638336530653964643931373031386135633131333332306139636264663262343564653738316232646431616634316364366563366662386362633730383461363937363061633361373134363539313564373034227d"

remote_from_0_to_4_wrong_hash_tx = "7b227369676e6564223a202234633363393065656531653135396265356165656566363931653635653338373032663732636331613237383663346635633664336231326538336662616365386337656535313731626264383365316430663436323630373363386463333463643161303066633963653634623362313838636563643836616136666230663762323236383631373336383232336132303232333136343334333633303339363233353336333933313331363136313330333133303633333236363339333633303632363433383635333636363634333533323332363433363338333836343634363336343633363233333332333336353635333233313335333836323334363233393330333233343633333433353633363332323263323032323733373436313732373432323361323033303764222c20227369675f6465746163686564223a20223463336339306565653165313539626535616565656636393165363565333837303266373263633161323738366334663563366433623132653833666261636538633765653531373162626438336531643066343632363037336338646333346364316130306663396365363462336231383863656364383661613666623066222c20227665726966795f6b6579223a202262623435616232343061373138383133353631616461366437633233326463323432343133336335306632303431653030383564656637303163663139353665227d"


class TestSignedState(object):
    @pytest.fixture(scope="function")
    def signed_state_instance(self):
        """
        Fixture to tear up and tear down
        """
        database = PrismaDB('test_db')
        database.destroy_db()
        database.create_collections()
        database.create_indexes()

        graph = Graph(database, "password1")

        signed_state_manager = SignedStateManager(graph)
        yield signed_state_manager
        database.destroy_db()

    @pytest.fixture(scope="module")
    def get_remote_cg(self, request):
        """
        Fixture to format the event with given transactions
        """
        ev = collections.namedtuple('Event_', 'd')
        ev_tuple = ev(request.param)
        remote_cg = {'somehash': ev_tuple}
        return remote_cg

    # Creation of one sign
    def test_sign_creating_without_data(self, signed_state_instance):
        """
        Test of creation of sign without data in db
        """
        with pytest.raises(ValueError):
            signed_state_instance.get_con_sign_response()

    def test_sign_creating(self, signed_state_instance):
        """
        Test of creation of one ordinary signature from 0 to 4
        """
        transaction = Transaction(signed_state_instance.graph.database)
        crypto = Crypto()

        # Insert consensus
        signed_state_instance.graph.database.insert_consensus(set(range(5)))
        # Check if it was successfully inserted
        assert signed_state_instance.graph.database.get_consensus_count() == 5

        # From 0 to 4
        created_sign = signed_state_instance.get_con_sign_response()

        # Check if generated tx is valid
        tx_dict = transaction.parse_transaction_hex(created_sign)
        assert tx_dict != False

        # Check if signature is valid
        data = crypto.validate_sign_consensus(tx_dict)
        assert data != False

        # Check main data fields
        assert data['hash'] == from_0_to_4_hash
        assert data['start'] == 0

        # Check last_created flag in db
        assert signed_state_instance.graph.database.get_consensus_last_created_sign() == 4

    # Creation of many sign
    def test_sign_creating_many_without_data(self, signed_state_instance):
        """
        Test of creation of many signatures without providing data
        """
        signed_state_instance.graph.unsent_count = 10

        assert signed_state_instance.get_con_signatures() == []
        assert signed_state_instance.graph.unsent_count == 10

    def test_sign_creating_many(self, signed_state_instance):
        """
        Test of creation of many (2) signatures
        """
        transaction = Transaction(signed_state_instance.graph.database)
        crypto = Crypto()

        signed_state_instance.graph.unsent_count = 10

        # Insert consensus
        signed_state_instance.graph.database.insert_consensus(set(range(10)))
        # Check the consensus was successfully inserted
        assert signed_state_instance.graph.database.get_consensus_count() == 10

        sign_list = signed_state_instance.get_con_signatures()
        # Check if precisely two signatures were created
        assert len(sign_list) == 2

        # Check last_created flag in db
        assert signed_state_instance.graph.database.get_consensus_last_created_sign() == 9

        """Check main data fields"""

        # From 0 to 5
        data = crypto.validate_sign_consensus( transaction.parse_transaction_hex(sign_list[0]))

        assert data['hash'] == from_0_to_4_hash
        assert data['start'] == 0

        # From 4 to 9
        data = crypto.validate_sign_consensus(transaction.parse_transaction_hex(sign_list[1]))

        assert data['hash'] == from_5_to_10_hash
        assert data['start'] == 5

    # Validation and insertion of signatures
    @pytest.mark.parametrize('get_remote_cg',
                             [([remote_from_0_to_4_sign_tx])],
                             indirect=True)
    def test_one_sign_insertation(self, signed_state_instance, get_remote_cg):
        """
        Test one valid remote sign insertion
        """
        remote_cg = get_remote_cg
        signed_state_instance.handle_new_sign(remote_cg)

        res = signed_state_instance.graph.database.get_signature_greater_than(-1)

        # Check if only one unchecked_pair was inserted
        assert 'unchecked_pair' in res
        assert len(res['unchecked_pair']) == 1

    @pytest.mark.parametrize('get_remote_cg',
                             [([remote_from_0_to_4_sign_tx, remote_from_0_to_4_sign_tx])],
                             indirect=True)
    def test_duplicated_sign_insertation(self, signed_state_instance, get_remote_cg):
        """
        Test duplicated remote signature insertion
        Only one remote sign should be inserted.
        """
        remote_cg = get_remote_cg
        signed_state_instance.handle_new_sign(remote_cg)

        res = signed_state_instance.graph.database.get_signature_greater_than(-1)

        # Check if only one unchecked_pair was inserted
        assert 'unchecked_pair' in res
        assert len(res['unchecked_pair']) == 1

    @pytest.mark.skip(reason="There is no possibility to test this(will be fixed in future update)")
    @pytest.mark.parametrize('get_remote_cg',
                             [([our_from_0_to_4_sign_tx])],
                             indirect=True)
    def test_our_sign_insertion(self, signed_state_instance, get_remote_cg):
        """
        Test our sign insertion.
        For case if someone will send our sign in transaction
        """
        remote_cg = get_remote_cg
        signed_state_instance.handle_new_sign(remote_cg)

        # Check if signature was NOT inserted
        assert signed_state_instance.graph.database.get_signature_greater_than(-1) == False

    @pytest.mark.parametrize('get_remote_cg',
                             [(["SOME INVALID TEXT"])],
                             indirect=True)
    def test_invalid_tx_insertion(self, signed_state_instance, get_remote_cg):
        remote_cg = get_remote_cg

        # Check if tx has NOT passed validation
        assert signed_state_instance.handle_new_sign(remote_cg) == False

        # Check if signature was NOT inserted
        assert signed_state_instance.graph.database.get_signature_greater_than(-1) == False

    # Handling signatures
    @pytest.mark.parametrize('get_remote_cg',
                             [([remote_from_0_to_4_sign_tx])],
                             indirect=True)
    def test_signing_first_5(self, signed_state_instance, get_remote_cg):
        """
        Test signing first 5 if consensus exists
        """
        remote_cg = get_remote_cg

        # Insert consensus into db
        signed_state_instance.graph.database.insert_consensus(set(range(5)))
        # Check if it was inserted successfully
        assert signed_state_instance.graph.database.get_consensus_count() == 5

        signed_state_instance.handle_new_sign(remote_cg)

        # Check if 5 consensuses were signed in db
        assert signed_state_instance.graph.database.get_consensus_last_signed() == 4

        # Check if last_signed var was changed
        assert signed_state_instance.graph.last_signed_state == 4

    @pytest.mark.parametrize('get_remote_cg',
                             [([remote_from_0_to_4_wrong_hash_tx])],
                             indirect=True)
    def test_signing_wrong_hash(self, signed_state_instance, get_remote_cg):
        """
        Test whether it was not signed by signature with wrong hash
        """
        remote_cg = get_remote_cg

        # Insert  consensus to db
        signed_state_instance.graph.database.insert_consensus(set(range(5)))
        # Check if it was inserted successfully
        assert signed_state_instance.graph.database.get_consensus_count() == 5

        signed_state_instance.handle_new_sign(remote_cg)

        # Check if 5 consensuses were NOT signed into db
        assert signed_state_instance.graph.database.get_consensus_last_signed() == -1

        signatures = signed_state_instance.graph.database.get_signature_greater_than(-1)

        # Check if only _id was created
        assert len(signatures) == 1

        # Check if id equal to start
        assert '_id' in signatures and signatures['_id'] == 0


    @pytest.mark.parametrize('get_remote_cg',
                             [([remote_from_0_to_4_sign_tx])],
                             indirect=True)
    def test_signing_first_10_con_after_sign(self, signed_state_instance, get_remote_cg):
        """
        Test signing first 10 if enough consensus was collected after sign was obtained.
        Legend: we get sign[0;4], then collect 10+ consensus, than get sign[5;9]
        """
        remote_cg = get_remote_cg

        # First sign [0;4]
        signed_state_instance.handle_new_sign(remote_cg)

        # Insert consensus to db
        signed_state_instance.graph.database.insert_consensus(set(range(10)))
        # Check if it was inserted successfully
        assert signed_state_instance.graph.database.get_consensus_count() == 10

        ev = collections.namedtuple('Event_', 'd')
        ev_tuple = ev([remote_from_5_to_9_sign_tx])
        remote_cg = {'somehash': ev_tuple}
        # Second run [5;9]
        signed_state_instance.handle_new_sign(remote_cg)

        # Check if 10 consensuses were signed in db
        assert signed_state_instance.graph.database.get_consensus_last_signed() == 9

        # Check if last_signed var was changed
        assert signed_state_instance.graph.last_signed_state == 9

    @pytest.mark.parametrize('get_remote_cg',
                             [([remote_from_5_to_9_sign_tx, remote_from_10_to_14_sign_tx])],
                             indirect=True)
    def test_multiple_consensus_after_signatures(self, signed_state_instance, get_remote_cg):
        """
        Test signing if we have got signatures with start 10 and 15,
        and only after that we have got sign with start 0.
        [0;14] should be signed.
        """
        remote_cg = get_remote_cg

        signed_state_instance.handle_new_sign(remote_cg)

        # Insert consensus to db
        signed_state_instance.graph.database.insert_consensus(set(range(15)))
        # Check if inserted successfully
        assert signed_state_instance.graph.database.get_consensus_count() == 15

        ev = collections.namedtuple('Event_', 'd')
        ev_tuple = ev([remote_from_0_to_4_sign_tx])
        remote_cg = {'somehash': ev_tuple}
        signed_state_instance.handle_new_sign(remote_cg)

        # Check if 15 consensuses were signed in db
        assert signed_state_instance.graph.database.get_consensus_last_signed() == 14

        # Check if last_signed var was changed
        assert signed_state_instance.graph.last_signed_state == 14