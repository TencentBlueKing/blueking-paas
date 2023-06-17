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
import datetime
import logging
import re
from typing import Dict, List, Optional, Tuple

from bkpaas_auth import get_user_by_user_id
from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from django.utils import timezone
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError as SqlIntegrityError
from sqlalchemy.orm import Session

from paasng.engine.constants import ConfigVarEnvName
from paasng.platform.applications.exceptions import IntegrityError
from paasng.platform.legacydb import models as legacy_models
from paasng.platform.mgrlegacy.constants import LegacyAppState
from paasng.platform.oauth2.models import OAuth2Client
from paasng.publish.sync_market.constant import EnvItem, SaaSPackageInfo
from paasng.publish.sync_market.models import TagData

logger = logging.getLogger(__name__)


class AppAdaptor:
    def __init__(self, session: Session):
        self.session = session
        self.model = legacy_models.LApplication

    def get(self, code: str) -> "legacy_models.LApplication":
        app = self.session.query(self.model).filter_by(code=code).scalar()
        return app

    def get_by_app_id(self, app_id: int) -> "legacy_models.LApplication":
        app = self.session.query(self.model).filter_by(id=app_id).scalar()
        return app

    def get_by_keyword(self, keyword: str) -> List[Dict[str, str]]:
        """Query application info not in PaaS3.0 by keywords (APP ID, APP Name)"""
        legacy_apps = (
            self.session.query(self.model)
            .filter(
                self.model.from_paasv3 == 0,
                self.model.migrated_to_paasv3 == 0,
                self.model.is_lapp == 0,
            )
            .order_by(self.model.code)
        )

        if keyword:
            # 模糊匹配的关键字
            fuzzy_keyword = f"%{keyword}%"
            legacy_apps = legacy_apps.filter(
                or_(
                    self.model.name.like(fuzzy_keyword),
                    self.model.name_en.like(fuzzy_keyword),
                    self.model.code.like(fuzzy_keyword),
                )
            )
        return [{"code": app.code, "name": app.name, "name_en": app.name} for app in legacy_apps]

    def update(self, code: str, data: dict) -> int:
        """
        The updated fields are：extra,name,is_display,state,is_already_online,migrated_to_paasv3,logo,external_url
        created_date,creater,description,introduction,isresize,issetbar,language,tags_id,width,height
        is_mapp,use_mobile_online,use_mobile_test,mobile_url_test,mobile_url_prod
        """
        # 兼容老数据
        for key in [
            'description',
            'created_state',
            'is_mapp',
            'use_mobile_online',
            'use_mobile_test',
            'mobile_url_test',
            'mobile_url_prod',
            'deploy_env',
            'deploy_ver',
            'use_celery',
            'use_celery_beat',
        ]:
            if key in data:
                data.pop(key)
                logger.info(f'Application attribute {key} does not exist, skip synchronization')

        if 'isresize' in data:
            data['is_resize'] = data.pop('isresize')
        if 'issetbar' in data:
            data['is_setbar'] = data.pop('issetbar')

        count = self.session.query(self.model).filter_by(code=code).update(data)
        return count

    def create(
        self,
        code: str,
        name: str,
        deploy_ver: str,
        from_paasv3: bool = True,
        logo: str = '',
        is_lapp: bool = False,
        creator: str = 'blueking',
        tag: Optional["legacy_models.LApplicationTag"] = None,
        external_url: str = '',
        introduction: str = '',
        height: int = 550,
        width: int = 890,
        state: int = LegacyAppState.DEVELOPMENT.value,
        is_already_test: int = 0,
        is_already_online: int = 0,
    ) -> "legacy_models.LApplication":
        datetime_now = timezone.now()
        app = self.model(
            name=name,  # 应用名称
            code=code,  # 应用编码
            logo=logo,  # 应用 logo 的访问地址
            introduction=introduction,  # 应用简介
            creater=creator,  # 创建者
            created_date=datetime_now,
            external_url=external_url,  # 第三方应用URL
            tags_id=tag.id if tag else None,  # app分类(LApplicationTag)的id
            state=state,
            is_already_test=is_already_test,
            is_already_online=is_already_online,
            width=width,  # app页面宽度
            height=height,  # app页面高度
            first_test_time=datetime_now,  # 应用首次提测时间
            first_online_time=datetime_now,  # 应用首次上线时间
            is_use_celery=0,  # app是否使用celery，确定一下是否需要
            is_use_celery_beat=0,  # app是否使用celery beat，确定一下是否需要
            use_count=0,
            is_default=0,  # 是否为默认应用
            is_max=0,  # 是否默认窗口最大化
            is_setbar=1,  # 窗口是否有评分和介绍按钮
            is_resize=1,  # 是否能对窗口进行拉伸
            is_saas=0,  # 是否为 smart 应用
            is_sysapp=0,  # 默认内部应用, 为了获取esb鉴权(esb加白)而生成securt_key的给其他系统调用esb使用 而生成的应用
            is_third=0,  # 第三方应用
            is_platform=0,  # 平台级别应用(cc, ijobs等)
            is_lapp=0 if not is_lapp else 1,  # 是否是轻应用
            is_display=1,  # 是否显示在桌面
            from_paasv3=1 if from_paasv3 else 0,  # 是否Paas3.0应用
            migrated_to_paasv3=0,  # 是否已经迁移到Paas3.0
            open_mode='new_tab',  # 应用打开方式, desktop: 桌面打开, new_tab: 新标签页打开
        )
        try:
            self.session.add(app)
            self.session.commit()
        except SqlIntegrityError as e:
            if len(e.args) > 0:
                error_msg = e.args[0]
                if re.search("Duplicate entry '.*' for key '.*code'", error_msg):
                    raise IntegrityError(field='code')
                elif re.search("Duplicate entry '.*' for key '.*name'", error_msg):
                    raise IntegrityError(field='name')
                else:
                    raise e
            else:
                raise e

        # 注册应用完成后，同步 oauth 信息
        try:
            oauth = OAuth2Client.objects.get(client_id=code)
        except OAuth2Client.DoesNotExist:
            logger.info(f'APP(code:{code}) oauth information does not exist, skip oauth synchronization')
        else:
            self.sync_oauth('', code, oauth.client_secret)
        return app

    def sync_oauth(self, region: str, code: str, secret: str) -> "legacy_models.LApplication":
        """必须在注册完成应用后再执行"""
        # 企业版 secret 以明文存储
        app = self.get(code)
        if not app:
            logger.info(f'APP(code:{code}) does not exist, skip oauth synchronization')
            return None

        self.update(
            code,
            {
                "auth_token": secret,
            },
        )
        return app

    def get_saas_package_info(self, app_id: str) -> Optional["SaaSPackageInfo"]:
        """获取SaaS应用的源码包信息
        注意：目前只获取正式环境部署的包信息
        """
        # PaaS 2.0 存放 Smart 包信息相关的表
        saas_app_module = legacy_models.LSMartApplication
        saas_app = self.session.query(saas_app_module).filter_by(app_id=app_id).scalar()
        if not saas_app:
            return None

        # Smart 应用是否有线上版本信息
        app_online_version_id = saas_app.online_version_id
        if not app_online_version_id:
            return None

        saas_app_version_module = legacy_models.LSMartApplicationVersion
        app_version_obj = self.session.query(saas_app_version_module).filter_by(id=app_online_version_id).scalar()
        if not app_version_obj:
            return None

        # 查询 Smart 包的路径信息
        saas_upload_file_module = legacy_models.LSMartApplicationPackage
        file_obj = self.session.query(saas_upload_file_module).filter_by(id=app_version_obj.upload_file_id).scalar()
        if not file_obj:
            return None

        return SaaSPackageInfo(
            version=app_version_obj.version,
            url=f'{settings.BK_PAAS2_INNER_URL}/media/{file_obj.file}',
            name=file_obj.name,
        )

    def soft_delete(self, code: str):
        """应用软删除"""
        self.session.query(self.model).filter_by(code=code).update(
            {"state": LegacyAppState.OUTLINE.value, "is_already_test": False, "is_already_online": False}
        )


