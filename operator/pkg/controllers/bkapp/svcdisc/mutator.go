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

// Package svcdisc provides svc-discovery related functions
package svcdisc

import (
	"context"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	v1 "k8s.io/api/core/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
)

const (
	// DataKeyBkSaaS is the key of the configmap data that contains the svc-discovery results of BK-SaaS.
	DataKeyBkSaaS = "bk_saas_encoded_json"

	// EnvKeyBkSaaS is the environment variable key that contains the svc-discovery results of BK-SaaS.
	EnvKeyBkSaaS = "BKPAAS_SERVICE_ADDRESSES_BKSAAS"
)

// NewWorkloadsMutator creates a new WorkloadsMutator
func NewWorkloadsMutator(client client.Client, bkapp *paasv1alpha2.BkApp) *WorkloadsMutator {
	return &WorkloadsMutator{
		client: client,
		bkapp:  bkapp,
	}
}

// WorkloadsMutator mutates an app's workloads to inject svc-discovery related information
type WorkloadsMutator struct {
	client client.Client
	bkapp  *paasv1alpha2.BkApp
}

// ApplyToDeployment mutates the given deployment, it try to inject service discovery information
// to the env variables and volumes of the deployment, it mutate the deployments in-place.
// Return whether the mutation is performed.
func (w *WorkloadsMutator) ApplyToDeployment(ctx context.Context, d *appsv1.Deployment) bool {
	if !w.validateConfigMap(ctx) {
		return false
	}

	d.Spec.Template.Spec.Containers = w.updateContainers(d.Spec.Template.Spec.Containers)
	return true
}

// ApplyToPod mutates the given pod, it try to inject service discovery information
// to the env variables and volumes of the pod, it mutate the pod in-place.
// Return whether the mutation is performed.
func (w *WorkloadsMutator) ApplyToPod(ctx context.Context, d *corev1.Pod) bool {
	if !w.validateConfigMap(ctx) {
		return false
	}

	d.Spec.Containers = w.updateContainers(d.Spec.Containers)
	return true
}

// Update a list of containers to add the svc-discovery related env variables, return a new slice.
func (w *WorkloadsMutator) updateContainers(containers []corev1.Container) []corev1.Container {
	results := make([]corev1.Container, len(containers))
	for i, container := range containers {
		container.Env = append(container.Env, v1.EnvVar{
			Name: EnvKeyBkSaaS,
			ValueFrom: &v1.EnvVarSource{
				ConfigMapKeyRef: &v1.ConfigMapKeySelector{
					LocalObjectReference: v1.LocalObjectReference{Name: w.configMapResourceName()},
					Key:                  DataKeyBkSaaS,
				},
			},
		})
		results[i] = container
	}
	return results
}

// Validate if the configmap that required for svc-discovery exists and it's data is valid.
func (w *WorkloadsMutator) validateConfigMap(ctx context.Context) bool {
	log := logf.FromContext(ctx)

	if w.bkapp.Spec.SvcDiscovery == nil {
		return false
	}

	configmap, err := w.getConfigMap(ctx)
	if err != nil {
		log.V(1).Info("failed to validate svc-discovery configmap.", "appName", w.bkapp.GetName(), "error", err)
		return false
	}
	if _, ok := configmap.Data[DataKeyBkSaaS]; !ok {
		log.V(1).Info("failed to validate svc-discovery configmap, data invalid.", "appName", w.bkapp.GetName())
		return false
	}
	return true
}

// getConfigMap get the configmap that contains the svc-discovery results, the results was written by the
// apiserver service of bk-paas earlier.
// return nil if the configmap resource does not exist or an error occurred.
func (w *WorkloadsMutator) getConfigMap(ctx context.Context) (*v1.ConfigMap, error) {
	c := v1.ConfigMap{}
	name := w.configMapResourceName()
	if err := w.client.Get(ctx, client.ObjectKey{Namespace: w.bkapp.Namespace, Name: name}, &c); err != nil {
		return nil, err
	}
	return &c, nil
}

// Return the name of ConfigMap resource
func (w *WorkloadsMutator) configMapResourceName() string {
	return "svc-disc-results-" + w.bkapp.Name
}
