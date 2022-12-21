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

package v1alpha1

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

var _ = Describe("test webhook.Validator", func() {
	host := "bkapp-sample.example.com"
	var dgm *DomainGroupMapping

	BeforeEach(func() {
		dgm = &DomainGroupMapping{
			TypeMeta: metav1.TypeMeta{
				Kind:       KindDomainGroupMapping,
				APIVersion: GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      "domaingroupmapping-q67hn2n3",
				Namespace: "default",
			},
			Spec: DomainGroupMappingSpec{
				Ref: MappingRef{
					Name:       "bkapp-q67hn2n3",
					Kind:       KindBkApp,
					APIVersion: GroupVersion.String(),
				},
				Data: []DomainGroup{
					{
						SourceType: SourceTypeSubDomain,
						Domains: []Domain{
							{
								Host:           host,
								PathPrefixList: []string{"/"},
							},
						},
					},
				},
			},
		}
		// 预先准备好被引用的 BkApp
		bkapp := &BkApp{
			TypeMeta:   metav1.TypeMeta{Kind: KindBkApp, APIVersion: GroupVersion.String()},
			ObjectMeta: metav1.ObjectMeta{Name: "bkapp-q67hn2n3", Namespace: "default"},
			Spec: AppSpec{
				Processes: []Process{{Name: "web", Replicas: ReplicasOne, Image: "nginx:latest"}},
			},
		}
		_ = k8sClient.Create(ctx, bkapp)
	})

	Context("Test DomainGroupMapping actions", func() {
		It("Create normal", func() {
			err := dgm.ValidateCreate()
			Expect(err).ShouldNot(HaveOccurred())
		})

		It("Update normal", func() {
			err := dgm.ValidateUpdate(dgm)
			Expect(err).ShouldNot(HaveOccurred())
		})

		It("Delete normal", func() {
			err := dgm.ValidateDelete()
			Expect(err).ShouldNot(HaveOccurred())
		})
	})

	Context("Test spec ref", func() {
		It("unsupported referred resource kind", func() {
			dgm.Spec.Ref.Kind = "BkAppPro"
			err := dgm.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("supported values: \"BkApp\""))
		})

		It("not found referred bkapp", func() {
			dgm.Spec.Ref.Name = "bkapp-wigeqago"
			err := dgm.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("Not found"))
		})
	})

	Context("Test spec domain group", func() {
		It("unsupported source type", func() {
			dgm.Spec.Data[0].SourceType = "InvalidType"
			err := dgm.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("supported values: \"subdomain\", \"subpath\", \"custom\""))
		})

		It("domains config not found", func() {
			dgm.Spec.Data[0].Domains = []Domain{}
			err := dgm.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("at least one domain required"))
		})
	})
})

var _ = Describe("Integrated tests for webhooks", func() {
	It("Create DomainGroupMapping with minimal required fields", func() {
		// 预先准备好被引用的 BkApp
		bkapp := &BkApp{
			TypeMeta:   metav1.TypeMeta{Kind: KindBkApp, APIVersion: GroupVersion.String()},
			ObjectMeta: metav1.ObjectMeta{Name: "bkapp-7rxsa1gf", Namespace: "default"},
			Spec: AppSpec{
				Processes: []Process{{Name: "web", Replicas: ReplicasOne, Image: "nginx:latest"}},
			},
		}
		Expect(k8sClient.Create(ctx, bkapp)).NotTo(HaveOccurred())

		// DomainGroupMapping 创建测试
		host := "bkapp-sample.example.com"
		dgm := &DomainGroupMapping{
			TypeMeta: metav1.TypeMeta{
				Kind:       KindDomainGroupMapping,
				APIVersion: GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      "domaingroupmapping-7rxsa1gf",
				Namespace: "default",
			},
			// Only include minimal required fields
			Spec: DomainGroupMappingSpec{
				Ref: MappingRef{
					Name:       "bkapp-7rxsa1gf",
					Kind:       KindBkApp,
					APIVersion: GroupVersion.String(),
				},
				Data: []DomainGroup{
					{
						SourceType: SourceTypeSubDomain,
						Domains: []Domain{
							{
								Host:           host,
								PathPrefixList: []string{"/"},
							},
						},
					},
				},
			},
		}
		Expect(k8sClient.Create(ctx, dgm)).NotTo(HaveOccurred())

		// Check if default values have been set
		var created DomainGroupMapping
		Expect(k8sClient.Get(ctx, client.ObjectKeyFromObject(dgm), &created)).NotTo(HaveOccurred())
		Expect(created.Spec.Data[0].SourceType).To(Equal(SourceTypeSubDomain))
		Expect(created.Spec.Data[0].Domains[0].Host).To(Equal(host))
	})
})
