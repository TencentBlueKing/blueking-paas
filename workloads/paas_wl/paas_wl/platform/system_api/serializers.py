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
import datetime
import re
from typing import TYPE_CHECKING

from django.conf import settings
from rest_framework import serializers

from paas_wl.monitoring.metrics.constants import MetricsResourceType, MetricsSeriesType
from paas_wl.monitoring.metrics.utils import MetricSmartTimeRange
from paas_wl.networking.ingress.utils import get_service_dns_name
from paas_wl.platform.applications import models
from paas_wl.utils.models import validate_procfile
from paas_wl.workloads.processes.models import Instance

if TYPE_CHECKING:
    from paas_wl.workloads.processes.models import Process

# proc type name is alphanumeric
# https://docs-v2.readthedocs.io/en/latest/using-workflow/process-types-and-the-procfile/#declaring-process-types
PROCTYPE_MATCH = re.compile(r'^(?P<type>[a-zA-Z0-9]+(\-[a-zA-Z0-9]+)*)$')
MEMLIMIT_MATCH = re.compile(r'^(?P<mem>(([0-9]+(MB|KB|GB|[BKMG])|0)(/([0-9]+(MB|KB|GB|[BKMG])))?))$', re.IGNORECASE)
CPUSHARE_MATCH = re.compile(r'^(?P<cpu>(([-+]?[0-9]*\.?[0-9]+[m]?)(/([-+]?[0-9]*\.?[0-9]+[m]?))?))$')
TAGVAL_MATCH = re.compile(r'^(?:[a-zA-Z\d][-\.\w]{0,61})?[a-zA-Z\d]$')
CONFIGKEY_MATCH = re.compile(r'^[a-z_]+[a-z0-9_]*$', re.IGNORECASE)


class AppAlreadyExistsError(Exception):
    """raised when trying to create an already existed app"""


class AppSerializer(serializers.ModelSerializer):
    """Serialize a class`~api.models.App` model."""

    owner = serializers.ReadOnlyField()
    structure = serializers.JSONField(required=False)

    class Meta:
        model = models.App
        fields = ['uuid', 'owner', 'region', 'name', 'structure', 'created', 'updated', 'type']

    def get_unique_together_validators(self):
        """By default, this serializer will use a default unique validator which validates region
        and name fields. However, this default behaviour will make it hard to distinguish unless
        making a string check on its error message.

        In order to fix this, we will disable this default behaviour and do a manually validation
        instead.
        """
        return []

    def validate(self, data):
        # Manually validate if app with the same name already exists
        if models.App.objects.filter(region=data['region'], name=data['name']).exists():
            raise AppAlreadyExistsError(f'app {data["name"]} already exists')
        return data


class ConfigSerializer(serializers.ModelSerializer):
    """Serialize a class`~api.models.Config` model."""

    owner = serializers.ReadOnlyField()
    app = serializers.SlugRelatedField(slug_field='uuid', queryset=models.App.objects.all())
    values = serializers.JSONField(required=False)
    resource_requirements = serializers.JSONField(required=False)
    node_selector = serializers.JSONField(required=False)
    image = serializers.CharField(required=False, allow_null=True)
    cluster = serializers.CharField(required=False, allow_null=True)
    metadata = serializers.JSONField(required=False)

    def validate_image(self, data):
        return data or settings.DEFAULT_SLUGRUNNER_IMAGE

    class Meta:
        model = models.Config
        exclude = ("runtime",)


class ConfigUpdateSerializer(serializers.Serializer):
    """Serializer for update_config"""

    metadata = serializers.JSONField(required=False, allow_null=True)
    cluster = serializers.CharField(required=False, allow_null=True, help_text="App cluster name")
    image = serializers.CharField(required=False, allow_null=True)
    runtime = serializers.JSONField(required=False, allow_null=True, help_text="RuntimeConfig")


class BuildSerializer(serializers.ModelSerializer):
    """Serialize a class`~api.models.Build` model."""

    owner = serializers.ReadOnlyField()
    app = serializers.SlugRelatedField(slug_field='uuid', queryset=models.App.objects.all())
    procfile = serializers.JSONField(required=False, validators=[validate_procfile])

    class Meta:
        model = models.Build
        fields = ['owner', 'app', 'slug_path', 'branch', 'revision', 'procfile', 'created', 'updated', 'uuid']

    def validate_procfile(self, data):
        for key, value in data.items():
            if value is None or value == "":
                raise serializers.ValidationError("Command can't be empty for process type")

            if not re.match(PROCTYPE_MATCH, key):
                raise serializers.ValidationError("Process types can only contain alphanumeric")

        return data


