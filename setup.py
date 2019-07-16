# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='bot',
    version='0.1.0',
    description='Triangular arbitrage trading bot',
    long_description=readme,
    author='Luyo',
    author_email='luyotw@gmail.com',
    url='https://github.com/greenseedyo/triangular_arbitrage',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)

