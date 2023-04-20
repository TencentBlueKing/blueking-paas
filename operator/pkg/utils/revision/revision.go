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

package revision

import (
	"strconv"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	appsv1 "k8s.io/api/apps/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// GetRevision returns the revision number of the input object.
func GetRevision(obj metav1.Object) (int64, error) {
	v, ok := obj.GetAnnotations()[paasv1alpha2.RevisionAnnoKey]
	if !ok {
		return 0, nil
	}
	return strconv.ParseInt(v, 10, 64)
}

// MaxRevision finds the highest revision in the deployments
func MaxRevision(allProcesses []*appsv1.Deployment) (max int64) {
	for _, process := range allProcesses {
		if v, err := GetRevision(process); err != nil {
			continue
		} else if v > max {
			max = v
		}
	}
	return max
}
