#!/usr/bin/env bash

### Run first
# adduser jb
# apt-get update && apt-get install sudo
# adduser jb sudo
# dpkg-reconfigure locales (choose en_US-UTF-8)
# login as your new user and run the following.

sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 0C49F3730359A14518585931BC711F9BA15703C6
echo "deb http://repo.mongodb.org/apt/debian jessie/mongodb-org/3.4 main" | sudo tee /etc/apt/sources.list.d/mongodb-org-3.4.list
sudo apt-get update && sudo apt-get -y install python3-dev python3-pip mongodb-org git
git clone https://gitlab.com/hashgraph/prisma.git && cd prisma && sudo pip3 install -e .

echo "Done installing prisma."
exit 0
