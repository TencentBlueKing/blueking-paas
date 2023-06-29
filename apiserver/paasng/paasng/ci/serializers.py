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
from rest_framework import serializers

from paasng.ci.constants import CIBackend
from paasng.ci.exceptions import NotSupportedCIBackend
from paasng.ci.managers import get_ci_manager_cls_by_backend
from paasng.engine.constants import JobStatus
from paasng.engine.serializers import DeploymentSLZ


class CIAtomJobListSerializer(serializers.Serializer):
    backend = serializers.ChoiceField(choices=CIBackend.get_django_choices(), required=False)
    status = serializers.ChoiceField(choices=JobStatus.get_choices(), required=False)


class CIAtomJobSerializer(serializers.Serializer):
    status = serializers.CharField()
    backend = serializers.CharField()
    deployment = DeploymentSLZ()
    created = serializers.DateTimeField()
    build_id = serializers.CharField()
    output = serializers.CharField()
    repo_info = serializers.SerializerMethodField()
    detail = serializers.SerializerMethodField()

    def get_detail(self, obj) -> dict:
        """get detail"""
        try:
            manager = get_ci_manager_cls_by_backend(obj.backend)
        # 兼容代码，TODO: 清理掉 tencent_ci 任务后删除
        except NotSupportedCIBackend:
            return {"url": ""}

        return {"url": manager.make_job_detail(obj)}

    def get_repo_info(self, obj) -> dict:
        """Get deployment's repo info as dict"""
        version_type, version_name = obj.deployment.source_version_type, obj.deployment.source_version_name
        # Backward compatibility
        if not (version_type and version_name):
            version_name = obj.deployment.source_location.split('/')[-1]
            version_type = 'trunk' if version_name == 'trunk' else obj.deployment.source_location.split('/')[-2]

        return {
            'source_type': obj.deployment.source_type,
            'type': version_type,
            'name': version_name,
            'url': obj.deployment.source_location,
            'revision': obj.deployment.source_revision,
            'comment': obj.deployment.source_comment,
        }
