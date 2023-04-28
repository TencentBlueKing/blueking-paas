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
	corev1 "k8s.io/api/core/v1"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
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
	if paasv1alpha2.CheckEnvName(name) {
		return name
	}
	return paasv1alpha2.EnvName("")
}
