# -*- coding: utf-8 -*-
import logging

from bkapi_client_core.esb import ESBClient, Operation, OperationGroup, bind_property
from bkapi_client_core.esb import generic_type_partial as _partial
from bkapi_client_core.esb.django_helper import get_client_by_username as _get_client_by_username

logger = logging.getLogger(__name__)


class MonitorV3Group(OperationGroup):
    # 快速创建APM应用
    apm_create_application = bind_property(
        Operation,
        name="apm_create_application",
        method="POST",
        path="/api/c/compapi{bk_api_ver}/monitor_v3/apm/create_application/",
    )


class Client(ESBClient):
    """ESB Components"""

    monitor_v3 = bind_property(MonitorV3Group, name="monitor_v3")


get_client_by_username = _partial(Client, _get_client_by_username)