class AppTagAdaptor:
    def __init__(self, session: Session):
        self.model = legacy_models.LApplicationTag
        self.session = session

    def get_tag_list(self) -> list:
        """获取桌面的分类列表，可由API提供"""
        console_tags = self.session.query(self.model).order_by('id')

        tag_list = []
        for tag in console_tags:
            region = settings.DEFAULT_REGION_NAME
            tag_list.append(
                TagData(id=tag.id, name=tag.name, enabled=True, index=tag.index, remark='', parent_id=0, region=region)
            )
        return tag_list

    def get(self, code: str) -> "legacy_models.LApplicationTag":
        return self.session.query(self.model).filter_by(code=code).first()


class AuthUserAdaptor:
    """用户信息，主要用于同步成员时，用户不存在时新建用户，若同步成员由 API 实现则可以删除"""

    def __init__(self, session: Session):
        self.model = legacy_models.LUser
        self.session = session

    def get_or_create(self, username: str) -> Tuple["legacy_models.LUser", bool]:
        """根据用户名创建一个 console 的用户对象"""
        user = self.session.query(self.model).filter_by(username=username).scalar()
        if user:
            return user, False

        user_id = user_id_encoder.encode(username=username, provider_type=settings.USER_TYPE)
        auth_user = get_user_by_user_id(user_id)

        user = self.model(
            username=username,
            chname=auth_user.chinese_name if auth_user.chinese_name else "",
            email=auth_user.email if auth_user.email else "",
            is_staff=auth_user.is_staff,
            is_superuser=auth_user.is_superuser,
            last_login=datetime.datetime.now(),
            date_joined=datetime.datetime.now(),
            password='',
            company='',
            qq='',
            phone='',
            role='',
        )
        self.session.add(user)
        self.session.commit()
        return user, True


