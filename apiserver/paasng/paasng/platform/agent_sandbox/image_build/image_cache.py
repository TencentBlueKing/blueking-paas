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

import logging
import time

from celery import shared_task

from paas_wl.bk_app.agent_sandbox.image_cache import KUBEFLEDGED_NAMESPACE, ImageCache
from paas_wl.bk_app.agent_sandbox.image_credential import IMAGE_CREDENTIAL_NAME, ensure_image_credential
from paas_wl.infras.cluster.entities import AllocationContext
from paas_wl.infras.cluster.shim import ClusterAllocator
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paasng.platform.agent_sandbox.image_build.exceptions import ImagePrePullError
from paasng.platform.agent_sandbox.models import ImageBuildRecord

logger = logging.getLogger(__name__)

# Default timeout for image pre-pull: 10 minutes
_DEFAULT_PRE_PULL_TIMEOUT = 10 * 60


def _wait_for_image_cache(image_cache: ImageCache, timeout: float):
    """Wait for ImageCache to reach Succeeded status.

    :param image_cache: The ImageCache instance to monitor.
    :param timeout: Maximum time to wait in seconds.
    :raises ImagePrePullError: If the image pre-pull fails, times out, or ImageCache is not found.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Check interval 5s for status polling
        time.sleep(5)

        cache_info = image_cache.get()
        if cache_info is None:
            raise ImagePrePullError(
                f"ImageCache {image_cache.name} not found — it may have been deleted or failed to create."
            )

        status = cache_info.status
        if status is None:
            continue

        if status.status == "Succeeded":
            return

    raise ImagePrePullError(f"ImageCache {image_cache.name} pull exceeded {timeout} seconds")


@shared_task()
def pre_pull_sandbox_image(build_id: str, timeout: float = _DEFAULT_PRE_PULL_TIMEOUT):
    """Pre-pull the sandbox image to cluster nodes using kube-fledged ImageCache.

    This function:
    1. Gets the cluster for the tenant from build.tenant_id
    2. Ensures the image pull secret exists in kube-fledged namespace
    3. Creates an ImageCache CRD to trigger image pre-pull
    4. Waits for the ImageCache status to become Succeeded
    5. Deletes the ImageCache after successful pre-pull

    :param build_id: The UUID of the ImageBuildRecord.
    :param timeout: Maximum time to wait for image pre-pull in seconds.
    """

    try:
        build = ImageBuildRecord.objects.get(uuid=build_id)
    except ImageBuildRecord.DoesNotExist:
        logger.error(f"ImageBuildRecord {build_id} not found")  # noqa: TRY400
        return

    # Allocate cluster for the tenant
    cluster = ClusterAllocator(AllocationContext.create_for_agent_sandbox(build.tenant_id)).get_default()
    client = get_client_by_cluster_name(cluster.name)

    # Generate a unique name for the ImageCache
    cache_name = f"pre-pull-{build.uuid.hex}"

    # Ensure image pull secret in kube-fledged namespace
    ensure_image_credential(client=client, namespace=KUBEFLEDGED_NAMESPACE)

    # Create ImageCache for pre-pulling the image
    image_cache = ImageCache(
        client=client,
        name=cache_name,
        images=[build.output_image],
        image_pull_secrets=[IMAGE_CREDENTIAL_NAME],
    )

    try:
        image_cache.upsert()
        _wait_for_image_cache(image_cache, timeout)
    except Exception:
        logger.exception("Failed to pre-pull image %s", build.output_image)
    finally:
        # 立即删除 ImageCache CRD，实现"仅预加载、不托管"的效果。
        #
        # 背景：kube-fledged 的更新机制存在"强制清理差异镜像"的行为。
        # 当 ImageCache 资源发生更新（镜像列表变化）时，controller 会自动删除
        # 被移除的镜像，无论这些镜像是否正在被使用。这会导致非预期的镜像清理。
        #
        # 解决方案：创建 ImageCache 触发镜像预加载后，立即删除该 CRD 资源。
        # 这样 kube-fledged 不再跟踪此资源，后续也不会因为 CRD 的更新/删除
        # 而触发任何镜像清理逻辑。镜像将保留在节点上，直到节点自身清理策略
        # 或手动介入才移除。
        #
        # 注意：直接删除整个 ImageCache CRD 不会触发镜像清理，因为 controller
        # 只会在"更新时移除镜像"的场景下执行强制删除。详见 upsert() 方法注释。

        # 后续：如果运营过程中，节点上的沙箱镜像占用过大，需要及时清理，则可以按 FIFO 策略轮转 ImageCache
        # 的 images(比如最多维持 5 个镜像)，利用更新机制来主动淘汰旧镜像。此时，不再直接删除 ImageCache
        try:
            image_cache.delete()
        except Exception:
            logger.exception("Failed to delete ImageCache %s", cache_name)
