#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2012, Dongsheng Cai
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the Dongsheng Cai nor the names of its
#      contributors may be used to endorse or promote products derived
#      from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL DONGSHENG CAI BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from hashlib import sha1

from pymongo.connection import Connection
from pymongo.errors import CollectionInvalid
from tornado.options import define, options
import tornado.options

from constants import VERSION


define("apns", default=(), help="APNs address and port")
define("pemdir", default="pemdir", help="Directory to store pems")
define("passwordsalt", default="d2o0n1g2s0h3e1n1g", help="Being used to make password hash")

define("mongohost", default="localhost", help="MongoDB host name")
define("mongoport", default=27017, help="MongoDB port")
define("mongodbname", default="airnotifier", help="MongoDB database name")
define("masterdb", default="airnotifier", help="MongoDB DB to store information")


if __name__ == "__main__":
    tornado.options.parse_config_file("airnotifier.conf")
    tornado.options.parse_command_line()
    mongodb = Connection(options.mongohost, options.mongoport)
    masterdb = mongodb[options.masterdb]
    collection_names = masterdb.collection_names()
    try:
        if not 'applications' in collection_names:
            masterdb.create_collection('applications')
            print("db.applications installed")
    except CollectionInvalid as ex:
        print("Failed to created applications collection", ex)
        pass

    try:
        if not 'managers' in collection_names:
            masterdb.create_collection('managers')
            masterdb.managers.ensure_index("username", unique=True)
            print("db.managers installed")
    except CollectionInvalid:
        print("Failed to created managers collection")
        pass

    try:
        manager = {}
        manager['username'] = 'admin'
        manager['password'] = sha1('%sadmin' % options.passwordsalt).hexdigest()
        masterdb['managers'].insert(manager)
        print("Admin user created, username: admin, password: admin")
    except Exception:
        print("Failed to create admin user")

    try:
        if not 'options' in collection_names:
            masterdb.create_collection('options')
            print("db.options installed")
    except CollectionInvalid:
        print("db.options installed")

    try:
        option_ver = {}
        option_ver['name'] = 'version'
        option_ver['value'] = VERSION
        masterdb['options'].insert(option_ver)
        print("Version number written: %s" % VERSION)
    except Exception:
        print("Failed to write version number")