class PlaceHolderBuildSerializer(BuildSerializer):
    """Simply Serialize a class`~api.models.Build` model"""

    env_variables = serializers.JSONField(required=False)

    class Meta:
        model = models.Build
        fields = ['owner', 'app', 'procfile', 'env_variables', 'created', 'updated', 'uuid']


###########
# Release #
###########
class CreateReleaseSerializer(serializers.Serializer):
    build = serializers.CharField(required=True)
    deployment_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="deployment_id will be used to initialize stream channel and call the `finish_release` api",
    )
    procfile = serializers.JSONField(required=True, validators=[validate_procfile])
    extra_envs = serializers.JSONField(required=False, default=dict)


class ReleaseSerializer(serializers.ModelSerializer):
    build = serializers.CharField(required=True)

    class Meta:
        model = models.Release
        fields = ['uuid', 'build', 'failed', 'summary', 'version']
        read_only_fields = ['failed', 'summary', 'version']


class ReleaseResultSerializer(serializers.ModelSerializer):
    failed = serializers.BooleanField(required=True)
    lines = serializers.ListField(read_only=True)

    class Meta:
        model = models.Release
        fields = ['uuid', 'failed', 'summary', 'lines']


################
# BuildProcess #
################
class CreateBuildProcessBuildpacksSerializer(serializers.Serializer):
    """Serializer for creating build process' buildpacks field
    Will pass to slugbuilder by REQUIRED_BUILDPACKS environments
    """

    type = serializers.CharField(required=True)
    name = serializers.CharField(required=True)
    url = serializers.CharField(required=True)
    version = serializers.CharField(default="")

    @classmethod
    def validate_type(cls, data):
        if data not in {"tar", "git"}:
            raise serializers.ValidationError("buildpack type not supported")
        return data


class CreateBuildProcessSerializer(serializers.Serializer):
    """Serializer for creating build process"""

    source_tar_path = serializers.CharField(required=True, help_text='File path in blobstore')
    source_tar_sha256sum = serializers.CharField(required=False)
    branch = serializers.CharField(required=True)
    revision = serializers.CharField(required=True)
    procfile = serializers.JSONField(required=True)
    stream_channel_id = serializers.CharField(required=False, min_length=32)
    extra_envs = serializers.JSONField(required=False)
    image = serializers.CharField(required=False, default=settings.DEFAULT_SLUGBUILDER_IMAGE, allow_null=True)
    buildpacks = serializers.ListField(
        required=False, default=list, child=CreateBuildProcessBuildpacksSerializer(), allow_null=True
    )

    def validate_image(self, data):
        return data or settings.DEFAULT_SLUGBUILDER_IMAGE

    def validate_buildpacks(self, data):
        return data or []


class BuildProcessSerializer(serializers.ModelSerializer):
    build = BuildSerializer(read_only=True)

    class Meta:
        model = models.BuildProcess
        fields = '__all__'


class BuildProcessResultSerializer(serializers.ModelSerializer):
    """Serializer for BuildProcess with result"""

    app = serializers.SlugRelatedField(slug_field='name', queryset=models.App.objects.all())
    build = BuildSerializer(read_only=True)
    lines = serializers.ListField(read_only=True)

    class Meta:
        model = models.BuildProcess
        fields = ['uuid', 'app', 'status', 'build', 'lines']


class LineSerializer(serializers.Serializer):
    stream = serializers.CharField()
    line = serializers.CharField()
    created = serializers.DateTimeField()


##########################
# Process & ProcInstance #
##########################
class InstanceSerializer(serializers.Serializer):
    name = serializers.CharField()
    process_type = serializers.CharField()
    host_ip = serializers.CharField()
    start_time = serializers.CharField()
    image = serializers.CharField()
    state = serializers.CharField()
    state_message = serializers.CharField(required=False)
    ready = serializers.BooleanField()
    restart_count = serializers.IntegerField()
    version = serializers.IntegerField()


class ProcSpecsSerializer(serializers.Serializer):
    """Representing ProcSpecs object"""

    name = serializers.CharField(source='metadata.name')
    type = serializers.CharField(source='name')
    replicas = serializers.IntegerField(source="status.replicas")
    success = serializers.IntegerField(source="status.success")
    failed = serializers.IntegerField(source="status.failed")
    version = serializers.IntegerField()


