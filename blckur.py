import requests
import json
import time
import re
import collections
import copy
import uuid
import sys

STR_EXP = re.compile('\{\$([^}]+)\}')
JSON_INDENT = 2

class Base(object):
    base_url = None
    def __init__(self):
        self.objects = {}
        self.requests = requests.request

    @property
    def TestCase(self):
        return type('TestCase', (TestCase,), {
            'base': self,
        })

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
    input_data = None
    expect_data = None
    require = None
    required = True

    def __init__(self):
        self._error_marked = False

        if self.__class__ in self.base.objects:
            raise ValueError('Test case %r already run' % self.__class__)

        if self.require:
            if not isinstance(self.require, (list, tuple)):
                self.require = (self.require,)

            requires = []
            for require in self.require:
                require = self.base.objects.get(require)
                if not require:
                    require = require()
                requires.append(require)
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
                data = self.require[index].data
            elif exp_type == 'require_input':
                data = self.require[index].inputted
            elif exp_type == 'require_output':
                data = self.require[index].output_data
            else:
                raise TypeError('TODO %r' % exp)
        elif exp_type == 'input':
            data = self.inputted
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
                            if self.check_data(value, item):
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
                                return False
                        else:
                            value = self.parse_value(value)
                            data[key] = value
                            if value != test_data_len:
                                return False
                    elif key == '$exists':
                        value = self.parse_value(value)
                        data[key] = value
                        if value != test_data_exists:
                            return False
                    elif key == '$ne':
                        values = [value]
                        matched = self.check_match(values, test_data)
                        data[key] = values[0]
                        if matched:
                            return False
                    elif key == '$not':
                        if self.check_data(
                                    value,
                                    test_data,
                                    test_data_exists,
                                ):
                            return False
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
                        if not isinstance(test_data, value):
                            return
                    else:
                        raise Exception('TODO', key)
                else:
                    if isinstance(value, dict):
                        if key in test_data:
                            out_exists = True
                            out_value = test_data[key]
                        else:
                            out_exists = False
                            out_value = None
                        if not self.check_data(value, out_value, out_exists):
                            return
                    else:
                        if isinstance(test_data, list):
                            raise TypeError('TODO %r' % test_data)

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

    def run(self):
        self.path = self.parse_str(self.path)
        self.inputted = self.parse_input(self.input_data)

        self.response = self.base.requests.request(
            self.method,
            self.base.base_url + self.path,
            json=self.inputted,
        )

        try:
            self.output_data = self.response.json()
        except:
            self.output_data = {}
        self.data = self.output_data

        if self.expect_data:
            check = self.check_data(self.expect_data, self.output_data)

            if not check:
                print '***************************************************'
                print 'TEST FAILED'
                print 'name:', self.__class__.__name__
                print 'method:', self.method
                print 'path:', self.path
                print 'status_code:', json.dumps(self.status_code,
                    indent=JSON_INDENT)
                print 'input_data:', json.dumps(self.inputted,
                    indent=JSON_INDENT)
                print 'expect_data:', json.dumps(self.expect_data,
                    indent=JSON_INDENT)
                print 'response:', json.dumps(self.output_data,
                    indent=JSON_INDENT)
                print '***************************************************'
                if self.required:
                    sys.exit(1)

        self.base.objects[self.__class__] = self
