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

// This file contains some compatibility utilities which is able to handle the legacy
// API version of BkApp CRD.
package v1alpha2

import (
	"fmt"

	"bk.tencent.com/paas-app-operator/pkg/utils/kubetypes"
	"github.com/pkg/errors"
	corev1 "k8s.io/api/core/v1"

	"bk.tencent.com/paas-app-operator/pkg/config"
	"bk.tencent.com/paas-app-operator/pkg/utils/quota"
)

type procImageGetter struct {
	bkapp *BkApp
}

// NewProcImageGetter create a new ProcImageGetter
func NewProcImageGetter(bkapp *BkApp) *procImageGetter {
	return &procImageGetter{bkapp: bkapp}
}

// Get get the container image by process name, both the standard and legacy API versions
// are supported at this time.
//
// - name: process name
// - return: <image>, <imagePullPolicy>, <error>
func (r *procImageGetter) Get(name string) (string, corev1.PullPolicy, error) {
	// Standard: the image was defined in build config directly
	if image := r.bkapp.Spec.Build.Image; image != "" {
		return r.bkapp.Spec.Build.Image, r.bkapp.Spec.Build.ImagePullPolicy, nil
	}

	// Legacy API version: read image configs from annotations
	legacyProcImageConfig, _ := kubetypes.GetJsonAnnotation[LegacyProcConfig](
		r.bkapp,
		LegacyProcImageAnnoKey,
	)
	if config, ok := legacyProcImageConfig[name]; ok {
		return config["image"], corev1.PullPolicy(config["policy"]), nil
	}

	return "", corev1.PullIfNotPresent, errors.New("image not configured")
}

// ProcResourcesGetter help getting resources requirements for creating processes
type procResourcesGetter struct {
	bkapp *BkApp
}

// NewProcResourcesGetter create a new ProcResourcesGetter
func NewProcResourcesGetter(bkapp *BkApp) *procResourcesGetter {
	return &procResourcesGetter{bkapp: bkapp}
}

// GetDefault returns the default resources requirements for creating processes
func (r *procResourcesGetter) GetDefault() corev1.ResourceRequirements {
	return r.fromQuotaPlan("default")
}

// Get get the container resources by process name
//
// - name: process name
// - return: <resources requirements>, <error>
func (r *procResourcesGetter) Get(name string) (result corev1.ResourceRequirements, err error) {
	// Standard: read the "ResQuotaPlan" field from process
	procObj := r.bkapp.Spec.FindProcess(name)
	if procObj == nil {
		return result, fmt.Errorf("process %s not found", name)
	}
	if plan := procObj.ResQuotaPlan; plan != "" {
		return r.fromQuotaPlan(plan), nil
	}

	// Legacy version: try to read resources configs from legacy annotation
	legacyProcResourcesConfig, _ := kubetypes.GetJsonAnnotation[LegacyProcConfig](
		r.bkapp,
		LegacyProcResAnnoKey,
	)
	if config, ok := legacyProcResourcesConfig[name]; ok {
		return r.fromRawString(config["cpu"], config["memory"]), nil
	}
	return result, errors.New("resources unconfigured")
}

// fromQuotaPlan try to get resource requirements by the name of quota plan
func (r *procResourcesGetter) fromQuotaPlan(plan string) corev1.ResourceRequirements {
	planToResources := map[string][2]string{
		"default": {
			config.Global.GetProcDefaultCpuLimits(),
			config.Global.GetProcDefaultMemLimits(),
		},
		// TODO: Add more plans
	}

	values, ok := planToResources[plan]
	if !ok {
		return r.GetDefault()
	}
	return r.fromRawString(values[0], values[1])
}

// fromRawString build the resource requirements from raw string
func (r *procResourcesGetter) fromRawString(cpu, memory string) corev1.ResourceRequirements {
	cpuQuota, _ := quota.NewQuantity(cpu, quota.CPU)
	memQuota, _ := quota.NewQuantity(memory, quota.Memory)

	return corev1.ResourceRequirements{
		// 目前 Requests 配额策略：CPU 为 Limits 1/4，内存为 Limits 的 1/2
		Requests: corev1.ResourceList{
			corev1.ResourceCPU:    *quota.Div(cpuQuota, 4),
			corev1.ResourceMemory: *quota.Div(memQuota, 2),
		},
		Limits: corev1.ResourceList{
			corev1.ResourceCPU:    *cpuQuota,
			corev1.ResourceMemory: *memQuota,
		},
	}
}
