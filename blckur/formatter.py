from blckur.constants import *
from blckur.exceptions import *

import json

class ReportFormatter(object):
    def json_default(self, obj):
        if hasattr(obj, '__name__'):
            return '%s()' % obj.__name__
        raise TypeError(repr(obj) + ' is not JSON serializable')

    def error(self, test_case, error_msg):
        return '***************************************************\n' + \
            '%s\n' % error_msg + \
            'name: %r\n' % test_case.__class__.__name__ + \
            'method: %r\n' % test_case.method + \
            'path: %r\n' % test_case.path + \
            'expect_status: %s\n' % json.dumps(
                test_case.expect_status,
                default=self.json_default,
                indent=JSON_INDENT,
            ) + \
            'response_status: %s\n' % test_case.response_status + \
            'expect_headers: %s\n' % json.dumps(
                test_case.expect_headers,
                default=self.json_default,
                indent=JSON_INDENT,
            ) + \
            'response_headers: %s\n' % json.dumps(
                dict(test_case.response_headers.items()),
                default=self.json_default,
                indent=JSON_INDENT,
            ) + \
            'input_data: %s\n' % json.dumps(
                test_case.input_data,
                default=self.json_default,
                indent=JSON_INDENT,
            ) + \
            'expect_data: %s\n' % json.dumps(
                test_case.expect_data,
                default=self.json_default,
                indent=JSON_INDENT,
            ) + \
            'response_data: %s\n' % json.dumps(
                test_case.response_data,
                default=self.json_default,
                indent=JSON_INDENT,
            ) + \
            '***************************************************'
