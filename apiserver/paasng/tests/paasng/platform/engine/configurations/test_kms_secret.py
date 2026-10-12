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

import copy
import json
import posixpath
from typing import Any
from unittest.mock import PropertyMock

import pytest
from django.test import override_settings
from kubernetes.client.exceptions import ApiException

from paas_wl.bk_app.cnative.specs.crd import bk_app as crd
from paas_wl.bk_app.cnative.specs.crd.metadata import ObjectMetadata
from paas_wl.bk_app.processes.entities import SecretFileMount
from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.infras.kms.client import CredentialInfo, KMSClient, KMSScope, ServiceAccountAuth
from paasng.infras.kms.constants import (
    KMS_SECRET_MOUNT_DIR,
    KMS_SECRET_VOLUME_NAME,
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
from paasng.infras.kms.naming import build_service_account_name
from paasng.platform.applications.constants import AppFeatureFlag
from paasng.platform.applications.models import Application
from paasng.platform.engine.configurations.env_var.encryption import (
    CIPHER_PREFIX,
    ENCRYPTED_KEYS_ENV_NAME,
    SECRET_KEY_ENV_VAR_NAME,
)
from paasng.platform.engine.configurations.kms_secret import (
    KMS_UNMANAGED_ENV_KEYS,
    KMSSaaSSettings,
    KMSSecretProvisioner,
    KubeResources,
    add_kms_secret_mount,
    build_kms_secret_mount,
    collect_kms_managed_keys,
    collect_kms_managed_keys_by_env,
    create_kms_config_version,
    ensure_kms_injection_supported,
    is_kms_injection_enabled,
    load_kms_settings,
    provision_kms_secret,
    strip_kms_managed_env_vars,
)
from paasng.platform.engine.constants import KMSConfigVersionStatus
from paasng.platform.engine.exceptions import DeployShouldAbortError
from paasng.platform.engine.models import KMSConfigVersion

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

CLUSTER_NAME = "test-cluster"
SCOPE_NAME = "test-scope"
ES_API_VERSION = "external-secrets.io/v1beta1"
SENSITIVE_ENV = {"DB_PASSWORD": "s3cret-value-xyz", "API_TOKEN": "tok-abc-123"}


class FakeKMS(KMSClient):
    """KMSClient 的替身：凭证保存在内存中，并记录收到的信封与明文次数

    继承 KMSClient 仅为通过类型检查，不调用其构造函数，也不发起任何网络请求。
    未覆盖的方法调用会因缺少会话而失败，避免测试悄悄访问真实 KMS。
    """

    def __init__(self) -> None:
        self.plaintexts: list[str] = []
        self.credentials: dict[str, CredentialInfo] = {}
        self.envelopes: dict[str, str] = {}
        self.created: list[str] = []
        # 创建请求已生效，但调用方收到网络错误
        self.create_outcome_unknown = False
        self.fail_create_with: Exception | None = None
        self._next_id = 100

    def encrypt_credential_value(self, plaintext: str) -> str:
        self.plaintexts.append(plaintext)
        return f"envelope-{len(self.plaintexts)}"

    def find_credential(self, *, scope: KMSScope, name: str) -> CredentialInfo | None:
        return self.credentials.get(name)

    def create_credential_from_envelope(
        self,
        *,
        scope: KMSScope,
        name: str,
        envelope: str,
        auth: ServiceAccountAuth,
        description: str = "",
        annotation: str = "",
    ) -> int:
        if self.fail_create_with is not None:
            raise self.fail_create_with
        if name in self.credentials:
            raise KMSAPIError(1000, "credential already exists")
        self._next_id += 1
        self.credentials[name] = CredentialInfo(
            credential_id=self._next_id, scope=scope, name=name, enable_encrypt=True, auth=auth
        )
        self.envelopes[name] = envelope
        self.created.append(name)
        if self.create_outcome_unknown:
            raise KMSRequestError("timeout after the request was accepted")
        return self._next_id


class FakeKube:
    """Kubernetes 替身：按 (apiVersion, kind, namespace, name) 保存对象，UID 在首次 apply 时分配"""

    def __init__(self):
        self.objects: dict[tuple[str, str, str | None, str], dict[str, Any]] = {}
        self.applied_kinds: list[str] = []
        self.get_calls = 0
        self.fail_apply_with: Exception | None = None
        self._seq = 0

    def apply(self, manifest):
        if self.fail_apply_with is not None:
            raise self.fail_apply_with
        meta = manifest["metadata"]
        key = (manifest["apiVersion"], manifest["kind"], meta.get("namespace"), meta["name"])
        self.applied_kinds.append(manifest["kind"])
        existing = self.objects.get(key)
        if existing is None:
            self._seq += 1
            uid = f"uid-{self._seq}"
        else:
            uid = existing["metadata"]["uid"]
        obj = copy.deepcopy(dict(manifest))
        obj["metadata"] = {**obj["metadata"], "uid": uid}
        if existing is not None and "status" in existing:
            obj["status"] = existing["status"]
        self.objects[key] = obj
        return uid

    def get(self, *, api_version, kind, name, namespace):
        self.get_calls += 1
        return copy.deepcopy(self.objects.get((api_version, kind, namespace, name)))

    def mark_synced(self, namespace: str, name: str) -> None:
        """模拟 ESO 同步成功：ExternalSecret 变为 Ready，并生成带 ownerReference 的目标 Secret"""
        es = self.objects[(ES_API_VERSION, "ExternalSecret", namespace, name)]
        es["status"] = {
            "conditions": [{"type": "Ready", "status": "True", "reason": "SecretSynced"}],
            "refreshTime": "2026-10-12T08:00:00Z",
        }
        self.objects[("v1", "Secret", namespace, name)] = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": name,
                "namespace": namespace,
                "uid": "secret-uid-1",
                "ownerReferences": [
                    {
                        "apiVersion": ES_API_VERSION,
                        "kind": "ExternalSecret",
                        "name": name,
                        "uid": es["metadata"]["uid"],
                    }
                ],
            },
            "data": {"envelope": "ZW52", "privateKey": "cHJpdg=="},
        }


