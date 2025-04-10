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

package applications

import (
	"fmt"

	"github.com/pkg/errors"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
)

// ErrParseAppMetadata 指示从资源头对象中无法获取到蓝鲸应用的元信息
var ErrParseAppMetadata = errors.New("unable to parse app metadata")

// BluekingAppInfo contains a quadruple that uniquely specifies an EngineApp
type BluekingAppInfo struct {
	Region      string
	AppCode     string
	AppName     string
	ModuleName  string
	Environment string
	WlAppName   string
	AppTenantID string
}

// GetBkAppInfo 获取蓝鲸应用元信息
func GetBkAppInfo(bkapp *paasv1alpha2.BkApp) (*BluekingAppInfo, error) {
	annotations := bkapp.GetAnnotations()

	var region, appCode, appName, moduleName, environment, wlAppName, appTenantID string
	var ok bool

	if region, ok = annotations[paasv1alpha2.BkAppRegionKey]; !ok {
		return nil, errors.Wrapf(ErrParseAppMetadata, "for missing %s", paasv1alpha2.BkAppRegionKey)
	}

	if appCode, ok = annotations[paasv1alpha2.BkAppCodeKey]; !ok {
		return nil, errors.Wrapf(ErrParseAppMetadata, "for missing %s", paasv1alpha2.BkAppCodeKey)
	}
	if appName, ok = annotations[paasv1alpha2.BkAppNameKey]; !ok {
		return nil, errors.Wrapf(ErrParseAppMetadata, "for missing %s", paasv1alpha2.BkAppNameKey)
	}
	if moduleName, ok = annotations[paasv1alpha2.ModuleNameKey]; !ok {
		return nil, errors.Wrapf(ErrParseAppMetadata, "for missing %s", paasv1alpha2.ModuleNameKey)
	}
	if environment, ok = annotations[paasv1alpha2.EnvironmentKey]; !ok {
		return nil, errors.Wrapf(ErrParseAppMetadata, "for missing %s", paasv1alpha2.EnvironmentKey)
	}
	if wlAppName, ok = annotations[paasv1alpha2.WlAppNameKey]; !ok {
		wlAppName = fmt.Sprintf("bkapp-%s-%s", appCode, environment)
	}

	appTenantID = annotations[paasv1alpha2.BkAppTenantIDKey]

	return &BluekingAppInfo{
		region,
		appCode,
		appName,
		moduleName,
		environment,
		wlAppName,
		appTenantID,
	}, nil
}
