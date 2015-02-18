from blikur.constants import *
from blikur.exceptions import *

class ReportFilter(object):
    def response(self, test_case):
        return True

    def error(self, test_case):
        return True
