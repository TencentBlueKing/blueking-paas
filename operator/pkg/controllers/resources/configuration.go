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
	"context"

	corev1 "k8s.io/api/core/v1"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	"bk.tencent.com/paas-app-operator/api/v1alpha1"
	"bk.tencent.com/paas-app-operator/pkg/platform/applications"
	"bk.tencent.com/paas-app-operator/pkg/platform/external"
)

// GetAppEnvs will return all EnvVar for the given BkApp, this will include:
// - user defined Configuration in Spec
// - env vars from addons
// - (TODO) built-in env vars
func GetAppEnvs(bkapp *v1alpha1.BkApp) []corev1.EnvVar {
	// 应用声明的环境变量(优先级最低)
	envs := NewEnvVarsGetter(bkapp).Get()
	// 增强服务的环境变量
	envs = append(envs, retrieveAddonEnvVar(bkapp)...)
	return envs
}

// retrieveAddonEnvVar 获取增强服务的环境变量
func retrieveAddonEnvVar(bkapp *v1alpha1.BkApp) []corev1.EnvVar {
	envs := []corev1.EnvVar{}
	metadata, err := applications.GetBkAppInfo(bkapp)
	if err != nil {
		return envs
	}

	var addons []string
	if addons, err = bkapp.ExtractAddons(); err != nil {
		return envs
	}

	client, err := external.GetDefaultClient()
	if err != nil {
		return envs
	}

	// TODO: 处理获取环境变量报错的情景, 将错误逐层往上传递
	for _, addonName := range addons {
		ctx, cancel := context.WithTimeout(context.Background(), external.DefaultTimeout)
		defer cancel()

		instance, err := client.QueryAddonInstance(
			ctx,
			metadata.AppCode,
			metadata.ModuleName,
			metadata.Environment,
			addonName,
		)
		if err != nil {
			logf.Log.Error(err, "An err occur when QueryAddonInstance")
			continue
		}
		for key, value := range instance.Credentials {
			envs = append(envs, corev1.EnvVar{Name: key, Value: value.String()})
		}
	}
	return envs
}
