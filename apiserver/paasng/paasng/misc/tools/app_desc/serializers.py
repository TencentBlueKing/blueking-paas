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


from rest_framework import serializers
from rest_framework.fields import empty

from paasng.platform.applications.serializers.fields import SourceDirField


class DisplayOptionsSerializer(serializers.Serializer):
    width = serializers.IntegerField(required=False)
    height = serializers.IntegerField(required=False)
    open_mode = serializers.CharField(required=False)
    is_win_maximize = serializers.BooleanField(required=False)
    visible = serializers.BooleanField(required=False)


class MarketSerializer(serializers.Serializer):
    category = serializers.CharField(required=False)
    introduction = serializers.CharField()
    description = serializers.CharField(required=False)
    display_options = DisplayOptionsSerializer(required=False)


class AppSerializer(serializers.Serializer):
    region = serializers.CharField(required=False)
    bk_app_code = serializers.CharField(required=False)
    bk_app_name = serializers.CharField(required=False)
    market = MarketSerializer(required=False)


class EnvVariableSerializer(serializers.Serializer):
    key = serializers.CharField()
    value = serializers.CharField(allow_blank=True)
    description = serializers.CharField(required=False)
    environment_name = serializers.CharField(required=False)


class ExecProbeSerializer(serializers.Serializer):
    command = serializers.ListField(child=serializers.CharField())


class HTTPGetProbeSerializer(serializers.Serializer):
    host = serializers.CharField(required=False)
    path = serializers.CharField(required=False)
    port = serializers.IntegerField()
    scheme = serializers.CharField(required=False)
    http_headers = serializers.ListField(child=serializers.DictField(), required=False)

    def validate_http_headers(self, value):
        if value:
            for item in value:
                if len(item) != 1:
                    raise serializers.ValidationError("Each item in http_headers must be one key: value pair.")
                if "name" not in item and "value" not in item:
                    raise serializers.ValidationError("http_headers item key should be 'name' or 'value'.")
        return value


class TCPSocketProbeSerializer(serializers.Serializer):
    port = serializers.IntegerField()
    host = serializers.CharField(required=False)


class ProbeSerializer(serializers.Serializer):
    exec = ExecProbeSerializer(required=False)
    http_get = HTTPGetProbeSerializer(required=False)
    tcp_socket = TCPSocketProbeSerializer(required=False)
    initial_delay_seconds = serializers.IntegerField(required=False)
    timeout_seconds = serializers.IntegerField(required=False)
    period_seconds = serializers.IntegerField(required=False)
    success_threshold = serializers.IntegerField(required=False)
    failure_threshold = serializers.IntegerField(required=False)


class ProcessSerializer(serializers.Serializer):
    command = serializers.CharField()
    plan = serializers.CharField(required=False)
    replicas = serializers.IntegerField(required=False)
    probes = serializers.DictField(child=ProbeSerializer(), required=False)

    def validate_probes(self, value):
        allowed_keys = ["liveness", "readiness", "startup"]
        for key in value:
            if key not in allowed_keys:
                raise serializers.ValidationError(f"Probe type '{key}' is not valid. Must be one of {allowed_keys}.")
        return value


class ServiceSerializer(serializers.Serializer):
    name = serializers.CharField()
    share_from = serializers.CharField(required=False)


class ScriptsSerializer(serializers.Serializer):
    pre_release_hook = serializers.CharField()

    def validate_pre_release_hook(self, value):
        if value.strip().startswith("start"):
            raise serializers.ValidationError("The pre_release_hook command cannot start with 'start'.")

        if "\n" in value:
            raise serializers.ValidationError("The pre_release_hook command must be a single line.")

        return value


class SvcDiscoverySerializer(serializers.Serializer):
    bk_saas = serializers.ListField()

    def validate_bk_saas(self, value):
        for item in value:
            if isinstance(item, str):
                continue
            if isinstance(item, dict):
                if "bk_app_code" not in item:
                    raise serializers.ValidationError(
                        "If bk_saas item is a dictionary, it must contain 'bk_app_code'."
                    )
            else:
                raise serializers.ValidationError("Each item in 'bk_saas' must be either a string or a dictionary.")

        return value


class BkMonitorPortSerializer(serializers.Serializer):
    port = serializers.IntegerField()


class ModuleSerializer(serializers.Serializer):
    is_default = serializers.BooleanField(required=False)
    source_dir = SourceDirField(required=False, default=empty)
    language = serializers.CharField()
    services = ServiceSerializer(many=True, required=False)
    env_variables = EnvVariableSerializer(many=True, required=False)
    processes = serializers.DictField(child=ProcessSerializer())
    scripts = ScriptsSerializer(required=False)
    svc_discovery = SvcDiscoverySerializer(required=False)
    package_plans = serializers.DictField(required=False)
    bkmonitor = BkMonitorPortSerializer(required=False)


class AppDescSpec2Serializer(serializers.Serializer):
    spec_version = serializers.IntegerField(required=False)
    app_version = serializers.CharField(required=False)
    app = AppSerializer(required=False)
    modules = serializers.DictField(child=ModuleSerializer(), required=False)
    module = ModuleSerializer(required=False)

    def validate(self, attrs):
        if "spec_version" in attrs and attrs.get("spec_version") != 2:
            raise serializers.ValidationError("spec_version must be 2.")
        if ("modules" not in attrs and "module" not in attrs) or ("modules" in attrs and "module" in attrs):
            raise serializers.ValidationError("one of 'modules' or 'module' is required.")
        return attrs
