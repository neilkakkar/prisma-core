# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging
import json
from autobahn.twisted.websocket import WebSocketClientProtocol, WebSocketClientFactory


class ClientProtocol(WebSocketClientProtocol):
    """
    This is the client protocol that can be used by a prompt, a web based interface or a gui to connect
    to the websocket API server.
    """
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger('Client')

    def onOpen(self):
        """
        Announce that we are connected.
        """
        self.logger.debug('Connected to {0}'.format(self.peer))

    def onMessage(self, payload, isBinary):
        """
        Print anything that comes to prompt.

        :param payload:
        :param isBinary:
        """
        if not isBinary:
            message = json.loads(payload.decode('utf-8'))
            if self.factory.prompt is not None:
                if 'push' in message and message['push'] == 'info':
                    self.factory.prompt.info_peer_count = message['peer_count']
                    self.factory.prompt.info_last_event_time = message['latest_event_time']
                    self.factory.prompt.info_my_balance = message['my_balance']
                    self.factory.prompt.info_my_address = message['my_address']
                else:
                    if message['ok']:
                        if len(message) != 1:
                            del message['ok']
                        for k in message:
                            self.factory.prompt.print(k + ': ' + str(message[k]))
                    else:
                        self.factory.prompt.print('Error: ' + message['error'], True)
                # release prompt block
                self.factory.prompt.block = False

    def onClose(self, wasClean, code, reason):
        """
        When closing the connection, no mather the reason stop the reactor. This is usually called after
        closing the connection from the client. In other circumstances it shouldn't close?

        :param wasClean:
        :param code:
        :param reason:
        """
        self.logger.debug('Connection closed: ' + str(reason))

    def send_json(self, obj):
        """
        Converts an object to json encoded in utf-8 and sends it

        :param obj: the object to send
        """
        message = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.sendMessage(message)

    def block_and_send_json(self, obj):
        """
        This blocks the prompt before sending message. Prompt will be unblocked
        when message is received.

        :param obj:
        """
        self.factory.prompt.block = True
        self.send_json(obj)


class ClientFactory(WebSocketClientFactory):
    """
    Basically, a normal client factory for ApiClientProtocol.
    """
    protocol = ClientProtocol

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt = None
