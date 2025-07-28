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

package apiresources

import (
	"github.com/pkg/errors"
)

// AuthApiErr Token 鉴权 API 异常
var AuthApiErr = errors.New("Auth API unavailable")

// PaaSApiErr 无法获取蓝鲸应用基础信息
var PaaSApiErr = errors.New("PaaS API unavailable")

// ApiRespDecodeErr API 返回格式异常
var ApiRespDecodeErr = errors.New("Decode api response failed")

// Requester API 调用入口
type Requester interface {
	// CheckToken 检查 AccessToken 是否有效，若有效则返回用户身份信息
	CheckToken(token string) (map[string]any, error)

	// ListAppMinimal 获取应用简明信息列表
	ListAppMinimal() (map[string]any, error)
	// GetAppInfo 获取应用基础信息
	GetAppInfo(appCode string) (map[string]any, error)

	// DeployApp 部署应用
	DeployApp(appCode, appModule, deployEnv string, data map[string]any) (map[string]any, error)
	// GetAppDeployResult 获取应用部署结果
	GetAppDeployResult(appCode, appModule, deployID string) (map[string]any, error)
	// ListAppDeployHistory 获取应用部署历史（最近N次）
	ListAppDeployHistory(appCode, appModule, appEnv string) (map[string]any, error)
	// UpdateBkAppModel 导入 manifest 更新 BkAppModel
	UpdateBkAppModel(appCode, appModule string, manifest map[string]any) ([]map[string]any, error)
}
