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

// Package v1alpha2 contains some compatibility utilities
// which is able to handle the legacy API version of BkApp CRD.
package v1alpha2

import (
	"github.com/pkg/errors"
	corev1 "k8s.io/api/core/v1"

	"bk.tencent.com/paas-app-operator/pkg/kubeutil"
)

// ProcImageGetter help getting container image from bkapp
type ProcImageGetter struct {
	bkapp *BkApp
}

// NewProcImageGetter create a new ProcImageGetter
func NewProcImageGetter(bkapp *BkApp) *ProcImageGetter {
	return &ProcImageGetter{bkapp: bkapp}
}

// Get get the container image by process name, both the standard and legacy API versions
// are supported at this time.
//
// - name: process name
// - return: <image>, <imagePullPolicy>, <error>
func (r *ProcImageGetter) Get(name string) (string, corev1.PullPolicy, error) {
	// Legacy API version: read image configs from annotations
	legacyProcImageConfig, _ := kubeutil.GetJsonAnnotation[LegacyProcConfig](
		r.bkapp,
		LegacyProcImageAnnoKey,
	)
	if cfg, ok := legacyProcImageConfig[name]; ok {
		return cfg["image"], corev1.PullPolicy(cfg["policy"]), nil
	}

	// Standard: the image was defined in build config directly
	if image := r.bkapp.Spec.Build.Image; image != "" {
		return r.bkapp.Spec.Build.Image, r.bkapp.Spec.Build.ImagePullPolicy, nil
	}

	return "", corev1.PullIfNotPresent, errors.New("image not configured")
}
