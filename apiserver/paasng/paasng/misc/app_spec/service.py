# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

import re
from collections import OrderedDict

from paasng.utils.camel_converter import snake_to_camel


def transform_spec2_to_spec3(spec2):
    """转换配置版本 spec2 到 spec3"""
    spec3 = OrderedDict()

    spec3["specVersion"] = 3
    if "app_version" in spec2:
        spec3["appVersion"] = spec2["app_version"]

    if "app" in spec2:
        spec3["app"] = _transform_app_section(spec2["app"])

    if "modules" in spec2:
        spec3["modules"] = _transform_modules_section(spec2["modules"])
    elif "module" in spec2:
        # 只有一个 module 时, module 取代 modules 在顶层
        module = spec2["module"]
        module["name"] = "default"
        module["is_default"] = True
        spec3["modules"] = [_transform_module(module)]  # type: ignore
    return spec3


def _transform_app_section(app):
    """转换 app 部分"""
    return {
        snake_to_camel(key): {
            snake_to_camel(mk): {snake_to_camel(dk): dv for dk, dv in mv.items()}
            if mk == "display_options" and isinstance(mv, dict)
            else mv
            for mk, mv in value.items()
        }
        if key == "market" and isinstance(value, dict)
        else value
        for key, value in app.items()
    }


def _transform_modules_section(modules):
    """转换 modules 部分"""
    return [_transform_module({**module, "name": module_name}) for module_name, module in modules.items()]


def _transform_module(module):
    """转换 modules 列表里的 module"""
    new_module = OrderedDict()
    new_module["name"] = module["name"]
    new_module["isDefault"] = module.get("is_default", False)

    # 处理 module 内容
    for key, value in module.items():
        if key in ["name", "is_default", "package_plans"]:
            # name 和 is_default 已设置, 新版没有package_plans
            continue
        new_key = snake_to_camel(key)
        if key in ["services", "env_variables", "processes", "scripts", "svc_discovery"]:
            # 收集这些到 module.spec
            if "spec" not in new_module:
                new_module["spec"] = OrderedDict()
            _transform_module_spec(new_module["spec"], key, value)
        else:
            # 其他
            new_module[new_key] = value
    return new_module


def _transform_module_spec(spec, key, value):
    """收集 ["services", "env_variables", "processes", "scripts", "svc_discovery"] 到 module.spec"""
    if key == "services":
        # 改为 addons 列表
        spec["addons"] = [{snake_to_camel(k): v for k, v in service.items()} for service in value]
    elif key == "env_variables":
        # 改为 configuration . env
        spec.setdefault("configuration", OrderedDict())["env"] = [
            OrderedDict(("name" if k == "key" else snake_to_camel(k), v) for k, v in env_var.items())
            for env_var in value
        ]
    elif key == "processes":
        # 改为 processes 列表
        spec["processes"] = [
            _transform_module_spec_process(proc_name, proc_info) for proc_name, proc_info in value.items()
        ]
    elif key == "scripts":
        # 改为 hooks . preRelease . procCommand
        spec["hooks"] = {"preRelease": {"procCommand": value["pre_release_hook"]}}
    elif key == "svc_discovery" and "bk_saas" in value:
        # 改为 svcDiscovery . bkSaaS
        bk_saas_list = [
            {snake_to_camel(k): v for k, v in item.items()} if isinstance(item, dict) else {"bkAppCode": item}
            for item in value["bk_saas"]
        ]
        spec["svcDiscovery"] = {"bkSaaS": bk_saas_list}


def _transform_module_spec_process(process_name, process_info):
    """转换 module.spec.processes"""
    services = {"name": process_name, "protocol": "TCP", "targetPort": 5000, "port": 80}
    if process_name == "web":
        services["exposedType"] = {"name": "bk/http"}

    return OrderedDict(
        [("name", process_name)]
        + [
            ("procCommand", pv)
            if pk == "command"
            # 去掉"R", e.g. convert "2C4G4R" to "2C4G"
            else ("resQuotaPlan", re.sub(r"\d+R", "", pv))
            if pk == "plan"
            else ("probes", _transform_module_spec_processes_probes(pv))
            if pk == "probes"
            else (snake_to_camel(pk), pv)
            for pk, pv in process_info.items()
        ]
        + [("services", [services])]
    )


def _transform_module_spec_processes_probes(probes):
    """转换 module.spec.processes.probes"""
    return OrderedDict(
        (
            probe_type,
            OrderedDict(
                (
                    snake_to_camel(pk),
                    (OrderedDict((snake_to_camel(k), v) for k, v in pv.items()) if isinstance(pv, dict) else pv),
                )
                for pk, pv in probe_content.items()
            ),
        )
        for probe_type, probe_content in probes.items()
    )
