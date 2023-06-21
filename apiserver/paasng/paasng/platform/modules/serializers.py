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
import string
from typing import Dict, Optional

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from pydantic import ValidationError as PDValidationError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paas_wl.cluster.serializers import ClusterSLZ
from paas_wl.cluster.shim import EnvClusterService
from paas_wl.cnative.specs.constants import ApiVersion
from paas_wl.cnative.specs.crd.bk_app import BkAppResource
from paas_wl.cnative.specs.models import to_error_string
from paasng.dev_resources.sourcectl.models import GitRepository, RepoBasicAuthHolder, SvnRepository
from paasng.dev_resources.sourcectl.serializers import RepositorySLZ
from paasng.dev_resources.sourcectl.validators import validate_image_url
from paasng.dev_resources.sourcectl.version_services import get_version_service
from paasng.dev_resources.templates.constants import TemplateType
from paasng.dev_resources.templates.models import Template
from paasng.engine.constants import RuntimeType
from paasng.platform.applications.utils import RE_APP_CODE
from paasng.platform.modules.constants import DeployHookType, SourceOrigin
from paasng.platform.modules.models import AppSlugBuilder, AppSlugRunner, BuildConfig, Module
from paasng.platform.modules.specs import ModuleSpecs
from paasng.utils.i18n.serializers import TranslatedCharField
from paasng.utils.serializers import SourceControlField, UserNameField
from paasng.utils.validators import DnsSafeNameValidator, ReservedWordValidator, validate_procfile


class ModuleNameField(serializers.RegexField):
    """Field for validating Module Name"""

    def __init__(self, regex=RE_APP_CODE, *args, **kwargs):
        preset_kwargs = dict(
            max_length=16,
            required=True,
            help_text='模块名称',
            validators=[ReservedWordValidator("模块名称"), DnsSafeNameValidator("模块名称")],
            error_messages={'invalid': _('格式错误，只能包含小写字母(a-z)、数字(0-9)和半角连接符(-)')},
        )
        preset_kwargs.update(kwargs)
        super().__init__(regex, *args, **preset_kwargs)


class ModuleSLZ(serializers.ModelSerializer):
    repo = RepositorySLZ(help_text="源码库信息", source="get_source_obj", allow_null=True)
    repo_auth_info = serializers.SerializerMethodField(help_text="仓库鉴权相关信息", required=False, allow_null=True)
    web_config = serializers.SerializerMethodField(help_text='模块配置信息，可用于驱动客户端功能')
    template_display_name = serializers.SerializerMethodField(help_text='初始化时使用的模板名称')
    source_origin = serializers.IntegerField(help_text='模块源码来源，例如 1 表示 Git 等代码仓库', source='get_source_origin')
    clusters = serializers.SerializerMethodField(help_text="模块下属各环境部署的集群信息")
    build_method = serializers.SerializerMethodField(help_text="镜像构建方式")

    def get_repo_auth_info(self, instance):
        if not isinstance(instance.get_source_obj(), (SvnRepository, GitRepository)):
            # 非源码仓库直接返回
            return {}

        try:
            basic_auth = RepoBasicAuthHolder.objects.get_by_repo(instance, instance.get_source_obj())
            return basic_auth.desensitized_info
        except ObjectDoesNotExist:
            return {}

    def get_web_config(self, obj) -> dict:
        return ModuleSpecs(obj).to_dict()

    def get_template_display_name(self, obj):
        if not obj.source_init_template:
            return ""

        try:
            return Template.objects.get(
                name=obj.source_init_template, type__in=TemplateType.normal_app_types()
            ).display_name
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
        exclude = ['source_repo_id', 'source_type']


class ModuleWithOwnerAndCreatorSLZ(serializers.ModelSerializer):
    creator = UserNameField(help_text="创建者", default=None)
    owner = UserNameField(help_text="拥有者", default=None)

    class Meta:
        model = Module
        fields = ['id', 'name', 'is_default', 'creator', 'owner']


