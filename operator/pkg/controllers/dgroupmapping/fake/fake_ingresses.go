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

package fake

import (
	"fmt"

	paasv1alpha1 "bk.tencent.com/paas-app-operator/api/v1alpha1"
	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
)

// DGroupMappingSpecFixture makes a faked Spec object which contains all 3 kinds of
// example domain groups.
func DGroupMappingSpecFixture(bkapp *paasv1alpha2.BkApp) paasv1alpha1.DomainGroupMappingSpec {
	return paasv1alpha1.DomainGroupMappingSpec{
		Ref: paasv1alpha1.MappingRef{
			Name:       bkapp.Name,
			Kind:       paasv1alpha2.KindBkApp,
			APIVersion: paasv1alpha2.GroupVersion.String(),
		},
		Data: []paasv1alpha1.DomainGroup{
			{
				SourceType: "subdomain",
				Domains: []paasv1alpha1.Domain{
					{
						Host:           fmt.Sprintf("%s.example.com", bkapp.Name),
						PathPrefixList: []string{"/"},
					},
				},
			},
			{
				SourceType: "subpath",
				Domains: []paasv1alpha1.Domain{
					{
						Host:           "fake.example.com",
						PathPrefixList: []string{"/" + bkapp.Name},
					},
				},
			},
			{
				SourceType: "custom",
				Domains: []paasv1alpha1.Domain{
					{
						Name:           "1",
						Host:           fmt.Sprintf("%s-custom.example.com", bkapp.Name),
						PathPrefixList: []string{"/"},
					},
				},
			},
		},
	}
}
