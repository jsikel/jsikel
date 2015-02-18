from blikur.constants import *
from blikur.exceptions import *

class ReportHandler(object):
    def response(self, msg):
        print msg

    def error(self, msg):
        print msg
