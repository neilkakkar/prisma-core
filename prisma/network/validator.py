# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""

import logging
import ipaddress
from prisma.config import CONFIG


class Validator(object):
    """
    Validator
    """
    def __init__(self):
        self.logger = logging.getLogger('Validator')

    def validate_method(self, data_payload):
        if 'method' not in data_payload or data_payload['method'] not in self.valid_peers_methods():
            return False
        return True

    @staticmethod
    def valid_peers_methods():
        return [
            'get_state',
            'get_state_response',
            'get_peers',
            'get_peers_response',
            'get_events',
            'get_events_response'
        ]

    @staticmethod
    def is_valid_node_ip(ip):
        """
        Validate node ip address.

        :param ip: An IPv4 address.
        :type ip: string
        :rtype: False: Is either a non valid IPv4 address or is an RFC1918-address.
        :rtype: string (IP address)
        """
        try:
            address = ipaddress.IPv4Address(ip)
        except ValueError:
            return False
        if address.is_private:
            if CONFIG.get('developer', 'developer_mode') is False:
                return False
        return ip
