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

import (
	"github.com/pkg/errors"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/apiresources"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/helper"
)

// NewAppDeployer ...
func NewAppDeployer(appCode string) (Deployer, error) {
	appType := helper.FetchAppType(appCode)
	switch appType {
	case AppTypeDefault:
		return DefaultAppDeployer{}, nil
	case AppTypeCNative:
		return CNativeAppDeployer{}, nil
	default:
		return nil, errors.Errorf("unsupported app type: '%s'", appType)
	}
}

// DefaultAppDeployer 普通应用部署器
type DefaultAppDeployer struct{}

// Exec 执行部署操作
func (d DefaultAppDeployer) Exec(opts DeployOptions) (map[string]any, error) {
	return apiresources.DefaultRequester.DeployDefaultApp(
		opts.AppCode, opts.Module, opts.DeployEnv, opts.Branch,
	)
}

// GetResult 获取部署结果
func (d DefaultAppDeployer) GetResult(opts DeployOptions) (DeployResult, error) {
	// TODO implement me
	panic("implement me")
}

// GetHistory 获取部署历史
func (d DefaultAppDeployer) GetHistory(opts DeployOptions) (DeployHistory, error) {
	// TODO implement me
	panic("implement me")
}

var _ Deployer = DefaultAppDeployer{}

// CNativeAppDeployer 云原生应用部署器
type CNativeAppDeployer struct{}

// Exec 执行部署操作
func (d CNativeAppDeployer) Exec(opts DeployOptions) (map[string]any, error) {
	return apiresources.DefaultRequester.DeployCNativeApp(
		opts.AppCode, opts.Module, opts.DeployEnv, opts.BkAppManifest,
	)
}

// GetResult 获取部署结果
func (d CNativeAppDeployer) GetResult(opts DeployOptions) (DeployResult, error) {
	// TODO implement me
	panic("implement me")
}

// GetHistory 获取部署历史
func (d CNativeAppDeployer) GetHistory(opts DeployOptions) (DeployHistory, error) {
	// TODO implement me
	panic("implement me")
}

var _ Deployer = CNativeAppDeployer{}
