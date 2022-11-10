# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import logging
import math

from svc_bk_repo.vendor.exceptions import ExtendQuotaMaxSizeExceeded, ExtendQuotaUsageTooLow, NoNeedToExtendQuota
from svc_bk_repo.vendor.provider import BKGenericRepoManager

logger = logging.getLogger(__name__)


def extend_quota(
    manager: BKGenericRepoManager,
    bucket: str,
    extra_size_bytes: int,
    max_allowed_bytes: int,
    required_usage_rate: int = None,
) -> int:
    """
    :param extra_size_bytes: extra bytes to be extended
    :param max_allowed_bytes: max allowed bytes, raises ExtendQuotaMaxSizeExceeded when the
        desired_max_size exceeds the limits.
    :param required_usage_rate: the required usage rate, if given, the current usage max greater
        than this value or ExtendQuotaUsageTooLow will be raised
    :return: new max_size in bytes

    :raises: NoNeedToExtendQuota / ExtendQuotaUsageTooLow / ExtendQuotaMaxSizeExceeded
    """
    quota = manager.get_repo_quota(bucket)

    if math.isinf(quota.max_size):
        raise NoNeedToExtendQuota

    if required_usage_rate and quota.quota_used_rate < required_usage_rate:
        logger.warning(f'unable to extend quota for {bucket}: usage too low = {quota.quota_used_rate}')
        raise ExtendQuotaUsageTooLow(f'current usage is too low: {quota.quota_used_rate} < {required_usage_rate}')

    desired_max_size = int(quota.max_size + extra_size_bytes)
    if max_allowed_bytes and desired_max_size > max_allowed_bytes:
        logger.warning(f'unable to extend quota for {bucket}: exceeds max_size')
        raise ExtendQuotaMaxSizeExceeded('desired max_sized exceeds max allowed value')

    manager.update_repo_quota(bucket, quota=desired_max_size)
    return desired_max_size
