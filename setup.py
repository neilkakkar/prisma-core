from setuptools import setup, find_packages
from prisma import __version__

setup(
    name='prisma',
    packages=find_packages(),
    version=__version__,
    install_requires=[
        'autobahn==17.6.2',
        'configparser==3.5.0',
        'prompt_toolkit==1.0.14',
        'pygments==2.2.0',
        'pymongo==3.4.0',
        'pynacl==1.1.2',
        'twisted==17.1.0',
    ],
    classifiers=[
        "Programming Language :: Python :: 3.5"
    ],
    entry_points={
        'console_scripts': [
            'prismad=prisma.prismad:main'
        ],
    },
    scripts=[
        'bin/prisma_dev.py'
    ],
    package_data={
        'prisma': [
            'prisma-default.ini',
            'prisma-testnet.ini'
        ],
        'prisma.cryptograph': [
            'genesis.json',
            'genesis-testnet.json'
        ]
    },
    data_files=[
        ('/etc/init.d', ['etc/prismad']),
        ('/etc/prisma', [
            'prisma/prisma-default.ini',
            'prisma/prisma-testnet.ini'
        ])
    ]
)
