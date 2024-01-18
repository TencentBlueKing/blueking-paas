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
	"github.com/pkg/errors"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
)

// VolumeMount with volume source configurer
type VolumeMount struct {
	Name      string
	MountPath string
	VolumeSourceConfigurer
}

// VolumeSourceConfigurer ...
type VolumeSourceConfigurer interface {
	// ApplyToDeployment 将 volume source 应用到 deployment
	ApplyToDeployment(deployment *appsv1.Deployment, mountName, mountPath string) error
}

// VolumeMountMap is a map which key is mount name
type VolumeMountMap map[string]VolumeMount

// GetVolumeMountMap 结合 mounts 和 envoverlay.mounts, 生成 VolumeMountMap
func GetVolumeMountMap(bkapp *paasv1alpha2.BkApp) VolumeMountMap {
	volMountMap := make(VolumeMountMap)
	for _, mount := range bkapp.Spec.Mounts {
		// 因为 webhook 中已完成校验, 这里忽略错误
		cfg, _ := ToVolumeSourceConfigurer(mount.Source)
		volMountMap[mount.Name] = VolumeMount{
			Name:                   mount.Name,
			MountPath:              mount.MountPath,
			VolumeSourceConfigurer: cfg,
		}
	}

	if bkapp.Spec.EnvOverlay == nil {
		return volMountMap
	}

	runEnv := GetEnvName(bkapp)

	for _, mount := range bkapp.Spec.EnvOverlay.Mounts {
		if mount.EnvName == runEnv {
			// 因为 webhook 中已完成校验, 这里忽略错误
			cfg, _ := ToVolumeSourceConfigurer(mount.Mount.Source)
			volMountMap[mount.Mount.Name] = VolumeMount{
				Name:                   mount.Mount.Name,
				MountPath:              mount.Mount.MountPath,
				VolumeSourceConfigurer: cfg,
			}
		}
	}
	return volMountMap
}

// ToVolumeSourceConfigurer ...
func ToVolumeSourceConfigurer(vs *paasv1alpha2.VolumeSource) (VolumeSourceConfigurer, error) {
	if vs.ConfigMap != nil {
		return ConfigMapSource(*vs.ConfigMap), nil
	} else if vs.PersistentVolumeClaim != nil {
		return PersistentVolumeClaimSource(*vs.PersistentVolumeClaim), nil
	}
	return nil, errors.New("unknown volume source")
}

// ConfigMapSource ...
type ConfigMapSource paasv1alpha2.ConfigMapSource

// ApplyToDeployment 将 configmap source 应用到 deployment
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

// PersistentVolumeClaimSource ...
type PersistentVolumeClaimSource paasv1alpha2.PersistentVolumeClaimSource

// ApplyToDeployment 将 configmap source 应用到 deployment
func (p PersistentVolumeClaimSource) ApplyToDeployment(
	deployment *appsv1.Deployment,
	mountName, mountPath string,
) error {
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
				PersistentVolumeClaim: &corev1.PersistentVolumeClaimVolumeSource{
					ClaimName: p.Name,
				},
			},
		},
	)
	return nil
}
