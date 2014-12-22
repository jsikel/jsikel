from blckur.constants import *
from blckur.exceptions import *
from blckur import filter
from blckur import formatter
from blckur import handler
from blckur import test_case

import time
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
        self.requests = requests.request

    @property
    def TestCase(self):
        return type('TestCase', (test_case.TestCase,), {
            'base': self,
        })

    def main(self):
        module = __import__('__main__')

        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and \
                    issubclass(obj, test_case.TestCase) and \
                    obj.base == self and obj not in self.objects:
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

        self.request(
            self.method,
            self.base_url + self.path,
            json=self.input_json,
            params=self.input_params,
            data=self.input_data,
        )
