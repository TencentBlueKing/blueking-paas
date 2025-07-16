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

import string
from typing import Dict, Optional

import cattr
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paas_wl.infras.cluster.serializers import ClusterSLZ
from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.platform.applications.serializers.fields import DockerfilePathField, SourceDirField
from paasng.platform.bkapp_model.serializers import ModuleDeployHookSLZ as CNativeModuleDeployHookSLZ
from paasng.platform.bkapp_model.serializers import ModuleProcessSpecSLZ
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.modules import entities
from paasng.platform.modules.constants import DeployHookType, SourceOrigin
from paasng.platform.modules.models import AppSlugBuilder, AppSlugRunner, BuildConfig, Module
from paasng.platform.modules.models.build_cfg import ImageTagOptions
from paasng.platform.modules.specs import ModuleSpecs, SourceOriginSpecs
from paasng.platform.sourcectl.models import GitRepository, RepoBasicAuthHolder, SvnRepository
from paasng.platform.sourcectl.serializers import RepositorySLZ
from paasng.platform.sourcectl.validators import validate_image_url
from paasng.platform.sourcectl.version_services import get_version_service
from paasng.platform.templates.constants import TemplateType
from paasng.platform.templates.models import Template
from paasng.utils.i18n.serializers import TranslatedCharField
from paasng.utils.serializers import SourceControlField, UserNameField
from paasng.utils.validators import (
    RE_APP_CODE,
    DnsSafeNameValidator,
    ReservedWordValidator,
    validate_image_repo,
    validate_procfile,
    validate_repo_url,
)


def validate_build_method(build_method: RuntimeType, source_origin: SourceOrigin):
    """根据 SourceOrigin 校验 build_method"""
    origin_specs = SourceOriginSpecs.get(source_origin)
    if build_method not in origin_specs.supported_runtime_types():
        raise ValidationError(f"invalid build_method {build_method} when source is {source_origin}")


class ModuleNameField(serializers.RegexField):
    """Field for validating Module Name"""

    def __init__(self, regex=RE_APP_CODE, **kwargs):
        preset_kwargs = dict(
            max_length=16,
            required=True,
            help_text="模块名称",
            validators=[ReservedWordValidator("模块名称"), DnsSafeNameValidator("模块名称")],
            error_messages={
                "invalid": _("格式错误，只能包含小写字母(a-z)、数字(0-9)和半角连接符(-)，长度不超过 16 位")
            },
        )
        preset_kwargs.update(kwargs)
        super().__init__(regex, **preset_kwargs)


class ModuleSLZ(serializers.ModelSerializer):
    repo = RepositorySLZ(help_text="源码库信息", source="get_source_obj", allow_null=True)
    repo_auth_info = serializers.SerializerMethodField(help_text="仓库鉴权相关信息", required=False, allow_null=True)
    web_config = serializers.SerializerMethodField(help_text="模块配置信息，可用于驱动客户端功能")
    template_display_name = serializers.SerializerMethodField(help_text="初始化时使用的模板名称")
    source_origin = serializers.IntegerField(
        help_text="模块源码来源，例如 1 表示 Git 等代码仓库", source="get_source_origin"
    )
    clusters = serializers.SerializerMethodField(help_text="模块下属各环境部署的集群信息")
    creator = UserNameField()
    owner = UserNameField()

    def get_repo_auth_info(self, instance):
        if not isinstance(instance.get_source_obj(), (SvnRepository, GitRepository)):
            # 非源码仓库直接返回
            return {}

        try:
            basic_auth = RepoBasicAuthHolder.objects.get_by_repo(instance, instance.get_source_obj())
        except ObjectDoesNotExist:
            return {}
        else:
            return basic_auth.desensitized_info

    def get_web_config(self, obj) -> dict:
        return ModuleSpecs(obj).to_dict()

    def get_template_display_name(self, obj):
        if not obj.source_init_template:
            return ""

        try:
            return Template.objects.get(name=obj.source_init_template).display_name
        except ObjectDoesNotExist:
            # 可能存在远古模版，并不在当前模版配置中
            return ""

    def get_clusters(self, obj: Module) -> Dict:
        env_clusters = {}
        for env in obj.envs.all():
            try:
                cluster = EnvClusterService(env).get_cluster()
                env_clusters[env.environment] = ClusterSLZ(cluster).data
            except ObjectDoesNotExist:
                env_clusters[env.environment] = None
        return env_clusters

    def get_build_method(self, obj: Module):
        # 防止出现历史数据未绑定 BuildConfig 的情况
        build_config = BuildConfig.objects.get_or_create_by_module(obj)
        return build_config.build_method

    class Meta:
        model = Module
        exclude = ["source_repo_id", "source_type"]


