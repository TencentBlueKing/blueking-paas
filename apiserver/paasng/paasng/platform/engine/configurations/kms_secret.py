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

"""敏感变量的 KMS 托管：冻结配置版本，创建 KMS 凭证与 ESO 资源，并等待目标 Secret 就绪

- 每次需要托管的部署调用一次 create_kms_config_version，生成新的配置版本，不复用；
- KMSSecretProvisioner 负责该版本的远端资源：凭证先按名称核对再创建，Kubernetes 资源按名称 create_or_update；
- 每一步成功后才推进 status。失败时保持在最后完成的步骤，并把安全的错误分类写入 error_reason。
  已记录的 credential_id 与 UID 让重试可以跳过已完成的步骤。

本模块不删除任何远端资源，清理由删除清理流程负责。
"""

import logging
import time
import uuid
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Protocol

from django.conf import settings
from kubernetes.client.exceptions import ApiException

from paas_wl.bk_app.cnative.specs.crd import bk_app as crd
from paas_wl.bk_app.processes.entities import SecretFileMount
from paas_wl.infras.cluster.shim import EnvClusterService
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.base.exceptions import ResourceMissing
from paas_wl.infras.resources.base.kres import BaseKresource, KSecret, KServiceAccount
from paasng.infras.kms.client import CredentialInfo, KMSClient, KMSScope, ServiceAccountAuth, make_kms_client
from paasng.infras.kms.constants import (
    KMS_SECRET_MOUNT_DIR,
    KMS_SECRET_VOLUME_NAME,
    SCOPE_TYPE_SCOPE,
    SECRET_KEY_ENVELOPE,
    SECRET_KEY_PRIVATE_KEY,
)
from paasng.infras.kms.exceptions import (
    KMSAPIError,
    KMSConfigError,
    KMSCredentialMismatchError,
    KMSRequestError,
    KMSSecretNotReadyError,
    KMSValidationError,
)
from paasng.infras.kms.manifests import (
    CLUSTER_SECRET_STORE_KIND,
    EXTERNAL_SECRET_KIND,
    EXTERNAL_SECRETS_API_VERSION,
    build_cluster_secret_store,
    build_external_secret,
    build_service_account,
)
from paasng.infras.kms.naming import (
    build_credential_name,
    build_kms_role,
    build_openbao_key,
    build_resource_name,
    build_service_account_name,
)
from paasng.infras.kms.payload import build_frozen_payload
from paasng.infras.kms.readiness import SecretReadiness, evaluate_secret_readiness
from paasng.platform.applications.constants import AppFeatureFlag
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.configurations.env_var.encryption import (
    ENCRYPTED_KEYS_ENV_NAME,
    SECRET_KEY_ENV_VAR_NAME,
    collect_sensitive_keys,
    is_encrypted_value,
)
from paasng.platform.engine.constants import KMSConfigVersionStatus
from paasng.platform.engine.exceptions import DeployShouldAbortError
from paasng.platform.engine.models import Deployment, KMSConfigVersion
from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)

SECRET_API_VERSION = "v1"
SECRET_KIND = "Secret"

# KMSConfigVersion.error_reason 的最大长度
ERROR_REASON_MAX_CHARS = 255

# 配置版本的推进顺序。只向前推进：重复执行已完成的步骤时不会把 status 回退
_PROGRESS_ORDER = (
    KMSConfigVersionStatus.PENDING.value,
    KMSConfigVersionStatus.CREDENTIAL_CREATED.value,
    KMSConfigVersionStatus.RESOURCES_APPLIED.value,
    KMSConfigVersionStatus.READY.value,
)


class KClusterSecretStore(BaseKresource):
    """ESO 集群级 SecretStore（external-secrets.io）"""

    kind = CLUSTER_SECRET_STORE_KIND


class KExternalSecret(BaseKresource):
    """ESO ExternalSecret（external-secrets.io）"""

    kind = EXTERNAL_SECRET_KIND


# 本模块用到的 kind。按 kind 查找，未列出的 kind 不允许访问
_KRES_BY_KIND: dict[str, type[BaseKresource]] = {
    "ServiceAccount": KServiceAccount,
    "Secret": KSecret,
    "ClusterSecretStore": KClusterSecretStore,
    "ExternalSecret": KExternalSecret,
}


