# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

import pytest

from paas_wl.bk_app.sandbox_instance.entities import (
    SharedVolume,
    SandboxInstanceSpec,
    SidecarContainer,
    VolumeMount,
)


def _make_spec(**kwargs):
    """构造一个最小化的 SandboxInstanceSpec。"""
    defaults = {
        "name": "test-sandbox",
        "namespace": "default",
        "image": "registry.example.com/main:v1",
        "cpu_cores": 4,
        "memory": "2048Mi",
    }
    defaults.update(kwargs)
    return SandboxInstanceSpec(**defaults)


def _make_sidecar(name="log-collector", **kwargs):
    """构造一个最小化的 SidecarContainer。"""
    defaults = {
        "name": name,
        "image": f"registry.example.com/{name}:v1",
    }
    defaults.update(kwargs)
    return SidecarContainer(**defaults)


class TestSidecarContainer:
    """测试 SidecarContainer 数据类。"""

    def test_to_container_dict_minimal(self):
        """最小化 sidecar: 仅 name + image, 其余使用默认值"""
        sc = SidecarContainer(name="proxy", image="envoy:latest")
        d = sc.to_container_dict()

        assert d["name"] == "proxy"
        assert d["image"] == "envoy:latest"
        assert d["imagePullPolicy"] == "IfNotPresent"
        assert d["resources"]["limits"]["cpu"] == "500m"
        assert d["resources"]["limits"]["memory"] == "256Mi"
        assert "command" not in d
        assert "args" not in d
        assert "ports" not in d
        assert "env" not in d

    def test_to_container_dict_full(self):
        """完整字段 sidecar"""
        sc = SidecarContainer(
            name="proxy",
            image="envoy:latest",
            command=["/usr/bin/envoy"],
            args=["-c", "/etc/envoy.yaml"],
            ports=[{"containerPort": 8080, "protocol": "TCP"}],
            cpu="1000m",
            memory="512Mi",
            env_vars=[{"name": "LOG_LEVEL", "value": "debug"}],
            image_pull_policy="Always",
        )
        d = sc.to_container_dict()

        assert d["command"] == ["/usr/bin/envoy"]
        assert d["args"] == ["-c", "/etc/envoy.yaml"]
        assert d["ports"] == [{"containerPort": 8080, "protocol": "TCP"}]
        assert d["resources"]["limits"]["cpu"] == "1000m"
        assert d["resources"]["limits"]["memory"] == "512Mi"
        assert d["env"] == [{"name": "LOG_LEVEL", "value": "debug"}]
        assert d["imagePullPolicy"] == "Always"

    def test_frozen(self):
        """SidecarContainer 是 frozen dataclass, 不可修改"""
        sc = SidecarContainer(name="proxy", image="envoy:latest")
        with pytest.raises(AttributeError):
            sc.name = "changed"