class ModuleWithOwnerAndCreatorSLZ(serializers.ModelSerializer):
    creator = UserNameField(help_text="创建者", default=None)
    owner = UserNameField(help_text="拥有者", default=None)

    class Meta:
        model = Module
        fields = ["id", "name", "is_default", "creator", "owner"]


class MinimalModuleSLZ(serializers.ModelSerializer):
    source_origin = serializers.IntegerField(source="get_source_origin")

    class Meta:
        model = Module
        fields = ["id", "name", "source_origin", "is_default"]


class ListModulesSLZ(serializers.Serializer):
    """Serializer for listing modules"""

    source_origin = serializers.ChoiceField(required=False, allow_null=True, choices=SourceOrigin.get_choices())


class CreateModuleSLZ(serializers.Serializer):
    """Serializer for create module"""

    name = ModuleNameField()
    source_init_template = serializers.CharField(help_text=_("模板名称"))
    source_origin = serializers.ChoiceField(choices=SourceOrigin.get_choices(), default=SourceOrigin.AUTHORIZED_VCS)
    source_control_type = SourceControlField(allow_blank=True, required=False, default=None)
    source_repo_url = serializers.CharField(allow_blank=True, required=False, default=None)
    source_repo_auth_info = serializers.JSONField(required=False, allow_null=True, default={})
    source_dir = SourceDirField(help_text=_("构建目录"))

    def validate_name(self, name):
        if Module.objects.filter(application=self.context["application"], name=name).exists():
            raise ValidationError(_("名称为 {} 的模块已存在").format(name))
        return name

    def validate_source_init_template(self, tmpl_name):
        # 创建模块的时候，只能使用普通应用模板
        if not Template.objects.filter(name=tmpl_name, type=TemplateType.NORMAL).exists():
            raise ValidationError(_("模板 {} 不可用").format(tmpl_name))
        return tmpl_name

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        source_origin = SourceOrigin(data["source_origin"])

        if source_origin == SourceOrigin.IMAGE_REGISTRY:
            data["source_repo_url"] = validate_image_url(data["source_repo_url"])

        return data


class AppSlugBuilderMinimalSLZ(serializers.ModelSerializer):
    display_name = TranslatedCharField()
    description = TranslatedCharField()

    class Meta:
        model = AppSlugBuilder
        fields = ["id", "name", "display_name", "description", "image", "tag"]


class AppSlugRunnerMinimalSLZ(serializers.ModelSerializer):
    display_name = TranslatedCharField()
    description = TranslatedCharField()

    class Meta:
        model = AppSlugRunner
        fields = ["id", "name", "display_name", "description", "image", "tag"]


class AppBuildPackMinimalSLZ(serializers.Serializer):
    id = serializers.IntegerField()
    language = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    display_name = TranslatedCharField(read_only=True)
    description = TranslatedCharField(read_only=True)


class ModuleRuntimeSLZ(serializers.Serializer):
    image = serializers.CharField(max_length=64, allow_null=True)
    slugbuilder = AppSlugBuilderMinimalSLZ(allow_null=True)
    slugrunner = AppSlugRunnerMinimalSLZ(allow_null=True)
    buildpacks = serializers.ListField(child=AppBuildPackMinimalSLZ(), allow_null=True)


class ModuleRuntimeBindSLZ(serializers.Serializer):
    image = serializers.CharField(max_length=64, required=True)
    buildpacks_id = serializers.ListField(child=serializers.IntegerField(), required=False, default=list, min_length=0)


class RepositoryWithPermissionSLZ(RepositorySLZ):
    authorized = serializers.SerializerMethodField(default=False, help_text="是否已授权")

    def get_authorized(self, instance):
        try:
            return get_version_service(self.context["module"], self.context["user"]).touch()
        except Exception:
            return False


