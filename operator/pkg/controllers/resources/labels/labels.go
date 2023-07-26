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
	paasv1alpha1 "bk.tencent.com/paas-app-operator/api/v1alpha1"
	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/platform/applications"
)

const domainGroupMappingKey = "bkapp.paas.bk.tencent.com/domain-group-mapping-name"

// Deployment 为应用的不同进程生成关联 Deployment 的标签
func Deployment(bkapp *paasv1alpha2.BkApp, process string) map[string]string {
	labels := map[string]string{
		paasv1alpha2.BkAppNameKey:    bkapp.Name,
		paasv1alpha2.ProcessNameKey:  process,
		paasv1alpha2.ResourceTypeKey: "process",
	}
	if appInfo, err := applications.GetBkAppInfo(bkapp); err == nil {
		labels[paasv1alpha2.BkAppRegionKey] = appInfo.Region
		labels[paasv1alpha2.BkAppCodeKey] = appInfo.AppCode
		labels[paasv1alpha2.ModuleNameKey] = appInfo.ModuleName
		labels[paasv1alpha2.EnvironmentKey] = appInfo.Environment
	}
	return labels
}

// PodSelector return the spec.selector for Deployment
// Warning: spec.selector is immutable
func PodSelector(bkapp *paasv1alpha2.BkApp, process string) map[string]string {
	selector := map[string]string{
		paasv1alpha2.BkAppNameKey:   bkapp.Name,
		paasv1alpha2.ProcessNameKey: process,
	}
	return selector
}

// AppDefault generates the labels for various resources, only includes minimal values
func AppDefault(bkapp *paasv1alpha2.BkApp) map[string]string {
	labels := map[string]string{
		paasv1alpha2.BkAppNameKey: bkapp.Name,
	}
	return labels
}

// MappingIngress generates the labels for DomainGroupMapping resources, the value will be
// used for both resource creations and queries.
func MappingIngress(dgmapping *paasv1alpha1.DomainGroupMapping) map[string]string {
	labels := map[string]string{
		domainGroupMappingKey: dgmapping.Name,
	}
	return labels
}