@pytest.fixture()
def kms_cfg() -> KMSSaaSSettings:
    return KMSSaaSSettings(
        scope_id=15,
        scope_name=SCOPE_NAME,
        openbao_server="https://openbao.example.com",
        kv_path="secret",
        k8s_auth_mount="kubernetes",
        mtls_secret_namespace="paas-system",
        mtls_secret_name="openbao-mtls-client",
        refresh_interval="1h",
        ready_timeout_seconds=300,
        ready_poll_interval_seconds=5,
    )


@pytest.fixture()
def version(bk_stag_env, wl_app, mocker, kms_cfg) -> KMSConfigVersion:
    """一个已冻结、状态为 pending 的配置版本"""
    mocker.patch.object(EnvClusterService, "get_cluster_name", return_value=CLUSTER_NAME)
    return create_kms_config_version(bk_stag_env, SENSITIVE_ENV, kms=FakeKMS(), kms_settings=kms_cfg)


@pytest.fixture()
def kms() -> FakeKMS:
    return FakeKMS()


@pytest.fixture()
def kube() -> FakeKube:
    return FakeKube()


@pytest.fixture()
def make_provisioner(kms, kube, kms_cfg):
    def maker(version: KMSConfigVersion, **kwargs) -> KMSSecretProvisioner:
        return KMSSecretProvisioner(version, kms=kms, kube=kube, kms_settings=kms_cfg, **kwargs)

    return maker


