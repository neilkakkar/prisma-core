# -*- coding: utf-8 -*-
"""
Copyright 2017 Prisma crypto currency and its Authors.
This file is part of prisma crypto currency.
Licensed under the GNU Lesser General Public License, version 3 or later. See LICENSING for details.
"""
import os
import sys
from configparser import ConfigParser

CONFIG_FILE = 'prisma.ini'
CONFIG_FILE_DEFAULT = 'prisma-default.ini'


def create_config():
    """
    Parse config file with configparser
    https://docs.python.org/3/library/configparser.html
    """
    location_list = [
        os.path.join('/etc/prisma', CONFIG_FILE),
        os.path.join('/etc/prisma', CONFIG_FILE_DEFAULT),
        os.path.join(os.path.dirname(os.path.realpath(__file__)), CONFIG_FILE),
        os.path.join(os.path.dirname(os.path.realpath(__file__)), CONFIG_FILE_DEFAULT)
    ]
    parser = ConfigParser()
    for location in location_list:
        read = parser.read(location)
        if read:
            return parser
    print('Error: configuration file not found. Exiting...')
    sys.exit(0)

# Create config variable accessible with "prisma.config import CONFIG"
CONFIG = create_config()
