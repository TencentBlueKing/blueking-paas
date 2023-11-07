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
import json
import logging
import os
import urllib.parse
from typing import TYPE_CHECKING, Dict, Optional

from blue_krill.storages.blobstore.base import SignatureType
from django.conf import settings

# NOTE: Import kube resource related modules from paas_wl
from paas_wl.bk_app.applications.models.build import BuildProcess
from paas_wl.bk_app.applications.models.managers.app_configvar import AppConfigVarManager
from paas_wl.bk_app.deploy.app_res.utils import get_schedule_config
from paas_wl.utils.text import b64encode
from paas_wl.workloads.images.kres_entities import ImageCredentials
from paas_wl.workloads.images.utils import make_image_pull_secret_name
from paas_wl.workloads.release_controller.entities import ContainerRuntimeSpec
from paasng.platform.engine.configurations.building import SlugBuilderTemplate
from paasng.utils.blobstore import make_blob_store

if TYPE_CHECKING:
    from paas_wl.bk_app.applications.models import WlApp

logger = logging.getLogger(__name__)

# TODO: Refactor this module to engine.configurations


def generate_builder_name(app: 'WlApp') -> str:
    """Get the builder name"""
    return f"slug-builder--{app.module_name}"


def generate_slug_path(bp: BuildProcess) -> str:
    """Get the slug path for storing slug"""
    app: 'WlApp' = bp.app
    slug_name = f'{app.name}:{bp.branch}:{bp.revision}'
    return f'{app.region}/home/{slug_name}/push'


def generate_builder_env_vars(bp: BuildProcess, metadata: Dict) -> Dict[str, str]:
    """Generate all env vars required for building."""
    bucket = settings.BLOBSTORE_BUCKET_APP_SOURCE
    store = make_blob_store(bucket)
    app: 'WlApp' = bp.app
    env_vars: Dict[str, str] = {}

    # TODO: 支持构建镜像到私有仓库
    # Note: 从 ImageCredentials 加载凭证理论上会读取到用户配置的用户/密码, 只需要让 output_image 可以自定义即可支持构建镜像到私有仓库
    if metadata.get("use_dockerfile"):
        # build application form Dockerfile
        image_repository = metadata['image_repository']
        output_image = metadata['image']
        env_vars.update(
            SOURCE_GET_URL=store.generate_presigned_url(
                key=bp.source_tar_path, expires_in=60 * 60 * 24, signature_type=SignatureType.DOWNLOAD
            ),
            OUTPUT_IMAGE=output_image,
            CACHE_REPO=f"{image_repository}/dockerbuild-cache",
            DOCKER_CONFIG_JSON=b64encode(json.dumps(ImageCredentials.load_from_app(app).build_dockerconfig())),
        )
    elif metadata.get("use_cnb"):
        # build application as image
        image_repository = metadata['image_repository']
        output_image = metadata['image']
        env_vars.update(
            SOURCE_GET_URL=store.generate_presigned_url(
                key=bp.source_tar_path, expires_in=60 * 60 * 24, signature_type=SignatureType.DOWNLOAD
            ),
            OUTPUT_IMAGE=output_image,
            CACHE_IMAGE=f"{image_repository}:cnb-build-cache",
            CNB_REGISTRY_AUTH=json.dumps(ImageCredentials.load_from_app(app).build_app_registry_auth()),
        )
    else:
        # build application as slug
        cache_path = '%s/home/%s/cache' % (app.region, app.name)
        env_vars.update(
            # Path of source tarball
            TAR_PATH='%s/%s' % (bucket, bp.source_tar_path),
            # Path to store compiled slug package
            PUT_PATH='%s/%s' % (bucket, generate_slug_path(bp)),
            # Path to store cache to speed up build process
            CACHE_PATH='%s/%s' % (bucket, cache_path),
            # 以下是新的环境变量, 通过签发 http 协议的变量屏蔽对象存储仓库的实现.
            # TODO: 将 slug.tgz 抽成常量
            SLUG_SET_URL=store.generate_presigned_url(
                key=generate_slug_path(bp) + "/slug.tgz", expires_in=60 * 60 * 24, signature_type=SignatureType.UPLOAD
            ),
            SOURCE_GET_URL=store.generate_presigned_url(
                key=bp.source_tar_path, expires_in=60 * 60 * 24, signature_type=SignatureType.DOWNLOAD
            ),
            CACHE_GET_URL=store.generate_presigned_url(
                key=cache_path, expires_in=60 * 60 * 24, signature_type=SignatureType.DOWNLOAD
            ),
            CACHE_SET_URL=store.generate_presigned_url(
                key=cache_path, expires_in=60 * 60 * 24, signature_type=SignatureType.UPLOAD
            ),
            # 设置 slug-pilot 中 build 过程的超时时间(精确到分钟)
            PILOT_BUILDER_TIMEOUT=f'{settings.BUILD_PROCESS_TIMEOUT // 60}m',
        )

    env_vars.update(AppConfigVarManager(app=app).get_envs())

    # Inject extra env vars in settings for development purpose
    if settings.BUILD_EXTRA_ENV_VARS:
        env_vars.update(settings.BUILD_EXTRA_ENV_VARS)
    # Inject pip index url
    if settings.PYTHON_BUILDPACK_PIP_INDEX_URL:
        env_vars.update(get_envs_from_pypi_url(settings.PYTHON_BUILDPACK_PIP_INDEX_URL))

    if metadata:
        update_env_vars_with_metadata(env_vars, metadata)
    return env_vars


