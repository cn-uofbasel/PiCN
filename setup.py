#/usr/bin/env python3.6

import unittest
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config_PiCN = {
    'description': 'extendable ICN implementation in python',
    'author': 'Christopher Scherb',
    'url': 'https://github.com/cn-uofbasel/PiCN',
    'download_url': 'https://github.com/cn-uofbasel/PiCN/archive/master.zip',
    'author_email': 'christopher.scherb@unibas.ch',
    'version': '0.1.0',
    'license': 'BSD 3-clause',
    'platforms': ['UNIX', 'POSIX', 'BSD', 'MacOS 10.X', 'Linux'],
    'description': 'Python ICN',
    'long_description': 'A modular Python ICN implementation',
    'install_requires': [],
    'packages': ['PiCN', 'PiCN.Processes', 'PiCN.Layers.LinkLayer', 'PiCN.Layers.PacketEncodingLayer',
                 'PiCN.Layers.PacketEncodingLayer.Encoder', 'PiCN.Routing', 'PiCN.ProgramLibs.Fetch',
                 'PiCN.Layers.ICNLayer', 'PiCN.Layers.ICNLayer.ContentStore',
                 'PiCN.Layers.ICNLayer.ForwardingInformationBase', 'PiCN.Layers.ICNLayer.PendingInterestTable',
                 'PiCN.Packets', "PiCN.Mgmt", 'PiCN.ProgramLibs.ICNForwarder',
                 'PiCN.Executable', 'PiCN.Logger', 'PiCN.Layers.ChunkLayer', 'PiCN.Layers.ChunkLayer.Chunkifyer',
                 'PiCN.Layers.RepositoryLayer', 'PiCN.Layers.RepositoryLayer.Repository',
                 'PiCN.ProgramLibs.ICNDataRepository', 'PiCN.Layers.NFNLayer', 'PiCN.Layers.NFNLayer.Parser',
                 'PiCN.Layers.NFNLayer.NFNEvaluator', 'PiCN.Layers.NFNLayer.NFNEvaluator.NFNOptimizer',
                 'PiCN.Layers.NFNLayer.NFNEvaluator.NFNExecutor', 'PiCN.ProgramLibs.NFNForwarder'],
    'scripts': [],
    'test_suite': 'nose2.collector.collector',
    'tests_require': ['nose2', 'rednose', 'nose-progressive'],
    'name': 'PiCN'
}
classifiers_PiCN=[
    'Programming Language :: Python',
    'Environment :: Console',
    'Network Application :: ICN :: NFN'
]
setup(**config_PiCN, classifiers=classifiers_PiCN)


config_PyNDN = {
    'description': 'PyNDN',
    'author': 'UCLA, Jeff Thompson',
    'url': 'https://github.com/cn-uofbasel/PiCN',
    'download_url': '',
    'author_email': 'jefft0@remap.ucla.edu',
    'version': '2',
    'license': 'GNU LESSER GENERAL PUBLIC LICENSE, Version 3, 29 June 2007',
    'platforms': ['UNIX', 'POSIX', 'BSD', 'MacOS 10.X', 'Linux'],
    'description': 'PyNDN Packet encoder',
    'long_description': 'PyNDN Packet encoder for the NDN packet format',
    'install_requires': [],
    'packages': ['PiCNExternal.pyndn'],
    'scripts': [],
    'name': 'pyndn'
}
setup(**config_PyNDN)
