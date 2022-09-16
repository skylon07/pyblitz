def _convertDashesToCamelCase(string: str):
    strList = string.split("-")
    firstStr = strList.pop(0)
    return firstStr + "".join(
        _capitalize(strAfterDash)
        for strAfterDash in strList
    )

def _capitalize(string: str):
    return string[0].upper() + string[1:]
