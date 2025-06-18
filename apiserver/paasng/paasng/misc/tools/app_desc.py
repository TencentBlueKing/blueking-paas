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
from typing import Any, Dict, List, Union

from django.conf import settings

from paasng.utils.camel_converter import snake_to_camel


def transform_app_desc_spec2_to_spec3(spec2: Dict[str, Any]) -> OrderedDict[str, Any]:
    """
    Converts an application description file from spec_version 2 to specVersion 3 format.

    :param spec2: Application description in spec_version 2 format.
    :return: Transformed application description in specVersion 3 format.
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
        # When there is only one module, 'module' is at the first level as a dictionary
        module = spec2["module"]
        module["name"] = "default"
        spec3["module"] = transform_module(module)

    return spec3


def transform_app_section(app: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforms the 'app' section.

    :param app: The 'app' section from the spec_version 2 format.
    :return: Transformed 'app' section in specVersion 3 format.
    """
    return {
        snake_to_camel(key): transform_display_options(value) if key == "market" and isinstance(value, dict) else value
        for key, value in app.items()
    }


def transform_display_options(display_options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforms the 'displayOptions' section within 'market' in 'app'.

    :param display_options: The 'display_options' dictionary from spec_version 2 format.
    :return: Transformed 'displayOptions' dictionary in specVersion 3 format.
    """
    return {
        snake_to_camel(mk): {snake_to_camel(dk): dv for dk, dv in mv.items()} if isinstance(mv, dict) else mv
        for mk, mv in display_options.items()
    }


def transform_modules_section(modules: Dict[str, Dict[str, Any]]) -> List[OrderedDict[str, Any]]:
    """
    Transforms the 'modules' section.

    :param modules: The 'modules' section from the spec_version 2 format.
    :return: Transformed 'modules' section in specVersion 3 format.
    """
    return [transform_module({**module, "name": module_name}) for module_name, module in modules.items()]


def transform_module(module: Dict[str, Any]) -> OrderedDict[str, Any]:
    """
    Transforms a single module.

    :param module: The module from the spec_version 2 format.
    :return: Transformed module in specVersion 3 format.
    """
    new_module: OrderedDict[str, Any] = OrderedDict()

    new_module["name"] = module["name"]

    # Process the module content
    for key, value in module.items():
        if key in ["name", "package_plans"]:
            continue
        if key in ["services", "env_variables", "processes", "scripts", "svc_discovery", "bkmonitor"]:
            # Collect these into module.spec
            if "spec" not in new_module:
                new_module["spec"] = OrderedDict()
            transform_module_spec(new_module["spec"], key, value)
        else:
            # Others, such as is_default, source_dir, or language
            new_module[snake_to_camel(key)] = value

    return new_module


def transform_module_spec(spec: OrderedDict[str, Any], key: str, value: Any) -> None:
    """
    Transforms module fields like 'services', 'env_variables', 'processes', 'scripts', 'svc_discovery' and 'bkmonitor' into 'spec'.

    :param spec: The spec dictionary where the transformed data will be added.
    :param key: The name of the field (e.g., 'services', 'env_variables').
    :param value: The content of the field to be transformed.
    """
    if key == "services":
        spec["addons"] = transform_services(value)
    elif key == "env_variables":
        spec["configuration"] = {"env": transform_env_variables(value)}
    elif key == "processes":
        spec["processes"] = transform_processes(value)
    elif key == "scripts":
        spec["hooks"] = {"preRelease": {"procCommand": value["pre_release_hook"]}}
    elif key == "svc_discovery" and "bk_saas" in value:
        spec["svcDiscovery"] = {"bkSaaS": transform_bk_saas(value["bk_saas"])}
    elif key == "bkmonitor":
        metrics = tranform_bkmonitor(spec["processes"], value["port"])
        if metrics:
            spec["observability"] = {"monitoring": {"metrics": metrics}}


def transform_services(services: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Transforms the 'services' field of module.

    :param services: A list of services from spec_version 2 format.
    :return: Transformed list of services in specVersion 3 format.
    """
    return [{snake_to_camel(k): v for k, v in service.items()} for service in services]


def transform_env_variables(env_vars: List[Dict[str, Any]]) -> List[OrderedDict[str, Any]]:
    """
    Transforms the 'env_variables' field of module.

    :param env_vars: A list of environment variables from spec_version 2 format.
    :return: Transformed list of environment variables in specVersion 3 format.
    """
    return [
        OrderedDict(("name" if k == "key" else snake_to_camel(k), v) for k, v in env_var.items())
        for env_var in env_vars
    ]


def transform_processes(processes: Dict[str, Dict[str, Any]]) -> List[OrderedDict[str, Any]]:
    """
    Transforms the 'processes' field of module.

    :param processes: The 'processes' section from the spec_version 2 format.
    :return: Transformed list of processes in specVersion 3 format.
    """
    return [transform_process(process_name, process_info) for process_name, process_info in processes.items()]


def transform_process(process_name: str, process_info: Dict[str, Any]) -> OrderedDict[str, Any]:
    """
    Transforms a single process, adding associated service information.

    :param process_name: The name of the process (e.g., 'web', 'worker').
    :param process_info: The information about the process.
    :return: Transformed process information in specVersion 3 format.
    """
    transformed_process: OrderedDict[str, Any] = OrderedDict([("name", process_name)])

    for key, value in process_info.items():
        if key == "command":
            transformed_process["procCommand"] = value
        elif key == "plan":
            transformed_process["resQuotaPlan"] = re.sub(r"\d+R", "", value)
        elif key == "probes":
            transformed_process["probes"] = transform_process_probes(value)
        else:
            transformed_process[snake_to_camel(key)] = value

    if process_name == "web":
        transformed_process["services"] = [create_exposed_service()]

    return transformed_process


def create_exposed_service() -> Dict:
    """
    Creates service information for the web process.
    """

    return {
        "name": "web",
        "protocol": "TCP",
        "exposedType": {"name": "bk/http"},
        "targetPort": settings.CONTAINER_PORT,
        "port": 80,
    }


def transform_process_probes(probes: Dict[str, Dict[str, Any]]) -> OrderedDict[str, OrderedDict[str, Any]]:
    """
    Transforms the process probes in process.

    :param probes: The probes information.
    :return: Transformed probes information.
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


def transform_bk_saas(bk_saas: List[Union[Dict[str, Any], str]]) -> List[Dict[str, Any]]:
    """
    Transforms the 'bk_saas' section in 'svc_discovery' of module.

    :param bk_saas: The 'bk_saas' section from spec_version 2 format.
    :return: Transformed 'bkSaas' list in specVersion 3 format.
    """
    return [
        {snake_to_camel(k): v for k, v in item.items()} if isinstance(item, dict) else {"bkAppCode": item}
        for item in bk_saas
    ]


def tranform_bkmonitor(processes: List[OrderedDict[str, Any]], bkmonitor_port: int) -> List[Dict[str, str]]:
    """
    Transforms module field 'bkmonitor', add to process services as monitoring metric.

    :param processes: The transformed 'processes' in the specVersion 3 format.
    :param bkmonitor_port: The 'port' in 'bkmonitor' of module from spec_version 2 format.
    :return: Monitoring metrics list in specVersion 3 format.
    """
    for process in processes:
        if process["name"] == "web":
            process["services"].append(
                {"name": "metrics", "protocol": "TCP", "port": bkmonitor_port, "targetPort": bkmonitor_port}
            )
            return [{"process": "web", "serviceName": "metrics", "path": "/metrics"}]
    return []
