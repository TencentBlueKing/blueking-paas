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
	"encoding/json"
	"fmt"

	"github.com/tidwall/gjson"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/util/validation"
)

// ConvertToVolumeSource 将原始 source 根据 type 转换成对应的 VolumeSource
func ConvertToVolumeSource(source *runtime.RawExtension) (VolumeSource, error) {
	sourceType := gjson.Get(string(source.Raw), "type").String()

	if sourceType == ConfigMapType {
		var cs ConfigMapSource
		err := json.Unmarshal(source.Raw, &cs)
		if err != nil {
			return nil, err
		}
		return cs, nil
	}

	return nil, fmt.Errorf("not supported type: %s", sourceType)
}

// VolumeSource 接口, 区别与 k8s.io/api/core/v1.VolumeSource
// +k8s:deepcopy-gen=false
type VolumeSource interface {
	// GetType return source type
	GetType() string
	// Validate source
	Validate() []string
	// ApplyToDeployment 将 source 应用到 deployment
	ApplyToDeployment(deployment *appsv1.Deployment, mountName, mountPath string) error
}

// ConfigMapSource 基于 K8S ConfigMap 实现 VolumeSource
type ConfigMapSource struct {
	Type string `json:"type"`
	Name string `json:"name"`
}

// GetType return source type
func (c ConfigMapSource) GetType() string {
	return c.Type
}

// Validate source
func (c ConfigMapSource) Validate() []string {
	if c.Type != ConfigMapType {
		return []string{fmt.Sprintf("unexpected type: %s, expected: %s", c.Type, ConfigMapType)}
	}

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

var _ VolumeSource = new(ConfigMapSource)
