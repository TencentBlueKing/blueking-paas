from typing import Dict

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.core.region.models import get_all_regions
from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.plat_admin.admin42.serializers.config_vars import (
    BuiltinConfigVarInputSLZ,
    DefaultConfigVarCreateInputSLZ,
    DefaultConfigVarCreateOutputSLZ,
    DefaultConfigVarListOutputSLZ,
    DefaultConfigVarUpdateInputSLZ,
)
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.platform.applications.constants import AppEnvironment
from paasng.platform.engine.configurations.config_var import (
    generate_env_vars_by_region_and_env,
    generate_env_vars_for_bk_platform,
)
from paasng.platform.engine.constants import (
    AppInfoBuiltinEnv,
    AppRunTimeBuiltinEnv,
    NoPrefixAppRunTimeBuiltinEnv,
)
from paasng.platform.engine.models.config_var import DefaultConfigVar, add_prefix_to_key


class DefaultConfigVarView(GenericTemplateView):
    name = "环境变量管理"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    template_name = "admin42/platformmgr/default_env.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["system_prefix"] = settings.CONFIGVAR_SYSTEM_PREFIX
        context["region_list"] = list(get_all_regions().keys())
        return context

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class DefaultConfigVarViewSet(viewsets.GenericViewSet):
    """环境变量管理 API 接口"""

    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    serializer_class = DefaultConfigVarCreateInputSLZ

    def list(self, request):
        return Response(
            DefaultConfigVarListOutputSLZ(DefaultConfigVar.objects.order_by("-updated_at"), many=True).data
        )

    def create(self, request):
        slz = DefaultConfigVarCreateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        config_var = DefaultConfigVar.objects.create(
            key=data["key"],
            value=data["value"],
            description=data["description"],
            updater=request.user.username,
        )

        output_slz = DefaultConfigVarCreateOutputSLZ(config_var)
        return Response(output_slz.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk):
        slz = DefaultConfigVarUpdateInputSLZ(data=request.data, context={"id": pk})
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        config_var = DefaultConfigVar.objects.get(pk=pk)
        config_var.key = data["key"]
        config_var.value = data["value"]
        config_var.description = data["description"]
        config_var.updater = request.user.username
        config_var.save(update_fields=["key", "value", "description", "updater", "updated_at"])

        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, pk):
        config_var = DefaultConfigVar.objects.get(pk=pk)
        config_var.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _get_enum_choices_dict(self, enum_obj) -> Dict[str, str]:
        return {field[0]: field[1] for field in enum_obj.get_choices()}

    def get_all_builtin_envs(self, request):
        """获取所有内置环境变量，包括应用基本信息、应用运行时信息和蓝鲸体系内平台地址，其中和应用相关的环境变量只显示变量名和描述"""
        env_dict = add_prefix_to_key(
            {
                **self._get_enum_choices_dict(AppInfoBuiltinEnv),
                **self._get_enum_choices_dict(AppRunTimeBuiltinEnv),
            },
            settings.CONFIGVAR_SYSTEM_PREFIX,
        )
        env_dict = {**env_dict, **self._get_enum_choices_dict(NoPrefixAppRunTimeBuiltinEnv)}

        bk_address_envs = generate_env_vars_for_bk_platform(settings.CONFIGVAR_SYSTEM_PREFIX)
        bk_address_envs_list = [env.to_dict() for env in bk_address_envs]

        slz = BuiltinConfigVarInputSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        region = slz.validated_data["region"]
        environment = AppEnvironment.PRODUCTION.value
        envs_by_region_and_env = generate_env_vars_by_region_and_env(
            region, environment, settings.CONFIGVAR_SYSTEM_PREFIX
        )
        envs_by_region_and_env_list = [env.to_dict() for env in envs_by_region_and_env]

        for env in bk_address_envs_list + envs_by_region_and_env_list:
            env_dict.update(env)

        return Response(env_dict)