class ImageTagOptionsSLZ(serializers.Serializer):
    prefix = serializers.CharField(help_text="自定义前缀", allow_blank=False, allow_null=True, max_length=24)
    with_version = serializers.BooleanField(help_text="镜像Tag 是否带有分支/标签")
    with_build_time = serializers.BooleanField(help_text="镜像 Tag 是否带有构建时间")
    with_commit_id = serializers.BooleanField(help_text="镜像 Tag 是否带有提交ID(hash)")

    def validate_prefix(self, prefix: Optional[str]):
        charset = {*string.digits, *string.ascii_letters}
        if prefix is None:
            return None
        if prefix.startswith((".", "-")):
            raise ValidationError("Tag can not startswith '.' or '-'")
        if forbidden_chars := set(prefix) - charset:
            raise ValidationError(f"Tag can not contain {sorted(forbidden_chars)}")
        return prefix

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        return cattr.structure(data, ImageTagOptions)


class ModuleSourceConfigSLZ(serializers.Serializer):
    """模块源码仓库/模板等信息"""

    source_init_template = serializers.CharField(required=False, default="", allow_blank=True)
    source_origin = serializers.ChoiceField(choices=SourceOrigin.get_choices(), default=SourceOrigin.AUTHORIZED_VCS)
    source_control_type = SourceControlField(allow_blank=True, required=False, default=None)
    source_repo_url = serializers.CharField(allow_blank=True, required=False, default=None)
    source_repo_auth_info = serializers.JSONField(required=False, allow_null=True, default={})
    source_dir = SourceDirField(help_text="源码目录")
    auto_create_repo = serializers.BooleanField(required=False, default=False, help_text="是否由平台新建代码仓库")
    write_template_to_repo = serializers.BooleanField(
        required=False, default=False, help_text="是否将模板代码初始化到代码仓库中"
    )

    def validate_source_init_template(self, tmpl_name: str) -> str:
        if not tmpl_name:
            return tmpl_name

        filters = {"name": tmpl_name}
        # 插件应用还需要额外检查模板是否为插件专用的
        if self.parent.initial_data.get("is_plugin_app"):
            filters["type"] = TemplateType.PLUGIN

        if not Template.objects.filter(**filters).exists():
            raise ValidationError(_("模板 {} 不可用").format(tmpl_name))

        return tmpl_name

    def validate(self, attrs):
        source_repo_url = attrs.get("source_repo_url")

        # 由平台新建代码仓库，则源码仓库类型必填，且需要检查是否支持创建仓库
        if attrs["auto_create_repo"]:
            if not attrs.get("source_control_type"):
                raise ValidationError(_("新建代码仓库时，源码仓库类型不能为空"))
            # 由平台新建代码仓库，则用户填写的源码仓库地址无效
            if source_repo_url:
                raise ValidationError(_("新建代码仓库时，源码仓库地址无效"))

        if source_repo_url:
            self._validate_source_repo_url(source_repo_url, attrs["source_origin"])

        if attrs["write_template_to_repo"] and (not attrs.get("source_init_template")):
            raise ValidationError(_("将模板代码初始化到代码仓库中时，必须选择应用模板"))
        return attrs

    @staticmethod
    def _validate_source_repo_url(source_repo_url, source_origin):
        try:
            if source_origin == SourceOrigin.CNATIVE_IMAGE:
                validate_image_repo(source_repo_url)
            else:
                validate_repo_url(source_repo_url)
        except ValueError as e:
            raise ValidationError({"source_repo_url": str(e)})


