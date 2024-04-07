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
 */package svcdisc

import (
	"context"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/labels"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/names"
)

var _ = Describe("Test configmap related functions", func() {
	Context("Test WorkloadsMutator", func() {
		var bkapp *paasv1alpha2.BkApp
		var ctx context.Context
		var builder *fake.ClientBuilder
		var scheme *runtime.Scheme

		BeforeEach(func() {
			ctx = context.Background()
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
					SvcDiscovery: &paasv1alpha2.SvcDiscConfig{
						BkSaaS: []paasv1alpha2.SvcDiscEntryBkSaaS{{BkAppCode: "foo"}},
					},
				},
			}

			// Register schemas to the fake builder
			builder = fake.NewClientBuilder()
			scheme = runtime.NewScheme()
			Expect(paasv1alpha2.AddToScheme(scheme)).NotTo(HaveOccurred())
			Expect(v1.AddToScheme(scheme)).NotTo(HaveOccurred())
			builder.WithScheme(scheme)
		})

		Context("test ApplyToDeployment", func() {
			var deploy *appsv1.Deployment
			var configmap *v1.ConfigMap

			BeforeEach(func() {
				// An empty deployment resource
				deploy = &appsv1.Deployment{
					TypeMeta: metav1.TypeMeta{APIVersion: "apps/v1", Kind: "Deployment"},
					ObjectMeta: metav1.ObjectMeta{
						Name:      names.Deployment(bkapp, "foo"),
						Namespace: bkapp.Namespace,
						Labels:    labels.Deployment(bkapp, "foo"),
					},
					Spec: appsv1.DeploymentSpec{
						Template: corev1.PodTemplateSpec{
							Spec: corev1.PodSpec{
								Containers: []corev1.Container{{Name: "nginx", Image: "nginx:latest"}},
							},
						},
					},
				}

				configmap = &v1.ConfigMap{
					ObjectMeta: metav1.ObjectMeta{Namespace: bkapp.Namespace, Name: "svc-disc-results-" + bkapp.Name},
					Data: map[string]string{
						DataKeyBkSaaS: "some_value",
					},
				}
			})

			It("No configmap", func() {
				ret := NewWorkloadsMutator(builder.Build(), bkapp).ApplyToDeployment(ctx, deploy)
				Expect(ret).To(BeFalse())
			})
			It("Configmap has no valid key", func() {
				// Update the configmap to contain no valid keys
				configmap.Data = map[string]string{}
				ret := NewWorkloadsMutator(
					builder.WithObjects(configmap).Build(),
					bkapp,
				).ApplyToDeployment(ctx, deploy)
				Expect(ret).To(BeFalse())
			})
			It("Configmap exists, but svc-discovery config is empty", func() {
				bkapp.Spec.SvcDiscovery = nil
				ret := NewWorkloadsMutator(
					builder.WithObjects(configmap).Build(),
					bkapp,
				).ApplyToDeployment(ctx, deploy)
				Expect(ret).To(BeFalse())
			})
			It("Applied successfully", func() {
				Expect(len(deploy.Spec.Template.Spec.Containers[0].Env)).To(BeZero())

				ret := NewWorkloadsMutator(
					builder.WithObjects(configmap).Build(),
					bkapp,
				).ApplyToDeployment(ctx, deploy)
				Expect(ret).To(BeTrue())
				Expect(len(deploy.Spec.Template.Spec.Containers[0].Env)).To(Equal(1))
			})
		})

		Context("test ApplyToPod", func() {
			var pod *corev1.Pod
			var configmap *v1.ConfigMap

			BeforeEach(func() {
				// An empty pod object
				pod = &corev1.Pod{
					TypeMeta: metav1.TypeMeta{Kind: "Pod", APIVersion: "v1"},
					ObjectMeta: metav1.ObjectMeta{
						Name:      names.PreReleaseHook(bkapp),
						Namespace: bkapp.Namespace,
						Labels:    labels.Hook(bkapp, paasv1alpha2.HookPreRelease),
					},
					Spec: corev1.PodSpec{
						Containers: []corev1.Container{{Name: "nginx", Image: "nginx:latest"}},
					},
				}

				configmap = &v1.ConfigMap{
					ObjectMeta: metav1.ObjectMeta{Namespace: bkapp.Namespace, Name: "svc-disc-results-" + bkapp.Name},
					Data: map[string]string{
						DataKeyBkSaaS: "some_value",
					},
				}
			})

			It("Applied successfully", func() {
				Expect(len(pod.Spec.Containers[0].Env)).To(BeZero())

				ret := NewWorkloadsMutator(
					builder.WithObjects(configmap).Build(),
					bkapp,
				).ApplyToPod(ctx, pod)
				Expect(ret).To(BeTrue())
				Expect(len(pod.Spec.Containers[0].Env)).To(Equal(1))
			})
		})
	})
})
