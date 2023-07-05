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

import paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"

// VolumeMount ...
type VolumeMount struct {
	Name      string
	MountPath string
	paasv1alpha2.VolumeSource
}

// VolumeMounts ...
type VolumeMounts map[string]VolumeMount

// GetVolumeMounts ...
func GetVolumeMounts(bkapp *paasv1alpha2.BkApp) VolumeMounts {
	vm := VolumeMounts{}
	for _, mount := range bkapp.Spec.Mounts {
		// 因为 webhook 中已完成校验, 这里忽略错误
		vs, _ := paasv1alpha2.ConvertToVolumeSource(mount.Source)
		vm[mount.Name] = VolumeMount{Name: mount.Name, MountPath: mount.MountPath, VolumeSource: vs}
	}

	runEnv := GetEnvName(bkapp)

	for _, mount := range bkapp.Spec.EnvOverlay.Mounts {
		if mount.EnvName == runEnv {
			vs, _ := paasv1alpha2.ConvertToVolumeSource(mount.Mount.Source)
			vm[mount.Mount.Name] = VolumeMount{
				Name:         mount.Mount.Name,
				MountPath:    mount.Mount.MountPath,
				VolumeSource: vs,
			}
		}
	}
	return vm
}
