FROM ubuntu:xenial

RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 0C49F3730359A14518585931BC711F9BA15703C6
RUN echo "deb [ arch=amd64,arm64 ] http://repo.mongodb.org/apt/ubuntu xenial/mongodb-org/3.4 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-3.4.list

RUN apt-get update

RUN apt-get install -y mongodb-org

RUN apt-get -y install python3-pip

RUN apt-get -y install git

WORKDIR /

RUN git clone https://github.com/prismaproject/prisma-core.git

WORKDIR /prisma-core

# Install Prisma dependencies
RUN pip3 install -e .

# Need to create this for mongoDB
WORKDIR /data/db

WORKDIR /prisma-core

EXPOSE 8000
EXPOSE 9154