class KubeResources:
    """KMS 相关 Kubernetes 资源在单个集群中的读写

    只封装本模块用到的 kind，对外返回普通 dict，不暴露 kres 对象。
    """

    def __init__(self, client: Any):
        self._client = client
        self._kres_cache: dict[tuple[str, str], BaseKresource] = {}

    @classmethod
    def for_cluster(cls, cluster_name: str) -> "KubeResources":
        return cls(get_client_by_cluster_name(cluster_name))

    def apply(self, manifest: Mapping[str, Any]) -> str:
        """以 create_or_update 方式提交资源，返回 metadata.uid

        使用 replace 而非 patch：ESO 资源是 CRD，replace 不依赖 resourceVersion，可以无条件更新。
        """
        metadata = manifest["metadata"]
        kres = self._get_kres(manifest["apiVersion"], manifest["kind"])
        obj, _created = kres.create_or_update(
            metadata["name"], namespace=metadata.get("namespace"), body=dict(manifest)
        )
        return str(obj.to_dict()["metadata"]["uid"])

    def get(self, *, api_version: str, kind: str, name: str, namespace: str | None) -> dict[str, Any] | None:
        """按名称读取资源，不存在时返回 None"""
        try:
            obj = self._get_kres(api_version, kind).get(name, namespace=namespace)
        except ResourceMissing:
            return None
        return obj.to_dict()

    def _get_kres(self, api_version: str, kind: str) -> BaseKresource:
        cache_key = (api_version, kind)
        if cache_key not in self._kres_cache:
            kres_cls = _KRES_BY_KIND.get(kind)
            if kres_cls is None:
                raise ValueError(f"unsupported kind: {kind}")
            self._kres_cache[cache_key] = kres_cls(self._client, api_version=api_version)
        return self._kres_cache[cache_key]


class KubeResourceClient(Protocol):
    """本模块对 Kubernetes 的最小依赖，便于替换为测试替身"""

    def apply(self, manifest: Mapping[str, Any]) -> str: ...

    def get(self, *, api_version: str, kind: str, name: str, namespace: str | None) -> dict[str, Any] | None: ...


@dataclass(frozen=True)
class KMSSaaSSettings:
    """本 SaaS 接入 KMS 所需的配置快照"""

    scope_id: int
    scope_name: str
    openbao_server: str
    kv_path: str
    k8s_auth_mount: str
    mtls_secret_namespace: str
    mtls_secret_name: str
    refresh_interval: str
    ready_timeout_seconds: int
    ready_poll_interval_seconds: int


def load_kms_settings() -> KMSSaaSSettings:
    """从 Django settings 读取配置。必填项缺失时抛出 KMSConfigError，此时尚未发起任何请求"""
    required = {
        "KMS_SAAS_SCOPE_ID": settings.KMS_SAAS_SCOPE_ID > 0,
        "KMS_SAAS_SCOPE_NAME": bool(settings.KMS_SAAS_SCOPE_NAME),
        "KMS_OPENBAO_SERVER": bool(settings.KMS_OPENBAO_SERVER),
        "KMS_OPENBAO_MTLS_SECRET_NAMESPACE": bool(settings.KMS_OPENBAO_MTLS_SECRET_NAMESPACE),
    }
    missing = [name for name, configured in required.items() if not configured]
    if missing:
        raise KMSConfigError(f"KMS settings are not configured: {', '.join(missing)}")

    return KMSSaaSSettings(
        scope_id=settings.KMS_SAAS_SCOPE_ID,
        scope_name=settings.KMS_SAAS_SCOPE_NAME,
        openbao_server=settings.KMS_OPENBAO_SERVER,
        kv_path=settings.KMS_OPENBAO_KV_PATH,
        k8s_auth_mount=settings.KMS_OPENBAO_K8S_AUTH_MOUNT,
        mtls_secret_namespace=settings.KMS_OPENBAO_MTLS_SECRET_NAMESPACE,
        mtls_secret_name=settings.KMS_OPENBAO_MTLS_SECRET_NAME,
        refresh_interval=settings.KMS_SECRET_REFRESH_INTERVAL,
        ready_timeout_seconds=settings.KMS_SECRET_READY_TIMEOUT_SECONDS,
        ready_poll_interval_seconds=settings.KMS_SECRET_READY_POLL_INTERVAL_SECONDS,
    )


