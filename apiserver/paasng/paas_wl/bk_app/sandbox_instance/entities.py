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

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from paas_wl.bk_app.sandbox_instance.constants import (
    DEFAULT_NETWORK_MODE,
    DEFAULT_RUNTIME_CLASS_NAME,
    ROOTFS_DISK_FS_TYPE,
    ROOTFS_DISK_IMAGE,
    ROOTFS_DISK_NAME,
    ROOTFS_DISK_ROLE,
    ROOTFS_DISK_SOURCE_PATH,
    SANDBOX_INSTANCE_API_VERSION,
    SANDBOX_INSTANCE_KIND,
    STATE_VOLUME_NAME,
    DesiredState,
)


@dataclass(frozen=True)
class RootfsConfig:
    """rootfs 系统盘 + 持久化 PVC 配置。

    当提供时, operator 会用 volumeClaimTemplates 自动创建一块空白持久 PVC,
    cube 首启在其中 seed 出 rootdisk.img, 重建 Pod 时复用该盘以保留 rootfs 变更。
    不提供时, 沙箱重启数据会丢失。

    :param disk_size: disk-image 文件大小, 形如 "50Gi"。
    :param pvc_size: 承载 disk-image 的 PVC 容量, 需 >= disk_size, 形如 "60Gi"。
    """

    disk_size: str
    pvc_size: str


@dataclass(frozen=True)
class SharedVolume:
    """emptyDir 共享卷声明, 用于主容器与 sidecar 容器之间共享文件目录。

    :param name: volume 名称, 同一 SandboxInstanceSpec 中唯一。
    :param medium: emptyDir.medium, 空串为默认(磁盘), "Memory" 为 tmpfs。
    :param size_limit: emptyDir.sizeLimit, 形如 "1Gi", 空串表示不限制。
    """

    name: str
    medium: str = ""
    size_limit: str = ""


@dataclass(frozen=True)
class VolumeMount:
    """容器中的卷挂载点, 引用 SharedVolume.name。

    :param name: 引用 SharedVolume.name。
    :param mount_path: 容器内挂载路径, 如 "/shared"。
    :param read_only: 是否只读挂载, 默认 False。
    """

    name: str
    mount_path: str
    read_only: bool = False

    def to_k8s_dict(self) -> Dict[str, Any]:
        """转换为 K8s volumeMount dict。"""
        mount: Dict[str, Any] = {"name": self.name, "mountPath": self.mount_path}
        if self.read_only:
            mount["readOnly"] = True
        return mount


@dataclass(frozen=True)
class SidecarContainer:
    """SandboxInstance 的 sidecar 容器配置。

    sidecar 容器与主容器共享同一个 Pod 网络命名空间,
    可用于日志采集、代理转发、监控 agent 等辅助工作负载。

    :param name: 容器名, 不允许与主容器名 "main" 冲突, 且在 sidecars 列表中唯一。
    :param image: 容器镜像。
    :param command: 启动命令, 可选。
    :param args: 启动参数, 可选。
    :param ports: 容器端口列表, 结构 [{"containerPort": 8080, "protocol": "TCP"}]。
    :param cpu: CPU 资源限制, 形如 "500m"。
    :param memory: 内存资源限制, 形如 "256Mi"。
    :param env_vars: 环境变量, 标准 K8s env 结构 [{"name": ..., "value": ...}]。
    :param image_pull_policy: 镜像拉取策略, 默认 IfNotPresent。
    """

    name: str
    image: str
    command: List[str] = field(default_factory=list)
    args: List[str] = field(default_factory=list)
    ports: List[Dict[str, Any]] = field(default_factory=list)
    cpu: str = "500m"
    memory: str = "256Mi"
    env_vars: List[Dict[str, str]] = field(default_factory=list)
    image_pull_policy: str = "IfNotPresent"
    volume_mounts: List["VolumeMount"] = field(default_factory=list)

    def to_container_dict(self) -> Dict[str, Any]:
        """将 sidecar 配置转换为 K8s container spec dict。"""
        container: Dict[str, Any] = {
            "name": self.name,
            "image": self.image,
            "imagePullPolicy": self.image_pull_policy,
            "resources": {
                "limits": {"cpu": self.cpu, "memory": self.memory},
                "requests": {"cpu": self.cpu, "memory": self.memory},
            },
        }
        if self.command:
            container["command"] = self.command
        if self.args:
            container["args"] = self.args
        if self.ports:
            container["ports"] = list(self.ports)
        if self.env_vars:
            container["env"] = list(self.env_vars)
        if self.volume_mounts:
            container["volumeMounts"] = [vm.to_k8s_dict() for vm in self.volume_mounts]
        return container