class ModuleBuildConfigSLZ(serializers.Serializer):
    """模块镜像构建信息"""

    build_method = serializers.ChoiceField(help_text="构建方式", choices=RuntimeType.get_choices(), required=True)
    tag_options = ImageTagOptionsSLZ(help_text="镜像 Tag 规则", required=False)

    # buildpack build 相关字段
    bp_stack_name = serializers.CharField(help_text="buildpack 构建方案的基础镜像名", required=False, allow_null=True)
    buildpacks = serializers.ListField(child=AppBuildPackMinimalSLZ(), required=False, allow_null=True)

    # docker build 相关字段
    dockerfile_path = DockerfilePathField(help_text="Dockerfile 路径", required=False)
    docker_build_args = serializers.DictField(
        child=serializers.CharField(allow_blank=False), allow_empty=True, allow_null=True, required=False
    )

    # 源码构建（buildpack / dockerfile）产出的镜像的仓库地址
    env_image_repositories = serializers.JSONField(help_text="环境镜像仓库", required=False, allow_null=True)

    # custom image（纯镜像）专用字段
    image_repository = serializers.CharField(help_text="镜像仓库", required=False, allow_null=True)
    image_credential_name = serializers.CharField(help_text="镜像凭证名称", required=False, allow_null=True)

    # 高级选项：通过蓝盾流水线构建
    use_bk_ci_pipeline = serializers.BooleanField(help_text="是否使用蓝盾流水线构建", default=False)

    def validate(self, attrs):
        build_method = RuntimeType(attrs["build_method"])
        missed_params = []
        if build_method == RuntimeType.BUILDPACK:
            missed_params = [k for k in ["tag_options", "buildpacks", "bp_stack_name"] if attrs.get(k, None) is None]
        elif build_method == RuntimeType.DOCKERFILE:
            missed_params = [k for k in ["tag_options", "docker_build_args"] if attrs.get(k, None) is None]
        elif build_method == RuntimeType.CUSTOM_IMAGE:
            missed_params = [k for k in ["image_repository"] if attrs.get(k, None) is None]
        if missed_params:
            raise ValidationError(
                detail={param: _("This field is required.") for param in missed_params}, code="required"
            )

        if image_repository := attrs.get("image_repository"):
            try:
                validate_image_repo(image_repository)
            except ValueError as e:
                raise ValidationError({"image_repository": str(e)})

        return attrs

    def validate_use_bk_ci_pipeline(self, use_bk_ci_pipeline: bool) -> bool:
        if use_bk_ci_pipeline and not (settings.BK_CI_PAAS_PROJECT_ID and settings.BK_CI_BUILD_PIPELINE_ID):
            raise ValidationError("build image with bk_ci pipeline unsupported")

        return use_bk_ci_pipeline


class ImageCredentialSLZ(serializers.Serializer):
    """镜像凭证相关参数"""

    name = serializers.CharField(required=True)
    username = serializers.CharField(required=False)
    password = serializers.CharField(required=False)


class CreateModuleBuildConfigSLZ(serializers.Serializer):
    """Serializer for create module build config"""

    build_method = serializers.ChoiceField(help_text="构建方式", choices=RuntimeType.get_choices(), required=True)
    tag_options = ImageTagOptionsSLZ(help_text="镜像 Tag 规则", required=False)

    # docker build 相关字段
    dockerfile_path = DockerfilePathField(help_text="Dockerfile 路径", required=False)
    docker_build_args = serializers.DictField(
        child=serializers.CharField(allow_blank=False), allow_empty=True, allow_null=True, required=False
    )

    image_repository = serializers.CharField(help_text="镜像仓库", required=False, allow_null=True)
    image_credential = ImageCredentialSLZ(required=False, help_text=_("镜像凭证信息"))

    def to_internal_value(self, data) -> entities.BuildConfig:
        data = super().to_internal_value(data)
        return entities.BuildConfig(
            build_method=data["build_method"],
            tag_options=data.get("tag_options", ImageTagOptions()),
            dockerfile_path=data.get("dockerfile_path"),
            docker_build_args=data.get("docker_build_args"),
            image_repository=data.get("image_repository"),
            image_credential=data.get("image_credential"),
        )

    def validate(self, attrs):
        if attrs.build_method == RuntimeType.CUSTOM_IMAGE and not attrs.image_repository:
            raise ValidationError("image-based cloud-native application module requires a image_repository parameter")
        return attrs


class BkAppSpecSLZ(serializers.Serializer):
    """Serializer for create bkapp spec of module"""

    build_config = CreateModuleBuildConfigSLZ(required=True, help_text=_("构建配置"))
    processes = serializers.ListField(child=ModuleProcessSpecSLZ(), required=False)
    hook = CNativeModuleDeployHookSLZ(allow_null=True, default=None)

    def validate(self, attrs):
        attrs = super().validate(attrs)

        build_config = attrs["build_config"]
        if build_config.build_method == RuntimeType.CUSTOM_IMAGE and not attrs.get("processes"):
            raise ValidationError("image-based cloud-native application module requires a processes parameter")

        return attrs


