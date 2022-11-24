/*
 * Tencent is pleased to support the open source community by making
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

	"bk.tencent.com/paas-app-operator/api/v1alpha1"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources"
)

var _ = Describe("Test RevisionReconciler", func() {
	var bkapp *v1alpha1.BkApp
	var web *appsv1.Deployment

	var builder *fake.ClientBuilder
	var scheme *runtime.Scheme

	BeforeEach(func() {
		bkapp = &v1alpha1.BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       v1alpha1.KindBkApp,
				APIVersion: v1alpha1.GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      "bkapp-sample",
				Namespace: "default",
			},
			Spec: v1alpha1.AppSpec{
				Processes: []v1alpha1.Process{
					{
						Name:       "web",
						Image:      "nginx:latest",
						Replicas:   v1alpha1.ReplicasTwo,
						TargetPort: 80,
						CPU:        "100m",
						Memory:     "100Mi",
					},
				},
				Hooks: &v1alpha1.AppHooks{
					PreRelease: &v1alpha1.Hook{},
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
		Expect(v1alpha1.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(appsv1.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(corev1.AddToScheme(scheme)).NotTo(HaveOccurred())
		builder.WithScheme(scheme)
	})

	Context("test Reconcile", func() {
		It("first revision", func() {
			bkapp.Generation = 1
			r := RevisionReconciler{
				Client: builder.WithObjects(bkapp, web).Build(),
			}

			ret := r.Reconcile(context.Background(), bkapp)

			Expect(ret.ShouldAbort()).To(BeFalse())
			Expect(bkapp.Status.Revision).NotTo(BeNil())
			Expect(bkapp.Status.Revision.Revision).To(Equal(int64(1)))
		})

		It("second revision", func() {
			bkapp.Generation = 1
			web.Annotations[v1alpha1.RevisionAnnoKey] = "1"

			r := RevisionReconciler{
				Client: builder.WithObjects(bkapp, web).Build(),
			}

			ret := r.Reconcile(context.Background(), bkapp)

			Expect(ret.ShouldAbort()).To(BeFalse())
			Expect(bkapp.Status.Revision).NotTo(BeNil())
			Expect(bkapp.Status.Revision.Revision).To(Equal(int64(2)))
		})

		It("Generation not change", func() {
			bkapp.Generation = 1
			bkapp.Status.ObservedGeneration = 1
			bkapp.Status.Revision = &v1alpha1.Revision{
				Revision: 1,
			}
			web.Annotations[v1alpha1.RevisionAnnoKey] = "1"

			r := RevisionReconciler{
				Client: builder.WithObjects(bkapp, web).Build(),
			}
			ret := r.Reconcile(context.Background(), bkapp)

			Expect(ret.ShouldAbort()).To(BeFalse())
			Expect(bkapp.Status.Revision.Revision).To(Equal(int64(1)))
		})

		It("Generation change", func() {
			bkapp.Generation = 2
			bkapp.Status.ObservedGeneration = 1
			bkapp.Status.Revision = &v1alpha1.Revision{
				Revision: 1,
			}
			web.Annotations[v1alpha1.RevisionAnnoKey] = "1"

			r := RevisionReconciler{Client: builder.WithObjects(bkapp, web).Build()}
			ret := r.Reconcile(context.Background(), bkapp)

			Expect(ret.ShouldAbort()).To(BeFalse())
			Expect(bkapp.Status.Revision.Revision).To(Equal(int64(2)))
		})

		It("second revision, but hook is unfinished", func() {
			bkapp.Generation = 1
			bkapp.Status.Revision = &v1alpha1.Revision{
				Revision: 1,
			}
			bkapp.Status.SetHookStatus(v1alpha1.HookStatus{
				Type:      v1alpha1.HookPreRelease,
				Status:    v1alpha1.HealthProgressing,
				StartTime: lo.ToPtr(metav1.Now()),
			})
			web.Annotations[v1alpha1.RevisionAnnoKey] = "1"

			hook := resources.BuildPreReleaseHook(bkapp, bkapp.Status.FindHookStatus(v1alpha1.HookPreRelease))
			Expect(hook.Pod).NotTo(BeNil())

			r := RevisionReconciler{
				Client: builder.WithObjects(bkapp, web, hook.Pod).Build(),
			}
			ret := r.Reconcile(context.Background(), bkapp)

			Expect(ret.ShouldAbort()).To(BeTrue())
			Expect(ret.err).To(HaveOccurred())
			Expect(bkapp.Status.Revision.Revision).To(Equal(int64(1)))
		})
	})
})
