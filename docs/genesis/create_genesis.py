import collections
from prisma.crypto.crypto import Crypto
from json import dumps, dump, load

balances_file = 'docs/genesis/balances.json'
output_file = 'prisma/cryptograph/genesis.json'

def create_genesis(balances):
    balance = collections.OrderedDict(sorted(balances.items()))

    state = {'balance': balance}
    state_hash = Crypto().blake_hash(bytes(dumps(state).encode('utf-8')))

    genesis = {
        'state': state,
        'round': -1,
        'hash': state_hash,
        'signed': True
    }

    print(genesis)
    return genesis

def read_JSON_from_file(path):
    try:
        with open(path) as genesis_file:
            res = load(genesis_file)
        return res
    except Exception as e:
        print('Could not read from file, path:', path, e)
    return False


def write_JSON_to_file(path, data):
    try:
        with open(path, "w") as storage:
            dump(data, storage)
            print('Successfully wrote genesis event.')
    except Exception as e:
        print('Could not write genesis event . Reason: ', e)
    return False

if __name__ == "__main__":
    # Genesis tx in format {address: amount}
    balances = read_JSON_from_file(balances_file)

    if balances:
        genesis = create_genesis(balances)
        write_JSON_to_file(output_file, genesis)
    else:
        print("Could not create genesis event !")
