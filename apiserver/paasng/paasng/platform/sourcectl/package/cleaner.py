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
import logging

from paasng.platform.sourcectl.models import SourcePackage
from paasng.platform.sourcectl.package.utils import parse_url
from paasng.utils.blobstore import StoreType, make_blob_store

logger = logging.getLogger(__name__)


def delete_from_blob_store(package: SourcePackage):
    """从 blob_store 删除源码包

    不支持 http/https 协议的源码包"""
    o = parse_url(package.storage_url)
    if o.store_type in [StoreType.HTTP, StoreType.HTTPS]:
        return False

    logger.info("Removing source packages %s", o)
    store = make_blob_store(o.bucket, store_type=o.store_type)
    try:
        store.delete_file(o.key)
        package.is_deleted = True
        package.save(update_fields=["is_deleted", "updated"])
        return True
    except Exception:
        logger.exception("Source package %s failed to delete!", o)
        return False
