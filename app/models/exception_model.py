# 自定义异常
class ShutdownSignalException(Exception):
    pass

class SigIntException(ShutdownSignalException):
    pass

class SigTermException(ShutdownSignalException):
    pass
