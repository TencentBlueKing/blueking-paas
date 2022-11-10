class ProcNotDeployed(Exception):
    """Try to operate processes of an not deployed application"""


class ProcNotFoundInRes(Exception):
    """Try to operate a process which did not exists in app model res"""