class AppDeveloperAdaptor:
    """应用开发者"""

    def __init__(self, session: Session):
        self.session = session

    def get_apps_by_developer(self, username: str) -> List["legacy_models.LApplication"]:
        """
        :param username: username in legacy user
        :return: list containing legacy app (in which the user has developer identity)
        """
        return legacy_models.get_v2_application_by_developer(username=username)

    def get_developer_names(self, code: str) -> list:
        application = AppAdaptor(self.session).get(code)
        return legacy_models.get_developers_by_v2_application(application)

    def update_developers(self, code: str, target_developers: list):
        """
        更新应用在桌面上的开发者人员信息
        """
        app = AppAdaptor(self.session).get(code)
        if not app:
            logger.warning(f'App(code:{code}) does not exist, skip updating developers to console')
            return None

        console_delelopers = self.get_developer_names(code)
        to_delete = set(console_delelopers) - set(target_developers)
        if to_delete:
            self._delete_developers(app.id, to_delete)

        to_add = set(target_developers) - set(console_delelopers)
        if to_add:
            self._add_developers(app.id, to_add)

        return None

    def _delete_developers(self, app_id: int, to_delete: set):
        delete_developers = (
            self.session.query(legacy_models.LUser).filter(legacy_models.LUser.username.in_(to_delete)).all()
        )
        delete_developers_id = [user.id for user in delete_developers]
        # 包含 in 查询，必须设置为不同步，并手动 commit
        self.session.query(legacy_models.LAppDeveloper).filter(
            legacy_models.LAppDeveloper.app_id == app_id,
            legacy_models.LAppDeveloper.bkuser_id.in_(delete_developers_id),
        ).delete(synchronize_session=False)
        self.session.commit()
        return None

    def _add_developers(self, app_id: int, to_add: set):
        developers_objs = self._get_developer_objs_by_usernames(to_add)
        objects = [legacy_models.LAppDeveloper(app_id=app_id, bkuser_id=developer.id) for developer in developers_objs]
        self.session.add_all(objects)
        self.session.commit()
        return None

    def _create_developer_by_username(self, username: str) -> "legacy_models.LUser":
        """根据用户名创建一个 console 的 developer 对象"""
        developer_obj, created = AuthUserAdaptor(self.session).get_or_create(username)
        return developer_obj

    def _get_developer_objs_by_usernames(self, usernames: set) -> List["legacy_models.LUser"]:
        """将用户名转换成 console 的 developer 对象"""
        bk_users = self.session.query(legacy_models.LUser).filter(legacy_models.LUser.username.in_(usernames)).all()
        if len(bk_users) == len(usernames):
            return bk_users

        found_developers_usernames = [developer.auth_user.username for developer in bk_users]
        need_add_developers = set(usernames) - set(found_developers_usernames)
        for username in need_add_developers:
            developer_obj, created = AuthUserAdaptor(self.session).get_or_create(username)
            bk_users.append(developer_obj)
        return bk_users


