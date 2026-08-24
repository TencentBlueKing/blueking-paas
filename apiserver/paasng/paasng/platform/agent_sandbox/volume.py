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

from django.db import transaction

from paasng.platform.agent_sandbox.constants import VOLUME_SHARED_APP_CODES_MAX
from paasng.platform.agent_sandbox.exceptions import VolumeGranteeNotFound, VolumeShareLimitExceeded
from paasng.platform.agent_sandbox.models import Volume
from paasng.platform.applications.models import Application


def share_volume(volume: Volume, grantee_app_code: str) -> None:
    """授权另一应用把 ``volume`` 挂到自己的沙箱下。

    幂等：重复授权同一应用不会重复写入，也不会因为已达上限而失败。

    :param volume: 待授权的 Volume，调用方需已校验其归属与未删除状态。
    :param grantee_app_code: 被授权应用的 code，必须与 Volume 属于同一租户。
    :raises VolumeGranteeNotFound: 同租户下不存在该应用。
    :raises VolumeShareLimitExceeded: 授权应用数量已达上限。
    """
    grantee = Application.objects.filter(code=grantee_app_code, tenant_id=volume.tenant_id).first()
    if not grantee:
        raise VolumeGranteeNotFound(f"application {grantee_app_code} not found in tenant {volume.tenant_id}")

    # 归属方本来就能挂载，不必写入 shared_app_codes
    if grantee.pk == volume.application_id:
        return

    with transaction.atomic():
        locked = Volume.objects.select_for_update().get(pk=volume.pk)
        codes = list(locked.shared_app_codes or [])
        if grantee_app_code in codes:
            return
        if len(codes) >= VOLUME_SHARED_APP_CODES_MAX:
            raise VolumeShareLimitExceeded(
                f"volume {locked.uuid} has reached the limit of {VOLUME_SHARED_APP_CODES_MAX} grantees"
            )
        locked.shared_app_codes = [*codes, grantee_app_code]
        locked.save(update_fields=["shared_app_codes", "updated"])


def unshare_volume(volume: Volume, grantee_app_code: str) -> None:
    """撤销对指定应用的挂载授权。幂等。

    :param volume: 待撤销授权的 Volume，调用方需已校验其归属与未删除状态。
    :param grantee_app_code: 被撤销授权的应用 code。
    """
    with transaction.atomic():
        locked = Volume.objects.select_for_update().get(pk=volume.pk)
        codes = list(locked.shared_app_codes or [])
        if grantee_app_code not in codes:
            return
        locked.shared_app_codes = [c for c in codes if c != grantee_app_code]
        locked.save(update_fields=["shared_app_codes", "updated"])
