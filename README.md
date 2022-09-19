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

# set up server
# (valid names are registered in the `api` module)
pyblitz.http.setActiveServer("dev" or "prod")
pyblitz.setAuth("myApiToken_n74axeqz")

# create models (manually)
user = pyblitz.api.User(
    name="Samantha Roberts",
    id=98765,
)

# modify models
user.spouseId = 13579

# call api endpoints
pyblitz.api.users.register.POST(user)

# create models (from responses)
response = pyblitz.api.users.spouses.GET(user)
userSpouse = pyblitz.api.User.fromResponse(response)
print(userSpouse.name)      # "Jeremy Roberts"
print(userSpouse.id)        # 13579
print(userSpouse.spouseId)  # 98765
```

Easy, no?


## Features

### Endpoints

pyblitz was designed with scripting in mind. Its main feature is its `api` module, which contains a complete hierarchy of the Pronto public API. Internally, it's a nested `class` structure allowing use of auto-completable property syntax to navigate endpoints. The leaf methods are valid HTTP methods that can be called on the endpoint. Using these endpoints is as easy as:

```
pyblitz.api.my.endpoint.name.GET()
```

Data is passed as the first argument for all methods except `GET` and `DELETE`. If you need to pass headers or parameters, you can do so with keyword arguments. You can also still pass data to `GET` and `DELETE` through the `data=` keyword argument.

```
# `data` can be a `dict()`, `Schema`, byte string/array, etc.
pyblitz.api.my.endpoint.name.POST(
    data,
    headers=dict(),
    param1="query",
    param2="params",
    param3="here",
)
```

(Psst. If you're *actually* trying these examples and notice a `RuntimeError: Cannot make network requests until...` error, [check here](#configuring-http) before continuing.)

### Schema

pyblitz also provides `Schema` classes to easily manage data for requests/responses. You can create models manually or generate them from a response. Some examples are:

```
createdUser = pyblitz.api.User()
createdUser.name = "Jake McDonald"
createdUser.id = 12345

response = pyblitz.api.some.user.endpoint.GET()
userFromResponse = User.fromResponse(response)
```

Note that while each model contains all of the properties for a given schema, they are "dumb properties", meaning that there is no type checking or other logic to guard you from bad requests. This is *intentional* to allow testing for these kinds of bad requests. (Oh, and I guess it made them easier to implement too...)

### Generation

The `api` module is generated from the `generator` module. Should you need to do this yourself (say, to update the endpoint hierarchy), you can simply call `generator.generateAPI()`, and the rest of the process is automatic. An example:

```
parserClass = pyblitz.generator.Parser_3_1_0
path = "path/to/openapi.json"
pyblitz.generator.generateAPI(parserClass, path)
```

Please note that you should pass a `Parser` class reference, and not an instance. Also, `Parser` classes are suffixed with the openapi version they support (`Parser_3_1_0` supports openapi.json files v3.1.0), so make sure to use the right version for the file you're using.

### Configuring HTTP

Before you can actually use any `api` endpoints, you must first configure pyblitz by using the `http` module. There are two methods in particular that need to be used: `http.setActiveServer()` and `http.setAuth()`. `setActiveServer(name)` takes a `name` string, referencing one of the servers registered in the `api` module. `setAuth(token)` takes an authentication `token` string that gets slapped onto all future requests you make.

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
