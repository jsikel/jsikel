from blckur.constants import *
from blckur.exceptions import *
from blckur.helpers import *
from blckur import filter
from blckur import formatter
from blckur import handler
from blckur import test_case

import time
import uuid
import requests
import collections

class Base(object):
    base_url = None
    filter = filter.ReportFilter()
    formatter = formatter.ReportFormatter()
    handler = handler.ReportHandler()
    request_kwargs = None

    def __init__(self):
        self.objects = {}
        self.requests = requests

    def setup(self):
        pass

    def run_all(self):
        for tst_case in self.test_cases:
            if tst_case not in self.objects:
                tst_case(self)

    def handle_request(self, method, url, **kwargs):
        if self.request_kwargs:
            kwargs.update(self.request_kwargs)

        start = time.time()
        response = self.request(method, url, **kwargs)
        response.duration = int((time.time() - start) * 1000)

        return response

    def request(self, method, url, headers=None, json=None,
            params=None, data=None, **kwargs):
        return self.requests.request(
            method,
            url,
            headers=headers,
            json=json,
            params=params,
            data=data,
            **kwargs
        )

    def log_error(self, tst_case, error_msg):
        if not self.filter.error(self):
            return

        report = self.formatter.error(tst_case, error_msg)
        self.handler.error(report)

    def log_response(self, tst_case):
        if not self.filter.response(self):
            return

        report = self.formatter.response(tst_case)
        self.handler.response(report)

    @classmethod
    def main(cls):
        instance = cls()
        instance.setup()
        instance.run_all()

class SessionBase(Base):
    def __init__(self):
        Base.__init__(self)
        self.requests = requests.Session()

    def _get_attr(self, name, default=None):
        if hasattr(self, name):
            return getattr(self, name)
        return default

    def setup(self):
        tst_case = type('SessionInitTestCase', (test_case.TestCase,), {
            'require': self._get_attr('require'),
            'required': self._get_attr('required', True),
            'method': self._get_attr('method'),
            'path': self._get_attr('path'),
            'expect_status': self._get_attr('expect_status'),
            'input_headers': self._get_attr('input_headers'),
            'expect_headers': self._get_attr('expect_headers'),
            'input_json': self._get_attr('input_json'),
            'input_params': self._get_attr('input_params'),
            'input_data': self._get_attr('input_data'),
            'expect_json': self._get_attr('expect_json'),
            'request_kwargs': self._get_attr('request_kwargs'),
        })
        self.test_cases.appendleft(tst_case)

def append_to(base_cls):
    def _wrapped(cls):
        if not hasattr(base_cls, 'test_cases'):
            base_cls.test_cases = collections.deque()
        base_cls.test_cases.append(cls)
        return cls
    return _wrapped

def prepend_to(base_cls):
    def _wrapped(cls):
        if not hasattr(base_cls, 'test_cases'):
            base_cls.test_cases = collections.deque()
        base_cls.test_cases.appendleft(cls)
        return cls
    return _wrapped
