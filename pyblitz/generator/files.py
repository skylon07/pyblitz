import json
import sys
import os


# /path/to/pyblitz/__init__.py
_moduleInitPath = sys.modules['pyblitz'].__file__

# /path/to/pyblitz
_moduleRootPath = os.path.normpath(os.path.join(_moduleInitPath, ".."))


def _readOpenAPIFile(pathToJson):
    """Given the path to a json file, this converts it into a python `dict`"""
    with open(pathToJson) as jsonFile:
        jsonDict = json.load(jsonFile)
    return jsonDict


def _createApiFile(filePath):
    """This function creates the api.py file at the given file path"""
    assert filePath[-3:] == ".py"
    return open(filePath, "w")
