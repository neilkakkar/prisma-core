# README #

Prisma crypto currency. Based on a hashgraph instead of a blockchain.

# White paper
[White Paper](https://github.com/prismaproject/prisma-core/wiki/Prisma-cryptocurrency-White-Paper)

# API documentation
[API Documentation](https://github.com/prismaproject/prisma-core/wiki/Prisma-cryptocurrency-White-Paper)

# About development

* [Follow PEP8](http://legacy.python.org/dev/pep/pep-0008/): code standards are important for readability and project
homogeneity. Always use PEP8 lower_case_functions except when using Twisted framework.

# Installation

First install mongodb version 3.4: https://docs.mongodb.com/manual/tutorial/install-mongodb-on-debian/

Run the following command (this will create a symbolic link so development can be continued in this folder):

```
$ sudo pip3 install -e .
```

# Usage

```
$ prismad
```

# Run as a service

This was tested on Debian and working.

```
sudo pip3 install .
sudp update-rc.d prismad defaults
sudo prismad --create
sudo service prismad start|stop|restart
tail -f /var/logs/prismad.log
```

Check configuration file in `/etc/prisma/prisma-default.ini`.

# Run testing

Because of the twisted nature of the project, tests run using trial. From the current directory just run:

```
trial prisma
```

For more info: https://twistedmatrix.com/documents/current/core/howto/trial.html

# Howto generate the documentation

You will need a separate directory with the checkout of the branch `gh-pages` called `prisma-gh-pages`.

```
sphinx-apidoc -f -o docs/ prisma/
sphinx-build -E -b html ../prisma-gh-pages/ docs/
```
