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

This code snippet is all you need to perform any number of pyblitz requests (so long as the `api` module is generated; see [this section](#generation) for more info).

```
import pyblitz
import api as myApi # the generated api.py file

# set up server
pyblitz.http.setActiveServer("myServerName")
pyblitz.http.setAuth("myApiToken_n74axeqz")

# create models (manually)
# NOTE: this will work for whatever models are generated in the api.py file
user = myApi.User(
    name="Samantha Roberts",
    id=98765,
)

# modify models
user.spouseId = 13579

# call api endpoints
myApi.users.register.POST(user)

# create models (from responses)
pyblitzResponse = myApi.users.spouses.GET(user)
def transformToUser(responseJson):
    # let's say that the response looks like
    # "{spouse: {name: ..., id: ..., ...}, user: {name: ..., id: ..., ...}}"
    return responseJson['spouse']
userSpouse = pyblitzResponse.transform(myApi.User, transformToUser)
print(userSpouse.name)      # "Jeremy Roberts"
print(userSpouse.id)        # 13579
print(userSpouse.spouseId)  # 98765
```

Easy, no?


## Features

### Endpoints

pyblitz was designed with scripting in mind. Its main feature is its `api.py` module, a generated file which contains a complete hierarchy of commands for your API. It contains a nested `class` structure allowing you to use auto-completion to navigate your endpoints. The leaf methods are valid HTTP methods that can be called on the endpoint. Using these endpoints is as easy as:

```
import api as myApi

myApi.my.endpoint.name.GET()
```

(Psst. If you're *actually* trying these examples and notice a `RuntimeError: Cannot make network requests until...` error, [check here](#configuring-http) before continuing.)

Data is passed as the first argument for all methods except `GET` and `DELETE`. If you need to pass headers or parameters, you can do so with keyword arguments. You can also still pass data to `GET` and `DELETE` through the `data=` keyword argument.

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

### Schema

pyblitz also provides `Schema` classes to easily manage data for requests/responses. You can create models manually or generate them from a response. Some examples are:

```
import api as myApi

createdUser = myApi.User()
createdUser.name = "Jake McDonald"
createdUser.id = 12345

pyblitzResponse = myApi.some.user.endpoint.GET()
userFromResponse = pyblitzResponse.transform(myApi.User, someTransformUserFunction)
```

A transformation function is a function that takes a parsed JSON object and returns the desired part of that object which should be converted to your `Schema`. A simple example for the above case:

```
# `responseJson` is an object with this data heirarchy:
# {data: {extraData: [...], user: {name: ..., id: ..., ...}, ...}}
def someTransformUserFunction(responseJson):
    return responseJson['user']
```

Something important to note is while each model contains all of the properties for a given schema, they are "dumb properties", meaning that there is no type checking or other logic to guard you from bad requests. This is *intentional* to allow testing for these kinds of bad requests. (Oh, and I guess it made them easier to implement too...)

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

Before you can actually use any `api.py` endpoints, you must first configure pyblitz by using the `http` module. There are two methods in particular that need to be used: `http.setActiveServer()` and `http.setAuth()`. `setActiveServer(name)` takes a `name` string, referencing one of the servers registered in the `api.py` module (you can change the names if they bug you that much). `setAuth(token)` takes an authentication `token` string that gets slapped onto all future requests you make.

This module also provides HTTP request functions should you decide to call endpoints a little more manually (you madman). These functions are still capable of processing `Schema` as parameters, and their signatures are nearly identical to the endpoints' methods.

```
pyblitz.http.POST(
    "https://my.api.website.com/users",
    userSchema,
    headers=dict(),
    param1="you get the idea",
)
```

## [Big Back-to-top Button](#pyblitz)

Because I didn't know what else to put down here lol
