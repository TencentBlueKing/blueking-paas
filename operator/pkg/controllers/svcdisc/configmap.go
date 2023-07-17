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
package svcdisc

import (
	"context"

	appsv1 "k8s.io/api/apps/v1"
	v1 "k8s.io/api/core/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
)

const (
	// DataKeyBkSaaS is the key of the configmap data that contains the svc-discovery results of BK-SaaS.
	DataKeyBkSaaS = "bk_saas_encoded_json"

	// EnvKeyBkSaaS ...
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

// ApplyToDeployments mutates the given deployment, it try to inject service discovery information
// to the env variables and volumes of the deployment, it mutate the deployments in-place.
// return whether the mutation is performed.
func (w *WorkloadsMutator) ApplyToDeployments(ctx context.Context, deploys []*appsv1.Deployment) bool {
	log := logf.FromContext(ctx)

	if w.bkapp.Spec.SvcDiscovery == nil {
		return false
	}

	configmap, err := w.GetConfigMap(ctx)
	if err != nil {
		log.V(4).Info("unable to get configmap, skip apply.", "error", err)
		return false
	}
	if _, ok := configmap.Data[DataKeyBkSaaS]; !ok {
		log.V(4).Info("configmap data invalid, skip apply.", "error", err)
		return false
	}

	for _, d := range deploys {
		for i, container := range d.Spec.Template.Spec.Containers {
			// Use the index to modify the container structure in-place
			d.Spec.Template.Spec.Containers[i].Env = append(container.Env, v1.EnvVar{
				Name: EnvKeyBkSaaS,
				ValueFrom: &v1.EnvVarSource{
					ConfigMapKeyRef: &v1.ConfigMapKeySelector{
						LocalObjectReference: v1.LocalObjectReference{Name: w.configMapResourceName()},
						Key:                  DataKeyBkSaaS,
					},
				},
			})
		}
	}
	return true
}

// GetConfigMap get the configmap that contains the svc-discovery results, the results was written by the
// apiserver service of bk-paas earlier.
// return nil if the configmap resource does not exist or an error occurred.
func (w *WorkloadsMutator) GetConfigMap(ctx context.Context) (*v1.ConfigMap, error) {
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
