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

from paasng.platform.applications.serializers import ApplicationWithDeployInfoSLZ


class DocumentSLZ(serializers.Serializer):
    url = serializers.URLField()
    title = serializers.CharField()
    source_type = serializers.CharField(default="bk_document", help_text="文档来源")


class DocumentSearchWordSLZ(serializers.Serializer):
    keyword = serializers.CharField(required=True)


class UniversalSearchSLZ(serializers.Serializer):
    """An universal search serializer"""

    keyword = serializers.CharField(required=True)
    limit = serializers.IntegerField(required=False, default=10)
    offset = serializers.IntegerField(required=False, default=0)


class SearchDocumentarySLZ(serializers.Serializer):
    """Serializer for SearchDocumentary object"""

    source_type = serializers.CharField(help_text="来源")
    title = serializers.CharField(help_text="文档标题")
    url = serializers.URLField(help_text="文档目标地址")
    digest = serializers.CharField(required=False, help_text="文档摘要，注意处理其中的高亮标签。为 null 时不展示")
    author_name = serializers.CharField(required=False, help_text="作者名称, 为 null 不展示")
    updated_at = serializers.DateTimeField(required=False, help_text="最近更新时间，为 null 不展示")


class AppSearchResultSLZ(serializers.Serializer):
    """Return applications as search result"""

    results = serializers.ListField(child=ApplicationWithDeployInfoSLZ(), help_text="结果应用列表")
    count = serializers.IntegerField(help_text="结果条目总数，配合参数里的 limit+offset 判断是否还有下一页")


class DocSearchResultSLZ(serializers.Serializer):
    """Return documentaries as search result"""

    results = serializers.ListField(child=SearchDocumentarySLZ(), help_text="结果文档列表")
    count = serializers.IntegerField(help_text="结果条目总数，配合参数里的 limit+offset 判断是否还有下一页")
