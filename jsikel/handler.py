from jsikel.constants import *
from jsikel.exceptions import *

class ReportHandler(object):
    def response(self, msg):
        print msg

    def error(self, msg):
        print msg
