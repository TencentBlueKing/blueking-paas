/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *	http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

package handler

import "github.com/TencentBlueKing/blueking-paas/client/pkg/model"

// ShortRevisionLength 短版本信息长度
const ShortRevisionLength = 8

// Lister 应用/服务列表查询接口
type Lister interface {
	// Exec 请求 PaaS API，获取资源列表数据
	Exec() (model.Items, error)
}

// Retriever 各类应用信息查询接口
type Retriever interface {
	// Exec 请求 PaaS API，获取应用某类信息
	Exec(appCode string) (model.AppInfo, error)
}

// Deployer 部署器接口
type Deployer interface {
	// Deploy 下发部署命令
	Deploy(opts model.DeployOptions) error
	// GetResult 获取应用部署结果
	GetResult(opts model.DeployOptions) (model.DeployResult, error)
	// GetHistory 获取应用部署历史
	GetHistory(opts model.DeployOptions) (model.DeployHistory, error)
}
