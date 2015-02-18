class TestException(Exception):
    pass

class TestCheckFailed(TestException):
    pass

class TestStatusFailed(TestException):
    pass

class TestExpectFailed(TestException):
    pass