class TestCreateKMSConfigVersion:
    def test_freezes_env_vars_and_stores_only_envelope(self, bk_stag_env, wl_app, mocker, kms_cfg):
        mocker.patch.object(EnvClusterService, "get_cluster_name", return_value=CLUSTER_NAME)
        kms = FakeKMS()

        version = create_kms_config_version(bk_stag_env, SENSITIVE_ENV, kms=kms, kms_settings=kms_cfg)

        # 明文只交给加密一次，且包含本配置版本的 ID
        assert len(kms.plaintexts) == 1
        payload = json.loads(kms.plaintexts[0])
        assert payload["config_version_id"] == version.id
        assert payload["env"] == SENSITIVE_ENV

        row = KMSConfigVersion.objects.get(pk=version.id)
        assert row.status == KMSConfigVersionStatus.PENDING.value
        assert row.envelope == "envelope-1"
        # 数据库中的任何字段都不包含明文
        stored = " ".join(str(getattr(row, f.attname)) for f in KMSConfigVersion._meta.concrete_fields)
        assert "s3cret-value-xyz" not in stored
        assert "tok-abc-123" not in stored

    def test_names_are_derived_from_version(self, bk_stag_env, version):
        app_code = bk_stag_env.application.code
        module_name = bk_stag_env.module.name

        assert len(version.id) == 32
        assert version.credential_name.endswith(version.id)
        assert version.openbao_key == f"{version.tenant_id}/scope/{SCOPE_NAME}/secret/{version.credential_name}"
        assert version.kms_role == f"{version.tenant_id}.scope.{SCOPE_NAME}.secret.{version.credential_name}"
        assert version.resource_name == f"kms-{version.tenant_id}-{version.credential_name}"
        assert version.cluster_secret_store_name == version.resource_name
        assert version.service_account_name == build_service_account_name(
            app_code=app_code, module_name=module_name, env_name=bk_stag_env.environment
        )
        assert version.namespace == bk_stag_env.wl_app.namespace
        assert version.cluster_name == CLUSTER_NAME
        assert version.kms_scope_id == 15

    def test_each_call_creates_a_new_version(self, bk_stag_env, wl_app, mocker, kms_cfg):
        mocker.patch.object(EnvClusterService, "get_cluster_name", return_value=CLUSTER_NAME)

        first = create_kms_config_version(bk_stag_env, SENSITIVE_ENV, kms=FakeKMS(), kms_settings=kms_cfg)
        second = create_kms_config_version(bk_stag_env, SENSITIVE_ENV, kms=FakeKMS(), kms_settings=kms_cfg)

        assert first.id != second.id
        assert first.credential_name != second.credential_name
        assert KMSConfigVersion.objects.count() == 2

    def test_rejects_empty_sensitive_env(self, bk_stag_env, wl_app, kms_cfg):
        with pytest.raises(KMSValidationError):
            create_kms_config_version(bk_stag_env, {}, kms=FakeKMS(), kms_settings=kms_cfg)

        assert KMSConfigVersion.objects.count() == 0

    def test_missing_settings_fail_before_any_request(self, bk_stag_env, wl_app):
        kms = FakeKMS()

        with override_settings(KMS_SAAS_SCOPE_ID=0), pytest.raises(KMSConfigError, match="KMS_SAAS_SCOPE_ID"):
            create_kms_config_version(bk_stag_env, SENSITIVE_ENV, kms=kms)

        assert kms.plaintexts == []
        assert KMSConfigVersion.objects.count() == 0


class TestLoadKMSSettings:
    def test_reports_all_missing_required_settings(self):
        with (
            override_settings(KMS_SAAS_SCOPE_ID=0, KMS_SAAS_SCOPE_NAME="", KMS_OPENBAO_SERVER=""),
            pytest.raises(KMSConfigError) as exc_info,
        ):
            load_kms_settings()

        message = str(exc_info.value)
        assert "KMS_SAAS_SCOPE_ID" in message
        assert "KMS_SAAS_SCOPE_NAME" in message
        assert "KMS_OPENBAO_SERVER" in message


