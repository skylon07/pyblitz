import requests
import json
from typing import Any

from ..common import Schema


class Response:
    def __init__(self, response: requests.Response, jsonSchemaPathsFromCodes: dict[int, list[tuple[tuple, type]]]):
        self._response = response
        self._jsonDict = json.loads(response.text)
        self._transformedJsonDict = json.loads(response.text)
        
        code = self._response.status_code
        jsonSchemaPathList = jsonSchemaPathsFromCodes.get(code, [])
        for (pathKeyDescriptors, schemaClass) in jsonSchemaPathList:
            self._transformSchema(pathKeyDescriptors, schemaClass)

    def __getitem__(self, key):
        return self._transformedJsonDict[key]

    @property
    def status(self):
        return self._response.status_code

    def transform(self, transformFn):
        return transformFn(self._jsonDict)

    def _transformSchema(self, pathKeyDescriptors: tuple[tuple[str, Any]], schemaClass: type, startJsonItem = None):
        """
        Given a "path", a destination schema class, and optionally the json item
        to work with, this function will inflate JSON data to actual Schema
        instances

        A "path" is defined as a list of key descriptors. A key descriptor is a
        two-tuple of the type of access being made, and the key to use for the
        access. The type of access can be an 'object' property access or an
        'array' index access.

        For example:
        ```
        # explains that response.matchingNode.id is a NodeId
        pathKeyDescriptors = [
            ('object', 'matchingNode'),
            ('object', 'id'),
        ]
        
        # explains that response.users is an array, where each
        # user.contactInfo is a UserContactInfo
        pathKeyDescriptors = [
            ('object', 'users'),
            ('array', slice(None)),
            ('object', 'contactInfo'),
        ]
        ```
        """
        
        if startJsonItem is None:
            startJsonItem = self._transformedJsonDict
        
        currJsonItem = startJsonItem
        for (descriptorIdx, (itemType, itemKey)) in enumerate(pathKeyDescriptors[:-1]):
            if itemType == 'object':
                currJsonItem = currJsonItem[itemKey]
            elif itemType == 'array':
                restOfPath = pathKeyDescriptors[descriptorIdx + 1 :]
                for nextJsonItem in currJsonItem[itemKey]:
                    self._transformSchema(restOfPath, schemaClass, nextJsonItem)
                # since the call above handled the rest of the path for each
                # nextJsonItem, we are done here
                return
            else:
                raise ValueError(f"Unknown path list item type: {itemType}")

        (lastItemType, lastItemKey) = pathKeyDescriptors[-1]
        if lastItemType == 'object':
            self._deserializeSchema(currJsonItem, lastItemKey, schemaClass)
        elif lastItemType == 'array':
            if type(lastItemKey) is int:
                self._deserializeSchema(currJsonItem, lastItemKey, schemaClass)
            elif type(lastItemKey) is slice:
                sliceStart = lastItemKey.start if lastItemKey.start is not None else 0
                sliceEnd = lastItemKey.stop if lastItemKey.stop is not None else len(currJsonItem)
                sliceStep = lastItemKey.step if lastItemKey.step is not None else 1
                for schemaIdx in range(sliceStart, sliceEnd, sliceStep):
                    self._deserializeSchema(currJsonItem, schemaIdx, schemaClass)
            else:
                raise TypeError(f"An array cannot be accessed by a key of type {type(lastItemKey)}")
        else:
            raise ValueError(f"Unknown path list item type: {itemType}")

    def _deserializeSchema(self, jsonItem, keyToSchema, schemaClass: type[Schema]):
        try:
            jsonItem[keyToSchema] = schemaClass.fromSerialized(jsonItem[keyToSchema])
        except KeyError as err:
            jsonItem[keyToSchema]['__schema_deserialization_failed'] = {'cause': err}

