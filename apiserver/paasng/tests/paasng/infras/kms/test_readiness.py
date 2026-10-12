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

from typing import Any

import pytest

from paasng.infras.kms.readiness import evaluate_secret_readiness

ES_NAME = "kms-default-demo-web-prod-0b1f4c2e8d3a4f6b9c1d2e3f4a5b6c7d"
ES_UID = "es-uid-1"
SECRET_UID = "secret-uid-1"
READY_CONDITION = {"type": "Ready", "status": "True", "reason": "SecretSynced"}


def _external_secret(
    *, condition: dict | None = READY_CONDITION, refresh_time: str | None = "2026-10-12T08:00:00Z"
) -> dict[str, Any]:
    status: dict[str, Any] = {"conditions": [condition] if condition else []}
    if refresh_time:
        status["refreshTime"] = refresh_time
    return {"metadata": {"name": ES_NAME, "uid": ES_UID}, "status": status}


def _secret(
    *, owner_uid: str | None = ES_UID, data: dict[str, str] | None = None, uid: str = SECRET_UID
) -> dict[str, Any]:
    owners = [{"kind": "ExternalSecret", "name": ES_NAME, "uid": owner_uid}] if owner_uid else []
    return {
        "metadata": {"name": ES_NAME, "uid": uid, "ownerReferences": owners},
        "data": data if data is not None else {"envelope": "ZW52", "privateKey": "cHJpdg=="},
    }


def test_ready():
    result = evaluate_secret_readiness(
        external_secret=_external_secret(), secret=_secret(), expected_external_secret_uid=ES_UID
    )

    assert result.ready is True
    assert result.secret_uid == SECRET_UID


@pytest.mark.parametrize(
    ("external_secret", "secret", "expected_uid", "reason"),
    [
        (None, None, ES_UID, "external_secret_missing"),
        (_external_secret(), _secret(), "", "external_secret_uid_mismatch"),
        (_external_secret(), _secret(), "other-uid", "external_secret_uid_mismatch"),
        (_external_secret(condition=None), _secret(), ES_UID, "external_secret_not_ready:unknown"),
        # 只取条件的 reason，message 可能包含 OpenBao 返回的细节，不能写入数据库
        (
            _external_secret(condition={"type": "Ready", "status": "False", "reason": "Err", "message": "token=abc"}),
            _secret(),
            ES_UID,
            "external_secret_not_ready:Err",
        ),
        (_external_secret(refresh_time=None), _secret(), ES_UID, "external_secret_not_refreshed"),
        (_external_secret(), None, ES_UID, "secret_missing"),
        (_external_secret(), _secret(owner_uid="someone-else"), ES_UID, "secret_owner_mismatch"),
        (_external_secret(), _secret(owner_uid=None), ES_UID, "secret_owner_mismatch"),
        (_external_secret(), _secret(data={"envelope": "ZW52"}), ES_UID, "secret_data_missing"),
        (_external_secret(), _secret(data={"envelope": "", "privateKey": "x"}), ES_UID, "secret_data_missing"),
        (_external_secret(), _secret(uid=""), ES_UID, "secret_uid_missing"),
    ],
)
def test_not_ready(external_secret, secret, expected_uid, reason):
    result = evaluate_secret_readiness(
        external_secret=external_secret, secret=secret, expected_external_secret_uid=expected_uid
    )

    assert result.ready is False
    assert result.reason == reason