class TestSandboxInstanceSpecSidecars:
    """测试 SandboxInstanceSpec 的 sidecars 相关逻辑。"""

    def test_no_sidecars_backward_compat(self):
        """无 sidecar 时行为与原先一致: containers 只有 main"""
        spec = _make_spec()
        manifest = spec.build_manifest()
        containers = manifest["spec"]["podTemplate"]["containers"]

        assert len(containers) == 1
        assert containers[0]["name"] == "main"

    def test_sidecars_appended_to_containers(self):
        """sidecar 容器追加到 podTemplate.containers 中, main 在前"""
        sidecars = [
            _make_sidecar("log-collector"),
            _make_sidecar("proxy"),
        ]
        spec = _make_spec(sidecars=sidecars)
        manifest = spec.build_manifest()
        containers = manifest["spec"]["podTemplate"]["containers"]

        assert len(containers) == 3
        assert containers[0]["name"] == "main"
        assert containers[1]["name"] == "log-collector"
        assert containers[2]["name"] == "proxy"

    def test_sidecar_container_fields_in_manifest(self):
        """验证 sidecar 容器的各字段正确渲染到 manifest"""
        sc = SidecarContainer(
            name="monitor",
            image="prom/node-exporter:v1",
            command=["/bin/node_exporter"],
            ports=[{"containerPort": 9100}],
            cpu="200m",
            memory="128Mi",
            env_vars=[{"name": "INTERVAL", "value": "15s"}],
        )
        spec = _make_spec(sidecars=[sc])
        manifest = spec.build_manifest()
        sidecar_dict = manifest["spec"]["podTemplate"]["containers"][1]

        assert sidecar_dict["image"] == "prom/node-exporter:v1"
        assert sidecar_dict["command"] == ["/bin/node_exporter"]
        assert sidecar_dict["ports"] == [{"containerPort": 9100}]
        assert sidecar_dict["resources"]["limits"]["cpu"] == "200m"
        assert sidecar_dict["env"] == [{"name": "INTERVAL", "value": "15s"}]

    def test_sidecar_name_main_raises(self):
        """sidecar 名为 'main' 时抛 ValueError"""
        with pytest.raises(ValueError, match="与主容器冲突"):
            _make_spec(sidecars=[_make_sidecar("main")])

    def test_sidecar_duplicate_name_raises(self):
        """sidecar 名重复时抛 ValueError"""
        with pytest.raises(ValueError, match="重复"):
            _make_spec(sidecars=[_make_sidecar("dup"), _make_sidecar("dup")])

    def test_sidecars_default_empty(self):
        """sidecars 字段默认为空列表"""
        spec = _make_spec()
        assert spec.sidecars == []

    def test_main_container_env_not_leaked_to_sidecar(self):
        """主容器的 env_vars 不会泄漏到 sidecar"""
        sc = _make_sidecar("proxy")
        spec = _make_spec(
            env_vars=[{"name": "MAIN_SECRET", "value": "secret"}],
            sidecars=[sc],
        )
        manifest = spec.build_manifest()
        main_container = manifest["spec"]["podTemplate"]["containers"][0]
        sidecar_container = manifest["spec"]["podTemplate"]["containers"][1]

        assert main_container["env"] == [{"name": "MAIN_SECRET", "value": "secret"}]
        assert "env" not in sidecar_container