class TestKMSSecretProvisioner:
    def test_provision_creates_credential_and_resources(self, version, make_provisioner, kms, kube):
        make_provisioner(version).provision()

        version.refresh_from_db()
        assert version.status == KMSConfigVersionStatus.RESOURCES_APPLIED.value
        credential = kms.credentials[version.credential_name]
        assert version.credential_id == credential.credential_id
        # 凭证使用冻结时保存的信封，且只允许本环境的专用 SA 在本 namespace 中读取
        assert kms.envelopes[version.credential_name] == version.envelope
        assert credential.auth == ServiceAccountAuth(
            name_list=(version.service_account_name,), namespace_list=(version.namespace,)
        )

        # 提交顺序：SA 必须先于 ExternalSecret 存在
        assert kube.applied_kinds == ["ServiceAccount", "ClusterSecretStore", "ExternalSecret"]
        store = kube.get(
            api_version=ES_API_VERSION,
            kind="ClusterSecretStore",
            name=version.cluster_secret_store_name,
            namespace=None,
        )
        assert store["spec"]["provider"]["vault"]["auth"]["kubernetes"]["role"] == version.kms_role
        es = kube.get(
            api_version=ES_API_VERSION, kind="ExternalSecret", name=version.resource_name, namespace=version.namespace
        )
        assert es["spec"]["target"] == {
            "name": version.resource_name,
            "creationPolicy": "Owner",
            "deletionPolicy": "Retain",
        }
        assert es["spec"]["data"][0]["remoteRef"]["key"] == version.openbao_key
        assert version.cluster_secret_store_uid == store["metadata"]["uid"]
        assert version.external_secret_uid == es["metadata"]["uid"]

    def test_provision_is_idempotent(self, version, make_provisioner, kms, kube):
        provisioner = make_provisioner(version)
        provisioner.provision()
        uids = (version.cluster_secret_store_uid, version.external_secret_uid)

        provisioner.provision()

        assert kms.created == [version.credential_name]
        assert (version.cluster_secret_store_uid, version.external_secret_uid) == uids
        assert version.status == KMSConfigVersionStatus.RESOURCES_APPLIED.value

    def test_existing_matching_credential_is_adopted(self, version, make_provisioner, kms):
        provisioner = make_provisioner(version)
        provisioner.provision()
        version.credential_id = None  # 模拟保存 credential_id 之前进程中断
        version.save()

        provisioner.ensure_credential()

        assert kms.created == [version.credential_name]
        assert version.credential_id == kms.credentials[version.credential_name].credential_id

    def test_unknown_create_outcome_is_reconciled_by_name(self, version, make_provisioner, kms):
        kms.create_outcome_unknown = True

        make_provisioner(version).ensure_credential()

        version.refresh_from_db()
        assert kms.created == [version.credential_name]
        assert version.credential_id == kms.credentials[version.credential_name].credential_id
        assert version.status == KMSConfigVersionStatus.CREDENTIAL_CREATED.value
        assert version.error_reason == ""

    def test_mismatched_existing_credential_is_rejected(self, version, make_provisioner, kms):
        kms.credentials[version.credential_name] = CredentialInfo(
            credential_id=7,
            scope=KMSScope(scope_id=15),
            name=version.credential_name,
            enable_encrypt=True,
            auth=ServiceAccountAuth(name_list=("other-sa",), namespace_list=("other-ns",)),
        )

        with pytest.raises(KMSCredentialMismatchError):
            make_provisioner(version).ensure_credential()

        version.refresh_from_db()
        assert kms.created == []
        assert version.credential_id is None
        assert version.status == KMSConfigVersionStatus.PENDING.value
        assert version.error_reason == "KMSCredentialMismatchError"

    def test_kms_api_error_is_recorded_without_advancing(self, version, make_provisioner, kms):
        kms.fail_create_with = KMSAPIError(1010, "server busy")

        with pytest.raises(KMSAPIError):
            make_provisioner(version).ensure_credential()

        version.refresh_from_db()
        assert version.status == KMSConfigVersionStatus.PENDING.value
        assert version.error_reason == "kms_api_error_1010"

    def test_kube_api_error_is_recorded_without_advancing(self, version, make_provisioner, kube):
        kube.fail_apply_with = ApiException(status=403, reason="Forbidden")

        with pytest.raises(ApiException):
            make_provisioner(version).provision()

        version.refresh_from_db()
        # 凭证步骤已完成，停在最后完成的步骤
        assert version.status == KMSConfigVersionStatus.CREDENTIAL_CREATED.value
        assert version.credential_id is not None
        assert version.error_reason == "kube_api_error_403"

    def test_wait_ready_polls_until_secret_is_synced(self, version, make_provisioner, kube):
        provisioner = make_provisioner(
            version,
            # 第一次检查未就绪，sleep 之后 ESO 完成同步
            sleep=lambda _: kube.mark_synced(version.namespace, version.resource_name),
        )
        provisioner.provision()

        provisioner.wait_ready(timeout=60, poll_interval=0)

        version.refresh_from_db()
        assert version.status == KMSConfigVersionStatus.READY.value
        assert version.secret_uid == "secret-uid-1"
        assert version.error_reason == ""

    def test_wait_ready_timeout_records_last_reason(self, version, make_provisioner):
        provisioner = make_provisioner(version)
        provisioner.provision()

        with pytest.raises(KMSSecretNotReadyError) as exc_info:
            provisioner.wait_ready(timeout=0, poll_interval=0)

        version.refresh_from_db()
        assert exc_info.value.reason == "external_secret_not_ready:unknown"
        assert version.error_reason == "external_secret_not_ready:unknown"
        # 超时不回退 status，也不把 status 改成 failed：重试时从已提交的资源继续
        assert version.status == KMSConfigVersionStatus.RESOURCES_APPLIED.value

    def test_wait_ready_is_noop_when_already_ready(self, version, make_provisioner, kube):
        provisioner = make_provisioner(
            version, sleep=lambda _: kube.mark_synced(version.namespace, version.resource_name)
        )
        provisioner.provision()
        provisioner.wait_ready(timeout=60, poll_interval=0)
        calls_before = kube.get_calls

        provisioner.wait_ready(timeout=60, poll_interval=0)

        assert kube.get_calls == calls_before

    def test_reapply_never_moves_status_backwards(self, version, make_provisioner, kube):
        provisioner = make_provisioner(
            version, sleep=lambda _: kube.mark_synced(version.namespace, version.resource_name)
        )
        provisioner.provision()
        provisioner.wait_ready(timeout=60, poll_interval=0)

        provisioner.apply_resources()

        version.refresh_from_db()
        assert version.status == KMSConfigVersionStatus.READY.value


