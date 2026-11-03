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

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from paas_wl.utils.models import SimpleUserIDWrapper
from paas_wl.workloads.networking.ingress.models import TxtFile

# Only the unreserved characters of URL (RFC 3986) are allowed
TXT_FILE_PATH_REGEX = r"^/[A-Za-z0-9._~-]+\.txt$"
# The content is written into the annotation and the nginx config, keep it small
MAX_CONTENT_BYTES = 4096
MAX_FILES_PER_ENV = 20


class TxtFileSLZ(serializers.ModelSerializer):
    """txt 校验文件，需要在 context 中提供 env 和 served_hosts（环境当前可用的域名）"""

    host = serializers.CharField(max_length=253, help_text="生效的域名，需为列表接口返回的 hosts 之一")
    path = serializers.RegexField(
        TXT_FILE_PATH_REGEX,
        max_length=128,
        help_text="访问路径，仅支持根目录下的 .txt 文件，如 /verify.txt",
        error_messages={"invalid": _("路径格式错误，仅支持根目录下的 .txt 文件，如 /verify.txt")},
    )
    content = serializers.CharField(trim_whitespace=False, help_text="文件内容，原样返回")
    remark = serializers.CharField(max_length=128, allow_blank=True, default="")
    operator = serializers.SerializerMethodField(help_text="最近一次修改的操作人")

    class Meta:
        model = TxtFile
        fields = ["id", "host", "path", "content", "remark", "operator", "updated"]
        read_only_fields = ["id", "updated"]
        # Uniqueness is validated in `validate` with a friendlier message
        validators: list = []

    def get_operator(self, obj: TxtFile) -> str:
        # The value is a raw user id instead of a wrapper before the object is reloaded from DB
        return SimpleUserIDWrapper(obj.operator).username if obj.operator else ""

    def validate_host(self, host: str) -> str:
        if host not in self.context["served_hosts"]:
            raise serializers.ValidationError(_("该域名不可用，仅支持已部署环境的子域名和路径为 / 的独立域名"))
        return host

    def validate_content(self, content: str) -> str:
        content = content.replace("\r\n", "\n")
        if "$" in content:
            raise serializers.ValidationError(_("内容不能包含 $ 字符"))
        if not all(c.isprintable() or c in "\n\t" for c in content):
            raise serializers.ValidationError(_("内容只能包含可打印字符"))
        if len(content.encode()) > MAX_CONTENT_BYTES:
            raise serializers.ValidationError(_("内容不能超过 {} 字节").format(MAX_CONTENT_BYTES))
        return content

    def validate(self, attrs):
        files = TxtFile.objects.filter(environment_id=self.context["env"].id)
        if self.instance:
            files = files.exclude(pk=self.instance.pk)
        elif files.count() >= MAX_FILES_PER_ENV:
            raise serializers.ValidationError(_("每个环境最多配置 {} 个 txt 文件").format(MAX_FILES_PER_ENV))

        # The location of nginx matches case-insensitively, so do the unique index of MySQL
        if files.filter(host=attrs["host"], path__iexact=attrs["path"]).exists():
            raise serializers.ValidationError({"path": _("该域名下已存在相同路径的文件")})
        return attrs


class TxtFileListSLZ(serializers.Serializer):
    supported = serializers.BooleanField(help_text="当前环境是否可能有可用的域名（子域名或根路径的独立域名）")
    hosts = serializers.ListField(child=serializers.CharField(), help_text="当前可配置的域名，环境未部署时为空")
    files = TxtFileSLZ(many=True)
