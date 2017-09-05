# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging
import json
from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol

from prisma.api.methods import ApiMethods


class ApiProtocol(WebSocketServerProtocol):
    """
    API that uses a Json interface using POST.
    Talks to classes and methods within prisma.
    """
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger('Api')

    def onConnect(self, request):
        """
        In this callback you can do things like:

        * checking or setting cookies or other HTTP headers
        * verifying the client IP address
        * checking the origin of the WebSocket request
        * negotiate WebSocket subprotocols

        :param request:
        """
        self.logger.debug('Receiving connection from {0}'.format(request.peer))

    def onOpen(self):
        """
        Opening handshake is completed. Register the client.
        """
        self.factory.register(self)
        self.logger.debug('Connected to {0}'.format(self.peer))

    def onMessage(self, payload, isBinary):
        """
        When receiving a message, unload the payload and call the corresponding function.

        :param payload:
        :param isBinary:
        :return:
        """
        if not isBinary:
            response = {'ok': True}
            try:
                message = json.loads(payload.decode('utf-8'))
                request = message.get('req')
                if request is None:
                    raise Exception('please, specify a request')
                elif request == 'connected_clients':
                    response.update(self.get_connected_clients_list())
                else:
                    # calls the function in the request, with all the msg as parameters
                    del message['req']
                    result = getattr(ApiMethods, request)(**message)
                    # merges the response with the final result
                    response.update(result)
            except Exception as e:
                response['ok'] = False
                response['error'] = str(e)

            # send the response
            self.send_json(response)

    def send_json(self, payload):
        """
        Dumps a dictionary/list object into a json and sends it.

        :param payload: a dictionary/list object to transform to json and send.
        :return:
        """
        message = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.sendMessage(message, isBinary=False)
        self.logger.debug('Response sent: {}'.format(message))

    def onClose(self, wasClean, code, reason):
        """
        The connection has been completely closed.

        :param wasClean:
        :param code:
        :param reason:
        """
        self.factory.unregister(self)
        self.logger.debug('Connection closed: {}'.format(reason))

    def get_connected_clients_list(self):
        """
        Get a list of the connected clients.

        :return: a list of strings
        """
        clients_r = {}
        for c in self.factory.clients:
            clients_r[c] = True
        return clients_r


class ApiFactory(WebSocketServerFactory):
    """
    The server, that will invoke a protocol on every new connection.
    """
    protocol = ApiProtocol

    def __init__(self):
        super(ApiFactory, self).__init__()
        self.logger = logging.getLogger('Api')
        self.clients = {}

    def register(self, client):
        """
        Add client to list of managed connections.

        :param client:
        """
        self.clients[client.peer] = client

    def unregister(self, client):
        """
        Remove client from list of managed connections.

        :param client:
        """
        self.clients.pop(client.peer)
