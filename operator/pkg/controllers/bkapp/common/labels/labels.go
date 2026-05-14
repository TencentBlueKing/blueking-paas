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

// Package labels provides labels utils for resources
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
		labels[paasv1alpha2.WlAppNameKey] = appInfo.WlAppName
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

// Hook generate the labels for hook pods
func Hook(bkapp *paasv1alpha2.BkApp, hookType paasv1alpha2.HookType) map[string]string {
	return map[string]string{
		// 由于 Process 一开始没添加 ResourceTypeKey label, 通过命名空间过滤 Pod 会查询到 HookInstance 的 Pod
		// 所以 HookInstance 暂时不添加 ModuleNameKey, 以区分 Process 创建的 pod 和 HookInstance 创建的 pod
		paasv1alpha2.BkAppNameKey:    bkapp.GetName(),
		paasv1alpha2.ResourceTypeKey: "hook",
		paasv1alpha2.HookTypeKey:     string(hookType),
	}
}

// HookPodSelector generate the label selector for hook pods
func HookPodSelector(bkapp *paasv1alpha2.BkApp, hookType paasv1alpha2.HookType) map[string]string {
	return Hook(bkapp, hookType)
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

// Service 为应用的不同进程生成关联 Service 的 labels
func Service(bkapp *paasv1alpha2.BkApp, process string) map[string]string {
	labels := Deployment(bkapp, process)

	// 为蓝鲸监控采集注入对应的 label
	if appInfo, err := applications.GetBkAppInfo(bkapp); err == nil {
		labels["monitoring.bk.tencent.com/bk_app_code"] = appInfo.AppCode
		labels["monitoring.bk.tencent.com/module_name"] = appInfo.ModuleName
		labels["monitoring.bk.tencent.com/environment"] = appInfo.Environment
	}

	return labels
}
