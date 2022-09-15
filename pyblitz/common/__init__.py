def convertDashesToCamelCase(string: str):
    strList = string.split("-")
    firstStr = strList.pop(0)
    return firstStr + "".join(
        capitalize(strAfterDash)
        for strAfterDash in strList
    )

def capitalize(string: str):
    return string[0].upper() + string[1:]
