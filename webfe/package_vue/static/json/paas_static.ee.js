/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *     http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

/* eslint-disable */
import Vue from 'vue';
import i18n from '@/language/i18n';


const staticI18n = new Vue({
    i18n
})

export const PLATFORM_CONFIG = {
    // 应用类型
    APP_TYPES: {
        NORMAL_APP: 1,
        LESSCODE_APP: 2,
        SMART_APP: 3,
        IMAGE: 4,
        SCENE_APP: 5,
        CNATIVE_IMAGE: 6        //仅镜像的云原生
    },

    // 默认使用的代码库类型
    DEFAULT_SOURCE_CONTROL: 'bare_git',

    // 蓝鲸帮助助手信息
    HELPER: {
        name: staticI18n.$t('管理员'),
        href: ''
    },

    OA_DOMAIN: '',

    WOA_DOMAIN: '',

    IED_DOMAIN: '',

    // 链接
    LINK: {
        // 获取 用户/组织 API
        MEMBER_API: '',
        // 数据统计
        STATIC_JS_API: '',

        // 桌面应用市场
        APP_MARKET: BK_PAAS2_URL + '/console/?app=market',

        // 旧版开发者中心-首页
        V2_APP_SUMMARY: BK_PAAS2_URL + '/app/list/',

        // v2开发者中心-应用概览
        V2_APP_BASEINFO: BK_PAAS2_URL + '/app/info/',

        // v2应用logo
        V2_APP_LOGOG: '',

        // v2应用默认logo
        V2_DEFAULT_LOGO: '',

        // 蓝鲸数据可视化服务
        DATA_INDEX: '',

        // widget配置
        DATA_WIDGET_INDEX: '',

        // 视图面板配置
        DATA_DASHBOARD_INDEX: '',

        // MagicBox
        MAGICBOX_INDEX: 'https://magicbox.bk.tencent.com/static_api/v3/main/index.html',

        LESSCODE_INDEX: BK_LESSCODE_URL,

        // 前端jQuery组件库
        MAGICBOX_JQUERY: 'https://magicbox.bk.tencent.com/static_api/v3/index.html',

        // 前端Vue组件库
        MAGICBOX_VUE: 'https://magicbox.bk.tencent.com/static_api/v3/components_vue/2.0/example/index.html#/',

        // 前端套餐样例库
        MAGICBOX_TPL: 'https://magicbox.bk.tencent.com/static_api/v3/index.html#templates',

        // 蓝鲸前端开发脚手架（BKUI_CLI）
        MAGICBOX_BKUI_CLI: DOCS_URL_PREFIX + '/markdown/开发指南/SaaS开发/开发进阶/bkui/bkui.md',

        // Bamboo 流程引擎源码
        BAMBOO_CODE: 'https://github.com/TencentBlueKing/bamboo-engine',

        // AppRocket 502？
        APP_ROCKET: '',

        // API Gateway
        APIGW_INDEX: BK_APIGW_URL,

        // 问题反馈
        PA_ISSUE: 'https://bk.tencent.com/s-mart/community/question',

        // 加入圈子
        PA_MARKER: '',

        // BK助手
        BK_HELP: '',

        // BK桌面
        BK_DESKTOP: '',

        // BK插件
        BK_PLUGIN: 'https://github.com/TencentBlueKing/bk-plugin-framework-python',

        //BKtemplate
        BK_PLUGIN_TEMPLATE: 'https://github.com/TencentBlueKing/bk-plugin-framework-python/tree/master/template',

        // 产品文档
        BK_APP_DOC: DOCS_URL_PREFIX,

        // 开源社区
        BK_OPEN_COMMUNITY: 'https://github.com/TencentBlueKing/blueking-paas',

        // 技术支持
        BK_TECHNICAL_SUPPORT: 'https://wpa1.qq.com/KziXGWJs?_type=wpa&qidian=true',

        // 社区论坛
        BK_COMMUNITY: 'https://bk.tencent.com/s-mart/community/',

        // 产品官网
        BK_OFFICIAL_WEBSITE: 'https://bk.tencent.com/'
    },

    // 文档
    DOC: {
        // 产品文档，导航右上角展示的文档总入口
        PRODUCT_DOC: BK_DOCS_URL_PREFIX + '/markdown/PaaS/UserGuide/Overview/README.md',

        // 配置蓝鲸应用访问入口
        APP_ENTRY_INTRO: DOCS_URL_PREFIX + '/topics/paas/app_entry_intro#section-3',

        // API帮助文档中心
        API_HELP: BK_APIGW_DOC_URL,

        // Python 开发框架（blueapps）- 框架文档
        PYTHON_FRAMEWORK: DOCS_URL_PREFIX + '/topics/company_tencent/python_framework_usage',

        // Go 开发框架- 快速开始
        GO_START: DOCS_URL_PREFIX + '/quickstart/golang/golang_preparations',

        // 蓝鲸应用多模块功能简介
        MODULE_INTRO: DOCS_URL_PREFIX + '/topics/paas/multi_modules_intro',

        // 工蜂授权指南
        TC_GIT_AUTH: DOCS_URL_PREFIX + '/topics/paas/tc_git_oauth',

        // 权限管理 - 用户限制
        ACCESS_CONTROL: DOCS_URL_PREFIX + '/topics/paas/access_control/user',

        // 什么是“主模块”？
        MODULE_DEFAULT_INTRO: DOCS_URL_PREFIX + '/topics/paas/multi_modules_intro#%E4%BB%80%E4%B9%88%E6%98%AF%E4%B8%BB%E6%A8%A1%E5%9D%97',

        // 数据统计 - 自定义事件统计简介
        PA_ANALYSIS_CUSTOM: DOCS_URL_PREFIX + '/topics/paas/pa_custom_intro',

        // 数据统计 - 网站浏览统计简介
        PA_ANALYSIS_WEB: DOCS_URL_PREFIX + '/topics/paas/pa_introduction',

        // 数据统计 - 访问日志统计简介
        PA_ANALYSIS_INGRESS: DOCS_URL_PREFIX + '/topics/paas/pa_ingress_intro',

        // 访问日志统计的 UV 是怎么计算的
        PA_ANALYSIS_INGRESS_UV: DOCS_URL_PREFIX + '/topics/paas/pa_ingress_intro#%E8%AE%BF%E9%97%AE%E6%97%A5%E5%BF%97%E7%BB%9F%E8%AE%A1%E7%9A%84-uv-%E6%98%AF%E6%80%8E%E4%B9%88%E8%AE%A1%E7%AE%97%E7%9A%84',

        // 蓝鲸应用代码检查功能简介
        CODE_REVIEW: DOCS_URL_PREFIX + '/topics/paas/ci',

        // 示例：如何为 Python 应用添加 celery 后台任务进程
        PROCESS_CELERY: DOCS_URL_PREFIX + '/topics/paas/process_procfile#%E4%BB%80%E4%B9%88%E6%98%AFprocfile',

        // 应用进程概念介绍以及如何使用
        PROCESS_INTRO: DOCS_URL_PREFIX + '/topics/paas/process_procfile#section',

        //应用内部进程通信指南
        PROCESS_IPC: DOCS_URL_PREFIX + '/topics/paas/entry_proc_services#%E8%BF%9B%E7%A8%8B%E9%97%B4%E5%A6%82%E4%BD%95%E9%80%9A%E4%BF%A1',

        // 配置蓝鲸应用访问入口
        APP_ENTRY_INTRO: DOCS_URL_PREFIX + '/topics/paas/app_entry_intro#section-1',

        // 进程服务说明
        PROCESS_SERVICE: DOCS_URL_PREFIX + '/topics/paas/entry_proc_services',

        // 内置环境变量说明 - 什么是内置环境变量
        ENV_VAR_INLINE: DOCS_URL_PREFIX + '/topics/paas/builtin_configvars#%E4%BB%80%E4%B9%88%E6%98%AF%E5%86%85%E7%BD%AE%E7%8E%AF%E5%A2%83%E5%8F%98%E9%87%8F',

        // 日志查询语法
        LOG_QUERY_SYNTAX: DOCS_URL_PREFIX + '/topics/paas/log_query_syntax',

        // 为什么日志查询为空
        LOG_QUERY_EMPTY: DOCS_URL_PREFIX + '/topics/paas/log_empty',

        // 如何查询应用日志
        LOG_QUERY_USER: DOCS_URL_PREFIX + '/topics/paas/log_intro#%E5%A6%82%E4%BD%95%E6%9F%A5%E8%AF%A2%E5%BA%94%E7%94%A8%E6%97%A5%E5%BF%97',

        // 监控告警服务简介
        MONITOR_INTRO: DOCS_URL_PREFIX + '/topics/paas/monitoring/intro',

        // 旧应用迁移介绍
        LEGACY_MIGRATION: DOCS_URL_PREFIX + '/topics/paas/legacy_migration',

        // 增强服务介绍目录
        SERVICE_INDEX: DOCS_URL_PREFIX + '/topics/paas/services/index',

        // NodeJS 开发框架
        NODE_FRAMEWORK: DOCS_URL_PREFIX + '/quickstart/node/node_preparations',

        // 开发者常见问题
        FAQ: DOCS_URL_PREFIX + '/faq/saas_dev.md',

        // Python开发框架结合BKUI-CLI使用指南
        BKUI_WITH_PYTHON: DOCS_URL_PREFIX + '/topics/bkui/with-python',

        // APIGW API调用指引
        // APIGW_USER_API: BK_APIGW_DOC_URL + '/guide/use-api.html',
        APIGW_USER_API: BK_DOCS_URL_PREFIX + '/markdown/APIGateway/apigateway/use-api/use-apigw-api.md',

        // APIGW QUICK_START
        // APIGW_QUICK_START: BK_APIGW_DOC_URL + '/guide/quickstart.html',
        APIGW_QUICK_START: BK_DOCS_URL_PREFIX + '/markdown/APIGateway/apigateway/quickstart/create-api-with-http-backend.md',

        // APIGW FAQ
        // APIGW_FAQ: BK_APIGW_DOC_URL + '/guide/faq.html',
        APIGW_FAQ: BK_DOCS_URL_PREFIX + '/markdown/APIGateway/apigateway/faq/use-apigw-api.md',

        LESSCODE_START: BK_LESSCODE_URL + '/help/start',

        // Python 开发规范
        PTTHON_DEV_GUIDE: 'https://bk.tencent.com/docs/markdown/开发指南/开发规范/后台开发规范/README.md',

        // 前端开发规范
        FRONTEND_DEV_GUIDE: 'https://bk.tencent.com/docs/markdown/开发指南/开发规范/前端开发规范/README.md',

        // 如何查看慢查询的 SQL 语句
        CHECK_SQL: DOCS_URL_PREFIX + '/topics/paas/monitoring/handle_slow_query_alerts#%E5%A6%82%E4%BD%95%E6%9F%A5%E7%9C%8B%E6%85%A2%E6%9F%A5%E8%AF%A2%E7%9A%84-sql-%E8%AF%AD%E5%8F%A5',

        // 蓝鲸应用项目管理规范
        PROJECT_MANAGER_GUIDE: '',

        // 如何设置部署目录
        DEPLOY_DIR: DOCS_URL_PREFIX + '/topics/paas/deployment_directory',

        // 部署前置命令
        DEPLOY_ORDER: DOCS_URL_PREFIX + '/topics/paas/release_hooks',

        //应用进程与Profile
        PROCFILE_DOC: DOCS_URL_PREFIX + '/topics/paas/process_procfile',

        //应用描述文件
        APP_DESC_DOC: DOCS_URL_PREFIX + '/topics/paas/app_desc',

        // 使用Arm架构的机器如何构建x86平台镜像
        ARCHITECTURE_PLATFORM_IMAGE: DOCS_URL_PREFIX + '/topics/paas/deploy_flow#%E4%BD%BF%E7%94%A8-arm-%E6%9E%B6%E6%9E%84%E7%9A%84%E6%9C%BA%E5%99%A8%E5%A6%82%E4%BD%95%E6%9E%84%E5%BB%BA-x86-%E5%B9%B3%E5%8F%B0%E9%95%9C%E5%83%8F',

        // 服务发现配置
        SERVE_DISCOVERY: DOCS_URL_PREFIX + '/topics/paas/app_desc#%E6%9C%8D%E5%8A%A1%E5%8F%91%E7%8E%B0%E9%85%8D%E7%BD%AEsvc_discovery',
        
        // 帮助：如何构建镜像
        BUILDING_MIRRIRS_DOC: DOCS_URL_PREFIX + '/quickstart/docker/docker_hello_world',
        
        // 代码库 OAuth 授权配置指引
        OATUH_CONFIG_GUIDE: BK_DOCS_URL_PREFIX + '/markdown/PaaS平台/产品白皮书/产品功能/系统管理/PaaS3/SysOps.md#代码仓库%20OAuth%20授权配置',

        // 构建阶段钩子
        BUILD_PHASE_HOOK: DOCS_URL_PREFIX + '/topics/paas/build_hooks.md',
    },

    CONFIG: {
        IFRAME_CLASS: 'small',
        // 版本日志
        RELEASE_LOG: 'TRUE',
        // 镜像地址
        MIRROR_PREFIX: '',
        // 镜像示例
        MIRROR_EXAMPLE: 'docker.io/library/nginx',
        // region
        REGION_CHOOSE: 'default',
        // 市场信息
        MARKET_INFO: '',
        // 应用提示
        MARKET_TIPS: staticI18n.$t('蓝鲸桌面'),
        // 框架
        GO_FRAME: ''
    }
}

