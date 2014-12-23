from blckur.constants import *
from blckur.exceptions import *

class ReportHandler(object):
    def response(self, msg):
        print msg

    def error(self, msg):
        print msg
