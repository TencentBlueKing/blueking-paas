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
"""冻结敏感变量为 KMS 配置版本，创建 KMS 凭证与 ESO 资源，并等待目标 Secret 就绪"""

import hashlib
import hmac
import json
import logging
import time
import uuid
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass

from django.conf import settings
from kubernetes.client.exceptions import ApiException

from paas_wl.infras.cluster.shim import EnvClusterService
from paas_wl.workloads.release_controller.entities import SecretFileMount
from paasng.infras.kms.client import CredentialInfo, KMSClient, KMSScope, ServiceAccountAuth, make_kms_client
from paasng.infras.kms.constants import (
    KMS_SECRET_MOUNT_DIR,
    KMS_SECRET_VOLUME_NAME,
    SCOPE_TYPE_CUSTOM,
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
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.constants import KMSConfigVersionStatus
from paasng.platform.engine.models import Deployment, KMSConfigVersion

from .kube import SECRET_API_VERSION, SECRET_KIND, KubeResourceClient, KubeResources

logger = logging.getLogger(__name__)

ERROR_REASON_MAX_CHARS = 255

# status 只向前推进：重复执行已完成的步骤时不会回退
_PROGRESS_ORDER = (
    KMSConfigVersionStatus.PENDING.value,
    KMSConfigVersionStatus.CREDENTIAL_CREATED.value,
    KMSConfigVersionStatus.RESOURCES_APPLIED.value,
    KMSConfigVersionStatus.READY.value,
)


@dataclass(frozen=True)
class KMSSaaSSettings:
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
    """从 Django settings 读取配置，必填项缺失时抛出 KMSConfigError"""
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

    敏感变量内容不变时复用已就绪的版本，Secret 名称不变，避免每次部署都新建一套远端资源。
    复用时同样重新提交资源并检查就绪，集群中的资源被误删也能恢复。

    调用方需保证 namespace 已存在。任何一步失败都会原样抛出，不会降级为明文注入。
    """
    cfg = kms_settings or load_kms_settings()
    version = _find_reusable_version(env, _content_digest(sensitive_values, cfg.scope_id))
    if version is None:
        version = create_kms_config_version(env, sensitive_values, kms=kms, kms_settings=cfg)
    # 先绑定到部署再发起远程请求：失败时仍能从部署记录找到该版本，用于排查与回收。失败过的版本不会被后续部署复用
    deployment.kms_config_version = version
    deployment.save(update_fields=["kms_config_version"])

    provisioner = KMSSecretProvisioner(version, kms=kms, kube=kube, kms_settings=cfg)
    provisioner.provision()
    provisioner.wait_ready()
    return SecretFileMount(
        volume_name=KMS_SECRET_VOLUME_NAME,
        secret_name=version.resource_name,
        mount_dir=KMS_SECRET_MOUNT_DIR,
        sub_paths=(SECRET_KEY_ENVELOPE, SECRET_KEY_PRIVATE_KEY),
    )


def _find_reusable_version(env: ModuleEnvironment, content_digest: str) -> KMSConfigVersion | None:
    """同一环境、同一集群与 namespace 下，内容相同且已就绪的最新版本

    最近一次处理失败的版本（error_reason 非空）不再复用，避免远端资源损坏后每次部署都卡在同一个版本上。
    """
    return (
        KMSConfigVersion.objects.filter(
            env_id=env.pk,
            content_digest=content_digest,
            cluster_name=EnvClusterService(env).get_cluster_name(),
            namespace=env.wl_app.namespace,
            status=KMSConfigVersionStatus.READY.value,
            error_reason="",
        )
        .order_by("-created")
        .first()
    )


def _content_digest(values: Mapping[str, str], scope_id: int) -> str:
    """敏感变量内容的摘要。使用 HMAC 而不是普通哈希，避免数据库中的摘要被用来离线猜测明文"""
    content = json.dumps({"scope_id": scope_id, "env": dict(values)}, sort_keys=True, separators=(",", ":"))
    return hmac.new(settings.SECRET_KEY.encode(), content.encode(), hashlib.sha256).hexdigest()


def create_kms_config_version(
    module_env: ModuleEnvironment,
    sensitive_env_vars: Mapping[str, str],
    *,
    kms: KMSClient | None = None,
    kms_settings: KMSSaaSSettings | None = None,
) -> KMSConfigVersion:
    """冻结本次部署的敏感变量：本地加密后保存信封，生成状态为 pending 的新配置版本，不创建任何远端资源

    :raises KMSValidationError: 没有敏感变量，或明文超出上限
    :raises KMSConfigError: KMS 相关配置缺失
    """
    if not sensitive_env_vars:
        raise KMSValidationError("no sensitive env vars to freeze")
    cfg = kms_settings or load_kms_settings()

    module = module_env.module
    tenant_id = module_env.tenant_id
    app_code = module_env.application.code
    module_name = module.name
    env_name = module_env.environment
    version_id = uuid.uuid4().hex

    credential_name = build_credential_name(
        app_code=app_code, module_name=module_name, env_name=env_name, version_id=version_id
    )
    payload = build_frozen_payload(
        config_version_id=version_id,
        module_environment_id=str(module_env.pk),
        env_vars=sensitive_env_vars,
    )
    envelope = (kms or make_kms_client(tenant_id)).encrypt_credential_value(payload)

    return KMSConfigVersion.objects.create(
        id=version_id,
        tenant_id=tenant_id,
        app_code=app_code,
        module_name=module_name,
        env_name=env_name,
        env_id=module_env.pk,
        status=KMSConfigVersionStatus.PENDING.value,
        envelope=envelope,
        content_digest=_content_digest(sensitive_env_vars, cfg.scope_id),
        kms_scope_id=cfg.scope_id,
        credential_name=credential_name,
        openbao_key=build_openbao_key(
            tenant_id=tenant_id,
            scope_type=SCOPE_TYPE_CUSTOM,
            scope_name=cfg.scope_name,
            credential_name=credential_name,
        ),
        kms_role=build_kms_role(
            tenant_id=tenant_id,
            scope_type=SCOPE_TYPE_CUSTOM,
            scope_name=cfg.scope_name,
            credential_name=credential_name,
        ),
        cluster_name=EnvClusterService(module_env).get_cluster_name(),
        namespace=module_env.wl_app.namespace,
        service_account_name=build_service_account_name(app_code=app_code, module_name=module_name, env_name=env_name),
        resource_name=build_resource_name(credential_name=credential_name),
    )


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

    def ensure_credential(self) -> None:
        """确保 KMS 凭证存在，并记录 credential_id"""
        if self.version.credential_id is not None:
            return
        with self._recording_failure():
            self.version.credential_id = self._find_or_create_credential()
            self._advance(KMSConfigVersionStatus.CREDENTIAL_CREATED)

    def provision(self) -> None:
        """创建凭证，依次提交 ServiceAccount、ClusterSecretStore、ExternalSecret，并记录 ExternalSecret 的 UID

        ESO 用 ExternalSecret 所在 namespace 中的 SA 登录，SA 必须先存在。
        """
        self.ensure_credential()
        version = self.version
        cfg = self._cfg
        labels = self._labels()
        with self._recording_failure():
            self._kube.apply(
                build_service_account(name=version.service_account_name, namespace=version.namespace, labels=labels)
            )
            self._kube.apply(
                build_cluster_secret_store(
                    name=version.resource_name,
                    server=cfg.openbao_server,
                    kv_path=cfg.kv_path,
                    auth_mount=cfg.k8s_auth_mount,
                    role=version.kms_role,
                    namespace=version.namespace,
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
                    store_name=version.resource_name,
                    target_secret_name=version.resource_name,
                    openbao_key=version.openbao_key,
                    refresh_interval=cfg.refresh_interval,
                    labels=labels,
                )
            )
            version.external_secret_uid = es_uid
            self._advance(KMSConfigVersionStatus.RESOURCES_APPLIED)

    def wait_ready(self, *, timeout: float | None = None, poll_interval: float | None = None) -> None:
        """轮询直到目标 Secret 就绪，需先调用 provision。超时抛出 KMSSecretNotReadyError，error_reason 记录最后一次的未就绪原因"""
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
            self._advance(KMSConfigVersionStatus.READY)

    @property
    def _scope(self) -> KMSScope:
        return KMSScope(scope_id=self.version.kms_scope_id)

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
            "paas.bk.tencent.com/kms-config-version": uuid.UUID(str(version.id)).hex,
        }

    def _advance(self, status: KMSConfigVersionStatus) -> None:
        if _PROGRESS_ORDER.index(self.version.status) < _PROGRESS_ORDER.index(status.value):
            self.version.status = status.value
        self.version.error_reason = ""
        self.version.save()

    @contextmanager
    def _recording_failure(self) -> Iterator[None]:
        """失败时记录错误分类后原样抛出，status 保持不变"""
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
