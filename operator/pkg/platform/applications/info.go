/*
 * Tencent is pleased to support the open source community by making BlueKing - PaaS System available.
 * Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * 	http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

package applications

import (
	"errors"
	"fmt"

	"bk.tencent.com/paas-app-operator/api/v1alpha1"
)

// ErrParseAppMetadata 指示从资源头对象中无法获取到蓝鲸应用的元信息
var ErrParseAppMetadata = errors.New("unable to parse app metadata")

// BluekingAppInfo contains a quadruple that uniquely specifies an EngineApp
type BluekingAppInfo struct {
	Region        string
	AppCode       string
	AppName       string
	ModuleName    string
	Environment   string
	EngineAppName string
}

// GetBkAppInfo 获取蓝鲸应用元信息
func GetBkAppInfo(bkapp *v1alpha1.BkApp) (*BluekingAppInfo, error) {
	annotations := bkapp.GetAnnotations()

	var region, appCode, appName, moduleName, environment, engineAppName string
	var ok bool

	if region, ok = annotations[v1alpha1.BkAppRegionKey]; !ok {
		return nil, fmt.Errorf("%w, for missing %s", ErrParseAppMetadata, v1alpha1.BkAppRegionKey)
	}

	if appCode, ok = annotations[v1alpha1.BkAppCodeKey]; !ok {
		return nil, fmt.Errorf("%w, for missing %s", ErrParseAppMetadata, v1alpha1.BkAppCodeKey)
	}
	if appName, ok = annotations[v1alpha1.BkAppNameKey]; !ok {
		return nil, fmt.Errorf("%w, for missing %s", ErrParseAppMetadata, v1alpha1.BkAppNameKey)
	}
	if moduleName, ok = annotations[v1alpha1.ModuleNameKey]; !ok {
		return nil, fmt.Errorf("%w, for missing %s", ErrParseAppMetadata, v1alpha1.ModuleNameKey)
	}
	if environment, ok = annotations[v1alpha1.EnvironmentKey]; !ok {
		return nil, fmt.Errorf("%w, for missing %s", ErrParseAppMetadata, v1alpha1.EnvironmentKey)
	}
	if engineAppName, ok = annotations[v1alpha1.EngineAppNameKey]; !ok {
		engineAppName = fmt.Sprintf("bkapp-%s-%s", appCode, environment)
	}
	return &BluekingAppInfo{
		region,
		appCode,
		appName,
		moduleName,
		environment,
		engineAppName,
	}, nil
}
