# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

from collator import __version__

setup(name='collator',
      version=__version__,
      packages=find_packages(),
      install_requires=[
          'docopt==0.6.1',
      ],
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.6',
          'Topic :: Text Processing :: Markup :: XML',
      ],
      description='Script for collating two or more transcription files using CollateX.',
      url='https://github.com/stenskjaer/collator',
      author='Michael Stenskjær Christensen',
      author_email='michael.stenskjaer@gmail.com',
      license='MIT',
      scripts=['collator.py'],
)
