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
"""Adaptor to transform Application to StructuredApp

TODO: remove me!!! After fully refract workloads modules!!!
This is only a **temporary** adaption for workloads code.
"""
from typing import Iterable

from paas_wl.platform.applications.struct_models import AppSubResourceDescriptor, StructuredApp
from paasng.platform.applications.models import Application


def to_structured(application: Application) -> 'StructuredApp':
    """Make a structured application(with modules and envs) from a pure Application object

    :raise: ValueError when application can not be found
    """

    return StructuredApp.from_json_data(
        {
            "application": {
                "id": str(application.pk),
                "type": application.type,
                "region": application.region,
                "code": application.code,
                "name": application.name,
            },
            "modules": [{"id": module.pk, "name": module.name} for module in application.modules.all()],
            "envs": [
                {
                    "module_id": str(env.module.pk),
                    "id": str(env.pk),
                    "environment": env.environment,
                    "engine_app_id": str(env.engine_app_id),
                    "is_offlined": env.is_offlined,
                }
                for env in application.envs.all()
            ],
        }
    )


def set_model_structured(obj: object, application: Application):
    """Initialize an object with structured application data

    :param obj: Any valid data object which belongs to a single Application, multiple object supported
    :param application: The `Application` object which was used for initialization
    """
    data_source_name = AppSubResourceDescriptor.data_source_name
    if hasattr(obj, data_source_name):
        return
    setattr(obj, data_source_name, to_structured(application))


def set_many_model_structured(objs: Iterable[object], application: Application):
    """Initialize many objects with structured application data, the objs must
    share same application"""
    data_source_name = AppSubResourceDescriptor.data_source_name
    # Query for structured application only once
    struct_app = to_structured(application)
    for obj in objs:
        if hasattr(obj, data_source_name):
            return
        setattr(obj, data_source_name, struct_app)
