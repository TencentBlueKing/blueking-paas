# -*- coding: utf-8 -*-


class KubeException(Exception):
    def __init__(self, *args, **kwargs):
        self.extra_value = kwargs.get('extra_value', None)
        super().__init__(*args)


class ResourceDuplicate(KubeException):
    def __init__(self, resource, resource_name, *args, **kwargs):
        msg = f"{resource}(name={resource_name}) has already existed"
        super().__init__(msg, *args, **kwargs)


class ReadTargetStatusTimeout(KubeException):
    def __init__(self, pod_name, max_seconds, *args, **kwargs):
        msg = "Checking status of pod:%s has exceeded %s seconds, give up." % (pod_name, max_seconds)
        super().__init__(msg, *args, **kwargs)


class PodNotSucceededError(KubeException):
    """pod not succeeded"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reason = kwargs.get("reason", "")
        self.message = kwargs.get("message", "")
        self.exit_code = kwargs.get("exit_code", -1)


class PodNotSucceededAbsentError(PodNotSucceededError):
    """pod not succeeded triggered by pod's absence"""


class PodNotSucceededTimeoutError(PodNotSucceededError):
    """pod not succeeded triggered by timeout"""


class CreateServiceAccountTimeout(KubeException):
    def __init__(self, namespace, timeout, *args, **kwargs):
        msg = "Namespace:%s which didn't create service account in %s seconds" % (namespace, timeout)
        KubeException.__init__(self, msg, *args, **kwargs)


class ResourceMissing(KubeException):
    def __init__(self, namespace, name, *args, **kwargs):
        msg = "Resource: <%s/%s> missing" % (namespace, name)
        KubeException.__init__(self, msg, *args, **kwargs)


class ResourceDeleteTimeout(KubeException):
    def __init__(self, resource_type, namespace, name, *args, **kwargs):
        msg = f"{resource_type}<{namespace}/{name}> delete timeout"
        super().__init__(msg, *args, **kwargs)


class MapperNotInVersionError(Exception):
    """mapper is missing in this version"""
