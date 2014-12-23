from blckur.constants import *
from blckur.exceptions import *
from blckur import filter
from blckur import formatter
from blckur import handler
from blckur import test_case

import time
import uuid
import requests

class Base(object):
    base_url = None
    filter = filter.ReportFilter()
    formatter = formatter.ReportFormatter()
    handler = handler.ReportHandler()
    request_kwargs = None
    request_time = None

    def __init__(self):
        self.objects = {}
        self.requests = requests

    @property
    def TestCase(self):
        return type('TestCase', (test_case.TestCase,), {
            'id': uuid.uuid4().hex,
            'base': self,
        })

    def main(self):
        module = __import__('__main__')

        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and \
                    issubclass(obj, test_case.TestCase) and \
                    obj.base == self and obj.id not in self.objects:
                obj()

    def handle_request(self, method, url, **kwargs):
        if self.request_kwargs:
            kwargs.update(self.request_kwargs)

        start = time.time()
        response = self.request(method, url, **kwargs)
        self.request_time = int((time.time() - start) * 1000)

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

class SessionBase(Base):
    def __init__(self):
        Base.__init__(self)
        self.requests = requests.Session()
        self.init_session()

    def _get_attr(self, name, default=None):
        if hasattr(self, name):
            return getattr(self, name)
        return default

    def init_session(self):
        test_case = type('SessionInitTestCase', (self.TestCase,), {
            'base': self,
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
        test_case()
