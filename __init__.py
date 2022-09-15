from . import generator
del generator.createFileFromRoot
from . import http

try: 
    from . import api
except ImportError as error:
    if "api" in error.msg:
        # api needs generation; wrap dependent modules with errors
        class ErrorOnGetAttr:
            def __init__(self, moduleName):
                self._moduleName = moduleName
            
            def __getattribute__(self, name):
                validNames = ['_moduleName']
                if name in validNames:
                    return object.__getattribute__(self, name)
                
                moduleName = self._moduleName
                if moduleName == 'api':
                    raise RuntimeError("Module '{}' does not exist yet because it needs to be generated".format(moduleName))
                else:
                    raise RuntimeError("Module '{}' does not exist because it depends on module 'api', which is not yet generated".format(moduleName))
        
        api = ErrorOnGetAttr('api')
        del ErrorOnGetAttr
    else:
        raise error
