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

package ingress

import (
	"sort"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"github.com/pkg/errors"
	"github.com/samber/lo"
	networkingv1 "k8s.io/api/networking/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/config"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/names"
	testingutils "bk.tencent.com/paas-app-operator/pkg/testing"
)

var _ = Describe("Test ingresses.go", func() {
	var bkapp *paasv1alpha2.BkApp

	config.SetConfig(testingutils.Config{})

	BeforeEach(func() {
		bkapp = &paasv1alpha2.BkApp{
			TypeMeta:   metav1.TypeMeta{Kind: paasv1alpha2.KindBkApp, APIVersion: paasv1alpha2.GroupVersion.String()},
			ObjectMeta: metav1.ObjectMeta{Name: "demo", Namespace: "default"},
			Spec: paasv1alpha2.AppSpec{
				Build: paasv1alpha2.BuildConfig{
					Image: "nginx:latest",
				},
				Processes: []paasv1alpha2.Process{
					{
						Name:         "web",
						Replicas:     paasv1alpha2.ReplicasTwo,
						ResQuotaPlan: paasv1alpha2.ResQuotaPlanDefault,
						TargetPort:   80,
					},
				},
			},
		}
	})

	Context("Domain struct", func() {
		It("GetURLs no TLS", func() {
			d := Domain{Host: "foo.example.com", PathPrefixList: []string{"/", "/foo-bar/", "foo"}}
			Expect(d.GetURLs()).To(Equal([]string{
				"http://foo.example.com/",
				"http://foo.example.com/foo-bar/",
				"http://foo.example.com/foo/",
			}))
		})
		It("GetURLs TLS", func() {
			d := Domain{Host: "foo.example.com", PathPrefixList: []string{"/"}, TLSSecretName: "foo-sec"}
			Expect(d.GetURLs()).To(Equal([]string{"https://foo.example.com/"}))
		})
	})

	Context("IngressBuilder", func() {
		DescribeTable("Test different types", func(t DomainSourceType) {
			domains := DomainGroup{
				SourceType: t,
				Domains:    []Domain{{Host: "foo.example.com", PathPrefixList: []string{"/foo/", "/foo-bar/"}}},
			}
			builder, err := NewIngressBuilder(t, bkapp)
			Expect(err).NotTo(HaveOccurred())

			_, err = builder.Build(domains.Domains)
			Expect(err).NotTo(HaveOccurred())
		},
			Entry("subdomain", DomainSubDomain),
			Entry("subpath", DomainSubPath),
			Entry("custom", DomainCustom),
		)

		It("Wrong source type", func() {
			_, err := NewIngressBuilder("invalid-type", bkapp)
			Expect(errors.Is(err, ErrDomainGroupSourceType)).To(BeTrue())
		})
	})

	Context("MonoIngressBuilder", func() {
		It("test normal", func() {
			domains := DomainGroup{
				SourceType: DomainSubDomain,
				Domains: []Domain{
					{Host: "foo.example.com", PathPrefixList: []string{"/foo/", "/foo-bar/"}},
					{Host: "bar.example.com", PathPrefixList: []string{"/"}},
				},
			}
			builder := MonoIngressBuilder{bkapp, domains.SourceType}
			ingresses, err := builder.Build(domains.Domains)

			Expect(err).NotTo(HaveOccurred())
			Expect(len(ingresses)).To(Equal(1))
			Expect(ingresses[0].Name).To(Equal("demo-subdomain"))
			Expect(ingresses[0].Spec.Rules[0].Host).To(Equal("foo.example.com"))
			Expect(ingresses[0].Annotations[SkipFilterCLBAnnoKey]).To(Equal("true"))
			Expect(ingresses[0].Annotations[paasv1alpha2.IngressClassAnnoKey]).To(Equal("test-nginx"))
		})

		DescribeTable(
			"test if bkapp has one process service with exposed type",
			func(exposedType paasv1alpha2.ExposedTypeName, expectedBackendProtocol, pathPrefix, expectedPath string) {
				bkapp.EnableProcServicesFeature()
				bkapp.Spec.Processes[0].Services = []paasv1alpha2.ProcService{
					{
						Name:       "bar",
						TargetPort: 8080,
						Port:       80,
					},
					{
						Name:        "foo",
						ExposedType: &paasv1alpha2.ExposedType{Name: exposedType},
						TargetPort:  8000,
						Port:        80,
					},
				}
				domains := DomainGroup{
					SourceType: DomainSubDomain,
					Domains: []Domain{
						{Host: "foo.example.com", PathPrefixList: []string{pathPrefix}, TLSSecretName: "grpc-tls"},
					},
				}
				builder := MonoIngressBuilder{bkapp, domains.SourceType}
				ingresses, err := builder.Build(domains.Domains)

				Expect(err).NotTo(HaveOccurred())

				Expect(ingresses[0].GetAnnotations()[BackendProtocolAnnoKey]).To(Equal(expectedBackendProtocol))
				Expect(ingresses[0].Spec.Rules[0].Host).To(Equal("foo.example.com"))

				ingressPath := ingresses[0].Spec.Rules[0].IngressRuleValue.HTTP.Paths[0]
				Expect(ingressPath.Path).To(Equal(expectedPath))

				ingressServiceBackend := ingresses[0].Spec.Rules[0].IngressRuleValue.HTTP.Paths[0].Backend.Service
				Expect(ingressServiceBackend.Name).To(Equal(names.Service(bkapp, "web")))
				Expect(ingressServiceBackend.Port.Name).To(Equal("foo"))

				tls := ingresses[0].Spec.TLS
				Expect(tls[0].SecretName).To(Equal("grpc-tls"))
				Expect(tls[0].Hosts).To(Equal([]string{"foo.example.com"}))
			},
			Entry("When bk/http", paasv1alpha2.ExposedTypeNameBkHTTP, "", "/", "/()(.*)"),
			Entry("When bk/grpc", paasv1alpha2.ExposedTypeNameBkGRPC, "GRPC", "/", "/"),
		)
	})

	Context("CustomIngressBuilder", func() {
		It("test normal", func() {
			domains := DomainGroup{
				SourceType: DomainCustom,
				Domains: []Domain{
					{Host: "foo.example.com", PathPrefixList: []string{"/"}},
					{Host: "with-name.example.com", PathPrefixList: []string{"/"}, Name: "1"},
				},
			}
			builder := CustomIngressBuilder{bkapp}
			ingresses, err := builder.Build(domains.Domains)

			Expect(err).NotTo(HaveOccurred())
			Expect(len(ingresses)).To(Equal(2))

			names := lo.Map(ingresses, func(ing *networkingv1.Ingress, _ int) string { return ing.Name })
			Expect(names).To(Equal([]string{"custom-demo-foo.example.com", "custom-demo-with-name.example.com-1"}))
			Expect(ingresses[0].Spec.Rules[0].Host).To(Equal("foo.example.com"))
			Expect(ingresses[1].Spec.Rules[0].Host).To(Equal("with-name.example.com"))
			Expect(ingresses[1].Annotations[SkipFilterCLBAnnoKey]).To(Equal("true"))
			Expect(ingresses[0].Annotations[paasv1alpha2.IngressClassAnnoKey]).To(Equal("test-custom-domain-nginx"))
		})
	})

	Context("makeTLS", func() {
		It("Normal case", func() {
			domains := []Domain{
				{Host: "tls-1.example.com", PathPrefixList: []string{"/"}, TLSSecretName: "bar-secret"},
				{Host: "tls-2.example.com", PathPrefixList: []string{"/"}, TLSSecretName: "foo-secret"},
				{Host: "tls-3.example.com", PathPrefixList: []string{"/"}, TLSSecretName: "bar-secret"},
				{Host: "no-tls.example.com", PathPrefixList: []string{"/"}},
			}
			tlsObjs := makeTLS(domains)
			Expect(len(tlsObjs)).To(Equal(2))
			// First sort, then compare
			sort.Slice(tlsObjs, func(i, j int) bool { return tlsObjs[i].SecretName < tlsObjs[j].SecretName })
			Expect(tlsObjs[0].SecretName).To(Equal("bar-secret"))
			Expect(tlsObjs[0].Hosts).To(Equal([]string{"tls-1.example.com", "tls-3.example.com"}))
			Expect(tlsObjs[1].SecretName).To(Equal("foo-secret"))
			Expect(tlsObjs[1].Hosts).To(Equal([]string{"tls-2.example.com"}))
		})
	})
})
