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

package resources

import (
	"fmt"

	corev1 "k8s.io/api/core/v1"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/config"
	"bk.tencent.com/paas-app-operator/pkg/utils/kubetypes"
	"bk.tencent.com/paas-app-operator/pkg/utils/quota"
)

// ReplicasGetter get replicas from BkApp object
type ReplicasGetter struct {
	bkapp *paasv1alpha2.BkApp
	// replicasMap stores replications data, "{process} -> {replicas}"
	replicasMap map[string]int32
}

// NewReplicasGetter creates a ReplicasGetter object
func NewReplicasGetter(bkapp *paasv1alpha2.BkApp) *ReplicasGetter {
	obj := &ReplicasGetter{bkapp: bkapp, replicasMap: make(map[string]int32)}

	// Build internal index data
	obj.buildDefault()
	if env := GetEnvName(obj.bkapp); !env.IsEmpty() {
		obj.buildEnvOverlay(env)
	}
	return obj
}

// Get replicas by process name
func (r *ReplicasGetter) Get(name string) *int32 {
	if v, ok := r.replicasMap[name]; ok {
		return &v
	}
	return nil
}

// Build replicas map from default configuration
func (r *ReplicasGetter) buildDefault() {
	for _, proc := range r.bkapp.Spec.Processes {
		if proc.Replicas != nil {
			r.replicasMap[proc.Name] = *proc.Replicas
		}
	}
}

// Build replicas map from env overlay configs
func (r *ReplicasGetter) buildEnvOverlay(env paasv1alpha2.EnvName) {
	if r.bkapp.Spec.EnvOverlay == nil {
		return
	}
	// Pick values which matches environment
	for _, c := range r.bkapp.Spec.EnvOverlay.Replicas {
		if c.EnvName == env {
			r.replicasMap[c.Process] = c.Count
		}
	}
}

// EnvVarsGetter get env vars from BkApp object
type EnvVarsGetter struct {
	bkapp *paasv1alpha2.BkApp

	// Stores env vars by key/value
	itemsMap map[string]string
	// Stores env names in order
	itemsKeys []string
}

// NewEnvVarsGetter creates a ReplicasGetter object
func NewEnvVarsGetter(bkapp *paasv1alpha2.BkApp) *EnvVarsGetter {
	obj := &EnvVarsGetter{bkapp: bkapp, itemsMap: make(map[string]string)}
	// Load values from different sources, the order is important
	obj.loadDefault()
	if env := GetEnvName(obj.bkapp); !env.IsEmpty() {
		obj.loadEnvOverlay(env)
	}
	return obj
}

// Get all environment variables, results were sorted by insertion order
func (r EnvVarsGetter) Get() []corev1.EnvVar {
	results := []corev1.EnvVar{}
	processed := make(map[string]bool)
	for _, key := range r.itemsKeys {
		// Only process each key once
		if _, ok := processed[key]; ok {
			continue
		}
		results = append(results, corev1.EnvVar{Name: key, Value: r.itemsMap[key]})
		processed[key] = true
	}
	return results
}

// Load default env vars
func (r *EnvVarsGetter) loadDefault() {
	for _, d := range r.bkapp.Spec.Configuration.Env {
		r.itemsMap[d.Name] = d.Value
		r.itemsKeys = append(r.itemsKeys, d.Name)
	}
}

// Load from env overlays
func (r *EnvVarsGetter) loadEnvOverlay(env paasv1alpha2.EnvName) {
	if r.bkapp.Spec.EnvOverlay == nil {
		return
	}
	// Pick values which matches environment
	for _, c := range r.bkapp.Spec.EnvOverlay.EnvVariables {
		if c.EnvName == env {
			r.itemsMap[c.Name] = c.Value
			r.itemsKeys = append(r.itemsKeys, c.Name)
		}
	}
}

// GetEnvName get environment name from application, return an empty string
// when no information can be found.
func GetEnvName(bkapp *paasv1alpha2.BkApp) paasv1alpha2.EnvName {
	annots := bkapp.GetAnnotations()
	name := paasv1alpha2.EnvName(annots[paasv1alpha2.EnvironmentKey])
	if name.IsValid() {
		return name
	}
	return ""
}

// AutoscalingSpecGetter get autoscaling spec from BkApp object
type AutoscalingSpecGetter struct {
	bkapp *paasv1alpha2.BkApp
	// specMap stores process scaling spec, "{process} -> {autoscalingSpec}"
	specMap map[string]*paasv1alpha2.AutoscalingSpec
}

