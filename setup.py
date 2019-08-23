#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name="AirNotifier",
    version="1.0",
    author="Dongsheng Cai",
    author_email="hi@dongsheng.org",
    url="http://airnotifier.github.io",
    packages=find_packages(),
    description="Generic iOS app backend",
    install_requires=["pymongo", "tornado"],
    include_package_data=True,
    license="BSD License",
)