class TestKubeResources:
    def test_unsupported_kind_is_rejected(self):
        resources = KubeResources(client=None)

        with pytest.raises(ValueError, match="unsupported kind"):
            resources._get_kres("v1", "Pod")


KMS_MODULE = "paasng.platform.engine.configurations.kms_secret"


class SyncingKube(FakeKube):
    """apply ExternalSecret 后立即模拟 ESO 同步完成，使 wait_ready 无需真正等待"""

    def apply(self, manifest):
        uid = super().apply(manifest)
        if manifest["kind"] == "ExternalSecret":
            self.mark_synced(manifest["metadata"]["namespace"], manifest["metadata"]["name"])
        return uid


def _make_bkapp(
    env_vars: list[tuple[str, str]] | None = None,
    overlay_vars: list[tuple[str, str, str]] | None = None,
    mounts: list[crd.Mount] | None = None,
    overlay_mounts: list[crd.MountOverlay] | None = None,
) -> crd.BkAppResource:
    """构造只包含配置相关字段的 BkApp。overlay_vars 的每一项为 (envName, name, value)"""
    overlay = None
    if overlay_vars or overlay_mounts:
        overlay = crd.EnvOverlay(
            envVariables=[crd.EnvVarOverlay(envName=e, name=n, value=v) for e, n, v in overlay_vars or []] or None,
            mounts=overlay_mounts,
        )
    return crd.BkAppResource(
        metadata=ObjectMetadata(name="app"),
        spec=crd.BkAppSpec(
            configuration=crd.BkAppConfiguration(env=[crd.EnvVar(name=n, value=v) for n, v in env_vars or []]),
            mounts=mounts,
            envOverlay=overlay,
        ),
    )


