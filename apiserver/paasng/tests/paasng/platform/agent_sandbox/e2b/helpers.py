# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from paasng.platform.agent_sandbox.e2b.templates import make_custom_resource_name
from paasng.platform.agent_sandbox.models import E2BSandboxTemplate
from paasng.platform.applications.models import Application

IMAGE = "mirrors.example.com/e2b/envd:v1"


def make_builtin_template(template_id: str = "e2b-envd", **overrides) -> E2BSandboxTemplate:
    """直接落库，不经过服务层"""
    fields = {"name": template_id, "image": IMAGE, "cpu_count": 2, "memory_mb": 4096, "disk_size_mb": 20480}
    fields.update(overrides)
    return E2BSandboxTemplate.objects.create(template_id=template_id, resource_name=template_id, **fields)


def make_custom_template(application: Application, template_id: str = "my-tpl", **overrides) -> E2BSandboxTemplate:
    """直接落库，不经过服务层"""
    fields = {"name": template_id, "image": IMAGE, "cpu_count": 2, "memory_mb": 4096, "disk_size_mb": 20480}
    fields.update(overrides)
    return E2BSandboxTemplate.objects.create(
        application=application,
        template_id=template_id,
        resource_name=make_custom_resource_name(application, template_id),
        tenant_id=application.tenant_id,
        **fields,
    )
