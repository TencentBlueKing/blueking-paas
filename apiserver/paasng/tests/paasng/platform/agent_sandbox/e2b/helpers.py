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

from paasng.platform.agent_sandbox.e2b.constants import E2BTemplateSyncStatus
from paasng.platform.agent_sandbox.e2b.template_sync.manifests import spec_digest
from paasng.platform.agent_sandbox.e2b.templates import make_custom_resource_name
from paasng.platform.agent_sandbox.models import E2BSandboxTemplate, E2BSandboxTemplateSyncRecord
from paasng.platform.applications.models import Application
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

IMAGE = "mirrors.example.com/e2b/envd:v1"


def mark_applied(
    template: E2BSandboxTemplate, cluster_name: str = CLUSTER_NAME_FOR_TESTING
) -> E2BSandboxTemplateSyncRecord:
    """当作模板的当前配置已下发到集群"""
    record, _ = E2BSandboxTemplateSyncRecord.objects.update_or_create(
        template=template,
        cluster_name=cluster_name,
        defaults={"status": E2BTemplateSyncStatus.SUCCEEDED.value, "digest": spec_digest(template)},
    )
    return record


def make_builtin_template(template_id: str = "e2b-envd", **overrides) -> E2BSandboxTemplate:
    """直接落库，不经过服务层，因此不会触发下发"""
    fields = {"name": template_id, "image": IMAGE, "cpu_count": 2, "memory_mb": 4096, "disk_size_mb": 20480}
    fields.update(overrides)
    return E2BSandboxTemplate.objects.create(template_id=template_id, resource_name=template_id, **fields)


def make_custom_template(application: Application, template_id: str = "my-tpl", **overrides) -> E2BSandboxTemplate:
    """直接落库，不经过服务层，因此不会触发下发"""
    fields = {"name": template_id, "image": IMAGE, "cpu_count": 2, "memory_mb": 4096, "disk_size_mb": 20480}
    fields.update(overrides)
    return E2BSandboxTemplate.objects.create(
        application=application,
        template_id=template_id,
        resource_name=make_custom_resource_name(application, template_id),
        tenant_id=application.tenant_id,
        **fields,
    )
