import json
import sys
import os


# /path/to/pyblitz/__init__.py
_moduleInitPath = sys.modules['pyblitz'].__file__

# /path/to/pyblitz
_moduleRootPath = os.path.normpath(os.path.join(_moduleInitPath, ".."))


def readOpenAPIFile(pathToJson):
    with open(pathToJson) as jsonFile:
        jsonDict = json.load(jsonFile)
    return jsonDict


def createFileFromRoot(filePath):
    if filePath[0] == "/":
        # prevents os.path.join treating this as an absolute path
        filePath = filePath[1:]
    filePath = os.path.normpath(filePath)
    filePath_onlyFolders = os.path.sep.join(filePath.split(os.path.sep)[:-1])
    os.makedirs(os.path.join(_moduleRootPath, filePath_onlyFolders), exist_ok=True)
    return open(os.path.join(_moduleRootPath, filePath), "w")
