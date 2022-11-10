# -*- coding: utf-8 -*-
"""Middlewares to cooperate with other PaaS services"""
from typing import Dict

import cattr
from attrs import asdict

from .struct_models import (
    Application,
    ApplicationPermissions,
    EngineAppPlain,
    InstancesInPlace,
    Module,
    ModuleEnv,
    PermissionsInPlace,
    SitePermissions,
)


class InstancesInPlaceMiddleware:
    """Read instances from token payloads, store them in current request as `request.insts_in_place`.
    Also process related permission data.
    """

    key_insts = 'insts'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.insts_in_place = InstancesInPlace()
        request.perms_in_place = PermissionsInPlace()

        payload = getattr(request, 'extra_payload', None)
        if not payload:
            return self.get_response(request)

        for data in payload.get(self.key_insts, []):
            load_insts_data(request.insts_in_place, request.perms_in_place, data)

        response = self.get_response(request)
        return response


INST_TYPE_APPLICATION = 'application'
INST_TYPE_SITE = 'global_site'


def load_insts_data(insts: InstancesInPlace, perms: PermissionsInPlace, data: Dict):
    """Load instances data in JSON format, will modify the given objects

    :param insts: InstancesInPlace object, will be modified
    :param perms: PermissionsInPlace object, will be modified
    """
    if data['type'] == INST_TYPE_APPLICATION:
        value = data['value']
        app = cattr.structure(value['application'], Application)
        insts.applications.append(app)

        if value.get('module'):
            module = cattr.structure({'application': asdict(app), **value['module']}, Module)
            insts.modules.append(module)
        if value.get('module_env'):
            module_env = cattr.structure(
                {'application': asdict(app), 'module': asdict(module), **value['module_env']}, ModuleEnv
            )
            insts.module_envs.append(module_env)
        if value.get('engine_app'):
            engine_app = cattr.structure({'application': asdict(app), **value['engine_app']}, EngineAppPlain)
            insts.engine_apps.append(engine_app)

        # load permissions data
        _perms_map = ApplicationPermissions(application=app, detail=data['perms_map'])
        perms.application_perms.append(_perms_map)

    elif data['type'] == INST_TYPE_SITE:
        value = data['value']
        perms.site_perms = SitePermissions(role=value, detail=data['perms_map'])
