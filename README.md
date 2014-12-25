[![Blckur](media/logo1.png)](https://blckur.com)

# blckur: rest api testing framework
[Blckur](https://github.com/blckur/blckur) allows quickly writing unittests
for your REST API and microservices with a familiar format based on MongoDBs
query language. More information available at [blckur.com](https://blckur.com)

## operators

### $has

Tests that the output array contains an object.

```python
@blckur.append_to(ExampleSuite)
class GetExample(blckur.TestCase):
    method = 'GET'
    path = '/example'
    expect_status = 200
    expect_json = {'$has': {
        'key': 'value0',
    }}

matching_output = [
    {'key': 'value0'},
    {'key': 'value1'},
]
```

### $hasnt

Tests that the output array doesn't contain an object.

```python
@blckur.append_to(ExampleSuite)
class GetExample(blckur.TestCase):
    method = 'GET'
    path = '/example'
    expect_status = 200
    expect_json = {'$hasnt': {
        'key': 'value0',
    }}

matching_output = [
    {'key': 'value1'},
    {'key': 'value2'},
]
```

### $in

Checks that the output value exists in the provided array.

```python
@blckur.append_to(ExampleSuite)
class GetExample(blckur.TestCase):
    method = 'GET'
    path = '/example'
    expect_status = 200
    expect_json = {
        'key': {'$in': ['value0', 'value1']},
    }

matching_output = {
    'key': 'value1',
}
```

### $nin

Checks that the output value doesn't exists in the provided array.

```python
@blckur.append_to(ExampleSuite)
class GetExample(blckur.TestCase):
    method = 'GET'
    path = '/example'
    expect_status = 200
    expect_json = {
        'key': {'$nin': ['value0', 'value1']},
    }

matching_output = {
    'key': 'value2',
}
```

### $all

Checks that the output value contains all the provided elements in the array.

```python
@blckur.append_to(ExampleSuite)
class GetExample(blckur.TestCase):
    method = 'GET'
    path = '/example'
    expect_status = 200
    expect_json = {
        'key': {'$all': ['value0', 'value1']},
    }

matching_output = {
    'key': ['value0', 'value1', 'value2'],
}
```

### $size

Checks that the output value size matches the provided size.

```python
@blckur.append_to(ExampleSuite)
class GetExample(blckur.TestCase):
    method = 'GET'
    path = '/example'
    expect_status = 200
    expect_json = {
        'key': {'$size': 2},
    }

matching_output = {
    'key': ['value0', 'value1'],
}
```

### $exists

Checks that the output contains or doesn't contain the provided key.

```python
@blckur.append_to(ExampleSuite)
class GetExample(blckur.TestCase):
    method = 'GET'
    path = '/example'
    expect_status = 200
    expect_json = {
        'key': {'$exists': True},
    }

matching_output = {
    'key': 'value',
}
```
