#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""
import logging
import argparse
import signal
from twisted.python import log
from twisted.internet import reactor

from prisma.manager import Prisma, __version__
from prisma.config import CONFIG
from prisma.crypto.wallet import Wallet


def main():
    """
    Entry point
    """
    parser = argparse.ArgumentParser('Run a cryptograph manager.')
    parser.add_argument('--create', action='store_true', help='create a new wallet address')
    parser.add_argument('--list', action='store_true', help='list all wallet addresses')
    parser.add_argument('--wallet', help='wallet address')
    parser.add_argument('--listenport', help='what port the manager should bind to')
    parser.add_argument('--apiport', help='what port for the API should bind to')
    parser.add_argument('--database', help='mongodb database name')
    parser.add_argument('--prompt', '-p', action='store_true', help='show prompt')
    parser.add_argument('--log', '-l', help='log into a file')
    parser.add_argument('--version', action='store_true', help='print version')
    parser.add_argument('-v', action='store_true', help='verbose')
    parser.add_argument('-vv', action='store_true', help='very verbose')
    args = parser.parse_args()

    if args.version:
        print('Prisma v{0}'.format(__version__))
        exit(0)

    wallet = Wallet()

    # create a new wallet if --create
    if args.create:
        try:
            keys = wallet.create_wallet()
            print('Wallet created with address: ' + keys['address'])
        except Exception as e:
            print(str(e))
        exit()

    # list wallet list if --list
    if args.list:
        print(wallet.list_wallets())
        exit()

    # set logger options
    if args.vv:
        logging.basicConfig(
            format='[%(asctime)s] [%(levelname)-8s] [%(name)-10s] %(message)s [%(filename)s:%(lineno)d]',
            level=logging.DEBUG,
            filename=args.log
        )
    elif args.v:
        logging.basicConfig(
            format='[%(levelname)s] [%(name)s] %(message)s',
            level=logging.INFO,
            filename=args.log
        )

    observer = log.PythonLoggingObserver()
    observer.start()

    if args.listenport:
        CONFIG.set('network', 'listen_port', args.listenport)

    if args.apiport:
        CONFIG.set('api', 'listen_port', args.apiport)

    if args.wallet:
        CONFIG.set('general', 'wallet_address', args.wallet)

    if args.database:
        CONFIG.set('general', 'database', args.database)

    # preparing manager
    def signal_handler(sig, frame):
        Prisma().stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGQUIT, signal_handler)

    # starting manager
    Prisma().start(args.prompt)
    reactor.run()

# if this module is called directly then go to the entry point
if __name__ == "__main__":
    main()
