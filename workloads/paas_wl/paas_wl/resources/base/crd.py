# -*- coding: utf-8 -*-
from paas_wl.resources.base.kres import BaseKresource


class KServiceMonitor(BaseKresource):
    kind = "ServiceMonitor"


class BkApp(BaseKresource):
    """CRD: App model resource feature"""

    kind = 'BkApp'


class DomainGroupMapping(BaseKresource):
    """CRD: Mapping between BkApp and DomainGroups"""

    kind = 'DomainGroupMapping'
