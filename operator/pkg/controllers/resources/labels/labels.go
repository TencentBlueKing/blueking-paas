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

package labels

import (
	"bk.tencent.com/paas-app-operator/api/v1alpha1"
	"bk.tencent.com/paas-app-operator/pkg/platform/applications"
)

const domainGroupMappingKey = "bkapp.paas.bk.tencent.com/domain-group-mapping-name"

// Deployment 为应用的不同进程生成关联 Deployment 的标签
func Deployment(bkapp *v1alpha1.BkApp, process string) map[string]string {
	labels := map[string]string{
		v1alpha1.BkAppNameKey:   bkapp.Name,
		v1alpha1.ProcessNameKey: process,
	}
	if appInfo, err := applications.GetBkAppInfo(bkapp); err == nil {
		labels[v1alpha1.BkAppRegionKey] = appInfo.Region
		labels[v1alpha1.BkAppCodeKey] = appInfo.AppCode
		labels[v1alpha1.ModuleNameKey] = appInfo.ModuleName
		labels[v1alpha1.EnvironmentKey] = appInfo.Environment
	}
	return labels
}

// PodSelector return the spec.selector for Deployment
// Warning: spec.selector is immutable
func PodSelector(bkapp *v1alpha1.BkApp, process string) map[string]string {
	selector := map[string]string{
		v1alpha1.BkAppNameKey:   bkapp.Name,
		v1alpha1.ProcessNameKey: process,
	}
	return selector
}

// AppDefault generates the labels for various resources, only includes minimal values
func AppDefault(bkapp *v1alpha1.BkApp) map[string]string {
	labels := map[string]string{
		v1alpha1.BkAppNameKey: bkapp.Name,
	}
	return labels
}

// MappingIngress generates the labels for DomainGroupMapping resources, the value will be
// used for both resource creations and queries.
func MappingIngress(dgmapping *v1alpha1.DomainGroupMapping) map[string]string {
	labels := map[string]string{
		domainGroupMappingKey: dgmapping.Name,
	}
	return labels
}