def _overlay(bkapp: crd.BkAppResource) -> crd.EnvOverlay:
    assert bkapp.spec.envOverlay is not None
    return bkapp.spec.envOverlay


def _secret_source_mount(name: str, mount_path: str) -> crd.Mount:
    return crd.Mount(name=name, mountPath=mount_path, source=crd.VolumeSource(secret=crd.SecretSource(name="user")))


@pytest.fixture()
def kms_mount() -> SecretFileMount:
    return SecretFileMount(
        volume_name=KMS_SECRET_VOLUME_NAME,
        secret_name="kms-res-1",
        mount_dir=KMS_SECRET_MOUNT_DIR,
        sub_paths=(SECRET_KEY_ENVELOPE, SECRET_KEY_PRIVATE_KEY),
    )


class TestKMSInjectionGate:
    """开关与支持范围"""

    def test_disabled_by_default(self, bk_stag_env):
        assert is_kms_injection_enabled(bk_stag_env) is False

    def test_enabled_by_feature_flag(self, bk_stag_env):
        bk_stag_env.application.feature_flag.set_feature(AppFeatureFlag.KMS_SECRET_INJECTION, True)
        assert is_kms_injection_enabled(bk_stag_env) is True

    def test_normal_app_is_supported(self, bk_stag_env):
        ensure_kms_injection_supported(bk_stag_env)

    def test_isolated_sandbox_is_rejected(self, bk_stag_env, mocker):
        mocker.patch.object(Application, "use_isolated_sandbox", new_callable=PropertyMock, return_value=True)

        with pytest.raises(DeployShouldAbortError):
            ensure_kms_injection_supported(bk_stag_env)


class TestCollectKMSManagedKeys:
    def test_excludes_unmanaged_builtin_keys(self, bk_stag_env, mocker):
        mocker.patch(f"{KMS_MODULE}.collect_sensitive_keys", return_value={"DB_PASSWORD", "BKPAAS_APP_SECRET"})

        assert collect_kms_managed_keys(bk_stag_env) == {"DB_PASSWORD"}
        assert "BKPAAS_APP_SECRET" in KMS_UNMANAGED_ENV_KEYS

    def test_keys_are_collected_per_environment(self, bk_module, bk_stag_env, bk_prod_env, mocker):
        def fake_collect(env):
            return {"STAG_KEY"} if env.environment == bk_stag_env.environment else {"PROD_KEY"}

        mocker.patch(f"{KMS_MODULE}.collect_sensitive_keys", side_effect=fake_collect)

        assert collect_kms_managed_keys_by_env(bk_module) == {
            bk_stag_env.environment: frozenset({"STAG_KEY"}),
            bk_prod_env.environment: frozenset({"PROD_KEY"}),
        }


class TestBuildKMSSecretMount:
    def test_mount_matches_sdk_paths(self, version):
        mount = build_kms_secret_mount(version)

        assert mount.volume_name == KMS_SECRET_VOLUME_NAME
        assert mount.secret_name == version.resource_name
        assert mount.mount_dir == KMS_SECRET_MOUNT_DIR
        assert mount.sub_paths == (SECRET_KEY_ENVELOPE, SECRET_KEY_PRIVATE_KEY)
        # 与 SDK 约定的文件路径保持一致
        assert posixpath.join(mount.mount_dir, SECRET_KEY_ENVELOPE) == "/etc/kms/envelope"
        assert posixpath.join(mount.mount_dir, SECRET_KEY_PRIVATE_KEY) == "/etc/kms/privateKey"


