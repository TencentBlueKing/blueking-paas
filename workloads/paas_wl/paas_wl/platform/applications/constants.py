# -*- coding: utf-8 -*-
from blue_krill.data_types.enum import EnumField, StructuredEnum


class AppOperationType(int, StructuredEnum):
    """All types of application operation"""

    CREATE_APPLICATION = 1
    REGISTER_PRODUCT = 4
    MODIFY_PRODUCT_ATTRIBUTES = 5
    PROCESS_START = 6
    PROCESS_STOP = 7
    RECYCLE_ONLINE_RESOURCE = 8
    DELETE_APPLICATION = 9

    OFFLINE_APPLICATION_STAG_ENVIRONMENT = 11
    OFFLINE_APPLICATION_PROD_ENVIRONMENT = 12

    DEPLOY_APPLICATION = 14
    CREATE_MODULE = 15
    DELETE_MODULE = 16

    OFFLINE_MARKET = 10
    RELEASE_TO_MARKET = 17


class EngineAppType(str, StructuredEnum):
    """type of engine app"""

    DEFAULT = EnumField('default')  # 默认类型：无任何定制逻辑

    # 云原生架构应用：完全基于 YAML 模型的应用，当前作为一个独立应用类型存在，但未来它也许会成为所有应用
    # （比如基于 buildpack 的“普通应用”）统一底层架构。到那时，再来考虑如何处置这个类型吧
    CLOUD_NATIVE = EnumField('cloud_native')


class ApplicationType(str, StructuredEnum):
    """Application types, copied from "apiserver" """

    DEFAULT = EnumField('default')
    ENGINELESS_APP = EnumField('engineless_app')
    BK_PLUGIN = EnumField('bk_plugin')
    CLOUD_NATIVE = EnumField('cloud_native')
