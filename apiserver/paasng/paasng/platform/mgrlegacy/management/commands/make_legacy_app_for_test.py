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
import random
from argparse import ArgumentParser

from django.core.management.base import BaseCommand
from django.utils.decorators import method_decorator

from paasng.accessories.publish.sync_market.managers import AppDeveloperManger, AppManger, AppTagManger
from paasng.accessories.publish.sync_market.models import TagMap, market_models
from paasng.accessories.publish.sync_market.utils import run_required_db_console_config
from paasng.core.core.storages.sqlalchemy import console_db
from paasng.infras.oauth2.utils import get_random_secret_key

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """创建提供给`单元测试`使用或`本地测试一键迁移`的 legacy app
    Usage:
    python manage.py make_legacy_app_for_test \
        --username=admin \
        --framework-version=django1.3 \
        --svn-repo="svn://127.0.0.1:3790/apps-box/v3apps/$app_code" \
        --code=$app_code
    """

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument("--dry-run", dest="dry_run", help="dry run", action="store_true", default=False)
        parser.add_argument("--username", dest="username", help="username of legacy app developer", required=True)
        parser.add_argument(
            "--framework-version",
            dest="framework_version",
            help="source code template version",
            choices=["django1.8", "django1.3"],
            required=False,
            default="django1.8",
        )
        parser.add_argument(
            "--svn-repo",
            dest="svn_repo",
            required=False,
            default="no svn repo",
            help="url of svn repo, should be not None if using to test mgrlegacy",
        )
        parser.add_argument(
            "--code",
            type=str,
            dest="code",
            help="legacy app code, if missing, will generate by random",
            required=False,
            default=None,
        )
        parser.add_argument(
            "--name",
            type=str,
            dest="name",
            help="legacy app name, if missing, will generate by random",
            required=False,
            default=None,
        )
        parser.add_argument(
            "--deploy_ver",
            type=str,
            dest="deploy_ver",
            help="legacy region for app",
            required=False,
            default="ied",
            choices=["ied", "tencent", "oversea", "local-test"],
        )
        parser.add_argument(
            "--deploy-to-stag", dest="is_already_test", type=bool, help="deploy to stag in v3", default=False
        )
        parser.add_argument(
            "--deploy-to-prod", dest="is_already_online", type=bool, help="deploy to prod in v3", default=True
        )
        parser.add_argument(
            "--use-celery", dest="use_celery", type=bool, help="is this app use celery ?", default=False
        )
        parser.add_argument(
            "--use-celery-beat", dest="use_celery_beat", type=bool, help="is this app use celery beat?", default=False
        )
        parser.add_argument("--silence", dest="silence", help="keep silence?", action="store_true", default=False)

    @method_decorator(run_required_db_console_config)
    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        username = options["username"]
        code = options["code"] or self.random_str()
        name = options["name"] or "本地迁移测试-" + self.random_str()
        framework_version = options["framework_version"]
        svn_repo = options["svn_repo"]
        deploy_env = 101 if framework_version == "django1.3" else 102
        deploy_ver = options["deploy_ver"]
        is_already_test = options["is_already_test"]
        is_already_online = options["is_already_online"]
        use_celery = options["use_celery"]
        use_celery_beat = options["use_celery_beat"]
        silence = options["silence"]
        # 随机生成 secret key
        secret_key = get_random_secret_key()

        self.get_or_create_legacy_app(
            code,
            name,
            deploy_env,
            deploy_ver,
            svn_repo,
            is_already_test,
            is_already_online,
            use_celery,
            use_celery_beat,
        )
        if not dry_run:
            with console_db.session_scope() as session:
                AppDeveloperManger(session)._create_developer_by_username(username)
                AppManger(session).sync_oauth(deploy_ver, code=code, secret=secret_key)
                # TODO: 检查以下流程
                #  1. 是否使用 mysql 数据库?
                #  2. 如果是, 需要创建数据库 service_obj = mixed_service_mgr.find_by_name(service_name, self.application.region)
                #  3. 需注释或替换 GCSMysqlServiceMigration、注释 RabbitMQServiceMigration
        if not silence:
            print(f"create legacy {framework_version} app [{name}]<{deploy_ver}-{code}> with secret key: {secret_key}")
            print(f"connect to {username}")

    @staticmethod
    def get_or_create_legacy_app(
        code,
        name,
        deploy_env,
        deploy_ver,
        svn_repo,
        is_already_test,
        is_already_online,
        use_celery,
        use_celery_beat,
        *args,
        **options,
    ):
        with console_db.session_scope() as session:
            app = AppManger(session).get(code)
            if not app:
                app = AppManger(session).create(code, name, deploy_ver, from_paasv3=False)
            # legacy db 通过外键绑定了 tag, 因此创建 App 时需要使用真实存在的 tag
            tagmap = Command.get_or_create_tagmap(deploy_ver)
            AppManger(session).update(
                code,
                {
                    "language": "python",
                    # 借用 `description` 表示 svn repo url, 用于本地迁移测试
                    "description": svn_repo,
                    "tags_id": tagmap.remote_id,
                    "state": 4,  # 待发布
                    "deploy_env": deploy_env,
                    "deploy_ver": deploy_ver,
                    "is_already_online": int(is_already_online),
                    "is_already_test": int(is_already_test),
                    "use_celery": int(use_celery),  # app是否使用celery，确定一下是否需要
                    "use_celery_beat": int(use_celery_beat),  # app是否使用celery beat，确定一下是否需要
                },
            )
        return app

    @staticmethod
    def random_str(str_len=10):
        template = "abcdefghijklmnopqrstuvwxyz123456789"
        return "a" + "".join(random.choices(template, k=str_len))

    @staticmethod
    def get_or_create_tagmap(deploy_ver):
        # 尝试从 V3 数据库获取已存在的 TagMap
        tagmap = TagMap.objects.first()
        if tagmap is None:
            # TagMap 为空
            with console_db.session_scope() as session:
                try:
                    legacy_tag = AppTagManger(session).create_tag(
                        {"code": Command.random_str(), "name": "测试标签", "is_select": 1, "deploy_ver": deploy_ver}
                    )
                except TypeError:
                    # 兼容企业版桌面没有 is_select 的情况
                    legacy_tag = AppTagManger(session).create_tag(
                        {"code": Command.random_str(), "name": "测试标签", "index": 100}
                    )
            tag, _ = market_models.Tag.objects.get_or_create(name="测试子标签", enabled=True)
            return TagMap.objects.create(tag=tag, remote_id=legacy_tag.id)
        return tagmap