class MinimalModuleSLZ(serializers.ModelSerializer):
    source_origin = serializers.IntegerField(source='get_source_origin')

    class Meta:
        model = Module
        fields = ['id', 'name', 'source_origin', 'is_default']


class ListModulesSLZ(serializers.Serializer):
    """Serializer for listing modules"""

    source_origin = serializers.ChoiceField(required=False, allow_null=True, choices=SourceOrigin.get_choices())


class CreateModuleSLZ(serializers.Serializer):
    """Serializer for create module"""

    name = ModuleNameField()
    source_init_template = serializers.CharField(help_text=_('模板名称'))
    source_origin = serializers.ChoiceField(choices=SourceOrigin.get_choices(), default=SourceOrigin.AUTHORIZED_VCS)
    source_control_type = SourceControlField(allow_blank=True, required=False, default=None)
    source_repo_url = serializers.CharField(allow_blank=True, required=False, default=None)
    source_repo_auth_info = serializers.JSONField(required=False, allow_null=True, default={})
    source_dir = serializers.CharField(required=False, default='', allow_blank=True)

    def validate_name(self, name):
        if Module.objects.filter(application=self.context['application'], name=name).exists():
            raise ValidationError(_("名称为 {} 的模块已存在").format(name))
        return name

    def validate_source_init_template(self, tmpl_name):
        # 创建模块的时候，只能使用普通应用模板
        if not Template.objects.filter(name=tmpl_name, type=TemplateType.NORMAL).exists():
            raise ValidationError(_('模板 {} 不可用').format(tmpl_name))
        return tmpl_name

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        source_origin = SourceOrigin(data["source_origin"])

        if source_origin == SourceOrigin.IMAGE_REGISTRY:
            data["source_repo_url"] = validate_image_url(
                data["source_repo_url"], region=self.context['application'].region
            )

        return data


class AppSlugBuilderMinimalSLZ(serializers.ModelSerializer):
    display_name = TranslatedCharField()
    description = TranslatedCharField()

    class Meta:
        model = AppSlugBuilder
        fields = ['id', 'name', 'display_name', 'description', 'image', 'tag']


class AppSlugRunnerMinimalSLZ(serializers.ModelSerializer):
    display_name = TranslatedCharField()
    description = TranslatedCharField()

    class Meta:
        model = AppSlugRunner
        fields = ['id', 'name', 'display_name', 'description', 'image', 'tag']


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
        if prefix.startswith(".") or prefix.startswith("-"):
            raise ValidationError("Tag can not startswith '.' or '-'")
        if forbidden_chars := set(prefix) - charset:
            raise ValidationError(f"Tag can not contain {sorted(forbidden_chars)}")
        return prefix


class ModuleSourceConfigSLZ(serializers.Serializer):
    """模块源码仓库/模板等信息"""

    source_init_template = serializers.CharField(required=False, default='', allow_blank=True)
    source_origin = serializers.ChoiceField(choices=SourceOrigin.get_choices(), default=SourceOrigin.AUTHORIZED_VCS)
    source_control_type = SourceControlField(allow_blank=True, required=False, default=None)
    source_repo_url = serializers.CharField(allow_blank=True, required=False, default=None)
    source_repo_auth_info = serializers.JSONField(required=False, allow_null=True, default={})
    source_dir = serializers.CharField(required=False, default='', allow_blank=True)

    def validate_source_init_template(self, tmpl_name):
        if not tmpl_name:
            return tmpl_name

        # 创建模块的时候，只能使用普通应用模板
        if not Template.objects.filter(name=tmpl_name, type=TemplateType.NORMAL).exists():
            raise ValidationError(_('模板 {} 不可用').format(tmpl_name))
        return tmpl_name


