# -*- coding: utf-8 -*-
from rest_framework import serializers

from paas_wl.platform.applications.models import EngineApp
from paas_wl.platform.applications.models.managers.app_metadata import get_metadata
from paas_wl.platform.system_api.serializers import InstanceSerializer as _InstanceSerializer
from paas_wl.workloads.processes.drf_serializers import HumanizeDateTimeField
from paas_wl.workloads.processes.models import ProcessSpecPlan


class ProcessSpecBoundInfoSLZ(serializers.Serializer):
    id = serializers.CharField()
    app_code = serializers.SerializerMethodField()
    target_replicas = serializers.CharField(help_text="目标副本数")
    target_status = serializers.CharField(help_text="用户设置的目标状态")

    def get_app_code(self, data) -> str:
        engine_app = EngineApp.objects.get(pk=data.engine_app_id)
        return get_metadata(engine_app).get_paas_app_code()


class ProcessSpecPlanSLZ(serializers.ModelSerializer):
    created_humanized = HumanizeDateTimeField(source="created", read_only=True)
    updated_humanized = HumanizeDateTimeField(source="updated", read_only=True)
    limits = serializers.JSONField()
    requests = serializers.JSONField()
    instance_cnt = serializers.SerializerMethodField(help_text="使用该 plan 的 ProcessSpec 数量")

    def get_instance_cnt(self, obj):
        return obj.processspec_set.count()

    class Meta:
        model = ProcessSpecPlan
        fields = '__all__'


class InstanceSerializer(_InstanceSerializer):
    envs = serializers.DictField(child=serializers.CharField(), help_text="环境变量", required=False, default=dict)