class AppOpsAdaptor:
    """应用运营者"""

    def __init__(self, session: Session):
        self.session = session

    def get_ops_names(self, code: str) -> list:
        raise NotImplementedError

    def update_ops(self, code: str, target_devopses: list):
        raise NotImplementedError


class AppUseRecordAdaptor:
    def __init__(self, session: Session):
        self.session = session
        self.model = legacy_models.LApplicationUseRecord

    def get_records(self, application_codes: list, dt_before: datetime.date, limit: int) -> list:
        app_mode = AppAdaptor(self.session).model
        result = (
            self.session.query(app_mode.code, app_mode.name, app_mode.name_en, func.count(app_mode.code))
            .join(self.model)
            .filter(app_mode.code.in_(application_codes))
            .filter(self.model.use_time >= dt_before)
            .group_by(app_mode.code)
            .limit(limit)
            .all()
        )
        return result


class AppReleaseRecordAdaptor:
    def __init__(self, session: Session):
        self.session = session
        self.model = legacy_models.LApplicationReleaseRecord

    def create(self, code: str, username: str, env_name: str) -> bool:
        """Create a new release record to keep market updated
        :param app_code: the code of Application object
        :param username: the operator's username
        :param env_name: app environment name, "stag" or "prod"
        """
        app = AppAdaptor(self.session).get(code)
        if not app:
            logger.info(f"app with code({code}) does not exists, skip create release record")
            return False

        try:
            operate_id = {'stag': 0, 'prod': 1}[env_name]
        except KeyError:
            raise ValueError(f'{env_name} is not a valid environment name!')
        self.session.add(
            self.model(
                app_code=app.code,
                operate_id=operate_id,
                operate_user=username,
                is_success=True,
                operate_time=datetime.datetime.now(),
                # Default fields
                is_tips=False,
                is_version=False,
                version=None,
                message='',
                extra_data='{}',
                app_old_state=1,
            )
        )
        self.session.commit()
        return True


class AppEnvVarAdaptor:
    def __init__(self, session: Session):
        self.session = session
        self.model = legacy_models.LApplicationConfigVar

    def list(self, code: str) -> List[EnvItem]:
        env_vars = self.session.query(self.model).filter_by(app_code=code)
        # PaaS2.0的环境变量生效环境与PaaS3.0的对应关系
        environment_map = {
            'all': ConfigVarEnvName.GLOBAL.value,
            'test': ConfigVarEnvName.STAG.value,
            'prod': ConfigVarEnvName.PROD.value,
        }
        return [
            EnvItem(
                key=var.name,
                value=var.value,
                description=var.intro[:200],
                environment_name=environment_map.get(var.mode),
                is_builtin=False,
            )
            for var in env_vars
        ]

    def get_by_name(self, code: str, env_name: str) -> "legacy_models.LApplicationConfigVar":
        obj = (
            self.session.query(self.model)
            .filter(self.model.app_code == code)
            .filter(self.model.name == env_name)
            .scalar()
        )
        return obj

    def get_by_prefix(self, code: str, prefix: str) -> List["legacy_models.LApplicationConfigVar"]:
        env_vars = self.session.query(self.model).filter(
            self.model.app_code == code, self.model.variable_name.like(prefix)
        )
        return env_vars


class AppSecureInfoAdaptor:
    def __init__(self, session: Session):
        self.session = session
        self.model = legacy_models.LApplicationSecureInfo

    def get(self, code: str) -> legacy_models.LApplicationSecureInfo:
        """包含 db 信息和源码配置信息"""
        app = self.session.query(self.model).filter_by(app_code=code).scalar()
        return app


class EngineAppAdaptor:
    def __init__(self, session: Session):
        self.session = session
        self.model = legacy_models.LEngineApp

    def get(self, code: str) -> "legacy_models.LEngineApp":
        app = self.session.query(self.model).filter_by(app_code=code).scalar()
        return app
