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

package controllers

import (
	"strings"
	"time"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	networkingv1 "k8s.io/api/networking/v1"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"

	"bk.tencent.com/paas-app-operator/api/v1alpha1"
	paasv1alpha1 "bk.tencent.com/paas-app-operator/api/v1alpha1"
	res "bk.tencent.com/paas-app-operator/pkg/controllers/resources"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/labels"
	"bk.tencent.com/paas-app-operator/pkg/testing"
	"bk.tencent.com/paas-app-operator/pkg/utils/basic"
)

var _ = Describe("", func() {
	var bkapp *paasv1alpha1.BkApp
	var domainMapping *paasv1alpha1.DomainGroupMapping
	var getIngressesCnt func() int

	const (
		timeout  = time.Second * 10
		interval = time.Millisecond * 250
	)

	BeforeEach(func() {
		// Use a random name for every test case
		nameSuffix := strings.ToLower(basic.RandStr(6))
		bkapp = &paasv1alpha1.BkApp{
			TypeMeta: metav1.TypeMeta{Kind: v1alpha1.KindBkApp, APIVersion: v1alpha1.GroupVersion.String()},
			ObjectMeta: metav1.ObjectMeta{
				Name:        "sample-app-" + nameSuffix,
				Namespace:   "default",
				Annotations: map[string]string{},
			},
			Spec: v1alpha1.AppSpec{
				Processes: []paasv1alpha1.Process{
					{
						Name:       "web",
						Image:      "nginx:latest",
						Replicas:   v1alpha1.ReplicasTwo,
						TargetPort: 80,
						CPU:        "100m",
						Memory:     "100Mi",
					},
				},
			},
		}
		testing.WithAppInfoAnnotations(bkapp)

		domainMapping = &paasv1alpha1.DomainGroupMapping{
			TypeMeta: metav1.TypeMeta{
				Kind:       paasv1alpha1.KindDomainGroupMapping,
				APIVersion: paasv1alpha1.GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      "sample-mapping-" + nameSuffix,
				Namespace: "default",
			},
			Spec: paasv1alpha1.DomainGroupMappingSpec{
				Ref: paasv1alpha1.MappingRef{
					Name:       bkapp.Name,
					Kind:       paasv1alpha1.KindBkApp,
					APIVersion: paasv1alpha1.GroupVersion.String(),
				},
				// 1 builtin subdomain + 2 custom domains(same host, different path)
				Data: []paasv1alpha1.DomainGroup{
					{
						SourceType: "subdomain",
						Domains: []paasv1alpha1.Domain{
							{
								Host:           "sample.example.com",
								PathPrefixList: []string{"/"},
							},
						},
					},
					{
						SourceType: "custom",
						Domains: []paasv1alpha1.Domain{
							{
								Name:           "1",
								Host:           "custom.example.com",
								PathPrefixList: []string{"/"},
							},
							{
								Name:           "2",
								Host:           "custom.example.com",
								PathPrefixList: []string{"/foo/"},
							},
						},
					},
				},
			},
		}

		// A helper function which counts ingresses
		getIngressesCnt = func() int {
			result := networkingv1.IngressList{}
			err := k8sClient.List(
				ctx,
				&result,
				client.InNamespace(bkapp.GetNamespace()),
				client.MatchingLabels(labels.MappingIngress(domainMapping)),
			)
			if err != nil {
				return -1
			}
			return len(result.Items)
		}
	})

	It("Integrated tests for DomainGroupMapping", func() {
		By("By checking the condition of newly created DomainGroupMapping object")
		Expect(k8sClient.Create(ctx, domainMapping)).NotTo(HaveOccurred())

		LookupKey := client.ObjectKeyFromObject(domainMapping)
		createdMapping := paasv1alpha1.DomainGroupMapping{}

		Eventually(func() bool {
			if err := k8sClient.Get(ctx, LookupKey, &createdMapping); err != nil {
				return false
			}
			// Check condition's value
			condProcessed := apimeta.FindStatusCondition(
				createdMapping.Status.Conditions,
				paasv1alpha1.DomainMappingProcessed,
			)
			return condProcessed != nil &&
				condProcessed.Status == metav1.ConditionFalse &&
				condProcessed.Reason == "RefNotFound"
		}, timeout, interval).Should(BeTrue())

		By("By checking no Ingress resources yet")
		Expect(getIngressesCnt()).To(Equal(0))

		By("By creating the BkApp object which is referenced")
		Expect(k8sClient.Create(ctx, bkapp)).NotTo(HaveOccurred())

		Eventually(func() bool {
			if err := k8sClient.Get(ctx, LookupKey, &createdMapping); err != nil {
				return false
			}
			// Check condition's value
			condProcessed := apimeta.FindStatusCondition(
				createdMapping.Status.Conditions,
				paasv1alpha1.DomainMappingProcessed,
			)
			return condProcessed.Status == metav1.ConditionTrue && condProcessed.Reason == "Processed"
		}, timeout, interval).Should(BeTrue())

		By("By checking the Ingress resources was created")
		Eventually(getIngressesCnt, timeout, interval).Should(Equal(3))

		By("BkApp's status should also be updated")
		var app paasv1alpha1.BkApp
		_ = k8sClient.Get(ctx, client.ObjectKeyFromObject(bkapp), &app)
		Expect(app.Status.Addresses[0].URL).To(Equal("http://sample.example.com/"))

		By("Modifications of DomainGroupMapping object should update ingresses")
		// Remove domains to contain the first subdomain element only
		createdMapping.Spec.Data = createdMapping.Spec.Data[:1]
		Expect(k8sClient.Update(ctx, &createdMapping)).NotTo(HaveOccurred())
		Eventually(getIngressesCnt, timeout, interval).Should(Equal(1))
	})

	Context("Test resource deletions", func() {
		BeforeEach(func() {
			Expect(k8sClient.Create(ctx, domainMapping)).NotTo(HaveOccurred())
			Expect(k8sClient.Create(ctx, bkapp)).NotTo(HaveOccurred())
			Eventually(getIngressesCnt, timeout, interval).Should(Equal(3))
		})
		It("Test delete DomainGroupMapping", func() {
			var app paasv1alpha1.BkApp
			_ = k8sClient.Get(ctx, client.ObjectKeyFromObject(bkapp), &app)
			Expect(app.Status.Addresses[0].URL).To(Equal("http://sample.example.com/"))

			By("Related ingresses should also be deleted")
			_ = k8sClient.Delete(ctx, domainMapping)
			Eventually(getIngressesCnt, timeout, interval).Should(Equal(0))

			By("App's status.addresses should also be updated")
			_ = k8sClient.Get(ctx, client.ObjectKeyFromObject(bkapp), &app)
			Expect(len(app.Status.Addresses)).To(BeZero())
		})
		It("Test delete BkApp", func() {
			By("Delete BkApp should also remove ingresses")
			_ = k8sClient.Delete(ctx, bkapp)
			Eventually(getIngressesCnt, timeout, interval).Should(Equal(0))
		})
	})

	Context("ToAddressableStatus", func() {
		It("mixed types", func() {
			groups := []res.DomainGroup{
				{
					SourceType: res.DomainSubDomain,
					Domains: []res.Domain{
						{Host: "subdomain.example.com", PathPrefixList: []string{"/"}},
					},
				},
				{
					SourceType: res.DomainSubPath,
					Domains: []res.Domain{
						{Host: "subpath.example.com", PathPrefixList: []string{"/foo/", "/foo-bar/"}},
					},
				},
				{
					SourceType: res.DomainCustom,
					Domains: []res.Domain{
						{Host: "custom.example.com", PathPrefixList: []string{"/"}, TLSSecretName: "foo-sec"},
					},
				},
			}
			addresses := ToAddressableStatus(groups)
			Expect(addresses).To(Equal(
				[]paasv1alpha1.Addressable{
					{
						SourceType: string(res.DomainSubDomain),
						URL:        "http://subdomain.example.com/",
					},
					{
						SourceType: string(res.DomainSubPath),
						URL:        "http://subpath.example.com/foo/",
					},
					{
						SourceType: string(res.DomainSubPath),
						URL:        "http://subpath.example.com/foo-bar/",
					},
					{
						SourceType: string(res.DomainCustom),
						URL:        "https://custom.example.com/",
					},
				},
			))
		})
	})
})
