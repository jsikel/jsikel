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

class Base(object):
    _instance = None
    base_url = None
    filter = filter.ReportFilter()
    formatter = formatter.ReportFormatter()
    handler = handler.ReportHandler()
    request_kwargs = None
    request_time = None

    def __init__(self):
        self.objects = {}
        self.requests = requests

    @static_property
    def TestCase(cls):
        cls._instance = cls._instance or cls()
        return type('TestCase', (test_case.TestCase,), {
            'id': uuid.uuid4().hex,
            'base': cls._instance,
        })

    def setup(self):
        pass

    def run_all(self):
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

    @classmethod
    def main(cls):
        cls._instance.setup()
        cls._instance.run_all()

class SessionBase(Base):
    def __init__(self):
        Base.__init__(self)
        self.requests = requests.Session()

    def _get_attr(self, name, default=None):
        if hasattr(self, name):
            return getattr(self, name)
        return default

    def setup(self):
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
