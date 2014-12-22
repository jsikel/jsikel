class TestException(Exception):
    pass

class TestStatusFailed(TestException):
    pass

class TestExpectFailed(TestException):
    pass
