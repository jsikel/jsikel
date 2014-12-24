from blckur.constants import *
from blckur.exceptions import *

import copy
import collections
import time
import uuid
import types
import sys

class TestCase(object):
    require = None
    required = True
    method = None
    path = None
    expect_status = None
    input_headers = None
    expect_headers = None
    input_json = None
    input_params = None
    input_data = None
    expect_json = None
    request_kwargs = None

    def __init__(self, suite):
        self.suite = suite
        self._error_marked = False

        if self.has_run:
            raise ValueError('Test case %r already run' % (
                self.__class__.__name__))

        if self.require:
            if not isinstance(self.require, (list, tuple)):
                self.require = (self.require,)

            requires = []
            for require in self.require:
                require_obj = self.suite.objects.get(require)
                if not require_obj:
                    require_obj = require(self.suite)
                requires.append(require_obj)
            self.require = requires

        self.run()

    @property
    def parsed_method(self):
        if hasattr(self.method, '__call__'):
            method = self.method()
        else:
            method = self.method
        return self.parse_str(method)

    @property
    def parsed_path(self):
        if hasattr(self.path, '__call__'):
            path = self.path()
        else:
            path = self.path
        return self.parse_str(path)

    @property
    def has_run(self):
        return self.__class__ in self.suite.objects

    @has_run.setter
    def has_run(self, val):
        if val:
            self.suite.objects[self.__class__] = self
        else:
            self.suite.objects.pop(self.__class__, None)

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
                data = self.require[index].input_json
            elif exp_type == 'require_expect':
                data = self.require[index].expect_json
            else:
                raise ValueError('Unknown expression %r' % exp_type)
        elif exp_type == 'input':
            data = self.input_json
        elif exp_type == 'time':
            return str(int(time.time()))
        elif exp_type == 'time_float':
            return str(time.time())
        elif exp_type == 'uuid':
            return uuid.uuid4().hex
        else:
            raise ValueError('Unknown expression %r' % exp_type)

        return str(self.parse_exp_set(exp_set, data))

    def parse_str(self, parse_str):
        return STR_EXP.sub(
            lambda x: self.parse_exp(x.group(1)),
            parse_str,
        )

    def parse_input(self, data):
        if not data:
            pass
        elif isinstance(data, (int, long, float, complex)):
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
            try:
                return self.parse_exp(value[1:])
            except ValueError:
                pass
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
        match = True

        if not isinstance(data, dict):
            return self.check_match([data], test_data)

        try:
            for key, value in data.iteritems():
                if key == '$has':
                    if not isinstance(test_data, list):
                        raise TestCheckFailed

                    found = False
                    for item in test_data:
                        if self.check_data(value, item, mark_error=False):
                            found = True
                            break

                    if not found:
                        raise TestCheckFailed
                elif key == '$hasnt':
                    if not isinstance(test_data, list):
                        continue

                    for item in test_data:
                        if self.check_data(value, item, mark_error=mark_error):
                            raise TestCheckFailed
                elif key == '$in':
                    if not self.check_match(value, test_data):
                        raise TestCheckFailed
                elif key == '$nin':
                    if self.check_match(value, test_data):
                        raise TestCheckFailed
                elif key == '$all':
                    if not self.check_match_all(value, test_data):
                        raise TestCheckFailed
                elif key == '$size':
                    if isinstance(test_data, list):
                        test_data_len = len(test_data)
                    else:
                        test_data_len = 0

                    if isinstance(value, dict):
                        if not self.check_data(value, test_data_len,
                                mark_error=mark_error):
                            raise TestCheckFailed
                    else:
                        value = self.parse_value(value)
                        data[key] = value
                        if value != test_data_len:
                            raise TestCheckFailed
                elif key == '$exists':
                    value = self.parse_value(value)
                    data[key] = value
                    if value != test_data_exists:
                        raise TestCheckFailed
                elif key == '$eq':
                    values = [value]
                    matched = self.check_match(values, test_data)
                    data[key] = values[0]
                    if not matched:
                        raise TestCheckFailed
                elif key == '$ne':
                    values = [value]
                    matched = self.check_match(values, test_data)
                    data[key] = values[0]
                    if matched:
                        raise TestCheckFailed
                elif key == '$not':
                    if self.check_data(
                                value,
                                test_data,
                                test_data_exists,
                                mark_error=mark_error,
                            ):
                        raise TestCheckFailed
                elif key in ('$lt', '$lte', '$gt', '$gte'):
                    value = self.parse_value(value)
                    data[key] = value

                    if not self.check_match_compare(
                                value,
                                test_data,
                                key[1:],
                            ):
                        raise TestCheckFailed
                elif key == '$and':
                    for item in value:
                        if not self.check_data(
                                    item,
                                    test_data,
                                    test_data_exists,
                                    mark_error=mark_error,
                                ):
                            raise TestCheckFailed
                elif key == '$nor':
                    for item in value:
                        if self.check_data(
                                    item,
                                    test_data,
                                    test_data_exists,
                                    mark_error=mark_error,
                                ):
                            raise TestCheckFailed
                elif key == '$or':
                    matched = False
                    for item in value:
                        if self.check_data(
                                    item,
                                    test_data,
                                    test_data_exists,
                                    mark_error=mark_error,
                                ):
                            matched = True
                            break
                    if not matched:
                        raise TestCheckFailed
                elif key == '$text':
                    value = self.parse_value(value)
                    data[key] = value

                    if value not in test_data:
                        raise TestCheckFailed
                elif key == '$where':
                    if not value(test_data):
                        raise TestCheckFailed
                elif key == '$regex':
                    if isinstance(value, basestring):
                        value = self.parse_value(value)
                        data[key] = value

                        if not re.match(value, test_data):
                            raise TestCheckFailed
                    else:
                        if not value.match(test_data):
                            raise TestCheckFailed
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
                        raise TestCheckFailed
                else:
                    if isinstance(value, dict):
                        if isinstance(test_data, dict) and key in test_data:
                            out_exists = True
                            out_value = test_data[key]
                        else:
                            out_exists = False
                            out_value = None
                        if not self.check_data(value, out_value, out_exists,
                                mark_error=mark_error):
                            raise TestCheckFailed
                    else:
                        if not isinstance(test_data, dict):
                            raise TestCheckFailed

                        values = [value]
                        matched = self.check_match(values, test_data.get(key))
                        data[key] = values[0]

                        if not matched:
                            raise TestCheckFailed
        except TestCheckFailed:
            match = False

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

    def handle_expect_json(self, expect_json, response_data):
        if self.expect_json:
            return self.check_data(
                self.expect_json,
                self.response_data,
            )
        return True

    def handle_check_error(self, error_msg):
        self.suite.log_error(self, error_msg)

        if self.required:
            sys.exit(1)

    def handle_response(self, response):
        self.response_status = response.status_code
        self.response_headers = dict(response.headers.items())
        self.response_time = response.duration

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

        self.json_check = self.handle_expect_json(
            self.response_data,
            self.expect_json,
        )
        if not self.json_check:
            self.handle_check_error('Json check failed')
            return

        self.suite.log_response(self)

    def run(self):
        self.input_headers = self.parse_input(self.input_headers)
        self.input_json = self.parse_input(self.input_json)
        self.input_params = self.parse_input(self.input_params)
        self.input_data = self.parse_input(self.input_data)

        if self.input_headers:
            self.input_headers = {x.lower(): y for x, y in
                self.input_headers.iteritems()}

        if self.expect_headers:
            self.expect_headers = {x.lower(): y for x, y in
                self.expect_headers.iteritems()}

        kwargs = self.request_kwargs or {}

        self.response = self.suite.handle_request(
            self.parsed_method,
            self.suite.base_url + self.parsed_path,
            headers=self.input_headers,
            params=self.input_params,
            data=self.input_data,
            json=self.input_json,
            **kwargs
        )

        self.handle_response(self.response)

        self.has_run = True
