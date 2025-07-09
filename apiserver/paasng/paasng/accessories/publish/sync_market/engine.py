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

import datetime
import logging
from typing import Optional
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from paasng.accessories.publish.market.constant import AppState
from paasng.accessories.publish.market.models import MarketConfig
from paasng.accessories.publish.market.protections import AppPublishPreparer
from paasng.accessories.publish.market.utils import MarketAvailableAddressHelper
from paasng.accessories.publish.sync_market.constant import RegionConverter
from paasng.accessories.publish.sync_market.managers import AppManger, AppTagManger
from paasng.core.region.models import get_region
from paasng.platform.engine.models.mobile_config import MobileConfig
from paasng.utils.basic import get_username_by_bkpaas_user_id

from .exceptions import FieldNotFound, UndefinedMethod

logger = logging.getLogger(__name__)


class RemoteAppManager:
    def __init__(self, product, session):
        self.product = product
        self.application = product.application
        market_config, _ = MarketConfig.objects.get_or_create_by_app(self.application)
        self.market_config = market_config
        self.session = session

    @property
    def display_options(self):
        return self.product.displayoptions

    def single_field_hybrate(self, field):
        method_name = "hybrate_%s" % field.name
        attr = getattr(self, method_name, None)
        if attr is not None:
            return attr()
        else:
            raise UndefinedMethod(method_name)

    def fields_hybrate(self, field_names):
        """更新 field_names 列表中的字段"""
        data = dict()
        app_mode = AppManger(self.session).model
        for name in dir(app_mode):
            if name in field_names:
                field = getattr(app_mode, name)
                try:
                    data[name] = self.single_field_hybrate(field)
                except FieldNotFound:
                    continue
        return data

    def sync_data(self, field_names):
        data = self.fields_hybrate(field_names)
        count = AppManger(self.session).update(self.product.code, data)
        logger.info("成功更新应用%s的数据, 影响记录%s条，更新数据:%s", self.product.code, count, data)

    def hybrate_app_cate(self):
        """
        APP分类（公开/私有）
        私有应用默认打开白名单控制功能，首次提测时初始化开发商下的协作者和自定义白名单到redis中
        """
        return 0

    def hybrate_app_type(self):
        """应用类型"""
        return self.product.type

    def hybrate_audit_state(self):
        """app评审状态"""
        return 0

    def hybrate_cpu_limit(self):
        """上线或提测CPU限制"""
        return 1024

    def hybrate_created_date(self):
        """创建时间"""
        return self.application.created

    def hybrate_created_state(self):
        """
        app注册所处阶段
        CREATED_STATE = [
            (0, u"创建成功"),
            (1, u"基本信息注册"),
            (2, u"数据库创建"),
            (3, u"SVN代码初始化"),
        ]
        """
        return 3

    def hybrate_creater(self):
        """创建者"""
        return get_username_by_bkpaas_user_id(self.product.application.owner)

    def hybrate_deploy_env(self):
        """
        APP部署框架版本
        # 部署环境配置信息,第一位表示语言，后两位表示版本信息
        DEPLOY_ENV = [
            (101, u"Django 1.3"),
            (102, u"Django 1.8"),
        ]
        """
        return 102

    def hybrate_deploy_ver(self):
        """
        部署的版本
        DEPLOY_VER = [
            ('all', u"所有版本"),
            ('ied', u"IED版本"),
            ('tencent', u"TENCENT版本"),
            ('qcloud', u"QCLOUD版本"),
            ('txopen', u"投后版本"),
            ('campus', u"校园版"),
        ]
        """
        return RegionConverter.to_old(self.product.region)

    def hybrate_display_type(self):
        """
        app的显示类型
        选项：app,widget
        """
        return "app"

    def hybrate_init_svn_version(self):
        """SVN初始化版本"""
        return 0

    def hybrate_is_already_online(self):
        """
        是否已经上线, 影响应用打开后是否提示已下架
        app正式环境未下架，该字段为True。
        """
        if not self.application.engine_enabled:
            return True
        return self.product.state == AppState.RELEASED.value

    def hybrate_is_already_test(self):
        """
        是否已经提测
        app在测试环境下架或者开发中状态，修改该字段为False。
        """
        return 1

    def hybrate_is_base(self):
        """是否为基础应用, 基础应用可以允许app提供API接口"""
        return 0

    def hybrate_is_code_private(self):
        """代码是否仅开发者可读"""
        return 1

    def hybrate_is_default(self):
        """
        是否为默认应用
        如果你想该应用默认加入用户的桌面，就勾上这个吧！
        """
        return 0

    def hybrate_is_display(self):
        """
        是否显示在桌面
        选项: true(是)，false(否)
        """
        return self.display_options.visible

    def hybrate_is_lapp(self):
        """
        是否为轻应用
        目前专指gcloud app maker出来的APP
        """
        return 0

    def hybrate_is_mapp(self):
        """
        是否移动端应用
        该字段在桌面中并未使用
        """
        return 0

    def hybrate_is_max(self):
        """是否默认窗口最大化"""
        return self.display_options.is_win_maximize

    def hybrate_is_offical(self):
        """是否为官方APP, 官方APP的logo有特殊标识"""
        return 0

    def hybrate_is_open(self):
        """
        是否开放使用
        如果你想该应用让所有人使用（即无权限设置），就勾上这个吧！
        """
        return 1

    def hybrate_is_select_svn_dir(self):
        """是否手动选择要上线的目录（IED版本）"""
        return 1

    def hybrate_isflash(self):
        """是否为flash应用"""
        return 0

    def hybrate_isneed_reaudit(self):
        """上线是否需要重新评审"""
        return 1

    def hybrate_isresize(self):
        """是否能对窗口进行拉伸"""
        return 1 if self.display_options.resizable else 0

    def hybrate_issetbar(self):
        """窗口是否有评分和介绍按钮"""
        return 1 if self.display_options.win_bars else 0

    def hybrate_language(self):
        """语言"""
        mapper = {
            "PYTHON": "python",
            "PHP": "php",
            "GO": "go",
            "NODEJS": "nodejs",
            # 兼容精简版应用
            "": "",
        }
        return mapper[self.application.language.upper()]

    def hybrate_logo(self):
        logo_url = self.application.get_logo_url()
        region = get_region(self.application.region)
        if region.basic_info.extra_logo_bucket_info:
            # replace logo domain with target domain
            src_parse_result = urlparse(settings.RGW_ENDPOINT_URL)
            dst_parse_result = urlparse(region.basic_info.link_production_app)
            logo_url = logo_url.replace(src_parse_result.netloc, dst_parse_result.netloc)
        return logo_url

    def hybrate_mem_limit(self):
        """上线或提测内存限制"""
        return 512

    def hybrate_starnum(self):
        """
        星级评分（tencent or qcloud）
        note: 这个字段应该桌面操作的时候写回数据库的，开发者中心不应该写这个字段
        """
        return 0.0

    def hybrate_starnum_ied(self):
        """
        星级评分（ied）
        note: 这个字段应该桌面操作的时候写回数据库的，开发者中心不应该写这个字段
        """
        return 0.0

    def hybrate_state(self):
        """
        应用状态, app的开发状态, 控制能否在市场中打开
        当应用能发布至市场时, 设置 state = 4,
        否则 state = 0, 让图标变灰色
        STATE_CHOICES = [(0, u'已下架'),
            (1, u'开发中'),
            (3, u'测试中'),
            (4, u'已上线'),
            (8, u'正在提测'),
            (9, u'正在上线'),
            (10, u'正在下架'),
        ]
        """
        can_publish_to_market = self.market_config.enabled and AppPublishPreparer(self.application).all_matched
        return 4 if can_publish_to_market else 0

    def hybrate_svn_domain(self):
        """SVN域名"""
        return ""

    def hybrate_tags_id(self):
        """app分类"""
        tag = self.product.get_tag()
        if not tag:
            raise FieldNotFound

        try:
            return tag.tagmap.remote_id
        except ObjectDoesNotExist:
            # 当出现未关联标签时, 启动兼容方案
            logger.warning(f"`{tag.name}` 未关联桌面标签")

        # 尝试关联桌面上的同名标签
        console_tag = AppTagManger(self.session).get_tag_by_name(tag.name)
        if not console_tag:
            raise FieldNotFound
        return console_tag.id

    def hybrate_use_celery(self):
        """app是否使用celery"""
        return 0

    def hybrate_use_celery_beat(self):
        """use_celery_beat"""
        return 0

    def get_mobile_config(self, env_name: str) -> Optional[MobileConfig]:
        try:
            env = self.application.envs.get(module__is_default=True, environment=env_name)
        except ObjectDoesNotExist:
            logger.warning("The env object does not exist, app: %s(%s).", self.application.code, env_name)
            return None

        try:
            return env.mobile_config
        except ObjectDoesNotExist:
            logger.warning("The mobile config object does not exist, app: %s(%s).", self.application.code, env_name)
            return None

    def hybrate_use_mobile_online(self):
        """
        app是否在移动端(正式)使用
        选项: 1(是)，0(否)
        """
        mobile_config = self.get_mobile_config("prod")
        return mobile_config.is_enabled if mobile_config else 0

    def hybrate_use_mobile_test(self):
        """
        app是否在移动端(测试)使用
        选项: 1(是)，0(否)
        """
        mobile_config = self.get_mobile_config("stag")
        return mobile_config.is_enabled if mobile_config else 0

    def hybrate_mobile_url_test(self):
        """APP 移动端预发布环境地址"""
        mobile_config = self.get_mobile_config("stag")
        return mobile_config.access_url if mobile_config else ""

    def hybrate_mobile_url_prod(self):
        """APP 移动端生产环境地址"""
        mobile_config = self.get_mobile_config("prod")
        return mobile_config.access_url if mobile_config else ""

    def hybrate_usecount(self):
        """
        使用人数
        添加了该应用的人数，note：用户卸载应用后，要相应的减1
        note: 这个字段应该桌面操作的时候写回数据库的，开发者中心不应该写这个字段
        """
        raise FieldNotFound("usecount")

    def hybrate_usecount_ied(self):
        """
        使用人数
        添加了该应用的人数，note：用户卸载应用后，要相应的减1
        note: 这个字段应该桌面操作的时候写回数据库的，开发者中心不应该写这个字段
        """
        # raise FieldNotFound("usecount")
        return 0

    def hybrate_online_version(self):
        """上线代码版本目录"""
        return ""

    def hybrate_tem_svn(self):
        """
        开发框架代码地址
        app注册时选择的开发框架svn地址和版本
        """
        raise FieldNotFound("tem_svn")

    def hybrate_dev_time(self):
        """
        应用开发时间
        CharField
        单位为小时，总耗时，为每次上线时填写的开发成本总和
        """
        return "0.0"

    def hybrate_first_online_time(self):
        return datetime.datetime.now()

    def hybrate_first_test_time(self):
        return datetime.datetime.now()

    def hybrate_code(self):
        return self.product.code

    def hybrate_builtin_path(self):
        raise FieldNotFound("builtin_path")

    def hybrate_description(self):
        return self.product.description if self.product.description else ""

    def hybrate_external_url(self):
        application = self.application
        market_config = self.market_config
        module = market_config.source_module

        # 不刷新 module 会有异常
        module.refresh_from_db()

        if not market_config.enabled:
            # 未开启市场时, 不同步 external_url
            raise FieldNotFound("external_url")

        logger.info(f"sync exposed url for {application}")
        # NOTE: 该处有多种可能性
        # 当应用为精简版应用, 该处返回应用市场页设置的 `第三方地址`
        # 当应用选取独立域名为主入口, 该处返回 独立域名
        # 当模块的访问类型为 `独立子域名`, 该处返回 独立子域名
        # 当模块的访问类型为 `独立子路径`, 该处返回 独立子路径(但由于独立子路径为默认情况, 在上方已提早返回 None)
        access_entrance = MarketAvailableAddressHelper(market_config).access_entrance
        if access_entrance is None:
            raise FieldNotFound("external_url")
        return access_entrance.address

    def hybrate_group_id(self):
        raise FieldNotFound("group_id")

    def hybrate_extra(self):
        raise FieldNotFound("extra")

    def hybrate_open_mode(self):
        return self.display_options.open_mode

    def hybrate_height(self):
        return self.display_options.height if self.display_options.height else 550

    def hybrate_width(self):
        return self.display_options.width if self.display_options.width else 890

    def hybrate_id(self):
        raise FieldNotFound("id")

    def hybrate_introduction(self):
        return self.product.introduction_zh_cn if self.product.introduction_zh_cn else ""

    def hybrate_name(self):
        return self.product.name_zh_cn

    def hybrate_introduction_en(self):
        return self.product.introduction_en if self.product.introduction_en else ""

    def hybrate_name_en(self):
        return self.product.name_en

    def hybrate_product_ip(self):
        raise FieldNotFound("product_ip")

    def hybrate_from_paasv3(self):
        """桌面新增字段，用于标记是paas3.0应用"""
        return 1

    def hybrate_visiable_labels(self):
        """应用可见范围"""
        return self.product.transform_visiable_labels()
