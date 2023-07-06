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

package v1alpha2

import (
	"github.com/pkg/errors"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/util/validation"
)

// VolumeSource 参考 k8s.io/api/core/v1.VolumeSource
type VolumeSource struct {
	ConfigMap *ConfigMapSource `json:"configMap"`
}

// ToConfigurer 将有效的 source 转换成对应的 VolumeSourceConfigurer
func (vs *VolumeSource) ToConfigurer() (VolumeSourceConfigurer, error) {
	if vs.ConfigMap != nil {
		return vs.ConfigMap, nil
	}
	return nil, errors.New("unknown volume source")
}

// VolumeSourceConfigurer 接口
// +k8s:deepcopy-gen=false
type VolumeSourceConfigurer interface {
	// Validate source
	Validate() []string
	// ApplyToDeployment 将 source 应用到 deployment
	ApplyToDeployment(deployment *appsv1.Deployment, mountName, mountPath string) error
}

// ConfigMapSource represents a configMap that should populate this volume
type ConfigMapSource struct {
	Type string `json:"type"`
	Name string `json:"name"`
}

// Validate source
func (c ConfigMapSource) Validate() []string {
	return validation.IsDNS1123Subdomain(c.Name)
}

// ApplyToDeployment 将 source 应用到 deployment
func (c ConfigMapSource) ApplyToDeployment(deployment *appsv1.Deployment, mountName, mountPath string) error {
	containers := deployment.Spec.Template.Spec.Containers
	for idx := range containers {
		containers[idx].VolumeMounts = append(containers[idx].VolumeMounts, corev1.VolumeMount{
			Name:      mountName,
			MountPath: mountPath,
		})
	}

	deployment.Spec.Template.Spec.Volumes = append(
		deployment.Spec.Template.Spec.Volumes,
		corev1.Volume{
			Name: mountName,
			VolumeSource: corev1.VolumeSource{
				ConfigMap: &corev1.ConfigMapVolumeSource{
					LocalObjectReference: corev1.LocalObjectReference{Name: c.Name},
				},
			},
		},
	)

	return nil
}

var _ VolumeSourceConfigurer = new(ConfigMapSource)