// NewAutoscalingSpecGetter creates a AutoscalingSpecGetter object
func NewAutoscalingSpecGetter(bkapp *paasv1alpha2.BkApp) *AutoscalingSpecGetter {
	obj := &AutoscalingSpecGetter{
		bkapp:   bkapp,
		specMap: make(map[string]*paasv1alpha2.AutoscalingSpec),
	}

	// Build internal index data
	obj.buildDefault()
	if env := GetEnvName(obj.bkapp); !env.IsEmpty() {
		obj.buildEnvOverlay(env)
	}
	return obj
}

// Get scalingPolicy by process name
func (g *AutoscalingSpecGetter) Get(name string) *paasv1alpha2.AutoscalingSpec {
	if v, ok := g.specMap[name]; ok {
		return v
	}
	return nil
}

// Build policy map from default configuration
func (g *AutoscalingSpecGetter) buildDefault() {
	for _, proc := range g.bkapp.Spec.Processes {
		g.specMap[proc.Name] = proc.Autoscaling
	}
}

// Build autoscaling spec map from env overlay configs
func (g *AutoscalingSpecGetter) buildEnvOverlay(env paasv1alpha2.EnvName) {
	if g.bkapp.Spec.EnvOverlay == nil {
		return
	}
	// Pick values which matches environment
	for _, c := range g.bkapp.Spec.EnvOverlay.Autoscaling {
		if c.EnvName == env {
			g.specMap[c.Process] = &c.Spec
		}
	}
}

// ProcResourcesGetter help getting resources requirements for creating processes
type ProcResourcesGetter struct {
	bkapp *paasv1alpha2.BkApp
}

// NewProcResourcesGetter create a new ProcResourcesGetter
func NewProcResourcesGetter(bkapp *paasv1alpha2.BkApp) *ProcResourcesGetter {
	return &ProcResourcesGetter{bkapp: bkapp}
}

// GetDefault returns the default resources requirements for creating processes
func (r *ProcResourcesGetter) GetDefault() corev1.ResourceRequirements {
	return r.fromQuotaPlan(paasv1alpha2.ResQuotaPlanDefault)
}

// Get the container resources by process name
//
// - name: process name
// - return: <resources requirements>, <error>
func (r *ProcResourcesGetter) Get(name string) (result corev1.ResourceRequirements, err error) {
	// Legacy version: try to read resources configs from legacy annotation
	legacyProcResourcesConfig, _ := kubetypes.GetJsonAnnotation[paasv1alpha2.LegacyProcConfig](
		r.bkapp,
		paasv1alpha2.LegacyProcResAnnoKey,
	)
	if cfg, ok := legacyProcResourcesConfig[name]; ok {
		return r.fromRawString(cfg["cpu"], cfg["memory"]), nil
	}

	// Overlay: read the "ResQuotaPlan" field from envOverlay
	if env := GetEnvName(r.bkapp); !env.IsEmpty() && r.bkapp.Spec.EnvOverlay != nil {
		for _, q := range r.bkapp.Spec.EnvOverlay.ResQuotas {
			if q.EnvName == env && q.Process == name {
				return r.fromQuotaPlan(q.Plan), nil
			}
		}
	}

	// Standard: read the "ResQuotaPlan" field from process
	procObj := r.bkapp.Spec.FindProcess(name)
	if procObj == nil {
		return result, fmt.Errorf("process %s not found", name)
	}
	return r.fromQuotaPlan(procObj.ResQuotaPlan), nil
}

// fromQuotaPlan try to get resource requirements by the name of quota plan
func (r *ProcResourcesGetter) fromQuotaPlan(plan paasv1alpha2.ResQuotaPlan) corev1.ResourceRequirements {
	var cpuRaw, memRaw string
	switch plan {
	case paasv1alpha2.ResQuotaPlan1C512M:
		cpuRaw, memRaw = "1000m", "512Mi"
	case paasv1alpha2.ResQuotaPlan2C1G:
		cpuRaw, memRaw = "2000m", "1024Mi"
	case paasv1alpha2.ResQuotaPlan2C2G:
		cpuRaw, memRaw = "2000m", "2048Mi"
	case paasv1alpha2.ResQuotaPlan4C1G:
		cpuRaw, memRaw = "4000m", "1024Mi"
	case paasv1alpha2.ResQuotaPlan4C2G:
		cpuRaw, memRaw = "4000m", "2048Mi"
	case paasv1alpha2.ResQuotaPlan4C4G:
		cpuRaw, memRaw = "4000m", "4096Mi"
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
