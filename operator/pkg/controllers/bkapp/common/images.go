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

package common

import (
	corev1 "k8s.io/api/core/v1"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
)

// BuildImagePullSecrets 返回拉取镜像的 Secrets 列表
func BuildImagePullSecrets(app *paasv1alpha2.BkApp) []corev1.LocalObjectReference {
	pullSecretName := app.GetAnnotations()[paasv1alpha2.ImageCredentialsRefAnnoKey]
	switch pullSecretName {
	case "":
		return nil
	case "true":
		// 兼容支持多模块前的注解值
		// 历史版本使用 `true` 表示 image pull secret 已由 PaaS 创建, secret 名称约定为 $LegacyImagePullSecretName
		pullSecretName = paasv1alpha2.LegacyImagePullSecretName
	}
	// DefaultImagePullSecretName 由 workloads 服务负责创建
	return []corev1.LocalObjectReference{
		{
			Name: pullSecretName,
		},
	}
}
