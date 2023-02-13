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

from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from paasng.dev_resources.sourcectl.models import RepositoryInstance, SvnAccount, SvnRepository
from paasng.dev_resources.sourcectl.source_types import get_sourcectl_type
from paasng.dev_resources.sourcectl.type_specs import BkSvnSourceTypeSpec
from paasng.utils.serializers import SourceControlField, UserNameField, VerificationCodeField

logger = logging.getLogger(__name__)


class RepositorySLZ(serializers.Serializer):
    """Serializer for svn repo"""

    # 在现在的逻辑里，每一个 Repo 对象的 server_name 等于 Module 对象的 repo_type 字段
    # source_type 和 type 字段是一样的，为了保证 source_type 名称的统一意义保持冗余
    source_type = serializers.CharField(help_text='源码类型名称', source='get_source_type')
    type = serializers.CharField(help_text='同 source_type', source="get_source_type")
    trunk_url = serializers.SerializerMethodField(
        method_name="get_repo_url",
        required=False,
        allow_null=True,
        help_text="[Deprecated] 仅限 SVN 源码系统使用",
    )
    repo_url = serializers.SerializerMethodField(help_text='源码仓库地址', required=False, allow_null=True)
    source_dir = serializers.CharField(
        source="get_source_dir", help_text="源码目录", read_only=True, allow_blank=True, allow_null=True
    )
    repo_fullname = serializers.CharField(source="get_repo_fullname", help_text='仓库名')
    diff_feature = serializers.SerializerMethodField(help_text='与“查看源码差异”功能有关的配置字段')
    linked_to_internal_svn = serializers.BooleanField(help_text='[Deprecated] 与 SVN 有关的保留字段', default=True)
    display_name = serializers.CharField(help_text='源码系统用于展示的名称', source="get_display_name")

    def to_representation(self, instance: RepositoryInstance):
        try:
            source_type = get_sourcectl_type(instance.get_source_type())
            setattr(instance, "linked_to_internal_svn", isinstance(source_type, BkSvnSourceTypeSpec))
        except KeyError:
            setattr(instance, "linked_to_internal_svn", False)

        return super().to_representation(instance)

    def get_repo_url(self, instance: RepositoryInstance):
        try:
            source_type = get_sourcectl_type(instance.get_source_type())
            if isinstance(source_type, BkSvnSourceTypeSpec) and isinstance(instance, SvnRepository):
                # NOTE: 目前前端在代码签出时, 获取的是 trunk 的地址. 这里以后可以统一成 get_repo_url
                return instance.get_trunk_url()
        except KeyError:
            pass
        return instance.get_repo_url()

    def get_diff_feature(self, instance: RepositoryInstance) -> dict:
        try:
            source_type = get_sourcectl_type(instance.get_source_type())
            return source_type.diff_feature.to_dict()
        except KeyError:
            return {}


class SVNAccountResponseSLZ(serializers.Serializer):
    account = serializers.CharField()
    user = serializers.CharField()
    region = serializers.CharField()
    id = serializers.IntegerField()
    password = serializers.CharField()


class SvnAccountSLZ(serializers.ModelSerializer):
    account = serializers.ReadOnlyField()
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    verification_code = VerificationCodeField(write_only=True, required=False, default='NEVER-MATCH')
    synced_from_paas20 = serializers.ReadOnlyField(help_text="账户信息是否来自Paas2.0")

    class Meta:
        model = SvnAccount
        fields = ('region', 'account', 'user', 'id', "verification_code", "synced_from_paas20")
        lookup_field = "id"


class SvnAccountCreateSLZ(serializers.ModelSerializer):
    account = serializers.ReadOnlyField()
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    validators = [
        UniqueTogetherValidator(
            queryset=SvnAccount.objects.all(), fields=('user', 'region'), message=u"用户在当前Region的SVN账号已经存在"
        )
    ]

    class Meta:
        model = SvnAccount
        fields = ('region', 'account', 'user', 'id')
        lookup_field = "id"


class AlternativeVersionSLZ(serializers.Serializer):
    name = serializers.CharField()
    type = serializers.CharField()
    revision = serializers.CharField()
    url = serializers.CharField()
    last_update = serializers.DateTimeField()
    message = serializers.CharField(help_text="tag description or commit message")

    extra = serializers.JSONField(default=dict)


class PageNumberPaginationSLZ(serializers.Serializer):
    page = serializers.IntegerField(min_value=1, required=True)
    page_size = serializers.IntegerField(min_value=1, required=False, default=100)


class RepoSLZ(serializers.Serializer):
    """这个 SLZ 用于 models.Repository, 而不是 GitRepository， SvnRepository"""

    fullname = serializers.CharField()
    description = serializers.CharField()
    avatar_url = serializers.CharField()
    web_url = serializers.CharField()
    http_url_to_repo = serializers.CharField()
    ssh_url_to_repo = serializers.CharField()
    created_at = serializers.DateTimeField()
    last_activity_at = serializers.DateTimeField()


class CommitLogSLZ(serializers.Serializer):
    message = serializers.CharField()
    revision = serializers.CharField()
    date = serializers.DateTimeField()
    author = serializers.CharField()
    changelist = serializers.ListField()


class RepoBackendModifySLZ(serializers.Serializer):
    """应用引擎相关参数"""

    source_control_type = SourceControlField(allow_blank=True, help_text="blank for docker registry")

    source_repo_url = serializers.CharField()
    source_repo_auth_info = serializers.JSONField(required=False, default={})
    source_dir = serializers.CharField(help_text="Procfile 所在目录, 如果是根目录可不填.", default="", allow_blank=True)


##########################
# 源码包相关的 serializers #
##########################
class SourcePackageSLZ(serializers.Serializer):
    id = serializers.IntegerField(help_text="主键")
    version = serializers.CharField(help_text="版本信息")
    package_name = serializers.CharField(help_text="源码包名称")
    package_size = serializers.CharField(help_text="源码包大小")
    sha256_signature = serializers.CharField(help_text="sha256数字签名")
    is_deleted = serializers.BooleanField(help_text="源码包是否已被清理")
    updated = serializers.DateTimeField(help_text="更新时间")
    created = serializers.DateTimeField(help_text="创建时间")
    operator = UserNameField(read_only=True, source="owner")


class SourcePackageUploadViaUrlSLZ(serializers.Serializer):
    package_url = serializers.URLField(help_text="源码包下载路径")
    version = serializers.CharField(help_text="源码包版本号", required=False, default=None)
    allow_overwrite = serializers.NullBooleanField(help_text="是否允许覆盖原有的源码包", default=False)


class SourcePackageUploadViaFileSLZ(serializers.Serializer):
    package = serializers.FileField(help_text="源码包文件")
    allow_overwrite = serializers.NullBooleanField(help_text="是否允许覆盖原有的源码包", default=False)
