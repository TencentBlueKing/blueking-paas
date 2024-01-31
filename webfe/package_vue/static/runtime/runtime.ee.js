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
var SITE_URL = process.env.BK_PAAS3_URL || '' // 蓝鲸 PaaS3.0 平台访问地址
var LOGIN_SERVICE_URL = process.env.BK_LOGIN_URL || '' // 登录跳转地址
var BK_PAAS2_URL = process.env.BK_PAAS2_URL || '' // 蓝鲸 PaaS2.0 平台访问地址，用于平台访问链接拼接
var BK_DOCS_URL_PREFIX = process.env.BK_DOCS_URL_PREFIX || '' // 中心前缀，用于拼接文档地址
var BK_APIGW_URL = process.env.BK_APIGW_URL || '' // API GW 访问地址
var BK_APIGW_DOC_URL = process.env.BK_APIGW_DOC_URL || '' // API GW 文档中心地址
var BK_LESSCODE_URL = process.env.BK_LESSCODE_URL || '' // 用于拼接 lesscode 的访问地址，bk_leescode 作为 Smart 应用部署到 PaaS3.0上
var BK_COMPONENT_API_URL = process.env.BK_COMPONENT_API_URL || '' // 蓝鲸组件API地址，目前值跟 v2 开发者中心一致，内部版本不用填
var BK_ANALYSIS_JS = process.env.BK_ANALYSIS_JS || '' //上报js 内部版需要 外部版不需要
var BK_PAAS_VERSION = process.env.BK_PAAS_VERSION || ''

var BACKEND_URL = `${SITE_URL}/backend` // 后端接口前缀
var DOCS_URL_PREFIX = `${BK_DOCS_URL_PREFIX}/markdown/PaaS/DevelopTools/BaseGuide`
var USERS_URL = `${BK_COMPONENT_API_URL}/api/c/compapi/v2/usermanage/fs_list_users/` // 人员选择器接口地址，可选填
