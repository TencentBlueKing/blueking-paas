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

from rest_framework import serializers

from paasng.accessories.ci.constants import CIBackend
from paasng.accessories.ci.exceptions import NotSupportedCIBackend
from paasng.accessories.ci.managers import get_ci_manager_cls_by_backend
from paasng.accessories.ci.models import CIAtomJob
from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.serializers import DeploymentSLZ


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

    def get_detail(self, obj: CIAtomJob) -> dict:
        """get detail"""
        try:
            manager = get_ci_manager_cls_by_backend(obj.backend)
        # 兼容代码，TODO: 清理掉 tencent_ci 任务后删除
        except NotSupportedCIBackend:
            return {"url": ""}

        return {"url": manager.make_job_detail(obj)}

    def get_repo_info(self, obj: CIAtomJob) -> dict:
        """Get deployment's repo info as dict"""
        version_info = obj.deployment.get_version_info()
        revision = version_info.revision
        version_type = version_info.version_type
        version_name = version_info.version_name

        return {
            "source_type": obj.deployment.source_type,
            "type": version_type,
            "name": version_name,
            "url": obj.deployment.source_location,
            "revision": revision,
            "comment": obj.deployment.source_comment,
        }


class CodeCCDetailSerializer(serializers.Serializer):
    lastAnalysisTime = serializers.IntegerField(help_text="最近检查时间")
    rdIndicatorsScore = serializers.FloatField(help_text="综合得分/质量星级")
    codeSecurityScore = serializers.FloatField(help_text="代码安全得分")
    codeStyleScore = serializers.FloatField(help_text="代码规范得分")
    codeMeasureScore = serializers.FloatField(help_text="代码度量得分")
    lastAnalysisResultList = serializers.ListField(allow_null=True, help_text="代码检查详情")
    detailUrl = serializers.CharField(help_text="详情链接")
