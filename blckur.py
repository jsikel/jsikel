import requests
import json
import time
import re
import collections
import copy
import uuid
import sys
import types

STR_EXP = re.compile('\{\$([^}]+)\}')
JSON_INDENT = 2


class TestException(Exception):
    pass

class TestStatusFailed(TestException):
    pass

class TestExpectFailed(TestException):
    pass


class TestCaseReportFilter(object):
    def error(self, test_case):
        return True

class TestCaseReportFormatter(object):
    def error(self, test_case, error_msg):
        return '***************************************************\n' + \
            '%s\n' % error_msg + \
            'name: %r\n' % test_case.__class__.__name__ + \
            'method: %r\n' % test_case.method + \
            'path: %r\n' % test_case.path + \
            'expect_status: %s\n' % json.dumps(test_case.expect_status,
                indent=JSON_INDENT) + \
            'response_status: %s\n' % test_case.response_status + \
            'expect_headers: %s\n' % json.dumps(test_case.expect_headers,
                indent=JSON_INDENT) + \
            'response_headers: %s\n' % json.dumps(
                dict(test_case.response_headers.items()),
                indent=JSON_INDENT,
            ) + \
            'input_data: %s\n' % json.dumps(test_case.input_data,
                indent=JSON_INDENT) + \
            'expect_data: %s\n' % json.dumps(test_case.expect_data,
                indent=JSON_INDENT) + \
            'response_data: %s\n' % json.dumps(test_case.response_data,
                indent=JSON_INDENT) + \
            '***************************************************'

class TestCaseReportHandler(object):
    def error(self, error):
        print error

class Base(object):
    base_url = None
    filter = TestCaseReportFilter()
    formatter = TestCaseReportFormatter()
    handler = TestCaseReportHandler()

    def __init__(self):
        self.objects = {}
        self.requests = requests.request

    @property
    def TestCase(self):
        return type('TestCase', (TestCase,), {
            'base': self,
        })

    def main(self):
        module = __import__('__main__')

        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and issubclass(obj, TestCase) and \
                    obj.base == self and obj not in self.objects:
                obj()

    def handle_request(self, method, url, **kwargs):
        if self.request_kwargs:
            kwargs.update(self.request_kwargs)

        return self.request(method, url, **kwargs)

    def request(self, method, url, headers=None, json=None, **kwargs):
        return self.requests.request(
            method,
            url,
            headers=headers,
            json=json,
            **kwargs
        )

class SessionBase(Base):
    def __init__(self):
        Base.__init__(self)
        self.requests = requests.Session()
        self.requests.request(
            self.method,
            self.base_url + self.path,
            json=self.input_data,
        )

