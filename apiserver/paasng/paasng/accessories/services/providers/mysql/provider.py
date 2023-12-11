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
"""
原CDB/gcs数据库申请/授权逻辑
"""
import logging

import pymysql

from paasng.accessories.services.utils import gen_unique_id, generate_password

from .constants import GRANT_SQL_FMT, REVOKE_SQL_FMT, MySQLAuthTypeEnum
from .exceptions import CreateDatabaseFailed
from ..base import BaseProvider, InstanceData

logger = logging.getLogger(__name__)


class MySQLProvider(BaseProvider):
    display_name = "MySQL 通用申请服务"
    """
    desc: 普通数据库授权 / CDB 数据库授权
    example: qcloud的正式/测试环境的db申请, 内部版测试环境db申请
    steps:
    - 连接数据库
    - create database
    - 对账号鉴权/ip


    功能:
    - 新增数据库授权某些IP
    - 追加授权
    """

    def __init__(self, config):
        self.host = config["host"]
        self.port = config["port"]
        self.user = config["user"]
        self.password = config["password"]
        self.auth_ip_list = config["auth_ip_list"]

    def _get_connection(self):
        connection = pymysql.connect(host=self.host, port=self.port, user=self.user, password=self.password)
        return connection

    def _get_app_connection(self, host, port, user, password):
        connection = pymysql.connect(host=host, port=port, user=user, password=password)
        return connection

    def _change_auth_ips(self, connection, ip_list, database_name, database_user, database_password, auth_type):
        sql_fmt = GRANT_SQL_FMT if auth_type == MySQLAuthTypeEnum.GRANT else REVOKE_SQL_FMT

        with connection.cursor() as cursor:
            for auth_ip in ip_list:
                sql = sql_fmt.format(
                    db_name=database_name, db_user=database_user, auth_ip=auth_ip, db_password=database_password
                )

                if auth_type == MySQLAuthTypeEnum.GRANT:
                    cursor.execute(sql)
                else:
                    # NOTE: allow revoke fail
                    try:
                        cursor.execute(sql)
                    except Exception:
                        logger.exception("Revoke privileges FAIL: %s", sql)
                        continue

            cursor.execute("flush privileges;")
        connection.commit()

    def _grant_auth_ips(self, connection, auth_ip_list, database_name, database_user, database_password):
        self._change_auth_ips(
            connection,
            auth_ip_list,
            database_name,
            database_user,
            database_password,
            auth_type=MySQLAuthTypeEnum.GRANT,
        )

    def _revoke_auth_ips(self, connection, revoke_ip_list, database_name, database_user, database_password):
        self._change_auth_ips(
            connection,
            revoke_ip_list,
            database_name,
            database_user,
            database_password,
            auth_type=MySQLAuthTypeEnum.REVOKE,
        )

    # ============================================================================

    def create(self, params) -> InstanceData:
        """
        申请时, 我们是知道需要授权的IP列表的
        """
        preferred_name = params.get("engine_app_name")

        connection = None

        uid = gen_unique_id(preferred_name)
        database_name = uid
        database_user = uid

        database_password = generate_password()

        try:
            # 1. get connection
            connection = self._get_connection()

            # 2. create database
            with connection.cursor() as cursor:
                sql = (
                    "CREATE DATABASE IF NOT EXISTS `%s` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci"
                    % database_name
                )
                cursor.execute(sql)
            connection.commit()

            # 3. create user
            with connection.cursor() as cursor:
                # FIXME: 改成先查后创建, if not exists 在5.6不支持
                # sql = "CREATE USER IF NOT EXISTS `%s` IDENTIFIED BY '%s';" % (database_user, database_password)
                sql = "CREATE USER `%s` IDENTIFIED BY '%s';" % (database_user, database_password)
                cursor.execute(sql)
            connection.commit()

            # 4. grant privileges
            self._grant_auth_ips(connection, self.auth_ip_list, database_name, database_user, database_password)

        except Exception as e:
            logger.exception("CommonMySQLProvider CREATE FAIL! create database for %s FAIL", database_name)
            raise CreateDatabaseFailed("Can not create database: %s" % e)
        finally:
            if connection:
                connection.close()

        credentials = {
            "host": self.host,
            "port": self.port,
            "name": database_name,
            "user": database_user,
            "password": database_password,
        }
        return InstanceData(credentials=credentials, config={})

    def delete(self, instance_data: InstanceData) -> None:
        credentials = instance_data.credentials
        connection = None
        try:
            # 1. get connection
            connection = self._get_connection()

            # 2. create database
            with connection.cursor() as cursor:
                sql = f"DROP DATABASE `{credentials['MYSQL_NAME']}`"
                cursor.execute(sql)
            connection.commit()
        except Exception:
            logger.exception("delete failed")
            raise
        finally:
            if connection:
                connection.close()

    def patch(self, params):
        raise NotImplementedError("MySQL is not patchable")

    def stats(self, resource):
        raise NotImplementedError("Cannot fetch the stats of MySQL")