@dataclass
class SandboxInstanceSpec:
    """SandboxInstance 的业务参数, 由后端按此拼装出完整 CR manifest。

    与常规 BkApp CR 的差异
    ----------------------
    SandboxInstance 面向隔离型 AI Agent 应用, 工作负载由 sandbox-controller 渲染为
    cube MicroVM Pod, 与 BkApp(由 app-operator 渲染为普通 Deployment)在以下方面不同:

    已支持并映射的能力:
      - 环境变量(全局 + 环境覆盖 + 内置系统变量)
      - 镜像拉取策略(imagePullPolicy, 从 deployment.advanced_options 透传)
      - 镜像拉取凭证(imagePullSecrets, 复用平台镜像凭证下发机制)
      - 调度配置(nodeSelector / tolerations)
      - 域名解析(DNS nameservers / hostAliases)

    暂不支持 / 不适用的能力:
      - 挂载卷(mounts): SandboxInstance 以 rootfs 整盘为主存储模型, 暂不映射
        BkApp 的 configMap/secret/persistentStorage 挂载;
        已通过 shared_volumes + volume_mounts 支持 emptyDir 容器间文件共享。
      - 多副本 / 自动扩缩容: 一个 SandboxInstance 固定对应一个 MicroVM 实例。
      - 部署钩子(preRelease hook): sandbox 无中间态编排。
      - 健康检查(probes): cube Pod 存活由 sandbox-controller 管理, 不支持自定义探针。
      - 服务暴露(services/port): 平台侧自建 Service + Ingress, 不依赖 CR 声明。
      - 可观测性(observability): sandbox-controller 不识别此注解。

    :param name: 沙箱实例名(同时作为 CR name 与 Pod name)。
    :param namespace: 下发的目标命名空间。
    :param image: 主容器镜像。
    :param cpu_cores: vCPU 核数。
    :param memory: 内存, 形如 "4Gi"。
    :param command: 主容器 command, 可选。
    :param args: 主容器 args, 可选。
    :param rootfs: rootfs 持久化配置, 不提供则不持久化。
    :param desired_state: 期望运行态, 默认 Running。
    :param runtime_class_name: 运行时类, 默认 cube。
    :param annotations: 透传到渲染出的 Pod 的注解(如 TKE 网络相关)。渲染到 CR 的 annotations 会继承到渲染出的 pod 上。
    :param labels: 透传到 CR metadata 的标签, sandbox-controller 会继承到渲染出的 cube Pod。
    :param image_pull_policy: 镜像拉取策略, 默认 IfNotPresent。
    :param image_pull_secrets: 镜像拉取凭证引用列表, 结构 [{"name": "secret-name"}]。
    :param env_vars: 主容器环境变量, 标准 K8s env 结构 [{"name": ..., "value": ...}]。
    :param node_selector: 调度 nodeSelector。
    :param tolerations: 调度 tolerations 列表。
    :param dns_nameservers: DNS nameservers 列表。
    :param host_aliases: podTemplate.hostAliases, 结构 [{"ip": ..., "hostnames": [...]}]。
    :param sidecars: sidecar 容器列表, 默认空列表(向后兼容)。
    :param shared_volumes: emptyDir 共享卷声明列表, 用于主容器与 sidecar 之间共享文件目录。
    :param volume_mounts: 主容器的卷挂载点列表, 引用 shared_volumes 中的 name。
    """

    name: str
    namespace: str
    image: str
    cpu_cores: int
    memory: str
    command: List[str] = field(default_factory=list)
    args: List[str] = field(default_factory=list)
    rootfs: Optional[RootfsConfig] = None
    desired_state: DesiredState = DesiredState.RUNNING
    runtime_class_name: str = DEFAULT_RUNTIME_CLASS_NAME
    annotations: Dict[str, str] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)
    env_vars: List[Dict[str, str]] = field(default_factory=list)
    node_selector: Dict[str, str] = field(default_factory=dict)
    tolerations: List[Dict[str, Any]] = field(default_factory=list)
    image_pull_policy: str = "IfNotPresent"
    image_pull_secrets: List[Dict[str, str]] = field(default_factory=list)
    dns_nameservers: List[str] = field(default_factory=list)
    host_aliases: List[Dict[str, Any]] = field(default_factory=list)
    sidecars: List["SidecarContainer"] = field(default_factory=list)
    shared_volumes: List["SharedVolume"] = field(default_factory=list)
    volume_mounts: List["VolumeMount"] = field(default_factory=list)

    def __post_init__(self):
        """校验 sidecars 和 volume 配置的合法性。"""
        sidecar_names = set()
        for sc in self.sidecars:
            if sc.name == "main":
                raise ValueError("sidecar 容器名不能为 'main', 与主容器冲突")
            if sc.name in sidecar_names:
                raise ValueError(f"sidecar 容器名 '{sc.name}' 重复")
            sidecar_names.add(sc.name)

        # 校验 shared_volumes 名称唯一性
        volume_names: set = set()
        for sv in self.shared_volumes:
            if sv.name in volume_names:
                raise ValueError(f"shared_volumes 名称 '{sv.name}' 重复")
            volume_names.add(sv.name)

        # 校验 volume_mounts 引用的 name 必须存在于 shared_volumes 中
        for vm in self.volume_mounts:
            if vm.name not in volume_names:
                raise ValueError(f"主容器 volumeMount 引用了不存在的 volume '{vm.name}'")
        for sc in self.sidecars:
            for vm in sc.volume_mounts:
                if vm.name not in volume_names:
                    raise ValueError(
                        f"sidecar '{sc.name}' 的 volumeMount 引用了不存在的 volume '{vm.name}'"
                    )

    def build_manifest(self) -> Dict[str, Any]:
        """按业务参数拼装出完整的 SandboxInstance CR manifest(dict)。"""
        pvc_claim_name = f"{self.name}-pvc"

        domain: Dict[str, Any] = {
            "cpu": {"cores": self.cpu_cores},
            "memory": self.memory,
        }

        # v1beta1: 容器 / 卷统一下沉到 spec.podTemplate(扁平 PodSpec)
        containers = [self._build_main_container()]
        for sc in self.sidecars:
            containers.append(sc.to_container_dict())
        pod_template: Dict[str, Any] = {"containers": containers}

        # rootfs 持久化: 挂载系统盘 + 声明持久 PVC
        if self.rootfs:
            domain["devices"] = {
                "disks": [
                    {
                        "name": ROOTFS_DISK_NAME,
                        "volumeName": STATE_VOLUME_NAME,
                        "role": ROOTFS_DISK_ROLE,
                        "image": ROOTFS_DISK_IMAGE,
                        "sourcePath": ROOTFS_DISK_SOURCE_PATH,
                        "size": self.rootfs.disk_size,
                        "fsType": ROOTFS_DISK_FS_TYPE,
                    }
                ]
            }
            pod_template["volumes"] = [
                {
                    "name": STATE_VOLUME_NAME,
                    "persistentVolumeClaim": {"claimName": pvc_claim_name},
                }
            ]

        # emptyDir 共享卷: 用于主容器与 sidecar 之间共享文件目录
        if self.shared_volumes:
            volumes = pod_template.get("volumes", [])
            for sv in self.shared_volumes:
                empty_dir: Dict[str, Any] = {}
                if sv.medium:
                    empty_dir["medium"] = sv.medium
                if sv.size_limit:
                    empty_dir["sizeLimit"] = sv.size_limit
                volumes.append({"name": sv.name, "emptyDir": empty_dir})
            pod_template["volumes"] = volumes

        # 调度配置
        if self.node_selector:
            pod_template["nodeSelector"] = dict(self.node_selector)
        if self.tolerations:
            pod_template["tolerations"] = list(self.tolerations)

        # DNS 配置
        if self.dns_nameservers:
            pod_template["dnsConfig"] = {"nameservers": list(self.dns_nameservers)}
        if self.host_aliases:
            pod_template["hostAliases"] = list(self.host_aliases)

        # 镜像拉取凭证
        if self.image_pull_secrets:
            pod_template["imagePullSecrets"] = list(self.image_pull_secrets)

        spec: Dict[str, Any] = {
            "desiredState": self.desired_state.value,
            "runtimeClassName": self.runtime_class_name,
            "network": self._build_network(),
            "domain": domain,
            "podTemplate": pod_template,
        }

        if self.rootfs:
            spec["volumeClaimTemplates"] = [
                {
                    "metadata": {"name": pvc_claim_name},
                    "spec": {
                        "accessModes": ["ReadWriteOnce"],
                        "resources": {"requests": {"storage": self.rootfs.pvc_size}},
                    },
                }
            ]

        metadata: Dict[str, Any] = {"name": self.name, "namespace": self.namespace}
        if self.annotations:
            metadata["annotations"] = dict(self.annotations)
        if self.labels:
            metadata["labels"] = dict(self.labels)

        return {
            "apiVersion": SANDBOX_INSTANCE_API_VERSION,
            "kind": SANDBOX_INSTANCE_KIND,
            "metadata": metadata,
            "spec": spec,
        }

    def _build_network(self) -> Dict[str, Any]:
        network: Dict[str, Any] = {"mode": DEFAULT_NETWORK_MODE}
        return network

    def _build_main_container(self) -> Dict[str, Any]:
        container: Dict[str, Any] = {
            "name": "main",
            "image": self.image,
            "imagePullPolicy": self.image_pull_policy,
        }
        if self.command:
            container["command"] = self.command
        if self.args:
            container["args"] = self.args
        if self.env_vars:
            container["env"] = list(self.env_vars)
        if self.volume_mounts:
            container["volumeMounts"] = [vm.to_k8s_dict() for vm in self.volume_mounts]
        return container
