.. image:: media/logo1.png
    :target: http://blckur.com

blckur: rest api testing framework
==================================

`Blckur <https://github.com/blckur/blckur>`_ allows quickly writing unittests for your REST API and microservices with a familiar format based on MongoDBs query language. More information available at `blckur.com <https://blckur.com>`_

operators
=========

$has
----

Checks if an array contains an object.

```python
@blckur.append_to(ExampleSuite)
class GetExample(blckur.TestCase):
    method = 'GET'
    path = '/example'
    expect_status = 200
    expect_json = {'$has': {
        'key': 'value',
    }}
```