class ModuleBuildConfigSLZ(serializers.Serializer):
    """模块镜像构建信息"""

    image_repository = serializers.CharField(help_text="镜像仓库", read_only=True)
    build_method = serializers.ChoiceField(help_text="构建方式", choices=RuntimeType.get_choices(), required=True)
    tag_options = ImageTagOptionsSLZ(help_text="镜像 Tag 规则", required=False)

    # buildpack build 相关字段
    bp_stack_name = serializers.CharField(help_text="buildpack 构建方案的基础镜像名", allow_null=True, required=False)
    buildpacks = serializers.ListField(child=AppBuildPackMinimalSLZ(), allow_null=True, required=False)

    # docker build 相关字段
    dockerfile_path = serializers.CharField(help_text="Dockerfile 路径", allow_null=True, required=False)
    docker_build_args = serializers.DictField(
        child=serializers.CharField(allow_blank=False), allow_empty=True, allow_null=True, required=False
    )

    def validate(self, attrs):
        build_method = RuntimeType(attrs["build_method"])
        missed_params = []
        if build_method == RuntimeType.BUILDPACK:
            missed_params = [k for k in ['tag_options', 'buildpacks', 'bp_stack_name'] if not attrs.get(k)]
        elif build_method == RuntimeType.DOCKERFILE:
            missed_params = [k for k in ['tag_options', 'dockerfile_path', 'docker_build_args'] if not attrs.get(k)]
        if missed_params:
            raise ValidationError(
                detail={param: _('This field is required.') for param in missed_params}, code="required"
            )
        return attrs


class CreateCNativeModuleSLZ(serializers.Serializer):
    """Serializer for create cloud-native application's module"""

    name = ModuleNameField()
    source_config = ModuleSourceConfigSLZ(required=True, help_text=_('源码配置'))
    build_config = ModuleBuildConfigSLZ(required=True, help_text=_('构建配置'))
    manifest = serializers.JSONField(required=False, help_text=_('云原生应用 manifest'))

    def validate(self, attrs):
        build_cfg = attrs['build_config']

        # 如果托管方式为仅镜像，则应该设置 manifest
        if build_cfg['build_method'] == RuntimeType.CUSTOM_IMAGE:
            if not attrs.get('manifest'):
                raise ValidationError(_('云原生应用 manifest 不能为空'))

            source_cfg = attrs['source_config']
            # 检查 source_config 中 source_origin 类型必须为 IMAGE_REGISTRY
            if source_cfg['source_origin'] != SourceOrigin.IMAGE_REGISTRY:
                raise ValidationError(_('托管模式为仅镜像时，source_origin 必须为 IMAGE_REGISTRY'))

            try:
                bkapp_res = BkAppResource(**attrs['manifest'])
            except PDValidationError as e:
                raise ValidationError(to_error_string(e))

            if bkapp_res.apiVersion != ApiVersion.V1ALPHA2:
                raise ValidationError(_('请使用 BkApp v1alpha2 以支持多模块'))

            if bkapp_res.spec.build is None or bkapp_res.spec.build.image != source_cfg['source_repo_url']:
                raise ValidationError(_('Manifest 中定义的镜像信息与 source_repo_url 不一致'))

        return attrs

    def validate_name(self, name):
        if Module.objects.filter(application=self.context['application'], name=name).exists():
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
        slugbuilder: 'AppSlugBuilder' = self.context.get("slugbuilder")
        if not slugbuilder:
            return
        # NOTE: 按照约定, 相同 name 的 builder/runner 的基础镜像是一致的, 同时使用 display_name 字段存储的是 基础镜像 的信息
        # TODO: 使用专有的字段标记每个 builder/runner 的基础镜像
        return slugbuilder.display_name

    def get_image(self, instance):
        """从 AppSlugBuilder"""
        slugbuilder: 'AppSlugBuilder' = self.context.get("slugbuilder")
        if not slugbuilder:
            return
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

    def validate_procfile(self, data):
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