def generate_launcher_env_vars(slug_path: str) -> Dict[str, str]:
    """generate all env vars needed for launching a build result."""
    store = make_blob_store(bucket=settings.BLOBSTORE_BUCKET_APP_SOURCE)
    object_key = os.path.join(slug_path, "slug.tgz")
    return {
        'SLUG_URL': os.path.join(settings.BLOBSTORE_BUCKET_APP_SOURCE, object_key),
        # 以下是新的环境变量, 通过签发 http 协议的变量屏蔽对象存储仓库的实现.
        'SLUG_GET_URL': store.generate_presigned_url(
            # slug get url 签发尽可能长的时间, 避免应用长期不部署, 重新调度后无法运行。
            key=object_key,
            expires_in=60 * 60 * 24 * 365 * 20,
            signature_type=SignatureType.DOWNLOAD,
        ),
    }


def update_env_vars_with_metadata(env_vars: Dict, metadata: Dict):
    """Update slugbuilder envs from metadata into env_vars

    :param env_vars: slugbuilder envs dict
    :param metadata: metadata dict
    :return:
    """
    if 'extra_envs' in metadata:
        env_vars.update(metadata['extra_envs'])

    buildpacks = metadata.get("buildpacks")
    if buildpacks:
        # slugbuilder 自动下载指定的 buildpacks
        env_vars["REQUIRED_BUILDPACKS"] = buildpacks


def prepare_slugbuilder_template(
    app: 'WlApp', env_vars: Dict, builder_image: Optional[str] = None
) -> SlugBuilderTemplate:
    """Prepare the template for running a slug builder

    :param app: WlApp to build, provide info about namespace, region and etc.
    :param env_vars: Extra environment vars
    :param builder_image: image of slugbuilder
    :returns: args for start slugbuilder
    """
    # Builder image name
    image = builder_image or settings.DEFAULT_SLUGBUILDER_IMAGE
    logger.info(f"build wl_app<{app.name}> with slugbuilder<{image}>")

    return SlugBuilderTemplate(
        name=generate_builder_name(app),
        namespace=app.namespace,
        runtime=ContainerRuntimeSpec(
            image=image, envs=env_vars or {}, image_pull_secrets=[{"name": make_image_pull_secret_name(wl_app=app)}]
        ),
        schedule=get_schedule_config(app),
    )


def get_envs_from_pypi_url(index_url: str) -> Dict[str, str]:
    """Produce the environment variables for python buildpack, such as:

    PIP_INDEX_URL: http://pypi.douban.com/simple/
    PIP_INDEX_HOST: pypi.douban.com
    """
    parsed = urllib.parse.urlparse(index_url)
    return {'PIP_INDEX_URL': index_url, 'PIP_INDEX_HOST': parsed.netloc}