class TestCase(object):
    require = None
    required = True
    method = 'GET'
    path = '/'
    expect_status = None
    expect_headers = None
    input_data = None
    expect_data = None

    def __init__(self):
        self._error_marked = False

        if self.__class__ in self.base.objects:
            raise ValueError('Test case %r already run' % self.__class__)

        if self.require:
            if not isinstance(self.require, (list, tuple)):
                self.require = (self.require,)

            requires = []
            for require in self.require:
                require_obj = self.base.objects.get(require)
                if not require_obj:
                    require_obj = require()
                requires.append(require_obj)
            self.require = requires

        self.run()

    def parse_exp_set(self, exp_set, data):
        while exp_set:
            exp = exp_set.popleft()

            if exp == '$':
                new_data = []
                if exp_set:
                    for item in data:
                        new_data.append(self.arse_exp_set(
                            copy.copy(exp_set),
                            item,
                        ))
                return new_data
            elif exp.isdigit():
                data = data[int(exp)]
            else:
                data = data[exp]

        return data

    def parse_exp(self, exp):
        exp_set = collections.deque(exp.split('.'))
        exp_type = exp_set.popleft()

        if exp_type.startswith('require'):
            index = int(exp_set.popleft())

            if exp_type == 'require':
                data = self.require[index].response_data
            elif exp_type == 'require_input':
                data = self.require[index].input_data
            elif exp_type == 'require_expect':
                data = self.require[index].expect_data
            else:
                raise TypeError('TODO %r' % exp)
        elif exp_type == 'input':
            data = self.input_data
        elif exp_type == 'time':
            return str(int(time.time()))
        elif exp_type == 'time_float':
            return str(time.time())
        elif exp_type == 'uuid':
            return uuid.uuid4().hex
        else:
            raise TypeError('TODO %r' % exp)

        return str(self.parse_exp_set(exp_set, data))

    def parse_str(self, parse_str):
        return STR_EXP.sub(
            lambda x: self.parse_exp(x.group(1)),
            parse_str,
        )

    def parse_input(self, data):
        if not data:
            pass
        elif isinstance(data, dict):
            for key, val in data.iteritems():
                data[self.parse_str(key)] = self.parse_input(val)
        elif isinstance(data, (list, tuple)):
            new_data = []
            for item in data:
                new_data.append(self.parse_input(item))
            return new_data
        else:
            data = self.parse_str(data)

        return data

    def parse_value(self, value):
        if isinstance(value, basestring) and value.startswith('$'):
            return self.parse_exp(value[1:])
        return value

    def iter_parse_values(self, values):
        for i, value in enumerate(values):
            value = self.parse_value(value)
            values[i] = value
            yield value

    def check_match(self, in_values, out_value):
        matched = False
        out_value_is_list = isinstance(out_value, list)

        for in_value in self.iter_parse_values(in_values):
            if matched:
                continue
            elif out_value_is_list:
                if in_value in out_value:
                    matched = True
            else:
                if in_value == out_value:
                    matched = True
        return matched

    def check_match_all(self, in_values, out_value):
        matched = True
        out_value_is_list = isinstance(out_value, list)

        for in_value in self.iter_parse_values(in_values):
            if not matched:
                continue
            elif out_value_is_list:
                if in_value not in out_value:
                    matched = False
            else:
                if in_value != out_value:
                    matched = False
        return matched

    def check_match_compare(self, in_value, out_value, mode):
        if out_value is None:
            return False

        if not isinstance(out_value, list):
            out_value = [out_value]

        for value in out_value:
            if value is None:
                return False
            else:
                if mode == 'lt':
                    if not value < in_value:
                        return False
                elif mode == 'lte':
                    if not value <= in_value:
                        return False
                elif mode == 'gt':
                    if not value > in_value:
                        return False
                elif mode == 'gte':
                    if not value >= in_value:
                        return False

        return True

    def check_data(self, data, test_data, test_data_exists=True, expect=True,
            mark_error=True):
        match = False

        if not isinstance(data, dict):
            return self.check_match([data], test_data)

        try:
            for key, value in data.iteritems():
                if key.startswith('$'):
                    if key == '$has':
                        if not isinstance(test_data, list):
                            raise TypeError('TODO %r' % test_data)

                        found = False
                        for item in test_data:
                            if self.check_data(value, item, mark_error=False):
                                found = True
                                break

                        if not found:
                            return
                    elif key == '$hasnt':
                        if not isinstance(test_data, list):
                            raise TypeError('TODO %r' % test_data)

                        for item in test_data:
                            if self.check_data(value, item):
                                return
                    elif key == '$in':
                        if not self.check_match(value, test_data):
                            return
                    elif key == '$nin':
                        if self.check_match(value, test_data):
                            return
                    elif key == '$all':
                        if not self.check_match_all(value, test_data):
                            return
                    elif key == '$size':
                        if isinstance(test_data, list):
                            test_data_len = len(test_data)
                        else:
                            test_data_len = 0

                        if isinstance(value, dict):
                            if not self.check_data(value, test_data_len):
                                return
                        else:
                            value = self.parse_value(value)
                            data[key] = value
                            if value != test_data_len:
                                return
                    elif key == '$exists':
                        value = self.parse_value(value)
                        data[key] = value
                        if value != test_data_exists:
                            return
                    elif key == '$eq':
                        values = [value]
                        matched = self.check_match(values, test_data)
                        data[key] = values[0]
                        if not matched:
                            return
                    elif key == '$ne':
                        values = [value]
                        matched = self.check_match(values, test_data)
                        data[key] = values[0]
                        if matched:
                            return
                    elif key == '$not':
                        if self.check_data(
                                    value,
                                    test_data,
                                    test_data_exists,
                                ):
                            return
                    elif key in ('$lt', '$lte', '$gt', '$gte'):
                        value = self.parse_value(value)
                        data[key] = value

                        if not self.check_match_compare(
                                    value,
                                    test_data,
                                    key[1:],
                                ):
                            return
                    elif key == '$and':
                        for item in value:
                            if not self.check_data(
                                        item,
                                        test_data,
                                        test_data_exists,
                                    ):
                                return
                    elif key == '$nor':
                        for item in value:
                            if self.check_data(
                                        item,
                                        test_data,
                                        test_data_exists,
                                    ):
                                return
                    elif key == '$or':
                        matched = False
                        for item in value:
                            if self.check_data(
                                        item,
                                        test_data,
                                        test_data_exists,
                                    ):
                                matched = True
                                break
                        if not matched:
                            return
                    elif key == '$where':
                        if not value(test_data):
                            return
                    elif key == '$type':
                        json_types = {
                            'number': (int, long, float, complex),
                            'string': basestring,
                            'boolean': bool,
                            'array': list,
                            'object': dict,
                            'null': types.NoneType,
                        }
                        if not isinstance(test_data, json_types[value]):
                            return
                    else:
                        raise Exception('TODO', key)
                else:
                    if isinstance(value, dict):
                        if isinstance(test_data, dict) and key in test_data:
                            out_exists = True
                            out_value = test_data[key]
                        else:
                            out_exists = False
                            out_value = None
                        if not self.check_data(value, out_value, out_exists):
                            return
                    else:
                        if not isinstance(test_data, dict):
                            return

                        values = [value]
                        matched = self.check_match(values, test_data.get(key))
                        data[key] = values[0]

                        if not matched:
                            return

            match = True
        finally:
            if mark_error and match != expect and not self._error_marked:
                self._error_marked = True
                data['FAILED=' + key] = data.pop(key)

            return match == expect

    def handle_expect_status(self, expect_status, response_status):
        if self.expect_status:
            return self.check_data(
                self.expect_status,
                self.response_status,
            )
        return True

    def handle_expect_headers(self, expect_headers, response_headers):
        if self.expect_headers:
            return self.check_data(
                self.expect_headers,
                self.response_headers,
            )
        return True

    def handle_expect_data(self, expect_data, response_data):
        if self.expect_data:
            return self.check_data(
                self.expect_data,
                self.response_data,
            )
        return True

    def handle_check_error(self, error_msg):
        if not self.base.filter.error(self):
            return

        report = self.base.formatter.error(self, error_msg)
        self.base.handler.error(report)

        if self.required:
            sys.exit(1)

    def handle_response(self, response):
        self.response_status = response.status_code
        self.response_headers = dict(response.headers.items())

        try:
            self.response_data = response.json()
        except:
            self.response_data = {}

        self.status_check = self.handle_expect_status(
            self.expect_status,
            self.response_status,
        )
        if not self.status_check:
            self.handle_check_error('Status check failed')
            return

        self.headers_check = self.handle_expect_headers(
            self.expect_headers,
            self.response_headers,
        )
        if not self.headers_check:
            self.handle_check_error('Headers check failed')
            return

        self.data_check = self.handle_expect_data(
            self.response_data,
            self.expect_data,
        )
        if not self.data_check:
            self.handle_check_error('Data check failed')
            return

    def run(self):
        self.path = self.parse_str(self.path)
        self.input_data = self.parse_input(self.input_data)

        if self.expect_headers:
            self.expect_headers = {x.lower(): y for x, y in
                self.expect_headers.iteritems()}

        kwargs = self.request_kwargs or {}

        self.response = self.base.handle_request(
            self.method,
            self.base.base_url + self.path,
            headers=self.input_headers,
            json=self.input_data,
            **kwargs
        )

        self.handle_response(self.response)

        self.base.objects[self.__class__] = self
