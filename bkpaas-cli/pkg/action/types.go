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

package action

// DeployOptions 部署时需要使用的配置
type DeployOptions struct {
	AppCode       string
	AppType       string
	GitUrl        string
	Branch        string
	Module        string
	DeployEnv     string
	BkAppManifest map[string]any
}

// DeployInfo 部署相关信息
type DeployInfo struct {
	DeployInfo string
}

// DeployResult 部署结果
type DeployResult struct {
	Logs string
}

// Deployer 部署器接口
type Deployer interface {
	// Exec 下发部署命令
	Exec(opts DeployOptions) (DeployInfo, error)
	// GetResult 获取应用部署结果
	GetResult(info DeployInfo) (DeployResult, error)
}

// Viewer 各类应用信息查询接口
type Viewer interface {
	// Fetch 请求 PaaS API，获取应用某类信息
	Fetch(appCode string) (map[string]any, error)
	// Render 将某类应用信息转换成可展示的字符串
	Render(info map[string]any) (string, error)
}