def create_kms_config_version(
    module_env: ModuleEnvironment,
    sensitive_env_vars: Mapping[str, str],
    *,
    kms: KMSClient | None = None,
    kms_settings: KMSSaaSSettings | None = None,
) -> KMSConfigVersion:
    """冻结本次部署的敏感变量：生成新的配置版本，本地加密后保存信封，状态为 pending

    只调用 KMS 获取加密信息，不创建任何远端资源。明文只在本函数内存中存在，不落库。
    记录只在信封生成后才写入，因此不会出现没有信封的配置版本。

    :raises KMSValidationError: 没有敏感变量，或明文超出上限
    :raises KMSConfigError: KMS 相关配置缺失
    """
    if not sensitive_env_vars:
        raise KMSValidationError("no sensitive env vars to freeze")
    cfg = kms_settings or load_kms_settings()

    module = module_env.module
    if module is None:
        raise ValueError("module environment has no module")

    tenant_id = module_env.tenant_id
    app_code = module_env.application.code
    module_name = module.name
    env_name = module_env.environment
    module_environment_id = str(module_env.pk)
    version_id = uuid.uuid4().hex

    credential_name = build_credential_name(
        app_code=app_code, module_name=module_name, env_name=env_name, version_id=version_id
    )
    resource_name = build_resource_name(tenant_id=tenant_id, credential_name=credential_name)
    payload = build_frozen_payload(
        config_version_id=version_id,
        module_environment_id=module_environment_id,
        env_vars=sensitive_env_vars,
    )
    envelope = (kms or make_kms_client(tenant_id)).encrypt_credential_value(payload)

    version = KMSConfigVersion(
        id=version_id,
        tenant_id=tenant_id,
        app_code=app_code,
        module_name=module_name,
        env_name=env_name,
        module_environment_id=module_environment_id,
        status=KMSConfigVersionStatus.PENDING.value,
        envelope=envelope,
        kms_scope_id=cfg.scope_id,
        credential_name=credential_name,
        openbao_key=build_openbao_key(
            tenant_id=tenant_id,
            scope_type=SCOPE_TYPE_SCOPE,
            scope_name=cfg.scope_name,
            credential_name=credential_name,
        ),
        kms_role=build_kms_role(
            tenant_id=tenant_id,
            scope_type=SCOPE_TYPE_SCOPE,
            scope_name=cfg.scope_name,
            credential_name=credential_name,
        ),
        cluster_name=EnvClusterService(module_env).get_cluster_name(),
        namespace=module_env.wl_app.namespace,
        service_account_name=build_service_account_name(app_code=app_code, module_name=module_name, env_name=env_name),
        # ClusterSecretStore 是集群级资源，名称已包含租户与凭证名，与 ExternalSecret、Secret 共用同一名称
        cluster_secret_store_name=resource_name,
        resource_name=resource_name,
    )
    version.save(force_insert=True)
    return version


