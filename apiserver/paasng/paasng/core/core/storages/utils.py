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
"""sqlalchemy db manager"""
import logging
import urllib.parse
from contextlib import contextmanager
from typing import Callable, ClassVar, ContextManager, Dict, Iterator, Optional, Union

from django.utils.functional import LazyObject
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.automap import AutomapBase, automap_base
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from typing_extensions import Protocol

logger = logging.getLogger()


def make_sa_conn_string(config_dict, driver_type="pymysql"):
    """Convert a django db dict to sqlalchemy string"""
    return "mysql+%(driver_type)s://%(user)s:%(password)s@%(host)s:%(port)s/%(db)s?charset=utf8" % {
        "driver_type": driver_type,
        "user": config_dict["USER"],
        "password": urllib.parse.quote(config_dict["PASSWORD"]),
        "host": config_dict["HOST"],
        "port": config_dict["PORT"],
        "db": config_dict["NAME"],
    }


DEFAULT_POOL_OPTIONS = {"pool_size": 20, "max_overflow": 100, "pool_recycle": 600}


class DummyObject(LazyObject):
    def _setup(self):
        raise RuntimeError("Should not use a Dummy Object.")


class DBManagerProtocol(Protocol):
    @property
    def engine(self) -> Engine:
        ...

    def get_model(self, table_name: str):
        ...

    def get_scoped_session(self):
        ...

    def session_scope(self):
        ...


class DummyDB:
    @property
    def engine(self) -> Engine:
        raise NotImplementedError

    def get_model(self, table_name: str):
        # 返回一个 Dummy 对象, 已简化 get_model 的流程
        return DummyObject()

    def get_scoped_session(self):
        raise NotImplementedError

    def session_scope(self):
        raise NotImplementedError


class SADBManager:
    _INSTANCES: ClassVar = dict()
    _engine: Optional[Engine]

    @classmethod
    def get_instance(cls, db_config: Dict) -> DBManagerProtocol:
        """get or create a db manager via django like db config
        :param db_config: django db config dict
        """
        key = cls.make_uni_key(db_config)
        if key not in cls._INSTANCES:
            cls._INSTANCES[key] = cls(db_config)
        return cls._INSTANCES[key]

    @property
    def engine(self):
        if self._engine is None:
            self._engine = self._create_engine(self.db_config)
        return self._engine

    def __init__(self, db_config: Dict):
        self._engine = None
        self.db_config = db_config
        self.base: AutomapBase = automap_base()
        self.model_prepared = False

    def get_model(self, table_name: str):
        if not self.model_prepared:
            self._prepare_models()
        return getattr(self.base.classes, table_name)

    def get_scoped_session(self) -> Union[Session, scoped_session]:
        logger.debug("[sqlalchemy] Connecting to outer-db.")
        return scoped_session(sessionmaker(bind=self.engine, expire_on_commit=False))

    def __session_scope__(self) -> Iterator[Session]:
        """Provide a transactional scope around a series of operations."""
        session = self.get_scoped_session()
        try:
            yield session
            logger.debug("[sqlalchemy] outer-db commit.")
            session.commit()
        except Exception:
            logger.debug("[sqlalchemy] outer-db rollback.")
            session.rollback()
            raise
        finally:
            logger.debug("[sqlalchemy] outer-db close.")
            session.close()

    session_scope: Callable[..., ContextManager[Session]] = contextmanager(__session_scope__)

    def _prepare_models(self):
        """根据已有的数据表构建模型"""
        logger.debug("[sqlalchemy] auto mapping models.")
        self.base.prepare(self.engine, reflect=True)
        self.model_prepared = True

    @staticmethod
    def _create_engine(db_config) -> Engine:
        echo = logger.level == logging.DEBUG
        try:
            dbstr = make_sa_conn_string(db_config, driver_type="pymysql")
            pool_options = db_config.get("POOL_OPTIONS") or DEFAULT_POOL_OPTIONS
            return create_engine(dbstr, echo=echo, **pool_options)
        except Exception as e:
            raise RuntimeError(
                "engine<{db_name}> is not successfully initialized".format(db_name=db_config["NAME"])
            ) from e

    @staticmethod
    def make_uni_key(db_config) -> str:
        """保证同一份数据库配置只实例化一次.  避免出现数据库事务死锁的问题."""
        db_name = db_config["NAME"]
        db_user = db_config["USER"]
        db_host = db_config["HOST"]
        db_port = db_config["PORT"]
        return f"{db_host}:{db_port}:{db_user}:{db_name}"
