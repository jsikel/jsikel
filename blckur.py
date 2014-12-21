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
    output_data = None
    require = None

    def __init__(self):
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
                data = self.require[index].outputted
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

    def check_output(self, data, outputted, outputted_exists=True,
            expect=True):
        match = False

        try:
            for key, value in data.iteritems():
                if key.startswith('$'):
                    if key == '$has':
                        if not isinstance(outputted, list):
                            raise TypeError('TODO %r' % outputted)

                        found = False
                        for item in outputted:
                            if self.check_output(value, item):
                                found = True
                                break
                        if not found:
                            return False
                    elif key == '$hasnt':
                        if not isinstance(outputted, list):
                            raise TypeError('TODO %r' % outputted)

                        for item in outputted:
                            if self.check_output(value, item):
                                return False
                    elif key == '$in':
                        if not self.check_match(value, outputted):
                            return False
                    elif key == '$nin':
                        if self.check_match(value, outputted):
                            return False
                    elif key == '$all':
                        if not self.check_match_all(value, outputted):
                            return False
                    elif key == '$size':
                        if isinstance(outputted, list):
                            outputted_len = len(outputted)
                        else:
                            outputted_len = 0

                        if isinstance(value, dict):
                            if not self.check_output(value, outputted_len):
                                return False
                        else:
                            value = self.parse_value(value)
                            data[key] = value
                            if value != outputted_len:
                                return False
                    elif key == '$exists':
                        value = self.parse_value(value)
                        data[key] = value
                        if value != outputted_exists:
                            return False
                    elif key == '$ne':
                        values = [value]
                        matched = self.check_match(values, outputted)
                        data[key] = values[0]
                        if matched:
                            return False
                    elif key == '$not':
                        if self.check_output(
                                    value,
                                    outputted,
                                    outputted_exists,
                                ):
                            return False
                    elif key == '$and':
                        for item in value:
                            if not self.check_output(
                                        item,
                                        outputted,
                                        outputted_exists,
                                    ):
                                return False
                    elif key == '$nor':
                        for item in value:
                            if self.check_output(
                                        item,
                                        outputted,
                                        outputted_exists,
                                    ):
                                return False
                    elif key == '$or':
                        matched = False
                        for item in value:
                            if self.check_output(
                                        item,
                                        outputted,
                                        outputted_exists,
                                    ):
                                matched = True
                                break
                        if not matched:
                            return False
                    elif key == '$where':
                        if not value(outputted):
                            return False
                    elif key == '$type':
                        if not isinstance(outputted, value):
                            return False
                    else:
                        raise Exception('TODO', key)
                else:
                    if isinstance(value, dict):
                        if key in outputted:
                            out_exists = True
                            out_value = outputted[key]
                        else:
                            out_exists = False
                            out_value = None
                        if not self.check_output(value, out_value, out_exists):
                            return False
                    else:
                        if isinstance(outputted, list):
                            raise TypeError('TODO %r' % outputted)

                        values = [value]
                        matched = self.check_match(values, outputted.get(key))
                        data[key] = values[0]

                        if not matched:
                            return False

            match = True
        finally:
            if match != expect:
                data['FAILED=' + key] = data.pop(key)

        return True

    def run(self):
        self.path = self.parse_str(self.path)
        self.inputted = self.parse_input(self.input_data)

        self.response = self.base.requests.request(
            self.method,
            self.base.base_url + self.path,
            json=self.inputted,
        )

        self.outputted = self.response.json()
        self.data = self.outputted

        if self.output_data:
            check = self.check_output(self.output_data, self.outputted)

            if not check:
                raise Exception('TODO')

        self.base.objects[self.__class__] = self
