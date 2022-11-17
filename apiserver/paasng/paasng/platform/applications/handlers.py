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

import boto3
from bkstorages.backends.rgw import RGWBoto3Storage
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.files.storage import Storage
from django.db.models.signals import post_save
from django.dispatch import receiver

from paasng.accessories.iam.client import BKIAMClient
from paasng.accessories.iam.constants import NEVER_EXPIRE_DAYS
from paasng.accessories.iam.members.models import ApplicationGradeManager, ApplicationUserGroup
from paasng.engine.constants import JobStatus
from paasng.engine.models import Deployment
from paasng.metrics import NEW_APP_COUNTER
from paasng.platform.applications.models import Application
from paasng.platform.region.app import S3BucketRegionHelper
from paasng.platform.region.models import get_region
from paasng.utils.basic import get_username_by_bkpaas_user_id
from paasng.utils.blobstore import get_storage_by_bucket

from .signals import (
    application_logo_updated,
    before_finishing_application_creation,
    module_environment_offline_success,
    post_create_application,
)

logger = logging.getLogger(__name__)


# Post creation application handlers start
# The order of handlers is important because them will be called in the order of them were registered


@receiver(post_create_application)
def register_builtin_user_groups_and_grade_manager(sender, application: Application, **kwargs):
    """
    默认为每个新建的蓝鲸应用创建三个用户组（管理者，开发者，运营者），以及该应用对应的分级管理员
    将 创建者 添加到 管理者用户组 以获取应用的管理权限，并添加为 分级管理员成员 以获取审批其他用户加入各个用户组的权限
    """
    logger.debug(
        'register default user groups and grade manager after app creation: user=%s application=%s',
        application.creator,
        application.code,
    )
    cli = BKIAMClient()
    creator = get_username_by_bkpaas_user_id(application.creator)

    # 1. 创建分级管理员，并记录分级管理员 ID
    grade_manager_id = cli.create_grade_managers(application.code, application.name, creator)
    ApplicationGradeManager.objects.create(app_code=application.code, grade_manager_id=grade_manager_id)

    # 2. 将创建者，添加为分级管理员的成员
    cli.add_grade_manager_members(grade_manager_id, [creator])

    # 3. 创建默认的 管理者，开发者，运营者用户组
    user_groups = cli.create_builtin_user_groups(grade_manager_id, application.code)
    ApplicationUserGroup.objects.bulk_create(
        [
            ApplicationUserGroup(app_code=application.code, role=group['role'], user_group_id=group['id'])
            for group in user_groups
        ]
    )

    # 4. 为默认的三个用户组授权
    cli.grant_user_group_policies(application.code, application.name, user_groups)

    # 5. 将创建者添加到管理者用户组，返回数据中第一个即为管理者用户组信息
    cli.add_user_group_members(user_groups[0]['id'], [creator], NEVER_EXPIRE_DAYS)


@receiver(post_create_application)
def extra_setup_tasks(sender, application: Application, **kwargs):
    """Extra tasks to create an application"""
    # Send signal to trigger extra tasks before application was created
    before_finishing_application_creation.send(extra_setup_tasks, application=application)


@receiver(post_create_application)
def update_app_counter(sender, application: Application, **kwargs):
    """Update new application counter"""
    logger.debug('Increasing new application counter: application=%s', application.code)
    module = application.get_default_module()
    NEW_APP_COUNTER.labels(
        region=module.region,
        language=module.language,
        source_init_template=module.source_init_template,
    ).inc()


# Post creation application handlers end


@receiver(module_environment_offline_success)
def on_environment_offlined(sender, offline_instance, environment, **kwargs):
    """当应用某环境成功下架后触发。判断该应用是否所有环境都已经处于下架状态，如果是。将应用置为不可用"""
    application = offline_instance.app_environment.application
    # 检查是否所有环境都是下架状态
    any_env_active = any(app_env.is_running() for app_env in application.envs.all())

    if not any_env_active:
        logger.info("application[%s] active state is setting to inactive" % application.id.hex)
        application.is_active = False
        application.save(update_fields=['is_active'])


@receiver(post_save, sender=Deployment)
def on_model_post_save(sender, instance, created, raw, using, update_fields, *args, **kwargs):
    """当 Deployment 数据被创建或修改时触发。如果应用该次部署已经成功，将应用由不可用状态置为可用"""
    if isinstance(instance, Deployment) and not created:
        if instance.status != JobStatus.SUCCESSFUL.value:
            return

        application = instance.app_environment.application
        if not application.is_active:
            logger.info("application[%s] active state is setting to active" % application.id.hex)
            application.is_active = True
            application.save(update_fields=['is_active'])


@receiver(application_logo_updated)
def extra_setup_logo(sender, application: Application, **kwargs):
    """Do some extra setup works for logo, such as set object metadata"""
    if not application.has_customized_logo():
        return

    # Initialize logo's metadata
    bucket_name = S3BucketRegionHelper(application).get_logo_bucket()
    initialize_app_logo_metadata(Application._meta.get_field('logo').storage, bucket_name, application.logo.name)


@receiver(application_logo_updated)
def duplicate_logo_to_extra_bucket(sender, application: Application, **kwargs):
    """Duplicate app logo to another bucket if an extra bucket info was configured in settings."""
    region = get_region(application.region)
    extra_bucket_name = region.basic_info.get_extra_logo_bucket_name()
    if not extra_bucket_name:
        return
    if not application.has_customized_logo():
        return

    to_storage = get_storage_by_bucket(extra_bucket_name)
    with application.logo.storage.open(application.logo.name) as f:
        logger.info('Duplicating logo: %s to bucket: %s...', application.logo.name, extra_bucket_name)
        to_storage.save(application.logo.name, f)
        # update extra bucket logo cache
        initialize_app_logo_metadata(to_storage, extra_bucket_name, application.logo.name)


def initialize_app_logo_metadata(storage: Storage, bucket_name: str, key: str):
    """Initialize app logo's S3 metadata, set it as public, add cache support etc.

    :param storage: Django Storage object
    :param bucket_name: S3 bucket name
    :param key: S3 key
    """
    # Only support s3 storage
    # TODO: Replace this condition check with conciser type checking
    if not isinstance(storage, RGWBoto3Storage):
        return

    s3 = boto3.resource(
        's3',
        aws_access_key_id=storage.access_key,
        aws_secret_access_key=storage.secret_key,
        endpoint_url=storage.endpoint_url,
    )
    try:
        obj = s3.Object(bucket_name, key)
        obj.load()
        metadata = obj.metadata
    except ClientError:
        logger.exception("get logo object:%s failed, will not continue", key)
        return

    # If already set, skip proceeding
    if 'CacheControl' in metadata:
        logger.debug("CacheControl was already set on %s", key)
        return

    # Set object as public; Add "CacheControl" header; Add "ContentType" header
    try:
        obj.copy(
            CopySource={"Bucket": bucket_name, "Key": key},
            ExtraArgs={
                "CacheControl": "max-age=%s" % settings.APP_LOGO_MAX_AGE,
                "MetadataDirective": "REPLACE",
                "ACL": "public-read",
                "ContentType": "image/png",
            },
        )
    except Exception:
        logger.exception("update key: %s's metadata failed", key)
