from blckur.constants import *
from blckur.exceptions import *

import json

class ReportFormatter(object):
    def json_default(self, obj):
        if hasattr(obj, '__name__'):
            return '%s()' % obj.__name__
        raise TypeError(repr(obj) + ' is not JSON serializable')

    def response(self, test_case):
        return '%s %s%s %s %sms' % (
            test_case.method,
            test_case.suite.base_url,
            test_case.path,
            test_case.response_status,
            test_case.response_time,
        )

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
            'response_time: %sms\n' % test_case.response_time + \
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
            'input_json: %s\n' % json.dumps(
                test_case.input_json,
                default=self.json_default,
                indent=JSON_INDENT,
            ) + \
            'input_data: %s\n' % json.dumps(
                test_case.input_data,
                default=self.json_default,
                indent=JSON_INDENT,
            ) + \
            'input_params: %s\n' % json.dumps(
                test_case.input_params,
                default=self.json_default,
                indent=JSON_INDENT,
            ) + \
            'expect_json: %s\n' % json.dumps(
                test_case.expect_json,
                default=self.json_default,
                indent=JSON_INDENT,
            ) + \
            'response_data: %s\n' % json.dumps(
                test_case.response_data,
                default=self.json_default,
                indent=JSON_INDENT,
            ) + \
            '***************************************************'
