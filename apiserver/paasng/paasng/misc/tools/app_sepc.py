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
from typing import Any

from paasng.utils.camel_converter import snake_to_camel


def transform_app_desc_spec2_to_spec3(spec2):
    """
    转换应用描述文件 spec_version 2 到 specVersion 3.

    Args:
        spec2 (dict): 应用描述文件.

    Returns:
        dict: 转换后的应用描述文件.
    """
    spec3: OrderedDict[str, Any] = OrderedDict()

    spec3["specVersion"] = 3
    if "app_version" in spec2:
        spec3["appVersion"] = spec2["app_version"]

    if "app" in spec2:
        spec3["app"] = transform_app_section(spec2["app"])

    if "modules" in spec2:
        spec3["modules"] = transform_modules_section(spec2["modules"])
    elif "module" in spec2:
        # 只有一个 module 时, module 取代 modules 在顶层
        module = spec2["module"]
        module["name"] = "default"
        module["is_default"] = True
        spec3["modules"] = [transform_module(module)]

    return spec3


def transform_app_section(app):
    """
    转换 app

    Args:
        app (dict): app.

    Returns:
        dict: 转换后的 app.
    """
    return {
        snake_to_camel(key): transform_display_options(value) if key == "market" and isinstance(value, dict) else value
        for key, value in app.items()
    }


def transform_display_options(value):
    """
    转换 market display_options.
    嵌套字典的 key 转为驼峰格式

    Args:
        value (dict): spec2 格式的 display_options 字典.

    Returns:
        dict: 转换后的 display_options 字典.
    """
    return {
        snake_to_camel(mk): {snake_to_camel(dk): dv for dk, dv in mv.items()} if isinstance(mv, dict) else mv
        for mk, mv in value.items()
    }


def transform_modules_section(modules):
    """
    转换 modules

    Args:
        modules (dict): spec2 格式的 modules 字典.

    Returns:
        list: 转换后的 modules 列表.
    """
    return [transform_module({**module, "name": module_name}) for module_name, module in modules.items()]


def transform_module(module):
    """
    转换单个 module.

    Args:
        module (dict): module.

    Returns:
        OrderedDict: 转换后的 moudle.
    """
    new_module = OrderedDict()
    # module 基本信息
    new_module["name"] = module["name"]
    new_module["isDefault"] = module.get("is_default", False)

    # 处理 module 内容
    for key, value in module.items():
        if key in ["name", "is_default", "package_plans"]:
            continue
        new_key = snake_to_camel(key)
        if key in ["services", "env_variables", "processes", "scripts", "svc_discovery"]:
            # 收集这些到 module.spec
            if "spec" not in new_module:
                new_module["spec"] = OrderedDict()
            transform_module_spec(new_module["spec"], key, value)
        else:
            # 其他
            new_module[new_key] = value
    return new_module


def transform_module_spec(spec, key, value):
    """
    转换 module 的 ["services", "env_variables", "processes", "scripts", "svc_discovery"], 添加到 spec

    Args:
        spec (OrderDict): 存放 spec 信息的字典.
        key (str): spec 名称, 比如, services, env_variables.
        value (dcit): spec 内容, 比如 services 的内容.

    Returns:
        OrderedDict: 转换后的 moudle.
    """
    if key == "services":
        spec["addons"] = transform_services(value)
    elif key == "env_variables":
        spec["configuration"] = {"env": transform_env_variables(value)}
    elif key == "processes":
        spec["processes"] = transform_processes(value)
    elif key == "scripts":
        spec["hooks"] = {"preRelease": {"procCommand": value.get("pre_release_hook")}}
    elif key == "svc_discovery" and "bk_saas" in value:
        spec["svcDiscovery"] = {"bkSaaS": transform_bk_saas(value["bk_saas"])}


def transform_services(services):
    """
    转换 services.

    Args:
        services (list): services.

    Returns:
        list: 转换后的 services.
    """
    return [{snake_to_camel(k): v for k, v in service.items()} for service in services]


def transform_env_variables(env_vars):
    """
    转换 env_variables.

    Args:
        env_vars (list): spec2 格式的环境变量列表.

    Returns:
        list: 转换后的环境变量列表.
    """
    return [
        OrderedDict(("name" if k == "key" else snake_to_camel(k), v) for k, v in env_var.items())
        for env_var in env_vars
    ]


def transform_processes(processes):
    """
    转换 processes.

    Args:
        processes (dict): processes.

    Returns:
        list: 转换后的 processes.
    """
    return [transform_process(process_name, process_info) for process_name, process_info in processes.items()]


def transform_process(process_name, process_info):
    """
    转换单个process. 并添加services，如果名称是web，设置exposedType.

    Args:
        process_name (str): 进程名，比如 web.
        process_info (dict): 进程信息.

    Returns:
        OrderedDict: 转换后的 process.
    """
    transformed_process = OrderedDict([("name", process_name)])

    for key, value in process_info.items():
        if key == "command":
            transformed_process["procCommand"] = value
        elif key == "plan":
            transformed_process["resQuotaPlan"] = re.sub(r"\d+R", "", value)
        elif key == "probes":
            transformed_process["probes"] = transform_process_probes(value)
        else:
            transformed_process[snake_to_camel(key)] = value

    transformed_process["services"] = [create_service(process_name)]

    return transformed_process


def create_service(process_name):
    """
    创建给定进程名的services

    Args:
        process_name (str): 进程名.

    Returns:
        dict: service 信息.
    """
    if process_name == "web":
        service = {
            "name": process_name,
            "protocol": "TCP",
            "exposedType": {"name": "bk/http"},
            "targetPort": 5000,
            "port": 80,
        }
    else:
        service = {
            "name": process_name,
            "protocol": "TCP",
            "targetPort": 5000,
            "port": 80,
        }

    return service


def transform_process_probes(probes):
    """
    转换 process 的 probe.

    Args:
        probes (dict): probes.

    Returns:
        OrderedDict: 转换后的 probes.
    """
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


def transform_bk_saas(bk_saas):
    """
    转换 svc_discovery.bk_saas.

    Args:
        bk_saas (list): bk_saas.

    Returns:
        list: 转换后的 bk_saas.
    """
    return [
        {snake_to_camel(k): v for k, v in item.items()} if isinstance(item, dict) else {"bkAppCode": item}
        for item in bk_saas
    ]