class CreateCNativeModuleSLZ(serializers.Serializer):
    """Serializer for create cloud-native application's module"""

    name = ModuleNameField()
    source_config = ModuleSourceConfigSLZ(required=True, help_text=_("源码配置"))
    bkapp_spec = BkAppSpecSLZ()

    def validate(self, attrs):
        attrs = super().validate(attrs)

        source_config = attrs["source_config"]
        build_config = attrs["bkapp_spec"]["build_config"]

        validate_build_method(build_config.build_method, source_config["source_origin"])

        if (
            build_config.build_method == RuntimeType.CUSTOM_IMAGE
            and build_config.image_repository != source_config.get("source_repo_url")
        ):
            raise ValidationError("image_repository is not consistent with source_repo_url")

        return attrs

    def validate_name(self, name):
        if Module.objects.filter(application=self.context["application"], name=name).exists():
            raise ValidationError(_("名称为 {} 的模块已存在").format(name))
        return name


class ModuleRuntimeOverviewSLZ(serializers.Serializer):
    """模块运行时概览-序列化器"""

    repo = RepositoryWithPermissionSLZ(help_text="模块仓库信息")
    stack = serializers.SerializerMethodField(allow_null=True, help_text="基础镜像")
    image = serializers.SerializerMethodField(allow_null=True, help_text="当前镜像")
    language = serializers.CharField(help_text="模块语言")
    source_origin = serializers.SerializerMethodField(help_text="源码来源")
    buildpacks = serializers.ListField(child=AppBuildPackMinimalSLZ(), allow_null=True)

    def get_stack(self, instance):
        """从 AppSlugBuilder 的 display_name 获取基础镜像"""
        slugbuilder: "AppSlugBuilder" = self.context.get("slugbuilder")
        if not slugbuilder:
            return None
        # NOTE: 按照约定, 相同 name 的 builder/runner 的基础镜像是一致的, 同时使用 display_name 字段存储的是 基础镜像 的信息
        # TODO: 使用专有的字段标记每个 builder/runner 的基础镜像
        return slugbuilder.display_name

    def get_image(self, instance):
        """从 AppSlugBuilder"""
        slugbuilder: "AppSlugBuilder" = self.context.get("slugbuilder")
        if not slugbuilder:
            return None
        return slugbuilder.name

    def get_source_origin(self, instance):
        module = self.context["module"]
        return module.get_source_origin()


class ModuleDeployHookSLZ(serializers.Serializer):
    type = serializers.ChoiceField(help_text="hook 类型", choices=DeployHookType.get_choices())
    command = serializers.CharField(help_text="指令")
    enabled = serializers.BooleanField(help_text="是否开启", read_only=True)

    def validate_command(self, data: str):
        if data.startswith("start "):
            raise serializers.ValidationError(_("指令不能以 'start ' 开头."))
        return data


class ProcfileSLZ(serializers.Serializer):
    name = serializers.CharField(help_text="命令名称, 只能包含字母、数字、连接符(-), 且不能以连字符(-)开头")
    command = serializers.CharField(help_text="启动指令, 不能以 'start ' 开头.")

    def validate_command(self, data: str):
        if data.startswith("start "):
            raise serializers.ValidationError(_("指令不能以 'start ' 开头."))
        return data


class ModuleDeployProcfileSLZ(serializers.Serializer):
    procfile = serializers.ListField(child=ProcfileSLZ(), default=list)

    def validate_procfile(self, data) -> Dict[str, str]:
        """validate and convert the format of procfile"""
        procfile = {proc_data["name"]: proc_data["command"] for proc_data in data}
        return validate_procfile(procfile)

    def to_representation(self, instance: dict):
        """convert Dict-format procfile to List-format"""
        if isinstance(instance, dict):
            instance["procfile"] = [{"name": k, "command": v} for k, v in instance["procfile"].items()]
        else:
            setattr(
                instance, "procfile", [{"name": k, "command": v} for k, v in getattr(instance, "procfile").items()]
            )
        return super().to_representation(instance)


class ModuleDeployConfigSLZ(ModuleDeployProcfileSLZ):
    """模块部署配置-序列化器"""

    hooks = ModuleDeployHookSLZ(many=True)
