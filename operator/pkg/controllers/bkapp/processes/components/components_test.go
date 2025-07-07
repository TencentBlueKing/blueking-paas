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

package components_test

import (
	"context"

	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/processes/components"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
)

var _ = Describe("ComponentsMutator", func() {
	var (
		ctx        context.Context
		fakeClient client.Client
		scheme     *runtime.Scheme
	)

	BeforeEach(func() {
		ctx = context.Background()
		scheme = runtime.NewScheme()
		_ = corev1.AddToScheme(scheme)
		_ = appsv1.AddToScheme(scheme)
		_ = paasv1alpha2.AddToScheme(scheme)
	})

	Describe("PatchAllComponentToDeployment", func() {
		var (
			proc   *paasv1alpha2.Process
			deploy *appsv1.Deployment
		)

		BeforeEach(func() {
			labelComponent := &corev1.ConfigMap{
				ObjectMeta: metav1.ObjectMeta{
					Name:      "label-component",
					Namespace: components.TEMPLATE_NAMESPACE,
				},
				Data: map[string]string{
					"v1": `{
						"spec": {
							"template": {
								"metadata": {
									"labels": {
										"component": "{{ .componentName }}"
									}
								}
							}
						}
					}`,
				},
			}

			sidecarComponent := &corev1.ConfigMap{
				ObjectMeta: metav1.ObjectMeta{
					Name:      "sidecar-component",
					Namespace: components.TEMPLATE_NAMESPACE,
				},
				Data: map[string]string{
					"v1": `{
						"spec": {
							"template": {
								"spec": {
									"containers": [
										{
											"name": "{{ .sidecarName }}",
											"image": "{{ .image }}",
											"ports": [
												{
													"containerPort": {{ .port }}
												}
											]
										}
									]
								}
							}
						}
					}`,
				},
			}
			fakeClient = fake.NewClientBuilder().
				WithScheme(scheme).
				WithObjects(labelComponent, sidecarComponent).
				Build()

			proc = &paasv1alpha2.Process{
				Components: []paasv1alpha2.Component{
					{
						Type:    "label-component",
						Version: "v1",
						Properties: runtime.RawExtension{
							Raw: []byte(`{"componentName":"web"}`),
						},
					},
					{
						Type:    "sidecar-component",
						Version: "v1",
						Properties: runtime.RawExtension{
							Raw: []byte(`{
            				    "sidecarName": "log-collector",
            				    "image": "docker.io/fluentd:latest",
            				    "port": 24224
            				}`),
						},
					},
				},
			}

			deploy = &appsv1.Deployment{
				ObjectMeta: metav1.ObjectMeta{
					Name: "test-deploy",
				},
				Spec: appsv1.DeploymentSpec{
					Replicas: paasv1alpha2.ReplicasOne,
					Template: corev1.PodTemplateSpec{
						Spec: corev1.PodSpec{
							Containers: []corev1.Container{
								{
									Name:  "web",
									Image: "nginx:latest",
									Ports: []corev1.ContainerPort{
										{
											ContainerPort: 80,
											Protocol:      corev1.ProtocolTCP,
										},
									},
									Env: []corev1.EnvVar{
										{
											Name:  "ENVIRONMENT",
											Value: "test",
										},
									},
								},
							},
						},
					},
				},
			}
		})

		It("should apply all components to deployment", func() {
			err := components.PatchAllComponentToDeployment(fakeClient, ctx, proc, deploy)
			Expect(err).NotTo(HaveOccurred())

			Expect(deploy.Spec.Template.Labels).To(HaveKeyWithValue("component", "web"))
			Expect(len(deploy.Spec.Template.Spec.Containers)).To(Equal(2))
			Expect(deploy.Spec.Template.Spec.Containers).To(
				ContainElement(
					WithTransform(func(c corev1.Container) string {
						return c.Name
					}, Equal("web")),
				),
			)
			Expect(deploy.Spec.Template.Spec.Containers).To(
				ContainElement(
					WithTransform(func(c corev1.Container) string {
						return c.Name
					}, Equal("log-collector")),
				),
			)
		})

		Context("when component patch fails", func() {
			BeforeEach(func() {
				proc.Components[0].Type = "non-existent"
				proc.Components[1].Type = "non-existent1"
			})

			It("should return error and stop processing", func() {
				err := components.PatchAllComponentToDeployment(fakeClient, ctx, proc, deploy)
				Expect(err).To(HaveOccurred())

				Expect(deploy.Spec.Template.Labels).To(BeEmpty())
			})
		})
	})
})
