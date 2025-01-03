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

package volumes

import (
	"fmt"
	"path"
	"path/filepath"

	"github.com/pkg/errors"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/envs"
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

// VolumeMounter ...
type VolumeMounter interface {
	// ApplyToDeployment 将挂载卷应用到 deployment
	ApplyToDeployment(bkapp *paasv1alpha2.BkApp, deployment *appsv1.Deployment) error
	// GetName 返回挂载卷的名字
	GetName() string
	// GetMountPath 返回挂载卷的挂载路径
	GetMountPath() string
}

// Volume is a named VolumeSource
type Volume struct {
	Name   string
	Source *paasv1alpha2.VolumeSource
}

// GenericVolumeMount is a Volume with a MountPath
type GenericVolumeMount struct {
	Volume    Volume
	MountPath string
}

// ApplyToDeployment 将 GenericVolumeMount 应用到 deployment
func (vm *GenericVolumeMount) ApplyToDeployment(bkapp *paasv1alpha2.BkApp, deployment *appsv1.Deployment) error {
	vs, err := ToCoreV1VolumeSource(vm.Volume.Source)
	if err != nil {
		return err
	}

	deployment.Spec.Template.Spec.Volumes = append(
		deployment.Spec.Template.Spec.Volumes,
		corev1.Volume{
			Name:         vm.Volume.Name,
			VolumeSource: vs,
		},
	)

	containers := deployment.Spec.Template.Spec.Containers
	for idx := range containers {
		volumeMounts := vm.getVolumeMounts()
		containers[idx].VolumeMounts = append(containers[idx].VolumeMounts, volumeMounts...)
	}
	return nil
}

// GetName ...
func (vm *GenericVolumeMount) GetName() string {
	return vm.Volume.Name
}

// GetMountPath ...
func (vm *GenericVolumeMount) GetMountPath() string {
	return vm.MountPath
}

// ToCoreV1VolumeSource work as an adaptor between paas v1alpha2.Volume Source and corev1.VolumeSource.
// The VolumeSource's type currently supported is that:
// - ConfigMap
func ToCoreV1VolumeSource(source *paasv1alpha2.VolumeSource) (corev1.VolumeSource, error) {
	if source.ConfigMap != nil {
		return corev1.VolumeSource{
			ConfigMap: &corev1.ConfigMapVolumeSource{
				LocalObjectReference: corev1.LocalObjectReference{Name: source.ConfigMap.Name},
			},
		}, nil
	} else if source.PersistentStorage != nil {
		return corev1.VolumeSource{
			PersistentVolumeClaim: &corev1.PersistentVolumeClaimVolumeSource{
				ClaimName: source.PersistentStorage.Name,
			},
		}, nil
	}
	return corev1.VolumeSource{}, errors.New("unknown volume source")
}

func (vm *GenericVolumeMount) getVolumeMounts() []corev1.VolumeMount {
	if configMap := vm.Volume.Source.ConfigMap; configMap != nil && configMap.SubPaths != nil {
		// configMap 不为空，且 configMap.SubPaths 不为空
		// 使用 subPath 挂载多个文件
		for _, subPath := range configMap.SubPaths {
			return []corev1.VolumeMount{
				{
					Name:      vm.Volume.Name,
					MountPath: filepath.Join(vm.MountPath, subPath),
					SubPath:   subPath,
				},
			}
		}
	}

	return []corev1.VolumeMount{{
		Name:      vm.Volume.Name,
		MountPath: vm.MountPath,
	}}
}

// BuiltinLogsVolumeMount 内置日志挂载卷
// TODO: when GenericVolumeMount support HostPath type, delete all code about BuiltinLogsVolumeMount and replace with GenericVolumeMount
type BuiltinLogsVolumeMount struct {
	Name      string
	MountPath string
	Source    *corev1.HostPathVolumeSource
}

// ApplyToDeployment 将内置日志挂载卷应用到 deployment
func (v BuiltinLogsVolumeMount) ApplyToDeployment(bkapp *paasv1alpha2.BkApp, deployment *appsv1.Deployment) error {
	deployment.Spec.Template.Spec.Volumes = append(deployment.Spec.Template.Spec.Volumes, corev1.Volume{
		Name: v.Name,
		VolumeSource: corev1.VolumeSource{
			HostPath: v.Source,
		},
	})
	containers := deployment.Spec.Template.Spec.Containers
	for idx := range containers {
		containers[idx].VolumeMounts = append(containers[idx].VolumeMounts, corev1.VolumeMount{
			Name:      v.Name,
			MountPath: v.MountPath,
		})
	}
	return nil
}

// GetName ...
func (v *BuiltinLogsVolumeMount) GetName() string {
	return v.Name
}

// GetMountPath ...
func (v *BuiltinLogsVolumeMount) GetMountPath() string {
	return v.MountPath
}

// ShouldApplyBuiltinLogsVolume 判断是否应用内置日志挂载卷
// 仅当 bkapp 的日志采集器类型是 BuiltinELKCollector 时才挂载日志到宿主机
func ShouldApplyBuiltinLogsVolume(bkapp *paasv1alpha2.BkApp) bool {
	return bkapp.Annotations[paasv1alpha2.LogCollectorTypeAnnoKey] == paasv1alpha2.BuiltinELKCollector
}

// VolumeMounterMap is a map of VolumeMounter, which key is the Volume name
type VolumeMounterMap map[string]VolumeMounter

// GetGenericVolumeMountMap 结合 mounts 和 envoverlay.mounts, 生成只含有 GenericVolumeMount 的 VolumeMounterMap
func GetGenericVolumeMountMap(bkapp *paasv1alpha2.BkApp) VolumeMounterMap {
	mounterMap := make(VolumeMounterMap)
	for _, mount := range bkapp.Spec.Mounts {
		mounterMap[mount.Name] = &GenericVolumeMount{
			Volume: Volume{
				Name:   mount.Name,
				Source: mount.Source,
			},
			MountPath: mount.MountPath,
		}
	}

	if bkapp.Spec.EnvOverlay == nil {
		return mounterMap
	}

	runEnv := envs.GetEnvName(bkapp)
	for _, mount := range bkapp.Spec.EnvOverlay.Mounts {
		if mount.EnvName == runEnv {
			mounterMap[mount.Mount.Name] = &GenericVolumeMount{
				Volume: Volume{
					Name:   mount.Name,
					Source: mount.Source,
				},
				MountPath: mount.Mount.MountPath,
			}
		}
	}
	return mounterMap
}

// GetBuiltinLogsVolumeMounts ...
func GetBuiltinLogsVolumeMounts(bkapp *paasv1alpha2.BkApp) ([]BuiltinLogsVolumeMount, error) {
	var legacyLogPath, moduleLogPath string
	if appInfo, err := applications.GetBkAppInfo(bkapp); err != nil {
		return nil, errors.Wrap(err, "InvalidAnnotations: missing bkapp info")
	} else {
		// {region}-{dns-safe-wl-app-name}
		legacyLogPath = fmt.Sprintf("%s-%s", appInfo.Region, paasv1alpha2.DNSSafeName(appInfo.WlAppName))
		// {region}-bkapp-{app_code}-{environment}/{module_name}
		moduleLogPath = fmt.Sprintf("%s-bkapp-%s-%s/%s", appInfo.Region, appInfo.AppCode, appInfo.Environment, appInfo.ModuleName)
	}

	return []BuiltinLogsVolumeMount{
		{
			Name:      VOLUME_NAME_APP_LOGGING,
			MountPath: VOLUME_MOUNT_APP_LOGGING_DIR,
			Source: &corev1.HostPathVolumeSource{
				Path: path.Join(VOLUME_HOST_PATH_APP_LOGGING_DIR, legacyLogPath),
			},
		},
		{
			Name:      MUL_MODULE_VOLUME_NAME_APP_LOGGING,
			MountPath: MUL_MODULE_VOLUME_MOUNT_APP_LOGGING_DIR,
			Source: &corev1.HostPathVolumeSource{
				Path: path.Join(MUL_MODULE_VOLUME_HOST_PATH_APP_LOGGING_DIR, moduleLogPath),
			},
		},
	}, nil
}

// GetAllVolumeMounterMap 返回属于 bkapp 的所有 VolumeMounter, 包括:
// - GenericVolumeMount
// - BuiltinLogsVolumeMount(优先级更高)
func GetAllVolumeMounterMap(bkapp *paasv1alpha2.BkApp) (VolumeMounterMap, error) {
	mounterMap := GetGenericVolumeMountMap(bkapp)

	if ShouldApplyBuiltinLogsVolume(bkapp) {
		volumes, err := GetBuiltinLogsVolumeMounts(bkapp)
		if err != nil {
			return nil, err
		}
		for idx, volume := range volumes {
			if _, existed := mounterMap[volume.GetName()]; existed {
				return nil, errors.New("user defined volume mount is conflicted with builtin log volume mount")
			}
			mounterMap[volume.GetName()] = &volumes[idx]
		}
	}
	return mounterMap, nil
}
