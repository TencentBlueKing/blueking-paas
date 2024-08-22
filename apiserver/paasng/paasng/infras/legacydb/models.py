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
from operator import itemgetter
from typing import List, Optional, no_type_check

from sqlalchemy import or_, text
from sqlalchemy.orm.session import Session

from paasng.core.core.storages.sqlalchemy import legacy_db
from paasng.infras.iam.legacy import Permission

logger = logging.getLogger(__name__)
LApplication = legacy_db.get_model("paas_app")
LEngineApp = legacy_db.get_model("engine_apps")

LApplicationSecureInfo = legacy_db.get_model("paas_app_secureinfo")
LApplicationConfigVar = legacy_db.get_model("paas_app_envvars")
LApplicationReleaseRecord = legacy_db.get_model("paas_release_record")
LApplicationUseRecord = legacy_db.get_model("console_analysis_appuserecord")
LApplicationTag = legacy_db.get_model("paas_apptags")

LAppDeveloper = legacy_db.get_model("paas_app_developer")
LUser = legacy_db.get_model("account_bkuser")


# 仅 EE 环境拥有的模型
LSMartApplication = legacy_db.get_model("paas_saas_app")
LSMartApplicationVersion = legacy_db.get_model("paas_saas_app_version")
LSMartApplicationPackage = legacy_db.get_model("paas_saas_upload_file")


# 由于 AutomapBase 的模型是运行时决定的, 因此无法进行静态类型检测
@no_type_check
def get_v2_application_by_developer(username: str, session: Optional[Session] = None) -> List["LApplication"]:
    """relationship between `account_bkuser` and `paas_app`
             +----------------+               +----------+
             | account_bkuser |               | paas_app |
             +----------------+               +----------+
             |    username    |               |   code   |
    +--<-----+*   user_id     |               |   id    *+-----<----+
    |        +----------------+               +----------+          |
    |                                                               |
    |                                                               ^
    v                      +--------------------+                   |
    |                      | paas_app_developer |                   |
    |                      +--------------------+                   |
    |                      |      app_id       *+-------------------+
    +--------------------->+*     bkuser_id     |
                           +--------------------+

    :param username str: username of the app developer
    :return: List[LApplication]
    """
    permission = Permission()
    session = session or legacy_db.get_scoped_session()

    # 用户有权限的 PaaS2.0 的普通应用列表，从权限中心查询过滤条件，sql_filters 为原生的 sql 查询条件
    sql_filters = permission.app_filters(username)
    # 如果 PaaS2.0 没有接入权限中心，则查询到的权限表达式为空，不能进行后续的表达式操作
    if not sql_filters:
        return []
    # SQLAlchemy 1.4 版本开始，原生 SQL 表达式必须通过 text 函数显式声明，以提高代码的明确性与安全性
    normal_app_subquery = session.query(LApplication).filter(text(sql_filters)).all()
    # 权限中心会返回 1=1 这样的过滤条件，不能用子查询
    normal_app_ids = [app.id for app in normal_app_subquery]

    # 去权限中心查询用户是否有管理 Smart 应用的权限
    is_has_smart_perm = permission.allowed_manage_smart(username)
    # 转成数据库中的值
    is_saas = 1 if is_has_smart_perm else 0
    # 根据关联关系, 查询所有 **不是** 从v3同步过去的应用, 最后的查询结果为用户具有开发者身份的legacy app
    return (
        session.query(LApplication)
        .filter(
            # 如果用户有管理 Smart 应用的权限，则返回所有的 Smart 应用
            or_(LApplication.id.in_(normal_app_ids), LApplication.is_saas == is_saas),
            LApplication.from_paasv3 != 1,
        )
        .all()
    )


@no_type_check
def get_developers_by_v2_application(application: LApplication, session: Optional[Session] = None) -> List[str]:
    """relationship between `account_bkuser` and `paas_app`
             +----------------+               +----------+
             | account_bkuser |               | paas_app |
             +----------------+               +----------+
             |    username    |               |   code   |
    +--<-----+*   user_id     |               |   id    *+-----<----+
    |        +----------------+               +----------+          |
    |                                                               |
    |                                                               ^
    v                      +--------------------+                   |
    |                      | paas_app_developer |                   |
    |                      +--------------------+                   |
    |                      |      app_id       *+-------------------+
    +--------------------->+*     bkuser_id     |
                           +--------------------+

    :param application: v2 application
    :return: username list for developers
    """
    session = session or legacy_db.get_scoped_session()
    # 根据 app_id 查询具有该应用权限的用户的 bkuser_id
    subq_for_bkuser_id = session.query(LAppDeveloper.bkuser_id).filter_by(app_id=application.id).subquery()
    # 根据关联关系，查询用户名称
    username_list = session.query(LUser.username).filter(LUser.id == subq_for_bkuser_id.c.bkuser_id).all()
    return list(map(itemgetter(0), username_list))
