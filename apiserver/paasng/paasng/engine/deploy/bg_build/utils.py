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
from paas_wl.platform.applications.models.build import BuildProcess
from paas_wl.platform.applications.models.managers.app_configvar import AppConfigVarManager
from paas_wl.release_controller.models import ContainerRuntimeSpec
from paas_wl.resources.utils.app import get_schedule_config
from paas_wl.utils.text import b64encode
from paas_wl.workloads.images.constants import PULL_SECRET_NAME
from paas_wl.workloads.images.entities import ImageCredentials, build_dockerconfig
from paasng.engine.configurations.building import SlugBuilderTemplate
from paasng.engine.configurations.image import generate_image_repository
from paasng.engine.models import EngineApp
from paasng.utils.blobstore import make_blob_store

if TYPE_CHECKING:
    from paas_wl.platform.applications.models import WlApp

logger = logging.getLogger(__name__)

# TODO: Refactor this module to engine.configurations


def generate_builder_name(app: 'WlApp') -> str:
    """Get the builder name"""
    return "slug-builder"


def generate_slug_path(bp: BuildProcess) -> str:
    """Get the slug path for storing slug"""
    app: 'WlApp' = bp.app
    slug_name = f'{app.name}:{bp.branch}:{bp.revision}'
    return f'{app.region}/home/{slug_name}/push'


def generate_image_tag(bp: BuildProcess) -> str:
    """Get the Image Tag for bp"""
    return f"{bp.branch}-{bp.revision}"


def generate_builder_env_vars(bp: BuildProcess, metadata: Optional[Dict]) -> Dict[str, str]:
    """generate all env vars needed for building"""
    bucket = settings.BLOBSTORE_BUCKET_APP_SOURCE
    store = make_blob_store(bucket)
    app: 'WlApp' = bp.app
    env_vars: Dict[str, str] = {}

    if metadata and metadata.get("use_dockerfile"):
        # build application form Dockerfile
        engine_app = EngineApp.objects.get(id=app.pk)
        image_repository = generate_image_repository(engine_app)
        env_vars.update(
            SOURCE_GET_URL=store.generate_presigned_url(
                key=bp.source_tar_path, expires_in=60 * 60 * 24, signature_type=SignatureType.DOWNLOAD
            ),
            OUTPUT_IMAGE=f"{image_repository}:{generate_image_tag(bp)}",
            CACHE_REPO=f"{image_repository}/dockerbuild-cache",
            DOCKER_CONFIG_JSON=b64encode(json.dumps(build_dockerconfig(ImageCredentials.load_from_app(app)))),
        )
    elif metadata and metadata.get("use_cnb"):
        # build application as image
        engine_app = EngineApp.objects.get(id=app.pk)
        image_repository = generate_image_repository(engine_app)
        env_vars.update(
            SOURCE_GET_URL=store.generate_presigned_url(
                key=bp.source_tar_path, expires_in=60 * 60 * 24, signature_type=SignatureType.DOWNLOAD
            ),
            OUTPUT_IMAGE=f"{image_repository}:{generate_image_tag(bp)}",
            CACHE_IMAGE=f"{image_repository}:cnb-build-cache",
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


def prepare_slugbuilder_template(app: 'WlApp', env_vars: Dict, metadata: Optional[Dict]) -> SlugBuilderTemplate:
    """Prepare the template for running a slug builder

    :param app: WlApp to build, provide info about namespace, region and etc.
    :param env_vars: Extra environment vars
    :param metadata: metadata about slugbuilder
    :returns: args for start slugbuilder
    """
    # Builder image name
    image = (metadata or {}).get("image", settings.DEFAULT_SLUGBUILDER_IMAGE)
    logger.info(f"build wl_app<{app.name}> with slugbuilder<{image}>")

    return SlugBuilderTemplate(
        name=generate_builder_name(app),
        namespace=app.namespace,
        runtime=ContainerRuntimeSpec(
            image=image, envs=env_vars or {}, image_pull_secrets=[{"name": PULL_SECRET_NAME}]
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
