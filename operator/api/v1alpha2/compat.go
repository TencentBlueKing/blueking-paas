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

	"github.com/pkg/errors"
	corev1 "k8s.io/api/core/v1"

	"bk.tencent.com/paas-app-operator/pkg/config"
	"bk.tencent.com/paas-app-operator/pkg/utils/kubetypes"
	"bk.tencent.com/paas-app-operator/pkg/utils/quota"
)

// ProcImageGetter help getting container image from bkapp
type ProcImageGetter struct {
	bkapp *BkApp
}

// NewProcImageGetter create a new ProcImageGetter
func NewProcImageGetter(bkapp *BkApp) *ProcImageGetter {
	return &ProcImageGetter{bkapp: bkapp}
}

// Get get the container image by process name, both the standard and legacy API versions
// are supported at this time.
//
// - name: process name
// - return: <image>, <imagePullPolicy>, <error>
func (r *ProcImageGetter) Get(name string) (string, corev1.PullPolicy, error) {
	// Legacy API version: read image configs from annotations
	legacyProcImageConfig, _ := kubetypes.GetJsonAnnotation[LegacyProcConfig](
		r.bkapp,
		LegacyProcImageAnnoKey,
	)
	if cfg, ok := legacyProcImageConfig[name]; ok {
		return cfg["image"], corev1.PullPolicy(cfg["policy"]), nil
	}

	// Standard: the image was defined in build config directly
	if image := r.bkapp.Spec.Build.Image; image != "" {
		return r.bkapp.Spec.Build.Image, r.bkapp.Spec.Build.ImagePullPolicy, nil
	}

	return "", corev1.PullIfNotPresent, errors.New("image not configured")
}

// ProcResourcesGetter help getting resources requirements for creating processes
type ProcResourcesGetter struct {
	bkapp *BkApp
}

// NewProcResourcesGetter create a new ProcResourcesGetter
func NewProcResourcesGetter(bkapp *BkApp) *ProcResourcesGetter {
	return &ProcResourcesGetter{bkapp: bkapp}
}

// GetDefault returns the default resources requirements for creating processes
func (r *ProcResourcesGetter) GetDefault() corev1.ResourceRequirements {
	return r.fromQuotaPlan(ResQuotaPlanDefault)
}

// Get the container resources by process name
//
// - name: process name
// - return: <resources requirements>, <error>
func (r *ProcResourcesGetter) Get(name string) (result corev1.ResourceRequirements, err error) {
	// Legacy version: try to read resources configs from legacy annotation
	legacyProcResourcesConfig, _ := kubetypes.GetJsonAnnotation[LegacyProcConfig](
		r.bkapp,
		LegacyProcResAnnoKey,
	)
	if cfg, ok := legacyProcResourcesConfig[name]; ok {
		return r.fromRawString(cfg["cpu"], cfg["memory"]), nil
	}

	// Standard: read the "ResQuotaPlan" field from process
	procObj := r.bkapp.Spec.FindProcess(name)
	if procObj == nil {
		return result, fmt.Errorf("process %s not found", name)
	}
	if plan := procObj.ResQuotaPlan; plan != "" {
		return r.fromQuotaPlan(plan), nil
	}
	return result, errors.New("resources unconfigured")
}

// fromQuotaPlan try to get resource requirements by the name of quota plan
func (r *ProcResourcesGetter) fromQuotaPlan(plan ResQuotaPlan) corev1.ResourceRequirements {
	var cpuRaw, memRaw string
	switch plan {
	case ResQuotaPlan1C512M:
		cpuRaw, memRaw = "1", "512Mi"
	case ResQuotaPlan2C1G:
		cpuRaw, memRaw = "2", "1Gi"
	case ResQuotaPlan2C2G:
		cpuRaw, memRaw = "2", "2Gi"
	case ResQuotaPlan4C2G:
		cpuRaw, memRaw = "4", "2Gi"
	default:
		cpuRaw, memRaw = config.Global.GetProcDefaultCpuLimits(), config.Global.GetProcDefaultMemLimits()
	}
	return r.fromRawString(cpuRaw, memRaw)
}

// fromRawString build the resource requirements from raw string
func (r *ProcResourcesGetter) fromRawString(cpu, memory string) corev1.ResourceRequirements {
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
