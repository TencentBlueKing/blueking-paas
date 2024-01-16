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
	"path"

	"github.com/pkg/errors"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/platform/applications"
)

const (
	// VOLUME_NAME_APP_LOGGING 应用日志(legacy)-挂载卷名称
	VOLUME_NAME_APP_LOGGING = "applogs"
	// VOLUME_HOST_PATH_APP_LOGGING_DIR 应用日志(legacy)-宿主机挂载路径
	VOLUME_HOST_PATH_APP_LOGGING_DIR = "/data/bkapp/logs"
	// VOLUME_MOUNT_APP_LOGGING_DIR 应用日志(legacy)-容器内挂载点
	VOLUME_MOUNT_APP_LOGGING_DIR = "/app/logs"
	// MUL_MODULE_VOLUME_NAME_APP_LOGGING 应用日志-挂载卷名称
	MUL_MODULE_VOLUME_NAME_APP_LOGGING = "appv3logs"
	// MUL_MODULE_VOLUME_HOST_PATH_APP_LOGGING_DIR 应用日志-宿主机挂载路径
	MUL_MODULE_VOLUME_HOST_PATH_APP_LOGGING_DIR = "/data/bkapp/v3logs"
	// MUL_MODULE_VOLUME_MOUNT_APP_LOGGING_DIR 应用日志-容器内挂载点
	MUL_MODULE_VOLUME_MOUNT_APP_LOGGING_DIR = "/app/v3logs"
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

// BuiltinLogsVolume 内置日志挂载卷
type BuiltinLogsVolume struct{}

// ShouldApply 是否应用内置日志挂载卷
// 仅当 bkapp 的日志采集器类型是 BuiltinElkCollector 时才挂载日志到宿主机
func (s BuiltinLogsVolume) ShouldApply(bkapp *paasv1alpha2.BkApp) bool {
	return bkapp.Annotations[paasv1alpha2.LogCollectorTypeAnnoKey] == paasv1alpha2.BuiltinElkCollector
}

// ApplyToDeployment 将内置日志挂载卷应用到 deployment
func (s BuiltinLogsVolume) ApplyToDeployment(bkapp *paasv1alpha2.BkApp, deployment *appsv1.Deployment) error {
	var legacyLogPath, moduleLogPath string
	if appInfo, err := applications.GetBkAppInfo(bkapp); err != nil {
		return errors.Wrap(err, "InvalidAnnotations: missing bkapp info")
	} else {
		// {region}-{dns-safe-wl-app-name}
		legacyLogPath = fmt.Sprintf("%s-%s", appInfo.Region, paasv1alpha2.DNSSafeName(appInfo.WlAppName))
		// {region}-bkapp-{app_code}-{environment}/{module_name}
		moduleLogPath = fmt.Sprintf("%s-bkapp-%s-%s/%s", appInfo.Region, appInfo.AppCode, appInfo.Environment, appInfo.ModuleName)
	}

	containers := deployment.Spec.Template.Spec.Containers
	for idx := range containers {
		containers[idx].VolumeMounts = append(containers[idx].VolumeMounts, corev1.VolumeMount{
			Name:      VOLUME_NAME_APP_LOGGING,
			MountPath: VOLUME_MOUNT_APP_LOGGING_DIR,
		})

		containers[idx].VolumeMounts = append(containers[idx].VolumeMounts, corev1.VolumeMount{
			Name:      MUL_MODULE_VOLUME_NAME_APP_LOGGING,
			MountPath: MUL_MODULE_VOLUME_MOUNT_APP_LOGGING_DIR,
		})
	}

	deployment.Spec.Template.Spec.Volumes = append(
		deployment.Spec.Template.Spec.Volumes, corev1.Volume{
			Name: VOLUME_NAME_APP_LOGGING,
			VolumeSource: corev1.VolumeSource{
				HostPath: &corev1.HostPathVolumeSource{
					Path: path.Join(VOLUME_HOST_PATH_APP_LOGGING_DIR, legacyLogPath),
				},
			},
		})

	deployment.Spec.Template.Spec.Volumes = append(
		deployment.Spec.Template.Spec.Volumes, corev1.Volume{
			Name: MUL_MODULE_VOLUME_NAME_APP_LOGGING,
			VolumeSource: corev1.VolumeSource{
				HostPath: &corev1.HostPathVolumeSource{
					Path: path.Join(MUL_MODULE_VOLUME_HOST_PATH_APP_LOGGING_DIR, moduleLogPath),
				},
			},
		})
	return nil
}
