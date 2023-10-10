# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from paasng.infras.iam.permissions.resources.application import AppAction, ApplicationPermission, AppPermCtx
from paasng.infras.accounts.models import User
from paasng.infras.accounts.permissions.application import can_exempt_application_perm
from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import global_site_resource
from paasng.platform.engine.models import EngineApp
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.modules.models import Module
from paasng.utils.basic import get_username_by_bkpaas_user_id

from .serializers import AppInstanceInfoSLZ

INST_TYPE_APPLICATION = 'application'
INST_TYPE_SITE = 'global_site'


def get_current_instances(user: User, path: str, include_perms_map: bool = True) -> List[Dict]:
    """Get current requested instances, instance types:

    - "application": this type includes application and related module info

    :param path: Requested path, only include proxied part
    :param include_perms_map: Whether include permission data
    :returns: List of instance info, structure: [{'type': 'application', 'value': ..., 'perms_map': ...}, ...]
    """
    obj_role = global_site_resource.get_role_of_user(user, None)
    site_role = obj_role.name
    site_inst = {'type': INST_TYPE_SITE, 'value': site_role.name.lower()}
    if include_perms_map:
        site_inst["perms_map"] = list_site_permissions(user)

    extracted_obj = ApplicationInPathExtractor().extract_objects(path)
    if not extracted_obj:
        return [site_inst]

    value = AppInstanceInfoSLZ(extracted_obj).data
    application_inst = {'type': INST_TYPE_APPLICATION, 'value': value}
    if include_perms_map:
        application_inst['perms_map'] = list_application_permissions(user, extracted_obj.application)
    return [application_inst, site_inst]


@dataclass
class ExtractedAppBasicInfo:
    """A simple model to store extracted application's info, in the format of basic types"""

    code: str
    module_name: Optional[str] = None
    environment: Optional[str] = None


@dataclass
class ExtractedAppInfo:
    """A model to store extracted application info"""

    application: Application
    module: Optional[Module] = None

    # Optional environment related fields
    module_env: Optional[ModuleEnvironment] = None
    engine_app: Optional[EngineApp] = None


class ApplicationInPathExtractor:
    """Extract application info from requested path"""

    _pattern_without_env = r'applications/(?P<code>[^/]+)(/modules/(?P<module_name>[^/]+))?/'
    _pattern_with_env = _pattern_without_env + r'envs/(?P<environment>stag|prod)/'

    RE_WITHOUT_ENV = re.compile(_pattern_without_env)
    RE_WITH_ENV = re.compile(_pattern_with_env)

    def extract_objects(self, request_path: str) -> Optional[ExtractedAppInfo]:
        """Try extract application and related objects from request_path

        :returns: `ExtractedAppInfo` object, None if no matches can be found.
        """
        info = self.extract_basic(request_path)
        if not info:
            return None

        try:
            application = Application.objects.get(code=info.code)
        except Application.DoesNotExist:
            return None

        module = None
        if info.module_name:
            try:
                module = application.modules.get(name=info.module_name)
            except Module.DoesNotExist:
                pass

        if module and info.environment:
            module_env = module.envs.get(environment=info.environment)
            engine_app = module_env.engine_app
        else:
            module_env, engine_app = None, None

        return ExtractedAppInfo(
            application=application,
            module=module,
            module_env=module_env,
            engine_app=engine_app,
        )

    def extract_basic(self, request_path: str) -> Optional[ExtractedAppBasicInfo]:
        """Try to extract application info from request_path, in the format of basic types

        :returns: `ExtractedAppBasicInfo` object, None if no matches can be found.
        """
        for re_obj in [self.RE_WITH_ENV, self.RE_WITHOUT_ENV]:
            obj = re_obj.search(request_path)
            if obj:
                return ExtractedAppBasicInfo(**obj.groupdict())
        return None


def list_application_permissions(user: User, obj: Application) -> Dict[str, bool]:
    """List user's all permissions on an application"""
    if can_exempt_application_perm(user, obj):
        return {action: True for action in AppAction}

    perm = ApplicationPermission()
    perm_ctx = AppPermCtx(code=obj.code, username=get_username_by_bkpaas_user_id(user.pk))

    return perm.resource_inst_multi_actions_allowed(
        username=perm_ctx.username,
        action_ids=list(AppAction),
        resources=perm.make_res_request(perm_ctx).make_resources(perm_ctx.resource_id),
    )


def list_site_permissions(user: User) -> Dict[SiteAction, bool]:
    """List user's all permissions on site"""
    role = global_site_resource.get_role_of_user(user, None)
    result = {}
    for action, _ in global_site_resource.permissions:
        result[action] = role.has_perm(action)
    return result
