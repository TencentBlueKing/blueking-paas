# -*- coding: utf-8 -*-


class EmptyAppIngressError(Exception):
    """Exception raised when trying to sync an ingress with no domains"""


class ValidCertNotFound(Exception):
    """When syncing a https domain, if we can not find a valid tls certificate. This exception
    is raised.
    """


class DefaultServiceNameRequired(Exception):
    """When trying to create a new ingress resource without a default service_name, this exception is
    raised
    """


class PersistentAppDomainRequired(Exception):
    """When performing some actions, a presistent(stored in database) AppDomain object is required,
    this includes generating an ingress name for a domain with customized subpath -- the primary key
    of AppDomain object is necessary part.
    """
