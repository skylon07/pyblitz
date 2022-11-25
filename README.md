# pyblitz
A scripting-ready python library for your OpenAPI!


## Table of Contents

- [Quickstart](#quickstart)
- [Features](#features)
    - [Endpoints](#endpoints)
    - [Schema](#schema)
    - [Generation](#generation)
    - [Configuring HTTP](#configuring-http)
- [Big Back-to-top Button](#big-back-to-top-button)


## Quickstart

This code snippet is all you need to perform any number of pyblitz requests through your [generated api](#generation).

``` 
import api as myApi # the generated api.py file

# set up server
myApi.http.setActiveServer("myServerName")
myApi.http.setAuth("myApiToken_n74axeqz")

# create models (manually)
user = myApi.User(
    name="Samantha Roberts",
    id=98765,
)

# modify models
user.name = "Sam Roberts"

# call api endpoints
myApi.users.register.POST(user)

# create models (from responses)
# assuming GET myApi/users/{userId}/friends returns:
# {
    friends: [{name: ..., id: ...}, ...],
    user: {name: ..., id: ...}
# }
friendsResponse = myApi.users(user.id).friends.GET()
userFromResponse = friendsResponse['user']
firstFriend = friendsResponse['friends'][0]
print(userFromResponse.name)    # Sam Roberts
print(userFromResponse.id)      # 98765
print(firstFriend.name)         # Jeremy Brady
print(firstFriend.id)           # 13579
```

Easy, no?


## Features

### Endpoints

`pyblitz` was designed with scripting in mind. It features a main `api.py` module, a generated file which contains a complete hierarchy of commands for your API. It contains a nested `class` structure allowing you to use auto-completion to navigate your endpoints. The leaf methods are valid HTTP methods that can be called on the endpoint. Using these endpoints is as easy as:

```
import api as myApi

myApi.my.endpoint.name.GET()
```

(Psst. If you're *actually* trying these examples and notice a `RuntimeError: Cannot make network requests until...` error, [check here](#configuring-http) before continuing.)

Data is passed as the first argument for all methods except `GET` and `DELETE`. If you need to pass headers or parameters, you can do so with keyword arguments. You can also still pass data to `GET` and `DELETE` through the `data` keyword argument.

```
import api as myApi

# `data` can be a `dict()`, `Schema`, byte string/array, etc.
myApi.my.endpoint.name.POST(
    data,
    headers=dict(),
    param1="query",
    param2="params",
    param3="here",
)
```

Endpoints with dynamic urls can also be used. Passing parameters into these URLs can be done
simply by calling the parent endpoint as a function of the parameter.

```
import api as myApi

userId = 12345
# GETs the /users/{userId}/friends endpoint
pyblitzResponse = myApi.users(userId).friends.GET()
```

### Schema

`pyblitz` also provides `Schema` classes to easily manage data for requests/responses. You can create models manually or generate them from a response. Some examples are:

```
import api as myApi

createdUser = myApi.User()
createdUser.name = "Jake McDonald"
createdUser.id = 12345

pyblitzResponse = myApi.some.user.endpoint.GET()
userFromResponse = pyblitzResponse['json']['path']['to']['user']
assert type(userFromResponse) is myApi.User
userFromResponseTransform = pyblitzResponse.transform(customTransformFn)
assert type(userFromResponseTransform) is myApi.User
```

A transformation function is a function that takes the JSON dictionary and converts it to whatever data you need. This can be used for filtering unnecessary data or escaping the automatic `Schema` generation. A simple example for the above case:

```
# `responseJson` is an object with this data heirarchy:
# {
#   data: {
#       extraData: [...],
#       user: {name: ..., id: ...},
#       ...
#   }
# }
def customTransformFn(responseJson):
    return myApi.User.fromSerialized(responseJson['data']['user'])
```

Once `Schema` are created, they can be sent directly into the endpoints' http methods to be automatically serialized into the request. This is useful especially if you want to change some data and sync it with the server:

```
import api as myApi

user.name = "NEW NAME"
pyblitzResponse = myApi.some.endpoint.PATCH({'user': user})
# assuming this endpoint returns the user after patching...
# {
#   user: {name: ..., id: ...}
# }
patchedUser = pyblitzResponse['user']
assert patchedUser == user
```

If serializing only a part of the `Schema` is desired when sending requests, you can use the `serialFilter()` function to set what properties are included upon serialization. This filter is set per-instance and is not shared between `Schema`. An example:

```
import api as myApi

user = myApi.User()
user.name = "Kenneth Gregory"
user.id = 35764
# assuming `extraData` is a valid User() property...
user.extraData = "this will ultimately be ignored"

user.serialFilter('name', 'id')
# PATCH sends: {'name': user.name, 'id': user.id}
pyblitzResponse = myApi.some.endpoint.PATCH({'user': user})
# reset the filter, if desired
user.serialFilter()
```

One last important thing to note is while each model contains all of the properties for a given schema, they are "dumb properties", meaning that there is no type checking or other logic to guard you from bad requests. This is *intentional* to allow testing for these kinds of bad requests. (It also just *happened* to make them easier to implement too...)

### Generation

The `api.py` file is generated from the `generator` module. You would need to do this every time your OpenAPI spec changes. To do so, you can simply call `generator.generateAPI()`, and the rest of the process is automatic. An example:

```
import pyblitz

parserClass = pyblitz.generator.Parser_3_1_0
openApiPath = "path/to/openapi.json"
apiOutPath = "path/to/new/api.py"
pyblitz.generator.generateAPI(parserClass, openApiPath, apiOutPath)
```

Please note that you should pass a `Parser` class *reference*, and not an *instance*. Also, `Parser` classes are suffixed with the openapi version they support (`Parser_3_1_0` supports openapi.json files v3.1.0), so make sure to use the right version for the file you're using.

### Configuring HTTP

Before you can actually use any `api.py` endpoints, you must first configure `pyblitz` by using the `http` module. There are two methods in particular that need to be used: `http.setActiveServer()` and `http.setAuth()`. `setActiveServer(name)` takes a `name` string, referencing one of the servers registered at the top of the `api.py` module (names and descriptions can be changed to your liking). `setAuth(token)` takes an authentication `token` string that is added onto all future requests you make.

This module also provides HTTP request functions should you decide to call endpoints a little more manually (in cases where you want to tell `pyblitz` to avoid using 70% of its functionality). These functions are still capable of processing `Schema` as parameters, and their signatures are nearly identical to the endpoints' methods.

```
import api as myApi

user = myApi.User()
user.name = "Henry Evans"
user.id = 753146
myApi.http.POST(
    "https://my.api.website.com/users",
    user,
    headers=dict(),
    param1="you get the idea",
)
```

## [Big Back-to-top Button](#pyblitz)

Because I didn't know what else to put down here
