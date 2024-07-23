from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.plat_admin.admin42.serializers.config_vars import (
    DefaultConfigVarCreateInputSLZ,
    DefaultConfigVarCreateOutputSLZ,
    DefaultConfigVarListOutputSLZ,
    DefaultConfigVarUpdateInputSLZ,
)
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.platform.engine.models.config_var import DefaultConfigVar


class DefaultConfigVarView(GenericTemplateView):
    name = "环境变量管理"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    template_name = "admin42/platformmgr/default_env.html"

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
