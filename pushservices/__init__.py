import os.path
import logging
from tornado.options import options

class PushService(object):
    def find_file(self, filename):
        fullpath = options.pemdir + filename
        if os.path.isfile(filename):
            return filename
        elif os.path.isfile(fullpath):
            return fullpath
