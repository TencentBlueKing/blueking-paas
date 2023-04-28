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

package reconcilers

import (
	"context"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"github.com/samber/lo"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources"
)

var _ = Describe("Test RevisionReconciler", func() {
	var bkapp *paasv1alpha2.BkApp
	var web *appsv1.Deployment

	var builder *fake.ClientBuilder
	var scheme *runtime.Scheme

	BeforeEach(func() {
		bkapp = &paasv1alpha2.BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       paasv1alpha2.KindBkApp,
				APIVersion: paasv1alpha2.GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      "bkapp-sample",
				Namespace: "default",
			},
			Spec: paasv1alpha2.AppSpec{
				Build: paasv1alpha2.BuildConfig{
					Image: "nginx:latest",
				},
				Processes: []paasv1alpha2.Process{
					{
						Name:         "web",
						Replicas:     paasv1alpha2.ReplicasTwo,
						ResQuotaPlan: "default",
						TargetPort:   80,
					},
				},
				Hooks: &paasv1alpha2.AppHooks{
					PreRelease: &paasv1alpha2.Hook{},
				},
			},
		}

		web = &appsv1.Deployment{
			TypeMeta: metav1.TypeMeta{
				APIVersion: "apps/v1",
				Kind:       "Deployment",
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:        "web",
				Namespace:   "default",
				Annotations: map[string]string{},
			},
			Spec: appsv1.DeploymentSpec{},
		}

		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		Expect(paasv1alpha2.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(appsv1.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(corev1.AddToScheme(scheme)).NotTo(HaveOccurred())
		builder.WithScheme(scheme)
	})

	Context("test Reconcile", func() {
		It("first revision", func() {
			bkapp.Generation = 1
			r := NewRevisionReconciler(builder.WithObjects(bkapp, web).Build())

			ret := r.Reconcile(context.Background(), bkapp)

			Expect(ret.ShouldAbort()).To(BeFalse())
			Expect(bkapp.Status.Revision).NotTo(BeNil())
			Expect(bkapp.Status.Revision.Revision).To(Equal(int64(1)))
		})

		It("second revision", func() {
			bkapp.Generation = 1
			bkapp.Status.SetHookStatus(paasv1alpha2.HookStatus{
				Type:      paasv1alpha2.HookPreRelease,
				Phase:     paasv1alpha2.HealthHealthy,
				StartTime: lo.ToPtr(metav1.Now()),
			})
			web.Annotations[paasv1alpha2.RevisionAnnoKey] = "1"

			r := NewRevisionReconciler(builder.WithObjects(bkapp, web).Build())

			ret := r.Reconcile(context.Background(), bkapp)

			Expect(ret.ShouldAbort()).To(BeFalse())
			Expect(bkapp.Status.Revision).NotTo(BeNil())
			Expect(bkapp.Status.Revision.Revision).To(Equal(int64(2)))
		})

		It("Generation not change", func() {
			bkapp.Generation = 1
			bkapp.Status.ObservedGeneration = 1
			bkapp.Status.Revision = &paasv1alpha2.Revision{
				Revision: 1,
			}
			web.Annotations[paasv1alpha2.RevisionAnnoKey] = "1"

			r := NewRevisionReconciler(builder.WithObjects(bkapp, web).Build())
			ret := r.Reconcile(context.Background(), bkapp)

			Expect(ret.ShouldAbort()).To(BeFalse())
			Expect(bkapp.Status.Revision.Revision).To(Equal(int64(1)))
		})

		It("Generation change", func() {
			bkapp.Generation = 2
			bkapp.Status.ObservedGeneration = 1
			bkapp.Status.Revision = &paasv1alpha2.Revision{
				Revision: 1,
			}
			bkapp.Status.SetHookStatus(paasv1alpha2.HookStatus{
				Type:      paasv1alpha2.HookPreRelease,
				Phase:     paasv1alpha2.HealthHealthy,
				StartTime: lo.ToPtr(metav1.Now()),
			})
			web.Annotations[paasv1alpha2.RevisionAnnoKey] = "1"

			r := NewRevisionReconciler(builder.WithObjects(bkapp, web).Build())
			ret := r.Reconcile(context.Background(), bkapp)

			Expect(ret.ShouldAbort()).To(BeFalse())
			Expect(bkapp.Status.Revision.Revision).To(Equal(int64(2)))
		})

		It("second revision, but hook is unfinished", func() {
			bkapp.Generation = 1
			bkapp.Status.Revision = &paasv1alpha2.Revision{
				Revision: 1,
			}
			bkapp.Status.SetHookStatus(paasv1alpha2.HookStatus{
				Type:      paasv1alpha2.HookPreRelease,
				Phase:     paasv1alpha2.HealthProgressing,
				StartTime: lo.ToPtr(metav1.Now()),
			})
			web.Annotations[paasv1alpha2.RevisionAnnoKey] = "1"

			hook := resources.BuildPreReleaseHook(bkapp, bkapp.Status.FindHookStatus(paasv1alpha2.HookPreRelease))
			Expect(hook.Pod).NotTo(BeNil())

			r := NewRevisionReconciler(builder.WithObjects(bkapp, web, hook.Pod).Build())
			ret := r.Reconcile(context.Background(), bkapp)

			Expect(ret.ShouldAbort()).To(BeTrue())
			Expect(ret.err).To(HaveOccurred())
			Expect(bkapp.Status.Revision.Revision).To(Equal(int64(1)))
		})

		It("skip failed hook", func() {
			// g4 表示第四个版本
			bkapp.Generation = 4
			// 在 g3 & r3 的时候，hook 失败
			bkapp.Status.Revision = &paasv1alpha2.Revision{
				Revision: 3,
			}
			bkapp.Status.SetHookStatus(paasv1alpha2.HookStatus{
				Type:      paasv1alpha2.HookPreRelease,
				Phase:     paasv1alpha2.HealthUnhealthy,
				StartTime: lo.ToPtr(metav1.Now()),
			})
			// r2 中调和循环正常结束，r3 中 hook 失败，因此 deployment 还是 r2
			web.Annotations[paasv1alpha2.RevisionAnnoKey] = "2"

			hook := resources.BuildPreReleaseHook(
				bkapp, bkapp.Status.FindHookStatus(paasv1alpha2.HookPreRelease),
			)

			cli := builder.WithObjects(bkapp, web, hook.Pod).Build()
			r := NewRevisionReconciler(cli)
			ret := r.Reconcile(context.Background(), bkapp)

			Expect(ret.ShouldAbort()).To(BeFalse())
			// 跳过失败的 hook 版本后，revision 应该是 deploy max revision: 2 + 1 + 1 = 4
			Expect(bkapp.Status.Revision.Revision).To(Equal(int64(4)))
		})
	})
})
