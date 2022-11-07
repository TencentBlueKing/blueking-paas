from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .constants import DeployStatus
from .models import AppModelDeploy, AppModelResource


class CreateAppModelResourceSerializer(serializers.Serializer):
    """[sys-api] 创建云原生架构应用 Serializer，支持简单字段，仅供“创建应用”时使用"""

    application_id = serializers.UUIDField(label=_('所属应用'))
    module_id = serializers.UUIDField(label=_('所属模块'), validators=[UniqueValidator(AppModelResource.objects.all())])
    code = serializers.CharField(label=_('所属应用 code'))
    image = serializers.CharField(label=_('容器镜像地址'), required=True)
    command = serializers.ListField(help_text='启动命令', child=serializers.CharField(), required=False, default=list)
    args = serializers.ListField(help_text='命令参数', child=serializers.CharField(), required=False, default=list)
    target_port = serializers.IntegerField(label=_('容器端口'), required=False)


class AppModelResourceSerializer(serializers.Serializer):
    """云原生架构应用 Serializer"""

    application_id = serializers.UUIDField(label=_('所属应用'))
    module_id = serializers.UUIDField(label=_('所属模块'))
    manifest = serializers.JSONField(label=_('BkApp 配置信息'), source='revision.json_value')


class CreateDeploySerializer(serializers.Serializer):
    """部署云原生应用 Serializer"""

    # TODO: 后续支持版本与部署分离，可以通过指定版本号的方式部署
    # 不提供时，使用应用当前 revision 所指向的 manifest 值
    manifest = serializers.JSONField(label=_('BkApp 配置信息'), required=False)


class QueryDeploysSerializer(serializers.Serializer):
    """Serializer for querying AppModelDeploy objects"""

    operator = serializers.CharField(label=_('操作者'), required=False)


class DeployDetailSerializer(serializers.ModelSerializer):
    """Serializer for representing detailed AppModelDeploy object"""

    manifest = serializers.JSONField(label=_('BkApp 配置信息'), source='revision.json_value')
    operator = serializers.CharField(source='operator.username')

    class Meta:
        model = AppModelDeploy
        exclude = ('module_id',)


class DeploySerializer(serializers.ModelSerializer):
    """Serializer for representing AppModelDeploy objects"""

    operator = serializers.CharField(source='operator.username')

    class Meta:
        model = AppModelDeploy
        exclude = ('module_id',)


class MresDeploymentStatusSLZ(serializers.Serializer):
    """Serializer for ModelResource deployment status"""

    deploy_id = serializers.IntegerField(help_text="部署ID", source="pk")
    status = serializers.ChoiceField(choices=DeployStatus.get_choices(), default=DeployStatus.UNKNOWN)
    reason = serializers.CharField(allow_blank=True)
    message = serializers.CharField(allow_blank=True)
    last_transition_time = serializers.DateTimeField()

    operator = serializers.CharField(source='operator.username', help_text="操作人")
    created = serializers.DateTimeField(help_text="发布时间")


class MresIngressInfoSLZ(serializers.Serializer):
    """Serializer for ModelResource Ingress info"""

    url = serializers.CharField(allow_null=True, allow_blank=True)


class MresConditionSLZ(serializers.Serializer):
    """Serializer for ModelResource Condition Field"""

    type = serializers.CharField()
    status = serializers.ChoiceField(choices=DeployStatus.get_choices(), default=DeployStatus.UNKNOWN)
    reason = serializers.CharField(allow_blank=True)
    message = serializers.CharField(allow_blank=True)


class MresStatusSLZ(serializers.Serializer):
    """Serializer for ModelResource status"""

    deployment = MresDeploymentStatusSLZ()
    ingress = MresIngressInfoSLZ()
    conditions = MresConditionSLZ(many=True)
