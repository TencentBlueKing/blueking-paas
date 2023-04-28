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

package kubestatus

import (
	"bk.tencent.com/paas-app-operator/api/v1alpha2"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"github.com/samber/lo"
	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	autoscaling "github.com/Tencent/bk-bcs/bcs-runtime/bcs-k8s/bcs-component/bcs-general-pod-autoscaler/pkg/apis/autoscaling/v1alpha1"
)

var _ = Describe("Test kubestatus/gpa", func() {
	var gpa *autoscaling.GeneralPodAutoscaler
	var builder *fake.ClientBuilder
	var scheme *runtime.Scheme

	BeforeEach(func() {
		gpa = &autoscaling.GeneralPodAutoscaler{
			TypeMeta: metav1.TypeMeta{
				APIVersion: "autoscaling.tkex.tencent.com/v1alpha1",
				Kind:       "GeneralPodAutoscaler",
			},
			ObjectMeta: metav1.ObjectMeta{
				Name: "default-web-gpa",
			},
			Spec: autoscaling.GeneralPodAutoscalerSpec{
				MinReplicas: lo.ToPtr(int32(2)),
				MaxReplicas: int32(5),
				ScaleTargetRef: autoscaling.CrossVersionObjectReference{
					APIVersion: "apps/v1",
					Kind:       "Deployment",
					Name:       "default-web",
				},
				AutoScalingDrivenMode: autoscaling.AutoScalingDrivenMode{
					MetricMode: &autoscaling.MetricMode{
						Metrics: []autoscaling.MetricSpec{},
					},
				},
			},
		}

		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		Expect(autoscaling.AddToScheme(scheme)).NotTo(HaveOccurred())
		builder.WithScheme(scheme)
	})

	Context("test GenGPAHealthStatus", func() {
		It("test healthy", func() {
			gpa.Status.Conditions = []autoscaling.GeneralPodAutoscalerCondition{
				{
					Type:    autoscaling.AbleToScale,
					Status:  v1.ConditionTrue,
					Reason:  "ReadyForNewScale",
					Message: "recommended size matches current size.",
				},
				{
					Type:    autoscaling.ScalingActive,
					Status:  v1.ConditionTrue,
					Reason:  "ValidMetricFound",
					Message: "the GPA was able to successfully calculate a replica count from.",
				},
			}
			status := GenGPAHealthStatus(gpa)
			Expect(status.Phase).To(Equal(v1alpha2.HealthHealthy))
			Expect(status.Reason).To(Equal("AutoscalingAvailable"))
		})
		It("test ScalingActive unhealthy", func() {
			gpa.Status.Conditions = []autoscaling.GeneralPodAutoscalerCondition{
				{
					Type:    autoscaling.AbleToScale,
					Status:  v1.ConditionTrue,
					Reason:  "ReadyForNewScale",
					Message: "recommended size matches current size.",
				},
				{
					Type:    autoscaling.ScalingActive,
					Status:  v1.ConditionFalse,
					Reason:  "FailedGetResourceMetric",
					Message: "the GPA was unable to compute the replica count: unable to get metrics for resource cpu.",
				},
			}
			status := GenGPAHealthStatus(gpa)
			Expect(status.Phase).To(Equal(v1alpha2.HealthUnhealthy))
			Expect(status.Reason).To(Equal("FailedGetResourceMetric"))
		})
		It("test AbleToScale unhealthy", func() {
			gpa.Status.Conditions = []autoscaling.GeneralPodAutoscalerCondition{
				{
					Type:   autoscaling.AbleToScale,
					Status: v1.ConditionFalse,
					Reason: "FailedGetScale",
				},
				{
					Type:    autoscaling.ScalingActive,
					Status:  v1.ConditionTrue,
					Reason:  "ValidMetricFound",
					Message: "the GPA was able to successfully calculate a replica count from.",
				},
			}
			status := GenGPAHealthStatus(gpa)
			Expect(status.Phase).To(Equal(v1alpha2.HealthUnhealthy))
			Expect(status.Reason).To(Equal("FailedGetScale"))
		})
	})
})
