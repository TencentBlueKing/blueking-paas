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

package dgroupmapping

import (
	"context"
	"sort"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"github.com/samber/lo"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	networkingv1 "k8s.io/api/networking/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	"bk.tencent.com/paas-app-operator/api/v1alpha1"
	"bk.tencent.com/paas-app-operator/api/v1alpha2"
	dgfake "bk.tencent.com/paas-app-operator/pkg/controllers/dgroupmapping/fake"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/labels"
)

var _ = Describe("Test DGroupMappingSyncer", func() {
	var bkapp *v1alpha2.BkApp
	var dgmapping *v1alpha1.DomainGroupMapping
	var builder *fake.ClientBuilder
	var scheme *runtime.Scheme

	BeforeEach(func() {
		// Set up client
		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		_ = v1alpha1.AddToScheme(scheme)
		_ = v1alpha2.AddToScheme(scheme)
		_ = appsv1.AddToScheme(scheme)
		_ = corev1.AddToScheme(scheme)
		_ = networkingv1.AddToScheme(scheme)
		builder.WithScheme(scheme)

		// Sample data
		bkapp = &v1alpha2.BkApp{
			TypeMeta:   metav1.TypeMeta{Kind: v1alpha2.KindBkApp, APIVersion: v1alpha2.GroupVersion.String()},
			ObjectMeta: metav1.ObjectMeta{Name: "demo", Namespace: "default"},
			Spec: v1alpha2.AppSpec{
				Build: v1alpha2.BuildConfig{
					Image: "nginx:latest",
				},
				Processes: []v1alpha2.Process{
					{
						Name:         "web",
						Replicas:     v1alpha2.ReplicasTwo,
						ResQuotaPlan: "default",
						TargetPort:   80,
					},
				},
			},
		}

		dgmapping = &v1alpha1.DomainGroupMapping{
			TypeMeta: metav1.TypeMeta{
				Kind:       v1alpha1.KindDomainGroupMapping,
				APIVersion: v1alpha1.GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      "sample-mapping",
				Namespace: "default",
			},
			Spec: v1alpha1.DomainGroupMappingSpec{},
		}
	})

	Context("Test Reconcile", func() {
		It("test integrated", func() {
			// Create an existed Ingress
			wrongIngress := networkingv1.Ingress{
				TypeMeta: metav1.TypeMeta{APIVersion: "v1", Kind: "Ingress"},
				ObjectMeta: metav1.ObjectMeta{
					Name:      "wrong-ingress",
					Namespace: bkapp.Namespace,
					Labels:    labels.MappingIngress(dgmapping),
				},
			}

			ctx := context.Background()
			syncer := NewDGroupMappingSyncer(builder.WithObjects(&wrongIngress).Build(), bkapp)

			// A helper function which get all Ingress's names
			getIngressNames := func() []string {
				objs, _ := syncer.ListCurrentIngresses(ctx, dgmapping)
				names := lo.Map(objs, func(obj *networkingv1.Ingress, _ int) string {
					return obj.GetName()
				})
				sort.Strings(names)
				return names
			}

			By("Wrong ingress should exists")
			Expect(getIngressNames()).To(Equal([]string{"wrong-ingress"}))

			// Update Spec to make it include domains
			dgmapping.Spec = dgfake.DGroupMappingSpecFixture(bkapp)
			_, err := syncer.Sync(ctx, dgmapping)
			Expect(err).Should(Not(HaveOccurred()))

			By("Check Ingresses after reconcile")
			Expect(getIngressNames()).To(Equal([]string{
				"custom-demo-demo-custom.example.com-1",
				"demo-subdomain",
				"demo-subpath",
			}))
		})

		It("test empty domains integrated", func() {
			ctx := context.Background()
			client := builder.Build()

			By("Sync ingresses by domain fixtures")
			dgmapping.Spec = dgfake.DGroupMappingSpecFixture(bkapp)
			syncer := NewDGroupMappingSyncer(client, bkapp)
			_, err := syncer.Sync(ctx, dgmapping)
			Expect(err).Should(Not(HaveOccurred()))
			objs, _ := syncer.ListCurrentIngresses(ctx, dgmapping)
			Expect(len(objs)).To(Equal(3))

			By("All ingresses should be removed")
			dgmapping.Spec.Data = []v1alpha1.DomainGroup{}
			_, err = syncer.Sync(ctx, dgmapping)
			Expect(err).Should(Not(HaveOccurred()))
			objs, _ = syncer.ListCurrentIngresses(ctx, dgmapping)
			Expect(objs).To(BeEmpty())
		})
	})

	Context("DeleteIngresses", func() {
		It("Test delete", func() {
			ctx := context.Background()
			client := builder.Build()

			dgmapping.Spec = dgfake.DGroupMappingSpecFixture(bkapp)
			syncer := NewDGroupMappingSyncer(client, bkapp)
			_, err := syncer.Sync(ctx, dgmapping)
			Expect(err).Should(Not(HaveOccurred()))
			objs, _ := syncer.ListCurrentIngresses(ctx, dgmapping)
			Expect(len(objs)).To(Equal(3))

			_ = DeleteIngresses(ctx, client, dgmapping)
			objs, _ = syncer.ListCurrentIngresses(ctx, dgmapping)
			Expect(len(objs)).To(Equal(0))
		})
	})
})
