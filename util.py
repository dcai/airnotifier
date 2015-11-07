#!/usr/bin/python
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

try:
    from HTMLParser import HTMLParser
except:
    from html.parser import HTMLParser

import calendar
import datetime
try:
    from htmlentitydefs import name2codepoint
except:
    from html.entities import name2codepoint
import re
import sys
import unicodedata
import os
from tornado.options import options
from hashlib import sha1

from bson.dbref import DBRef
from bson.max_key import MaxKey
from bson.min_key import MinKey
from bson.objectid import ObjectId
from bson.son import RE_TYPE
from bson.timestamp import Timestamp

try:
    import uuid
    _use_uuid = True
except ImportError:
    _use_uuid = False

class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.result = [ ]

    def handle_data(self, d):
        self.result.append(d)

    def handle_charref(self, number):
        codepoint = int(number[1:], 16) if number[0] in (u'x', u'X') else int(number)
        self.result.append(unichr(codepoint))

    def handle_entityref(self, name):
        codepoint = name2codepoint[name]
        self.result.append(unichr(codepoint))

    def get_text(self):
        return u''.join(self.result)

def strip_tags(html):
    s = HTMLTextExtractor()
    s.feed(html)
    return s.get_text()

def json_default(obj):
    """ adapted from bson.json_util.default """
    if isinstance(obj, ObjectId):
        """ _id field should be just string """
        return str(obj)
    if isinstance(obj, DBRef):
        return obj.as_doc()
    if isinstance(obj, datetime.datetime):
        # TODO share this code w/ bson.py?
        if obj.utcoffset() is not None:
            obj = obj - obj.utcoffset()
        millis = int(calendar.timegm(obj.timetuple()) * 1000 +
                     obj.microsecond / 1000)
        return {"$date": millis}
    if isinstance(obj, RE_TYPE):
        flags = ""
        if obj.flags & re.IGNORECASE:
            flags += "i"
        if obj.flags & re.MULTILINE:
            flags += "m"
        return {"$regex": obj.pattern,
                "$options": flags}
    if isinstance(obj, MinKey):
        return {"$minKey": 1}
    if isinstance(obj, MaxKey):
        return {"$maxKey": 1}
    if isinstance(obj, Timestamp):
        return {"t": obj.time, "i": obj.inc}
    if _use_uuid and isinstance(obj, uuid.UUID):
        return {"$uuid": obj.hex}
    raise TypeError("%r is not JSON serializable" % obj)

def filter_alphabetanum(string):
    # absolutely alphabeta and number only
    string = unicodedata.normalize("NFKD", string).encode("ascii", "ignore")
    string = re.sub(r"[^\w]+", " ", string)
    string = "".join(string.lower().strip().split())
    return string

def error_log(log):
    sys.stderr.write(log)

def get_filepath(filename):
    return os.path.join(os.path.abspath(options.pemdir), filename)

def save_file(req):
    filename = sha1(req['body']).hexdigest()
    filepath = get_filepath(filename)
    thefile = open(filepath, "w")
    thefile.write(req['body'])
    thefile.close()
    return filename

def file_exists(filename):
    if not filename:
        return False
    if os.path.exists(filename):
        return True
    fullpath = get_filepath(filename)
    if fullpath and os.path.exists(fullpath):
        return True
    return False

def rm_file(filename):
    if not filename:
        return
    fullpath = get_filepath(filename)
    if os.path.isfile(filename):
        os.remove(filename)
    elif os.path.isfile(fullpath):
        os.remove(fullpath)
