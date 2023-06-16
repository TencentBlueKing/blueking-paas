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

package resources

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"github.com/samber/lo"
	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"

	autoscaling "github.com/Tencent/bk-bcs/bcs-runtime/bcs-k8s/bcs-component/bcs-general-pod-autoscaler/pkg/apis/autoscaling/v1alpha1"
)

var _ = Describe("GPAResources", func() {
	var bkapp *paasv1alpha2.BkApp
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
				Processes: []paasv1alpha2.Process{
					{
						Name: "web",
						Autoscaling: &paasv1alpha2.AutoscalingSpec{
							Enabled:     true,
							MinReplicas: 1,
							MaxReplicas: 5,
							Policy:      paasv1alpha2.ScalingPolicyDefault,
						},
					},
					{
						Name: "hi",
						Autoscaling: &paasv1alpha2.AutoscalingSpec{
							Enabled: false,
						},
					},
				},
			},
		}

		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		Expect(paasv1alpha2.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(autoscaling.AddToScheme(scheme)).NotTo(HaveOccurred())
		builder.WithScheme(scheme)
	})

	Context("TestGenerateGPAs", func() {
		It("autoscaling disabled", func() {
			bkapp.Spec.Processes[0].Autoscaling.Enabled = false
			gpaList := GetWantedGPAs(bkapp)
			Expect(len(gpaList)).To(Equal(0))
		})

		It("autoscaling enabled", func() {
			gpaList := GetWantedGPAs(bkapp)
			Expect(len(gpaList)).To(Equal(1))

			webGPA := gpaList[0]
			Expect(webGPA.APIVersion).To(Equal("autoscaling.tkex.tencent.com/v1alpha1"))
			Expect(webGPA.Kind).To(Equal("GeneralPodAutoscaler"))
			Expect(webGPA.Name).To(Equal("bkapp-sample--web"))
			Expect(webGPA.Namespace).To(Equal(bkapp.Namespace))
			Expect(webGPA.Annotations).To(Equal(map[string]string{
				"bkapp.paas.bk.tencent.com/process-name": "web",
				"compute-by-limits":                      "true",
			}))
			Expect(webGPA.OwnerReferences[0].Kind).To(Equal(bkapp.Kind))
			Expect(webGPA.OwnerReferences[0].Name).To(Equal(bkapp.Name))
			// general-pod-autoscaler spec
			Expect(*webGPA.Spec.MinReplicas).To(Equal(int32(1)))
			Expect(webGPA.Spec.MaxReplicas).To(Equal(int32(5)))
			Expect(webGPA.Spec.ScaleTargetRef).To(Equal(
				autoscaling.CrossVersionObjectReference{
					APIVersion: "apps/v1",
					Kind:       "Deployment",
					Name:       "bkapp-sample--web",
				}),
			)
			Expect(*webGPA.Spec.MetricMode).To(Equal(
				autoscaling.MetricMode{
					Metrics: []autoscaling.MetricSpec{
						{
							Type: autoscaling.ResourceMetricSourceType,
							Resource: &autoscaling.ResourceMetricSource{
								Name: v1.ResourceCPU,
								Target: autoscaling.MetricTarget{
									Type:               autoscaling.UtilizationMetricType,
									AverageUtilization: lo.ToPtr(int32(85)),
								},
							},
						},
					},
				},
			))
		})
	})
})