export const PAAS_STATIC_CONFIG = {
    "header": {
        "message": staticI18n.$t("头部导航列表"),
        "list": {
            "nav": [
                {
                    "text": staticI18n.$t('首页'),
                },
                {
                    "text": staticI18n.$t("应用开发"),
                    "url": "apps"
                },
                {
                    "text": staticI18n.$t("插件开发")
                },
                {
                    "text": staticI18n.$t("API 网关")
                },
                {
                    "text": staticI18n.$t("服务")
                }
            ],
            "api_subnav_service": [
                {
                    "title": "",
                    "items": [
                        {
                            "text": staticI18n.$t("网关管理"),
                            "url": BK_APIGW_URL
                        },
                        {
                            "text": staticI18n.$t("API 文档"),
                            "url": BK_APIGW_DOC_URL + "/apigw-api"
                        }
                    ]
                }
            ],
            "subnav_service": [
                {
                    "title": staticI18n.$t("开发"),
                    "items": [
                        {
                            "text": staticI18n.$t("代码库管理"),
                            "url": "code",
                            "explain": staticI18n.$t("支持代码仓库 OAuth 授权")
                        },
                        {
                            "text": staticI18n.$t("API 网关"),
                            "url": "apigateway",
                            "explain": staticI18n.$t("蓝鲸API网关服务")
                        },
                        {
                            "text": staticI18n.$t("开发框架"),
                            "url": "framework",
                            "explain": staticI18n.$t("蓝鲸应用统一开发框架，集成基础功能模块及功能样例")
                        },
                        {
                            "text": staticI18n.$t("前端组件库"),
                            "url": "magicbox",
                            "explain": staticI18n.$t("蓝鲸前端组件样例库")
                        },
                        {
                            "text": staticI18n.$t("运维开发工具"),
                            "url": "lesscode",
                            "explain": staticI18n.$t("蓝鲸智云运维开发工具平台提供了前端页面在线可视化拖拽组装、配置编辑、源码生成、二次开发等能力。旨在帮助用户通过尽量少的手写代码的方式快速设计和开发 SaaS")
                        }
                    ]
                },
                {
                    "items": [
                        {
                            "title": staticI18n.$t("计算"),
                            "items": [
                                {
                                    "text": staticI18n.$t("应用引擎"),
                                    "url": "app-engine",
                                    "explain": staticI18n.$t("提供弹性、便捷的应用部署服务，支持Python、Go 等多种语言")
                                }
                            ]
                        },
                        {
                            "title": staticI18n.$t("增强服务"),
                            "items": [
                                {
                                    "text": staticI18n.$t("数据存储"),
                                    "url": "vas/1",
                                    "explain": staticI18n.$t("蓝鲸提供的数据存储类服务集合")
                                }
                            ]
                        }
                    ]
                },
                {
                    "title": staticI18n.$t("流程引擎"),
                    "items": [
                        {
                            "text": "Bamboo",
                            "url": "bamboo",
                            "explain": staticI18n.$t("标准运维V3使用的分布式的流程定义、管理、调度引擎")
                        }
                    ]
                },
                {
                    "title": staticI18n.$t("推广"),
                    "items": [
                        {
                            "text": staticI18n.$t("应用市场"),
                            "url": "market",
                            "explain": staticI18n.$t("蓝鲸提供的官方应用市场，用户可以在市场中搜索并使用您开发的应用")
                        }
                    ]
                }
            ],
            "subnav_doc": [
                {
                    "title": staticI18n.$t("文档"),
                    "items": [
                        {
                            "text": staticI18n.$t("新手入门"),
                            "url": DOCS_URL_PREFIX + "/quickstart/"
                        },
                        {
                            "text": staticI18n.$t("开发指南"),
                            "url": DOCS_URL_PREFIX + "/topics/"
                        },
                        {
                            "text": "FAQ",
                            "url": DOCS_URL_PREFIX + '/faq/saas_dev.md'
                        }
                    ]
                },
                {
                    "title": staticI18n.$t("资源与工具"),
                    "items": [
                        {
                            "text": staticI18n.$t("API文档"),
                            "url": BK_APIGW_DOC_URL + "/apigw-api"
                        },
                        {
                            "text": staticI18n.$t("SDK文档"),
                            "url": DOCS_URL_PREFIX + "/sdk/"
                        }
                    ]
                },
                {
                    "title": staticI18n.$t("社区"),
                    "items": [
                        {
                            "text": staticI18n.$t("蓝鲸论坛"),
                            "url": "https://bk.tencent.com/s-mart/community/"
                        }
                    ]
                }
            ]
        }
    },
    "footer": {
        "message": staticI18n.$t("尾部列表"),
        "owenner": staticI18n.$t("腾讯公司版权所有"),
        "list": [
            {
                "title": staticI18n.$t("文档"),
                "sublist": [
                    {
                        "text": staticI18n.$t("新手入门"),
                        "url": DOCS_URL_PREFIX + "/quickstart/"
                    },
                    {
                        "text": staticI18n.$t("开发指南"),
                        "url": DOCS_URL_PREFIX + "/topics/"
                    },
                    {
                        "text": "FAQ",
                        "url": DOCS_URL_PREFIX + '/faq/saas_dev.md'
                    }
                ]
            },
            {
                "title": staticI18n.$t("资源与工具"),
                "sublist": [
                    {
                        "text": staticI18n.$t("API文档"),
                        "url": BK_APIGW_DOC_URL + "/apigw-api"
                    },
                    {
                        "text": staticI18n.$t("SDK文档"),
                        "url": DOCS_URL_PREFIX + "/sdk/"
                    }
                ]
            },
            {
                "title": staticI18n.$t("社区"),
                "sublist": [
                    {
                        "text": staticI18n.$t("蓝鲸论坛"),
                        "url": "https://bk.tencent.com/s-mart/community/"
                    }
                ]
            },
            {
                "title": staticI18n.$t("联系我们"),
                "sublist": [
                    {
                        "text": staticI18n.$t("QQ咨询(800802001) "),
                        "url": ""
                    }
                ]
            }
        ]
    },
    "index": {
        "message": staticI18n.$t("首页静态数据接口"),
        "data": {
            "banner_btn": {
                "text": staticI18n.$t("我要创建应用"),
                "url": "javascript:;"
            },
            "new_user": {
                "notice": staticI18n.$t("新手入门指引列表"),
                "list": [
                    {
                        "title": staticI18n.$t("如何开始开发一个蓝鲸应用？"),
                        "url": DOCS_URL_PREFIX + "/quickstart/python/python_hello_world",
                        "info": staticI18n.$t("Step by Step 教您开发一个 Hello World 应用")
                    },
                    {
                        "title": staticI18n.$t("如何搭建本地开发环境？"),
                        "url": DOCS_URL_PREFIX + "/quickstart/python/python_setup_dev",
                        "info": staticI18n.$t("使用蓝鲸统一开发环境，本地快速搭建")
                    },
                    {
                        "title": staticI18n.$t("如何部署蓝鲸应用？"),
                        "url": DOCS_URL_PREFIX + "/topics/paas/deploy_intro",
                        "info": staticI18n.$t("应用在线一键部署到预发布环境/生产环境")
                    }
                ]
            },
            "guide_info": {
                "notice": staticI18n.$t("使用指南列表"),
                "list": [
                    {
                        "title": staticI18n.$t("如何使用蓝鲸开发框架？"),
                        "url": DOCS_URL_PREFIX + "/topics/company_tencent/python_framework_usage",
                        "info": staticI18n.$t("集成登录鉴权、安全防护、权限控制等基础模块，更有后台任务、云API调用等样例供您参考")
                    },
                    {
                        "title": staticI18n.$t("如何使用蓝鲸云API服务？"),
                        "url": DOCS_URL_PREFIX + "/quickstart/python/python_api_example",
                        "info": staticI18n.$t("蓝鲸服务总线对接多个原子系统，提供丰富的云API供您使用")
                    },
                    {
                        "title": staticI18n.$t("如何使用蓝鲸MagicBox服务？"),
                        "url": "https://magicbox.bk.tencent.com/static_api/v3/index.html#start",
                        "info": staticI18n.$t("蓝鲸MagicBox提供丰富的前端UI组件，更有样例套餐助您快速搭建前端页面")
                    }
                ]
            }
        },
        "result": true
    },
    "app_nav": {
        "message": staticI18n.$t("应用左侧导航"),
        "cloudList": [
            {
                "name": "cloudAppSummary",
                "label": staticI18n.$t("概览"),
                "matchRouters": ["appSummaryEmpty", "cloudAppSummary"],
                "iconfontName": "metrics",
                "supportModule": true,
                "destRoute": {
                  "name": "cloudAppSummary"
                },
                "children": []
            },
            {
                "name": "cloudAppImageManage",
                "label": staticI18n.$t("镜像管理"),
                "matchRouters": [
                    "cloudAppImageManage",
                    "cloudAppImageList",
                    "cloudAppBuildHistory",
                ],
                "iconfontName": "jingxiang",
                "supportModule": true,
                "destRoute": {
                  "name": "cloudAppImageManage"
                },
                "children": []
            },
            {
                "name": "cloudAppDeployManageStag",
                "label": staticI18n.$t("部署管理"),
                "matchRouters": [
                    "cloudAppDeployManage",
                    "cloudAppDeployManageStag",
                    "cloudAppDeployManageProd",
                    "cloudAppDeployHistory"
                ],
                "iconfontName": "bushu",
                "supportModule": false,
                "destRoute": {
                  "name": "cloudAppDeployManageStag"
                },
                "children": []
            },
            {
                "name": "appObservability",
                "label": staticI18n.$t("可观测性"),
                "iconfontName": "keguance",
                "supportModule": false,
                "children": [
                    {
                        "name": staticI18n.$t("日志查询"),
                        "destRoute": {
                            "name": "appLog"
                        }
                    },
                    {
                        "name": staticI18n.$t("事件查询"),
                        "destRoute": {
                            "name": "cloudAppEventQuery"
                        }
                    },
                    {
                        "name": staticI18n.$t("告警记录"),
                        "destRoute": {
                            "name": "monitorAlarm"
                        }
                    },
                    {
                        "name": staticI18n.$t("访问统计"),
                        "matchRouters": [
                            "cloudAppWebAnalysis",
                            "cloudAppLogAnalysis",
                            "cloudAppEventAnalysis"
                        ],
                        "destRoute": {
                            "name": "cloudAppAnalysis"
                        }
                    }
                ]
            },
            {
                "name": "appCloudAPI",
                "label": staticI18n.$t("云 API 权限"),
                "iconfontName": "cloudapi",
                "supportModule": false,
                "destRoute": {
                    "name": "appCloudAPI"
                },
                "children": []
            },
            {
                "name": "appEntryConfig",
                "label": staticI18n.$t("访问管理"),
                "iconfontName": "diamond",
                "supportModule": false,
                "destRoute": {
                    "name": "appEntryConfig"
                },
                "children": []
            },
            {
                "name": "appConfigs",
                "label": staticI18n.$t("应用配置"),
                "iconfontName": "gear",
                "children": [
                    {
                        "name": staticI18n.$t("模块配置"),
                        "matchRouters": [
                            "cloudAppDeploy",
                            "cloudAppDeployForBuild",
                            "cloudAppDeployForProcess",
                            "cloudAppDeployForEnv",
                            "cloudAppDeployForVolume",
                            "cloudAppDeployForYaml",
                            "cloudAppDeployForHook",
                            "cloudAppDeployForResource",
                            'imageCredential',
                            'observabilityConfig',
                            'moduleInfo',
                            'appServices',
                            'appServiceInnerShared',
                            'appServiceInner',
                            'cloudAppServiceInnerShared',
                            'cloudAppServiceInner',
                            'cloudAppServiceInnerWithModule',
                            'networkConfig'
                        ],
                        "iconfontName": "squares",
                        "supportModule": false,
                        "destRoute": {
                          "name": "cloudAppDeployForBuild"
                        },
                        "children": []
                    },
                    {
                        "name": staticI18n.$t("应用配置"),
                        "matchRouters": [
                            'appConfigs',
                            'appMarket',
                            'appBasicInfo',
                            'appMembers',
                        ],
                        "destRoute": {
                          "name": "appConfigs"
                        }
                    }
                ]
            },
            {
                "name": "docuManagement",
                "label": staticI18n.$t("文档管理"),
                "matchRouters": [
                    "docuManagement"
                ],
                "iconfontName": "page-fill",
                "supportModule": false,
                "destRoute": {
                    "name": "docuManagement"
                },
                "children": []
            }
        ],
        "pluginList": [
            {
                "name": "pluginSummary",
                "label": staticI18n.$t("概览"),
                "matchRouters": [
                    "appSummaryEmpty",
                    "pluginSummary"
                ],
                "iconfontName": "overview",
                "supportModule": true,
                "destRoute": {
                    "name": "pluginSummary"
                },
                "children": []
            },
            {
                "name": "pluginVersionManager",
                "label": staticI18n.$t("版本管理"),
                "matchRouters": [
                    "pluginVersionManager",
                    "pluginVersionEditor",
                    "pluginVersionRelease"
                ],
                "iconfontName": "publish-fill",
                "supportModule": true,
                "destRoute": {
                    "name": "pluginVersionManager"
                },
                "children": []
            },
            {
                "name": "pluginDeployEnv",
                "label": staticI18n.$t("配置管理"),
                "matchRouters": [
                    "pluginDeployEnv"
                ],
                "iconfontName": "configuration",
                "supportModule": true,
                "destRoute": {
                    "name": "pluginDeployEnv"
                },
                "children": []
            },
            {
                "name": "pluginLog",
                "label": staticI18n.$t("日志查询"),
                "matchRouters": ["pluginLog"],
                "iconfontName": "log-2",
                "supportModule": false,
                "destRoute": {
                  "name": "pluginLog"
                },
                "children": []
            },
            {
                "name": "pluginProcess",
                "label": staticI18n.$t("进程管理"),
                "iconfontName": "process",
                "supportModule": false,
                "destRoute": {
                  "name": "pluginProcess"
                },
                "children": []
            },
            {
                "name": "pluginCloudAPI",
                "label": staticI18n.$t("云 API 权限"),
                "iconfontName": "api",
                "supportModule": false,
                "destRoute": {
                  "name": "pluginCloudAPI"
                },
                "children": []
            },
            {
                "name": "pluginConfigs",
                "label": staticI18n.$t("基本设置"),
                "iconfontName": "setting-2",
                "children": [
                    {
                        "name": staticI18n.$t("基本信息"),
                        "destRoute": {
                          "name": "pluginBaseInfo"
                        },
                        "matchRouters": [
                            "pluginBaseInfo",
                            "marketInfoEdit",
                            "moreInfoEdit"
                        ]
                    },
                    {
                        "name": staticI18n.$t("成员管理"),
                        "destRoute": {
                          "name": "pluginRoles"
                        }
                    }
                ]
            },
        ],
        "list": [
            {
                "name": "appSummary",
                "label": staticI18n.$t("概览"),
                "matchRouters": [
                    "appSummaryEmpty",
                    "appSummary"
                ],
                "iconfontName": "metrics",
                "supportModule": true,
                "destRoute": {
                    "name": "appSummary"
                },
                "children": []
            },
            {
                "name": "appEngine",
                "label": staticI18n.$t("应用引擎"),
                "iconfontName": "squares",
                "supportModule": true,
                "children": [
                    {
                        "name": staticI18n.$t("部署管理"),
                        "matchRouters": [
                            "appDeploy",
                            "appDeployHistory",
                            "appDeployForStag",
                            "appDeployForProd",
                            "appDeployForHistory",
                            "appDeployForConfig"
                        ],
                        "destRoute": {
                            "name": "appDeployForStag"
                        }
                    },
                    {
                        "name": staticI18n.$t("包版本管理"),
                        "destRoute": {
                            "name": "appPackages"
                        }
                    },
                    {
                        "name": staticI18n.$t("进程管理"),
                        "destRoute": {
                            "name": "appProcess"
                        }
                    },
                    {
                        "name": staticI18n.$t("日志查询"),
                        "destRoute": {
                            "name": "appLog"
                        }
                    },
                    {
                        "name": staticI18n.$t("环境配置"),
                        "routerName": "appEnvVariables",
                        "destRoute": {
                            "name": "appEnvVariables"
                        }
                    }
                ]
            },
            {
                "name": "appEngineOperator",
                "label": staticI18n.$t("应用引擎"),     //运营者视角应用引擎
                "iconfontName": "squares",
                "supportModule": true,
                "children": []
            },
            {
                "name": "appServices",
                "label": staticI18n.$t("增强服务"),
                "iconfontName": "diamond",
                "supportModule": true,
                "children": []
            },
            {
                "name": "moduleManage",
                "label": staticI18n.$t("模块管理"),
                "matchRouters": [
                    "moduleManage"
                ],
                "iconfontName": "modules",
                "supportModule": true,
                "destRoute": {
                    "name": "moduleManage"
                },
                "children": []
            },
            {
                "name": "appCloudAPI",
                "label": staticI18n.$t("云 API 权限"),
                "iconfontName": "cloudapi",
                "supportModule": false,
                "destRoute": {
                    "name": "appCloudAPI"
                },
                "children": []
            },
            {
                "name": "monitorAlarm",
                "label": staticI18n.$t("监控告警"),
                "iconfontName": "monitor",
                "supportModule": true,
                "children": [
                    {
                        "name": staticI18n.$t("告警记录"),
                        "destRoute": {
                            "name": "monitorAlarm"
                        }
                    }
                ]
            },
            {
                "name": "appAnalysis",
                "label": staticI18n.$t("访问统计"),
                "iconfontName": "analysis",
                "matchRouters": [
                    "appWebAnalysis",
                    "appLogAnalysis",
                    "appEventAnalysis"
                ],
                "supportModule": true,
                "destRoute": {
                    "name": "appAnalysis"
                },
                "children": []
            },
            {
                "name": "appConfigs",
                "iconfontName": "gear",
                "label": staticI18n.$t("应用配置"),
                "matchRouters": [
                    'appConfigs',
                    'appMarket',
                    'appBasicInfo',
                    'appMembers',
                    'appMobileMarket',
                ],
                "destRoute": {
                  "name": "appConfigs"
                },
                "children": []
            },
            {
                "name": "docuManagement",
                "label": staticI18n.$t("文档管理"),
                "matchRouters": [
                    "docuManagement"
                ],
                "iconfontName": "page-fill",
                "supportModule": false,
                "destRoute": {
                    "name": "docuManagement"
                },
                "children": []
            }
        ]
    },
    "bk_service": {
        "message": staticI18n.$t("蓝鲸服务导航文案"),
        "list": [
            {
                "name": "development",
                "label": staticI18n.$t("开发"),
                "iconfontName": "window-source-code",
                "sublist": [
                    {
                        "name": staticI18n.$t("代码库管理"),
                        "destRoute": {
                          "name": "serviceCode"
                        }
                    },
                    {
                        "name": staticI18n.$t("API 网关"),
                        "destRoute": {
                            "name": "serviceAPIGateway"
                        }
                    },
                    {
                        "name": staticI18n.$t("开发框架"),
                        "destRoute": {
                            "name": "serviceFramework"
                        }
                    },
                    {
                        "name": staticI18n.$t("前端组件库"),
                        "destRoute": {
                            "name": "serviceMagicBox"
                        }
                    },
                    {
                        "name": staticI18n.$t("运维开发工具"),
                        "destRoute": {
                          "name": "serviceLesscode"
                        }
                    }
                ]
            },
            {
                "name": "computing",
                "label": staticI18n.$t("计算"),
                "iconfontName": "chip",
                "sublist": [
                    {
                        "name": staticI18n.$t("应用引擎"),
                        "destRoute": {
                            "name": "serviceAppEngine"
                        }
                    }
                ]
            },
            {
                "name": "appServices",
                "label": staticI18n.$t("增强服务"),
                "iconfontName": "diamond",
                "sublist": [
                    {
                        "name": staticI18n.$t("数据存储"),
                        "matchRouters": [
                            "serviceVas",
                            "serviceInnerPage"
                        ],
                        "destRoute": {
                            "name": "serviceVas",
                            "params": {
                                "category_id": "1"
                            }
                        }
                    }
                ]
            },
            {
                "name": "workflow",
                "label": staticI18n.$t("流程引擎"),
                "iconfontName": "dashboard",
                "sublist": [
                    {
                        "name": "Bamboo",
                        "destRoute": {
                            "name": "serviceBamboo"
                        }
                    }
                ]
            },
            {
                "name": "marketing",
                "label": staticI18n.$t("推广"),
                "iconfontName": "volumn",
                "sublist": [
                    {
                        "name": staticI18n.$t("应用市场"),
                        "destRoute": {
                            "name": "serviceMarket"
                        }
                    }
                ]
            }
        ]
    }
}
