from jsikel.constants import *
from jsikel.exceptions import *
from jsikel.helpers import *
from jsikel import filter
from jsikel import formatter
from jsikel import handler
from jsikel import test_case

import time
import uuid
import requests
import collections

class TestSuite(object):
    base_url = None
    verify = True
    filter = filter.ReportFilter()
    formatter = formatter.ReportFormatter()
    handler = handler.ReportHandler()
    request_kwargs = None

    def __init__(self):
        self.objects = {}
        self.requests = requests

        if self.base_url[-1] == '/':
            self.base_url = self.base_url[:-1]

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
            verify=self.verify,
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

class SessionTestSuite(TestSuite):
    def __init__(self):
        TestSuite.__init__(self)
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

class OAuthTestSuite(TestSuite):
    client_secret = None
    resource_owner_key = None
    resource_owner_secret = None
    callback_uri = None
    signature_method = None
    signature_type = None
    rsa_key = None
    verifier = None
    client_class = None
    force_include_body = None

    def __init__(self):
        import oauthlib.oauth1
        import requests_oauthlib
        TestSuite.__init__(self)

        self.requests = requests_oauthlib.OAuth1Session(
            client_key=unicode(self.consumer_key),
            client_secret=unicode(self.consumer_secret),
            resource_owner_key=unicode(self.access_token),
            resource_owner_secret=unicode(self.access_token_secret),
            signature_method=self.signature_method or \
                oauthlib.oauth1.SIGNATURE_HMAC,
            signature_type=self.signature_type or \
                oauthlib.oauth1.SIGNATURE_TYPE_AUTH_HEADER,
            rsa_key=self.rsa_key,
            verifier=self.verifier,
            client_class=self.client_class,
            force_include_body=self.force_include_body or False,
        )

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