class TestStripKMSManagedEnvVars:
    def test_removes_managed_keys_from_default_and_overlays(self):
        bkapp = _make_bkapp(
            env_vars=[("DB_PASSWORD", "s3cret"), ("PLAIN", "1")],
            overlay_vars=[
                ("stag", "DB_PASSWORD", "s3cret-stag"),
                ("prod", "DB_PASSWORD", f"{CIPHER_PREFIX}abc"),
                ("prod", "TOKEN", "tok"),
            ],
        )

        strip_kms_managed_env_vars(bkapp, "stag", {"stag": frozenset({"DB_PASSWORD"}), "prod": frozenset({"TOKEN"})})

        assert [var.name for var in bkapp.spec.configuration.env] == ["PLAIN"]
        # 覆盖项按各自环境的托管键过滤：stag 的托管键不影响 prod 的覆盖项
        assert [(var.envName, var.name) for var in _overlay(bkapp).envVariables or []] == [("prod", "DB_PASSWORD")]

    def test_without_overlay(self):
        bkapp = _make_bkapp(env_vars=[("DB_PASSWORD", "s3cret")])

        strip_kms_managed_env_vars(bkapp, "stag", {"stag": frozenset({"DB_PASSWORD"})})

        assert bkapp.spec.configuration.env == []
        assert bkapp.spec.envOverlay is None

    def test_encryption_metadata_removed_when_no_ciphertext_left(self):
        bkapp = _make_bkapp(
            overlay_vars=[
                ("stag", "DB_PASSWORD", f"{CIPHER_PREFIX}abc"),
                ("stag", SECRET_KEY_ENV_VAR_NAME, "key"),
                ("stag", ENCRYPTED_KEYS_ENV_NAME, "DB_PASSWORD"),
            ],
        )

        strip_kms_managed_env_vars(bkapp, "stag", {"stag": frozenset({"DB_PASSWORD"})})

        assert _overlay(bkapp).envVariables == []

    def test_encryption_metadata_kept_when_other_ciphertext_remains(self):
        bkapp = _make_bkapp(
            overlay_vars=[
                ("stag", "DB_PASSWORD", f"{CIPHER_PREFIX}abc"),
                ("prod", "TOKEN", f"{CIPHER_PREFIX}def"),
                ("prod", SECRET_KEY_ENV_VAR_NAME, "key"),
                ("prod", ENCRYPTED_KEYS_ENV_NAME, "TOKEN"),
            ],
        )

        strip_kms_managed_env_vars(bkapp, "stag", {"stag": frozenset({"DB_PASSWORD"})})

        # prod 的密文仍然存在，元数据必须保留，否则 prod 的密文无法解密
        assert [(var.envName, var.name) for var in _overlay(bkapp).envVariables or []] == [
            ("prod", "TOKEN"),
            ("prod", SECRET_KEY_ENV_VAR_NAME),
            ("prod", ENCRYPTED_KEYS_ENV_NAME),
        ]


