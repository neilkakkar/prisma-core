# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

from autobahn.twisted.websocket import connectWS
from os.path import expanduser
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.contrib.completers import WordCompleter
from prompt_toolkit.styles import style_from_dict
from prompt_toolkit.shortcuts import print_tokens
from pygments.token import Token
from time import sleep
from getpass import getpass

from prisma.manager import Prisma
from prisma.client.protocol import ClientFactory


class Prompt:
    """
    Build the client and the prompt.
    """

    # this command list is printed in the help and used as a word completer
    command_list = [
        {'command': 'connected_clients',
         'help': 'Get all the connected clients'},
        {'command': 'create_wallet',
         'help': 'Creates a new wallet, will ask for a password to encrypt'},
        {'command': 'list_wallets',
         'help': 'Shows the address of every stored wallet'},
        {'command': 'decrypt_wallet',
         'help': '[ADDRESS] Shows all wallet information decrypted, will ask for password to decrypt.'},
        {'command': 'peer_list',
         'help': 'Get peer list'},
        {'command': 'last_event_time',
         'help': 'Get the last event timestamp'},
        {'command': 'get_address_balance',
         'help': '[ADDRESS] Get an address balance.'},
        {'command': 'create_transaction_and_send',
         'help': '[TO_ADDRESS AMOUNT] Creates a transaction and sends it.'},
        {'command': 'create_transaction',
         'help': '[TO_ADDRESS AMOUNT ?FROM_ADDRESS] creates a transaction and saves it in a buffer.'},
        {'command': 'clear_transactions',
         'help': 'Clears the transaction buffer.'},
        {'command': 'list_transactions',
         'help': 'List all transactions in the buffer.'},
        {'command': 'send_transactions',
         'help': 'Sends all the transactions from the transaction buffer and clears the buffer.'},
        {'command': 'help',
         'help': 'Show this help'},
        {'command': 'exit',
         'help': 'Exit prisma'}
    ]

    def __init__(self):
        # prepare websocket client
        self.info_peer_count = 0
        self.info_last_event_time = False
        self.info_my_balance = False
        self.info_my_address = False
        self.block = False
        self.client_factory = ClientFactory(url='ws://127.0.0.1:{}'.format(Prisma().api.port))
        self.client_factory.prompt = self
        self.client_connection = connectWS(self.client_factory)
        # prompt style
        self.print_style_green = style_from_dict({
            Token.Text: '#00cc00',
        })
        self.print_style_red = style_from_dict({
            Token.Text: '#cc0000',
        })
        self.prompt_style = style_from_dict({
            Token.Pound:    '#ffff00',
            Token.Toolbar:  '#00ee00 bg:#333333',
        })
        # prompt autocompletion
        words = []
        for command in self.command_list:
            words.append(command['command'])
        self.completer = WordCompleter(words, ignore_case=True, sentence=True)
        # prompt memory
        self.history = FileHistory(expanduser('~/.prisma/history.txt'))

    def stop(self):
        """
        Closes the client connection and stops the manager.
        """
        self.print('Exiting, please wait...')
        self.client_connection.transport.protocol.sendClose()
        sleep(0.1)  # this has to be replaced to a clean way to wait until sendClose() is finished.
        Prisma().stop()

    def run(self):
        """
        Build and run the prompt. This must be executed in a separate thread to avoid blocking the reactor.

        :return:
        """
        def get_prompt_tokens(c):
            return [(Token.Pound, '> ')]

        def get_bottom_toolbar_tokens(c):
            return [(Token.Toolbar, 'Address: {0} | Balance: {1} | Peers: {2} | Last event: {3}'.format(
                self.info_my_address,
                self.info_my_balance,
                self.info_peer_count,
                self.info_last_event_time
            ))]

        sleep(0.1)  # i think that is good to sleep a moment before showing prompt

        while True:
            try:
                # sometimes we block the prompt to until we wait to receive a response, this can be improved
                # to be asynchronous, but right now is not really an issue
                if self.block:
                    sleep(0.1)
                    continue
                # ask for prompt
                command = prompt(
                    get_prompt_tokens=get_prompt_tokens,
                    get_bottom_toolbar_tokens=get_bottom_toolbar_tokens,
                    refresh_interval=1,
                    style=self.prompt_style,
                    completer=self.completer,
                    history=self.history,
                    patch_stdout=True
                )
                cmd = [x.strip() for x in command.split(' ') if x.strip()]
                # do something with the input
                if len(cmd) == 0:
                    pass
                elif len(cmd) == 1 and cmd[0] == 'connected_clients':
                    self.client_connection.transport.protocol.block_and_send_json({
                        'req': 'connected_clients'
                    })
                elif len(cmd) == 1 and cmd[0] == 'create_wallet':
                    password = getpass(prompt='New password: ')
                    password_verification = getpass(prompt='Verify password: ')
                    if password != password_verification:
                        raise Exception('Passwords do not match.')
                    self.client_connection.transport.protocol.block_and_send_json({
                        'req': 'create_wallet',
                        'password': password
                    })
                elif cmd[0] == 'decrypt_wallet':
                    if len(cmd) != 2:
                        raise Exception('Please specify an address.')
                    password = getpass(prompt='Password: ')
                    self.client_connection.transport.protocol.block_and_send_json({
                        'req': 'decrypt_wallet',
                        'address': cmd[1],
                        'password': password
                    })
                elif len(cmd) == 1 and cmd[0] == 'list_wallets':
                    self.client_connection.transport.protocol.block_and_send_json({
                        'req': 'list_wallets'
                    })
                elif len(cmd) == 1 and cmd[0] == 'peer_list':
                    self.client_connection.transport.protocol.block_and_send_json({
                        'req': 'peer_list'
                    })
                elif len(cmd) == 1 and cmd[0] == 'last_event_time':
                    self.client_connection.transport.protocol.block_and_send_json({
                        'req': 'last_event_time'
                    })
                elif cmd[0] == 'get_address_balance':
                    if len(cmd) != 2:
                        raise Exception('Please specify an address.')
                    self.client_connection.transport.protocol.block_and_send_json({
                        'req': 'get_address_balance',
                        'address': cmd[1]
                    })
                elif cmd[0] == 'create_transaction_and_send':
                    if len(cmd) != 3:
                        raise Exception('Please specify an address and a quantity.')
                    self.client_connection.transport.protocol.block_and_send_json({
                        'req': 'create_transaction_and_send',
                        'to_address': cmd[1],
                        'amount': int(cmd[2])
                    })
                elif cmd[0] == 'create_transaction':
                    if len(cmd) != 3 and len(cmd) != 4:
                        raise Exception('Please specify an address and a quantity.')
                    req = {
                        'req': 'create_transaction',
                        'to_address': cmd[1],
                        'amount': int(cmd[2])
                    }
                    if len(cmd) == 4:
                        password = getpass(prompt='Password: ')
                        req['from_address'] = cmd[3]
                        req['password'] = password
                    self.client_connection.transport.protocol.block_and_send_json(req)
                elif len(cmd) == 1 and cmd[0] == 'clear_transactions':
                    self.client_connection.transport.protocol.block_and_send_json({
                        'req': 'clear_transactions'
                    })
                elif len(cmd) == 1 and cmd[0] == 'list_transactions':
                    self.client_connection.transport.protocol.block_and_send_json({
                        'req': 'list_transactions'
                    })
                elif len(cmd) == 1 and cmd[0] == 'send_transactions':
                    self.client_connection.transport.protocol.block_and_send_json({
                        'req': 'send_transactions'
                    })
                elif len(cmd) == 1 and cmd[0] == 'help':
                    for command in self.command_list:
                        self.print(command['command'].ljust(30) + command['help'])
                elif len(cmd) == 1 and cmd[0] == 'exit':
                    self.stop()
                    break
                else:
                    self.print('Error: command \'{}\' not found.'.format(cmd))
            except EOFError:
                self.stop()
                break
            except KeyboardInterrupt:
                self.stop()
                break
            except Exception as e:
                self.print('Error: ' + str(e), True)

    def print(self, text, error=False):
        """
        Prints text with fashion.

        :param text: text to print
        :param error: if error is true then will print it in red
        """
        text = text + '\n'
        if error:
            print_style = self.print_style_red
        else:
            print_style = self.print_style_green
        print_tokens([(Token.Text, text)], style=print_style)
