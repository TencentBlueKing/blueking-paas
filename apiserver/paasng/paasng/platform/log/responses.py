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
import logging
from typing import Dict, Optional

from attrs import converters, define

from paasng.platform.log.exceptions import LogLineInfoBrokenError
from paasng.utils.es_log.models import LogLine, extra_field, field_extractor_factory

logger = logging.getLogger(__name__)


@define
class StandardOutputLogLine(LogLine):
    """标准输出日志结构
    :param region: [deprecated] app region
    :param app_code: [deprecated] app_code
    :param module_name: [deprecated] module_name
    :param environment: [deprecated] runtime environment(stag/prod)
    :param process_id: process_id
    :param stream: stream, such as "django", "celery", "stdout"
    :param pod_name: [required] pod_name, The name of the pod that logs are generated from.
    """

    region: Optional[str] = extra_field(converter=converters.optional(str))
    app_code: Optional[str] = extra_field(converter=converters.optional(str))
    module_name: Optional[str] = extra_field(converter=converters.optional(str))
    environment: Optional[str] = extra_field(converter=converters.optional(str))
    process_id: Optional[str] = extra_field(converter=converters.optional(str))
    stream: Optional[str] = extra_field(
        source=field_extractor_factory(field_key="stream", raise_exception=False), converter=converters.optional(str)
    )
    pod_name: str = extra_field(converter=str)


@define
class StructureLogLine(LogLine):
    """结构化日志结构
    :param region: [deprecated] app region
    :param app_code: [deprecated] app_code
    :param module_name: [deprecated] module_name
    :param environment: [deprecated] runtime environment(stag/prod)
    :param process_id: process_id
    :param stream: stream, such as "django", "celery", "stdout"
    """

    region: Optional[str] = extra_field(converter=converters.optional(str))
    app_code: Optional[str] = extra_field(converter=converters.optional(str))
    module_name: Optional[str] = extra_field(converter=converters.optional(str))
    environment: Optional[str] = extra_field(converter=converters.optional(str))
    process_id: Optional[str] = extra_field(converter=converters.optional(str))
    stream: Optional[str] = extra_field(
        source=field_extractor_factory(field_key="stream", raise_exception=False), converter=converters.optional(str)
    )


def get_engine_app_name(raw_log: Dict):
    if "engine_app_name" not in raw_log:
        raise LogLineInfoBrokenError("engine_app_name")
    # ingress 日志是从 serviceName 解析的 engine_app_name，下划线已经转换成 0us0
    return raw_log["engine_app_name"].replace("0us0", "_")


@define
class IngressLogLine(LogLine):
    """ingress 访问日志结构
    :param engine_app_name: [deprecated] engine_app_name

    :param method: [required] method, The HTTP method used in the request
    :param path: [required] path, The URL path of the request
    :param status_code: [required] status_code, The HTTP status code of the response
    :param response_time: [required] response_time, The response time in seconds
    :param client_ip: [required] client_ip, The IP address of the client
    :param bytes_sent: [required] bytes_sent, The number of bytes sent in the response
    :param user_agent: [required] user_agent, The user agent string of the client
    :param http_version: [required] http_version, The HTTP version used in the request
    """

    # [deprecated] 好像没有地方用到这个属性, 确定不需要就删了
    engine_app_name: Optional[str] = extra_field(source=get_engine_app_name, converter=converters.optional(str))

    method: Optional[str] = extra_field(converter=converters.optional(str))
    path: Optional[str] = extra_field(converter=converters.optional(str))
    status_code: Optional[int] = extra_field(converter=converters.optional(int))
    response_time: Optional[float] = extra_field(converter=converters.optional(float))
    client_ip: Optional[str] = extra_field(converter=converters.optional(str))
    bytes_sent: Optional[int] = extra_field(converter=converters.optional(int))
    user_agent: Optional[str] = extra_field(converter=converters.optional(str))
    http_version: Optional[str] = extra_field(converter=converters.optional(str))