class TestSharedVolumes:
    """测试 emptyDir 共享卷功能。"""

    def test_no_shared_volumes_backward_compat(self):
        """无 shared_volumes 时 podTemplate 中不出现额外 volumes"""
        spec = _make_spec()
        manifest = spec.build_manifest()
        pod_template = manifest["spec"]["podTemplate"]

        assert "volumes" not in pod_template

    def test_emptydir_rendered_to_volumes(self):
        """shared_volumes 正确渲染为 emptyDir volumes"""
        spec = _make_spec(
            shared_volumes=[SharedVolume(name="shared-data", size_limit="1Gi")],
        )
        manifest = spec.build_manifest()
        volumes = manifest["spec"]["podTemplate"]["volumes"]

        assert len(volumes) == 1
        assert volumes[0] == {"name": "shared-data", "emptyDir": {"sizeLimit": "1Gi"}}

    def test_emptydir_with_memory_medium(self):
        """Memory medium 的 emptyDir"""
        spec = _make_spec(
            shared_volumes=[SharedVolume(name="tmpfs-vol", medium="Memory", size_limit="512Mi")],
        )
        manifest = spec.build_manifest()
        volumes = manifest["spec"]["podTemplate"]["volumes"]

        assert volumes[0] == {"name": "tmpfs-vol", "emptyDir": {"medium": "Memory", "sizeLimit": "512Mi"}}

    def test_emptydir_minimal(self):
        """最小化 emptyDir: 不设 medium 和 sizeLimit"""
        spec = _make_spec(
            shared_volumes=[SharedVolume(name="data")],
        )
        manifest = spec.build_manifest()
        volumes = manifest["spec"]["podTemplate"]["volumes"]

        assert volumes[0] == {"name": "data", "emptyDir": {}}

    def test_main_container_volume_mounts(self):
        """主容器的 volumeMounts 正确渲染"""
        spec = _make_spec(
            shared_volumes=[SharedVolume(name="shared-data")],
            volume_mounts=[VolumeMount(name="shared-data", mount_path="/data/shared")],
        )
        manifest = spec.build_manifest()
        main_container = manifest["spec"]["podTemplate"]["containers"][0]

        assert main_container["volumeMounts"] == [
            {"name": "shared-data", "mountPath": "/data/shared"}
        ]

    def test_main_container_volume_mounts_readonly(self):
        """主容器 read_only volumeMount"""
        spec = _make_spec(
            shared_volumes=[SharedVolume(name="config")],
            volume_mounts=[VolumeMount(name="config", mount_path="/etc/config", read_only=True)],
        )
        manifest = spec.build_manifest()
        main_container = manifest["spec"]["podTemplate"]["containers"][0]

        assert main_container["volumeMounts"] == [
            {"name": "config", "mountPath": "/etc/config", "readOnly": True}
        ]

    def test_sidecar_volume_mounts(self):
        """sidecar 容器的 volumeMounts 正确渲染"""
        sc = SidecarContainer(
            name="log-agent",
            image="fluentd:v1",
            volume_mounts=[VolumeMount(name="logs", mount_path="/var/log/app")],
        )
        spec = _make_spec(
            shared_volumes=[SharedVolume(name="logs")],
            sidecars=[sc],
        )
        manifest = spec.build_manifest()
        sidecar_dict = manifest["spec"]["podTemplate"]["containers"][1]

        assert sidecar_dict["volumeMounts"] == [
            {"name": "logs", "mountPath": "/var/log/app"}
        ]

    def test_shared_volume_between_main_and_sidecar(self):
        """主容器和 sidecar 共享同一个 volume"""
        sc = SidecarContainer(
            name="log-agent",
            image="fluentd:v1",
            volume_mounts=[VolumeMount(name="shared", mount_path="/shared", read_only=True)],
        )
        spec = _make_spec(
            shared_volumes=[SharedVolume(name="shared")],
            volume_mounts=[VolumeMount(name="shared", mount_path="/app/shared")],
            sidecars=[sc],
        )
        manifest = spec.build_manifest()
        main_container = manifest["spec"]["podTemplate"]["containers"][0]
        sidecar_container = manifest["spec"]["podTemplate"]["containers"][1]

        assert main_container["volumeMounts"] == [{"name": "shared", "mountPath": "/app/shared"}]
        assert sidecar_container["volumeMounts"] == [
            {"name": "shared", "mountPath": "/shared", "readOnly": True}
        ]

    def test_shared_volumes_coexist_with_rootfs(self):
        """shared_volumes 与 rootfs PVC volumes 共存"""
        from paas_wl.bk_app.sandbox_instance.entities import RootfsConfig

        spec = _make_spec(
            rootfs=RootfsConfig(disk_size="50Gi", pvc_size="60Gi"),
            shared_volumes=[SharedVolume(name="exchange")],
            volume_mounts=[VolumeMount(name="exchange", mount_path="/exchange")],
        )
        manifest = spec.build_manifest()
        volumes = manifest["spec"]["podTemplate"]["volumes"]

        # rootfs PVC volume + emptyDir volume
        assert len(volumes) == 2
        volume_names = [v["name"] for v in volumes]
        assert "cube-state" in volume_names
        assert "exchange" in volume_names

    def test_main_volume_mount_invalid_ref_raises(self):
        """主容器 volumeMount 引用不存在的 volume 名报错"""
        with pytest.raises(ValueError, match="引用了不存在的 volume"):
            _make_spec(
                volume_mounts=[VolumeMount(name="nonexistent", mount_path="/mnt")],
            )

    def test_sidecar_volume_mount_invalid_ref_raises(self):
        """sidecar volumeMount 引用不存在的 volume 名报错"""
        sc = SidecarContainer(
            name="agent",
            image="agent:v1",
            volume_mounts=[VolumeMount(name="nonexistent", mount_path="/mnt")],
        )
        with pytest.raises(ValueError, match="引用了不存在的 volume"):
            _make_spec(sidecars=[sc])