class ProcessSerializer(serializers.Serializer):
    # aka process_type
    type = serializers.CharField()
    app_name = serializers.CharField(source="app.name")
    instances = InstanceSerializer(allow_null=True, many=True)
    command = serializers.CharField(source="runtime.proc_command")
    process_status = serializers.SerializerMethodField()
    desired_replicas = serializers.IntegerField(source="replicas")
    version = serializers.IntegerField()

    def get_process_status(self, obj: 'Process') -> dict:
        if obj.status:
            return obj.status.to_dict()
        return {}


class ProcExtraInfoSLZ(serializers.Serializer):
    """Extra info for process, including command / cluster_link fields"""

    type = serializers.CharField(source='name')
    command = serializers.CharField(source='runtime.proc_command')
    cluster_link = serializers.SerializerMethodField()

    def get_cluster_link(self, obj: 'Process') -> str:
        return 'http://' + get_service_dns_name(obj.app, obj.type)


class ProcessSpecSLZ(serializers.Serializer):
    """Process Spec SLZ"""

    name = serializers.CharField(allow_blank=True)
    command = serializers.CharField(allow_blank=True)
    replicas = serializers.IntegerField(allow_null=True, required=False)
    plan = serializers.CharField(allow_null=True, required=False)


class SyncProcSpecsSerializer(serializers.Serializer):
    """Serializer for syncing processes specs"""

    processes = ProcessSpecSLZ(many=True)


####################
# Resource Metrics #
####################
class ResourceMetricsSerializer(serializers.Serializer):
    start_time = serializers.CharField(required=False)
    end_time = serializers.CharField(required=False)
    metric_type = serializers.ChoiceField(choices=MetricsResourceType.choices())
    time_range_str = serializers.CharField(required=False)
    step = serializers.CharField()

    query_metrics = serializers.SerializerMethodField()
    time_range = serializers.SerializerMethodField()

    def validate(self, attrs):
        # to_now is a quick access
        if attrs.get('time_range_str'):
            return attrs

        # check time format
        try:
            start_time = self._validate_datetime(attrs['start_time'])
            end_time = self._validate_datetime(attrs['end_time'])

            if start_time > end_time:
                raise serializers.ValidationError("start time should earlier than end time")
        except KeyError:
            raise serializers.ValidationError("start & end time is not allowed to be null if time_range_str is null")
        return attrs

    @staticmethod
    def _validate_datetime(date_string):
        # default format, web page should pass
        return datetime.datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")

    def get_query_metrics(self, data):
        """根据 metric_type 注入 query_metrics 字段"""
        if data["metric_type"] == "__all__":
            query_metrics = [MetricsResourceType.MEM, MetricsResourceType.CPU]
        else:
            query_metrics = [MetricsResourceType(data["metric_type"])]
        return query_metrics

    def get_time_range(self, data):
        return MetricSmartTimeRange.from_request_data(data)


class SeriesMetricsResultSerializer(serializers.Serializer):
    type_name = serializers.CharField()
    results = serializers.ListField()
    display_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def to_representation(self, instance):
        result = super().to_representation(instance)
        result['display_name'] = MetricsSeriesType.get_choice_label(instance.type_name)
        return result


class ResourceMetricsResultSerializer(serializers.Serializer):
    type_name = serializers.CharField()
    results = SeriesMetricsResultSerializer(allow_null=True, many=True)


class InstanceMetricsResultSerializer(serializers.Serializer):
    instance_name = serializers.CharField()
    results = ResourceMetricsResultSerializer(allow_null=True, many=True)
    display_name = serializers.CharField(required=False)

    def to_representation(self, instance):
        result = super().to_representation(instance)
        result['display_name'] = Instance.get_shorter_instance_name(instance.instance_name)
        return result


class WebConsolePostSLZ(serializers.Serializer):
    command = serializers.CharField(default="bash", help_text="命令")
    container_name = serializers.CharField(required=False, default=None, allow_null=True, help_text="容器名称")
    operator = serializers.CharField(required=True, help_text="操作者")


class EnvAddressesSLZ(serializers.Serializer):
    """Represents environment's address related status"""

    env = serializers.CharField(help_text="环境名")
    is_running = serializers.BooleanField(help_text="是否运行中")
    addresses = serializers.JSONField(help_text="可访问地址列表")