class KMSSecretProvisioner:
    """为一个 KMSConfigVersion 创建 KMS 凭证与 ESO 资源，并等待目标 Secret 就绪

    各方法都可以重复调用：已记录的步骤直接跳过，未完成的步骤按名称核对后执行，status 不会回退。
    """

    def __init__(
        self,
        version: KMSConfigVersion,
        *,
        kms: KMSClient | None = None,
        kube: KubeResourceClient | None = None,
        kms_settings: KMSSaaSSettings | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.version = version
        self._cfg = kms_settings or load_kms_settings()
        self._kms = kms if kms is not None else make_kms_client(version.tenant_id)
        self._kube = kube if kube is not None else KubeResources.for_cluster(version.cluster_name)
        self._sleep = sleep
        self._clock = clock

    def provision(self) -> None:
        """创建凭证并提交 Kubernetes 资源，不等待 Secret 就绪"""
        self.ensure_credential()
        self.apply_resources()

    def ensure_credential(self) -> None:
        """确保 KMS 凭证存在，并记录 credential_id"""
        if self.version.credential_id is not None:
            return
        with self._recording_failure():
            self.version.credential_id = self._find_or_create_credential()
            self._advance(KMSConfigVersionStatus.CREDENTIAL_CREATED)

    def apply_resources(self) -> None:
        """依次提交 ServiceAccount、ClusterSecretStore、ExternalSecret，并记录后两者的 UID

        顺序有依赖：ESO 用 ExternalSecret 所在 namespace 中的 SA 登录，SA 必须先存在。
        """
        self.ensure_credential()
        version = self.version
        cfg = self._cfg
        labels = self._labels()
        with self._recording_failure():
            self._kube.apply(
                build_service_account(name=version.service_account_name, namespace=version.namespace, labels=labels)
            )
            store_uid = self._kube.apply(
                build_cluster_secret_store(
                    name=version.cluster_secret_store_name,
                    server=cfg.openbao_server,
                    kv_path=cfg.kv_path,
                    auth_mount=cfg.k8s_auth_mount,
                    role=version.kms_role,
                    service_account_name=version.service_account_name,
                    mtls_secret_namespace=cfg.mtls_secret_namespace,
                    mtls_secret_name=cfg.mtls_secret_name,
                    labels=labels,
                )
            )
            es_uid = self._kube.apply(
                build_external_secret(
                    name=version.resource_name,
                    namespace=version.namespace,
                    store_name=version.cluster_secret_store_name,
                    target_secret_name=version.resource_name,
                    openbao_key=version.openbao_key,
                    refresh_interval=cfg.refresh_interval,
                    labels=labels,
                )
            )
            version.cluster_secret_store_uid = store_uid
            version.external_secret_uid = es_uid
            self._advance(KMSConfigVersionStatus.RESOURCES_APPLIED)

    def wait_ready(self, *, timeout: float | None = None, poll_interval: float | None = None) -> None:
        """轮询直到目标 Secret 就绪，成功后记录 secret_uid 并进入 ready

        未提交过 Kubernetes 资源时先调用 provision。超时抛出 KMSSecretNotReadyError，
        error_reason 记录最后一次检查得到的未就绪原因。
        """
        if self.version.status == KMSConfigVersionStatus.READY.value:
            return
        if not self.version.external_secret_uid:
            self.provision()

        timeout = self._cfg.ready_timeout_seconds if timeout is None else timeout
        poll_interval = self._cfg.ready_poll_interval_seconds if poll_interval is None else poll_interval
        deadline = self._clock() + timeout
        with self._recording_failure():
            while True:
                result = self._check_secret()
                if result.ready:
                    break
                if self._clock() >= deadline:
                    raise KMSSecretNotReadyError(result.reason)
                self._sleep(poll_interval)
            self.version.secret_uid = result.secret_uid
            self._advance(KMSConfigVersionStatus.READY)

    @property
    def _scope(self) -> KMSScope:
        return KMSScope(scope_id=self._cfg.scope_id)

    @property
    def _auth(self) -> ServiceAccountAuth:
        """凭证只允许本模块环境的专用 SA 在本 namespace 中读取"""
        return ServiceAccountAuth(
            name_list=(self.version.service_account_name,),
            namespace_list=(self.version.namespace,),
        )

    def _find_or_create_credential(self) -> int:
        version = self.version
        existing = self._kms.find_credential(scope=self._scope, name=version.credential_name)
        if existing is not None:
            return self._verify_credential(existing)

        try:
            return self._kms.create_credential_from_envelope(
                scope=self._scope,
                name=version.credential_name,
                envelope=version.envelope,
                auth=self._auth,
                description=f"{version.app_code}/{version.module_name}/{version.env_name} sensitive env vars",
            )
        except KMSRequestError:
            # 请求可能已经生效，但结果未知：按名称核对，避免重复创建
            existing = self._kms.find_credential(scope=self._scope, name=version.credential_name)
            if existing is None:
                raise
            return self._verify_credential(existing)

    def _verify_credential(self, info: CredentialInfo) -> int:
        """已存在的同名凭证必须与本配置版本的期望一致，否则拒绝复用"""
        if (
            info.name != self.version.credential_name
            or info.scope != self._scope
            or not info.enable_encrypt
            or info.auth != self._auth
        ):
            raise KMSCredentialMismatchError(f"credential {info.credential_id} does not match the config version")
        return info.credential_id

    def _check_secret(self) -> SecretReadiness:
        version = self.version
        external_secret = self._kube.get(
            api_version=EXTERNAL_SECRETS_API_VERSION,
            kind=EXTERNAL_SECRET_KIND,
            name=version.resource_name,
            namespace=version.namespace,
        )
        secret = self._kube.get(
            api_version=SECRET_API_VERSION,
            kind=SECRET_KIND,
            name=version.resource_name,
            namespace=version.namespace,
        )
        result = evaluate_secret_readiness(
            external_secret=external_secret,
            secret=secret,
            expected_external_secret_uid=version.external_secret_uid,
        )
        logger.debug("KMS secret readiness, config_version: %s, reason: %s", version.id, result.reason)
        return result

    def _labels(self) -> dict[str, str]:
        version = self.version
        return {
            "paas.bk.tencent.com/code": version.app_code,
            "paas.bk.tencent.com/module-name": version.module_name,
            "paas.bk.tencent.com/environment": version.env_name,
            "paas.bk.tencent.com/kms-config-version": _hex_id(version.id),
        }

    def _advance(self, status: KMSConfigVersionStatus) -> None:
        current = self.version.status
        if current not in _PROGRESS_ORDER or _PROGRESS_ORDER.index(current) < _PROGRESS_ORDER.index(status.value):
            self.version.status = status.value
        self.version.error_reason = ""
        self.version.save()

    @contextmanager
    def _recording_failure(self) -> Iterator[None]:
        """失败时记录安全的错误分类后原样抛出。status 保持不变，重试从已完成的步骤继续"""
        try:
            yield
        except Exception as e:
            self.version.error_reason = _error_reason(e)
            self.version.save()
            raise


def _error_reason(exc: Exception) -> str:
    """把异常归为可落库的安全分类：只包含类别、业务错误码或 HTTP 状态码，不包含响应正文或 Secret 内容"""
    if isinstance(exc, KMSSecretNotReadyError):
        reason = exc.reason
    elif isinstance(exc, KMSAPIError):
        reason = f"kms_api_error_{exc.code}"
    elif isinstance(exc, ApiException):
        reason = f"kube_api_error_{exc.status}"
    else:
        reason = type(exc).__name__
    return reason[:ERROR_REASON_MAX_CHARS]


def _hex_id(value: Any) -> str:
    """配置版本 ID 统一为 32 位十六进制字符串，与数据库中的取值一致"""
    return uuid.UUID(str(value)).hex


#########################################################################
# 发布接入：部署流程使用以下函数决定哪些敏感变量交给 KMS，并生成 Secret 挂载
#########################################################################

# 敏感变量加密时写入的元数据变量。托管给 KMS 后，没有剩余密文时不再需要
_ENCRYPTION_METADATA_NAMES = frozenset({SECRET_KEY_ENV_VAR_NAME, ENCRYPTED_KEYS_ENV_NAME})

# 即使被标记为敏感，也不交给 KMS 托管、继续作为环境变量注入的内置变量（已确认的决策）
KMS_UNMANAGED_ENV_KEYS = frozenset({"BKPAAS_APP_SECRET"})


def is_kms_injection_enabled(env: ModuleEnvironment) -> bool:
    """应用是否开启 KMS 托管敏感变量。这是应用级开关，对该应用的所有模块环境生效"""
    return env.application.feature_flag.has_feature(AppFeatureFlag.KMS_SECRET_INJECTION)


def ensure_kms_injection_supported(env: ModuleEnvironment) -> None:
    """开启 KMS 时拒绝暂不支持的应用类型，避免敏感变量在没有挂载的情况下丢失

    隔离沙箱（SandboxInstance）的挂载路径尚未接入，列为后续工作。
    """
    if env.application.use_isolated_sandbox:
        raise DeployShouldAbortError("开启 KMS 托管敏感变量后，暂不支持隔离沙箱应用")


def collect_kms_managed_keys(env: ModuleEnvironment) -> frozenset[str]:
    """环境中由 KMS 托管的敏感变量键

    范围与旧版敏感变量加密保持一致：用户标记为敏感的变量，以及增强服务的隐藏/移除字段。
    KMS_UNMANAGED_ENV_KEYS 中的内置变量（BKPAAS_APP_SECRET）即使敏感也不在其中，继续作为环境变量注入。
    """
    return frozenset(collect_sensitive_keys(env)) - KMS_UNMANAGED_ENV_KEYS


def collect_kms_managed_keys_by_env(module: Module) -> dict[str, frozenset[str]]:
    """模块各环境的 KMS 托管键，用于从云原生 BkApp 中剥离敏感变量"""
    return {env.environment: collect_kms_managed_keys(env) for env in module.envs.all()}


def build_kms_secret_mount(version: KMSConfigVersion) -> SecretFileMount:
    """KMS 托管 Secret 的挂载方式：信封与私钥各为一个只读文件"""
    return SecretFileMount(
        volume_name=KMS_SECRET_VOLUME_NAME,
        secret_name=version.resource_name,
        mount_dir=KMS_SECRET_MOUNT_DIR,
        sub_paths=(SECRET_KEY_ENVELOPE, SECRET_KEY_PRIVATE_KEY),
    )


def provision_kms_secret(
    env: ModuleEnvironment,
    deployment: Deployment,
    sensitive_values: Mapping[str, str],
    *,
    kms: KMSClient | None = None,
    kube: KubeResourceClient | None = None,
    kms_settings: KMSSaaSSettings | None = None,
) -> SecretFileMount:
    """冻结本次部署的敏感变量，创建 KMS 凭证与 ESO 资源，并等待 Secret 就绪

    调用方需保证 namespace 已存在，且 sensitive_values 非空（为空时 create_kms_config_version 会报错）。
    任何一步失败都会原样抛出，部署随之失败，不会自动降级为明文注入。

    :returns: 需要挂载到主容器的 Secret 文件信息
    """
    version = create_kms_config_version(env, sensitive_values, kms=kms, kms_settings=kms_settings)
    # 先把配置版本绑定到本次部署，再发起远程请求，失败后可以从已记录的版本继续
    deployment.kms_config_version = version
    deployment.save(update_fields=["kms_config_version"])

    provisioner = KMSSecretProvisioner(version, kms=kms, kube=kube, kms_settings=kms_settings)
    provisioner.provision()
    provisioner.wait_ready()
    return build_kms_secret_mount(version)


def strip_kms_managed_env_vars(
    bkapp_res: crd.BkAppResource,
    env_name: str,
    managed_keys_by_env: Mapping[str, frozenset[str]],
) -> None:
    """从 BkApp 中移除由 KMS 托管的敏感变量：包括默认配置，以及各环境的覆盖项

    覆盖项按其所属环境的托管键过滤，因此其他环境的敏感值也不会进入本次提交的资源。
    """
    deploy_keys = managed_keys_by_env.get(env_name, frozenset())
    bkapp_res.spec.configuration.env = [var for var in bkapp_res.spec.configuration.env if var.name not in deploy_keys]

    overlay = bkapp_res.spec.envOverlay
    if overlay is None or not overlay.envVariables:
        return
    overlay.envVariables = [
        var for var in overlay.envVariables if var.name not in managed_keys_by_env.get(var.envName, frozenset())
    ]
    if not _has_encrypted_values(bkapp_res):
        overlay.envVariables = [var for var in overlay.envVariables if var.name not in _ENCRYPTION_METADATA_NAMES]


def add_kms_secret_mount(bkapp_res: crd.BkAppResource, env_name: str, mount: SecretFileMount) -> None:
    """在环境覆盖项中追加 KMS Secret 挂载。operator 会把它应用到业务进程与云原生 Hook 的容器上"""
    _ensure_mount_not_reserved(bkapp_res, env_name, mount)
    if bkapp_res.spec.envOverlay is None:
        bkapp_res.spec.envOverlay = crd.EnvOverlay()
    bkapp_res.spec.envOverlay.append_item(
        "mounts",
        crd.MountOverlay(
            envName=env_name,
            name=mount.volume_name,
            mountPath=mount.mount_dir,
            source=crd.VolumeSource(secret=crd.SecretSource(name=mount.secret_name)),
            subPaths=list(mount.sub_paths),
        ),
    )


def _has_encrypted_values(bkapp_res: crd.BkAppResource) -> bool:
    values = [var.value for var in bkapp_res.spec.configuration.env]
    overlay = bkapp_res.spec.envOverlay
    if overlay is not None and overlay.envVariables:
        values.extend(var.value for var in overlay.envVariables)
    return any(is_encrypted_value(value) for value in values)


def _ensure_mount_not_reserved(bkapp_res: crd.BkAppResource, env_name: str, mount: SecretFileMount) -> None:
    """用户自定义挂载不得占用 KMS 的卷名或目录，否则 Pod 规格会冲突，或者覆盖保留路径"""
    mounts: list[crd.Mount | crd.MountOverlay] = list(bkapp_res.spec.mounts or [])
    if bkapp_res.spec.envOverlay is not None:
        mounts.extend(m for m in bkapp_res.spec.envOverlay.mounts or [] if m.envName == env_name)

    reserved_dir = mount.mount_dir.rstrip("/")
    for user_mount in mounts:
        if (
            user_mount.name == mount.volume_name
            or user_mount.mountPath == reserved_dir
            or user_mount.mountPath.startswith(reserved_dir + "/")
        ):
            raise DeployShouldAbortError(f"挂载路径 {user_mount.mountPath} 与 KMS 保留的挂载冲突，请修改后重新部署")
