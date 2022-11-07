"""Serializer for third-party api"""
from rest_framework import serializers

from paasng.utils.i18n.serializers import I18NExtend, TranslatedCharField, i18n


class PluginTemplateSLZ(serializers.Serializer):
    """插件模板相关字段"""

    id = serializers.CharField()
    name = serializers.CharField()
    language = serializers.CharField()
    applicableLanguage = serializers.CharField(allow_null=True)
    repository = serializers.CharField()


@i18n
class PluginRequestSLZ(serializers.Serializer):
    """同步插件信息至第三方系统的请求体格式"""

    id = serializers.CharField()
    name = I18NExtend(serializers.CharField())
    template = PluginTemplateSLZ()
    extra_fields = serializers.DictField(allow_null=True, help_text="第三方系统声明的额外字段")
    repository = serializers.CharField(help_text="源码仓库")
    operator = serializers.CharField()


class PluginMarketRequestSLZ(serializers.Serializer):
    """同步插件市场信息至第三方系统的请求体格式"""

    category = serializers.CharField(allow_null=True)
    introduction = TranslatedCharField(allow_null=True)
    contact = serializers.CharField(allow_null=True, help_text="以分号(;)分割")
    extra_fields = serializers.DictField(allow_null=True, help_text="第三方系统声明的额外字段")
    operator = serializers.CharField()


class MarketCategorySLZ(serializers.Serializer):
    """插件市场-插件类别"""

    name = serializers.CharField()
    value = serializers.CharField()


class PluginReleaseVersionSLZ(serializers.Serializer):
    """插件发布版本的结构"""

    type = serializers.CharField(help_text="版本类型(正式/测试)")
    version = serializers.CharField(help_text="版本号")
    comment = serializers.CharField(help_text="版本日志")
    extra_fields = serializers.DictField(help_text="额外字段", default=dict)
    semver_type = serializers.CharField(help_text="语义化版本类型(相对于上一个版本而言)", allow_null=True)

    source_location = serializers.CharField(help_text="代码仓库地址")
    source_version_type = serializers.CharField(help_text="代码版本类型(branch/tag)")
    source_version_name = serializers.CharField(help_text="代码分支名/tag名")
    source_hash = serializers.CharField(help_text="代码提交哈希")


class DeployPluginRequestSLZ(serializers.Serializer):
    """插件部署操作的请求体格式"""

    plugin_id = serializers.CharField(help_text="插件id")
    version = PluginReleaseVersionSLZ(help_text="插件发布版本信息")
    operator = serializers.CharField(help_text="操作人")


class DeployStepSLZ(serializers.Serializer):
    """部署步骤的结构"""

    id = serializers.CharField(help_text="部署步骤id", source="name")
    name = serializers.CharField(help_text="部署步骤名称", source="display_name")
    start_time = serializers.DateTimeField(help_text="开始时间", allow_null=True)
    complete_time = serializers.DateTimeField(help_text="结束时间", allow_null=True)
    status = serializers.CharField(help_text="执行状态", allow_null=True)


class PluginDeployResponseSLZ(serializers.Serializer):
    """插件部署操作/检测部署状态的返回体格式"""

    deploy_id = serializers.CharField(help_text="部署操作id")
    status = serializers.CharField(allow_null=True, allow_blank=True)
    detail = serializers.CharField(allow_null=True, help_text="状态的具体信息")
    steps = DeployStepSLZ(many=True)


class PluginReleaseLogsResponseSLZ(serializers.Serializer):
    """插件发布日志的返回体格式"""

    finished = serializers.BooleanField(help_text="日志是否结束", default=False)
    logs = serializers.ListSerializer(child=serializers.CharField(help_text="日志内容", allow_null=True, allow_blank=True))
