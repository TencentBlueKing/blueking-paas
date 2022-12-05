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

	"bk.tencent.com/paas-app-operator/api/v1alpha1"
	res "bk.tencent.com/paas-app-operator/pkg/controllers/resources"
)

// FakeDomainsRetriever build domain groups data by simple rules, only meaningful
// for testing purpose, don't use in production.
type FakeDomainsRetriever struct {
	Bkapp *v1alpha1.BkApp
}

// Retrieve builds all types of example Domain groups
func (r FakeDomainsRetriever) Retrieve() []res.DomainGroup {
	subHost := fmt.Sprintf("%s.example.com", r.Bkapp.Name)
	subDomainG := res.DomainGroup{
		SourceType: res.DomainSubDomain,
		Domains: []res.Domain{
			{Host: subHost, PathPrefixList: []string{"/"}},
		},
	}
	subPathG := res.DomainGroup{
		SourceType: res.DomainSubPath,
		Domains: []res.Domain{
			{Host: "fake.example.com", PathPrefixList: []string{"/" + r.Bkapp.Name}},
		},
	}
	customHost := fmt.Sprintf("%s-custom.example.com", r.Bkapp.Name)
	customG := res.DomainGroup{
		SourceType: res.DomainCustom,
		Domains: []res.Domain{
			{Host: customHost, PathPrefixList: []string{"/"}, Name: "1"},
		},
	}
	return []res.DomainGroup{subDomainG, subPathG, customG}
}