class TestAddKMSSecretMount:
    def test_appends_overlay_mount_for_env(self, kms_mount):
        bkapp = _make_bkapp()

        add_kms_secret_mount(bkapp, "stag", kms_mount)

        assert bkapp.to_deployable()["spec"]["envOverlay"]["mounts"] == [
            {
                "envName": "stag",
                "name": KMS_SECRET_VOLUME_NAME,
                "mountPath": KMS_SECRET_MOUNT_DIR,
                "source": {"secret": {"name": "kms-res-1"}},
                "subPaths": [SECRET_KEY_ENVELOPE, SECRET_KEY_PRIVATE_KEY],
            }
        ]

    @pytest.mark.parametrize(
        ("name", "mount_path", "conflict"),
        [
            (KMS_SECRET_VOLUME_NAME, "/data", True),  # 卷名与 KMS 卷相同
            ("data", KMS_SECRET_MOUNT_DIR, True),  # 目录与 KMS 目录相同
            ("data", f"{KMS_SECRET_MOUNT_DIR}/extra", True),  # 位于 KMS 目录之下
            ("data", "/etc/kms-other", False),  # 只是前缀相同，不是子目录
        ],
    )
    def test_user_global_mount_conflicts(self, kms_mount, name, mount_path, conflict):
        bkapp = _make_bkapp(mounts=[_secret_source_mount(name, mount_path)])

        if conflict:
            with pytest.raises(DeployShouldAbortError):
                add_kms_secret_mount(bkapp, "stag", kms_mount)
        else:
            add_kms_secret_mount(bkapp, "stag", kms_mount)
            assert [m.name for m in _overlay(bkapp).mounts or []] == [KMS_SECRET_VOLUME_NAME]

    def test_overlay_mount_of_same_env_conflicts(self, kms_mount):
        bkapp = _make_bkapp(
            overlay_mounts=[
                crd.MountOverlay(
                    envName="stag",
                    name="data",
                    mountPath=KMS_SECRET_MOUNT_DIR,
                    source=crd.VolumeSource(secret=crd.SecretSource(name="user")),
                )
            ]
        )

        with pytest.raises(DeployShouldAbortError):
            add_kms_secret_mount(bkapp, "stag", kms_mount)

    def test_overlay_mount_of_other_env_does_not_conflict(self, kms_mount):
        bkapp = _make_bkapp(
            overlay_mounts=[
                crd.MountOverlay(
                    envName="prod",
                    name=KMS_SECRET_VOLUME_NAME,
                    mountPath=KMS_SECRET_MOUNT_DIR,
                    source=crd.VolumeSource(secret=crd.SecretSource(name="user")),
                )
            ]
        )

        add_kms_secret_mount(bkapp, "stag", kms_mount)

        assert [m.envName for m in _overlay(bkapp).mounts or []] == ["prod", "stag"]


class TestProvisionKMSSecret:
    @pytest.fixture()
    def _cluster(self, mocker):
        mocker.patch.object(EnvClusterService, "get_cluster_name", return_value=CLUSTER_NAME)

    @pytest.mark.usefixtures("wl_app", "_cluster")
    def test_provisions_and_links_deployment(self, bk_stag_env, bk_deployment, kms, kms_cfg):
        kube = SyncingKube()

        mount = provision_kms_secret(
            bk_stag_env, bk_deployment, SENSITIVE_ENV, kms=kms, kube=kube, kms_settings=kms_cfg
        )

        bk_deployment.refresh_from_db()
        version = bk_deployment.kms_config_version
        assert version is not None
        assert version.status == KMSConfigVersionStatus.READY.value
        assert version.secret_uid
        assert mount == build_kms_secret_mount(version)
        assert kms.created == [version.credential_name]
        assert kube.applied_kinds == ["ServiceAccount", "ClusterSecretStore", "ExternalSecret"]

    @pytest.mark.usefixtures("wl_app", "_cluster")
    def test_kms_failure_keeps_deployment_linked(self, bk_stag_env, bk_deployment, kms, kms_cfg):
        kube = SyncingKube()
        kms.fail_create_with = KMSAPIError(1000, "boom")

        with pytest.raises(KMSAPIError):
            provision_kms_secret(bk_stag_env, bk_deployment, SENSITIVE_ENV, kms=kms, kube=kube, kms_settings=kms_cfg)

        bk_deployment.refresh_from_db()
        version = bk_deployment.kms_config_version
        assert version is not None
        assert version.status == KMSConfigVersionStatus.PENDING.value
        assert version.error_reason == "kms_api_error_1000"
        # 失败后不会下发任何 Kubernetes 资源
        assert kube.applied_kinds == []

    @pytest.mark.usefixtures("wl_app", "_cluster")
    def test_empty_sensitive_values_are_rejected(self, bk_stag_env, bk_deployment, kms, kms_cfg):
        with pytest.raises(KMSValidationError):
            provision_kms_secret(bk_stag_env, bk_deployment, {}, kms=kms, kube=SyncingKube(), kms_settings=kms_cfg)

        bk_deployment.refresh_from_db()
        assert bk_deployment.kms_config_version is None
        assert kms.created == []
