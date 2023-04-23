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
	v1 "k8s.io/api/core/v1"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	"bk.tencent.com/paas-app-operator/api/v1alpha1"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/names"

	autoscaling "github.com/Tencent/bk-bcs/bcs-runtime/bcs-k8s/bcs-component/bcs-general-pod-autoscaler/pkg/apis/autoscaling/v1alpha1"
)

var _ = Describe("Test AutoscalingReconciler", func() {
	var bkapp *v1alpha1.BkApp
	var fakeGPA *autoscaling.GeneralPodAutoscaler
	var builder *fake.ClientBuilder
	var scheme *runtime.Scheme
	var ctx context.Context

	BeforeEach(func() {
		bkapp = &v1alpha1.BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       v1alpha1.KindBkApp,
				APIVersion: "paas.bk.tencent.com/v1alpha1",
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      "fake-app",
				Namespace: "default",
			},
			Spec: v1alpha1.AppSpec{
				Processes: []v1alpha1.Process{
					{
						Name: "web",
						Autoscaling: &v1alpha1.AutoscalingSpec{
							Enabled:     true,
							MinReplicas: 2,
							MaxReplicas: 5,
							Policy:      lo.ToPtr(v1alpha1.ScalingPolicyDefault),
						},
					},
				},
			},
		}

		fakeGPA = &autoscaling.GeneralPodAutoscaler{
			TypeMeta: metav1.TypeMeta{
				Kind:       "GeneralPodAutoscaler",
				APIVersion: "autoscaling.k8s.io/v1alpha1",
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      "fake-gpa",
				Namespace: "default",
			},
			Spec: autoscaling.GeneralPodAutoscalerSpec{
				ScaleTargetRef: autoscaling.CrossVersionObjectReference{
					APIVersion: "apps/v1",
					Kind:       "Deployment",
					Name:       names.Deployment(bkapp, "fake"),
				},
			},
			Status: autoscaling.GeneralPodAutoscalerStatus{
				Conditions: []autoscaling.GeneralPodAutoscalerCondition{},
			},
		}

		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		Expect(v1alpha1.AddToScheme(scheme)).To(BeNil())
		Expect(autoscaling.AddToScheme(scheme)).To(BeNil())
		builder.WithScheme(scheme)
		ctx = context.Background()
	})

	Describe("test Reconcile", func() {
		It("case with autoscaling", func() {
			client := builder.WithObjects(bkapp, fakeGPA).Build()
			r := NewAutoscalingReconciler(client)
			ret := r.Reconcile(ctx, bkapp)
			Expect(ret.err).To(BeNil())
			Expect(ret.endReconcile).To(BeFalse())
		})

		It("case with no autoscaling", func() {
			bkapp.Spec.Processes[0].Autoscaling = nil

			client := builder.WithObjects(bkapp, fakeGPA).Build()
			r := NewAutoscalingReconciler(client)
			ret := r.Reconcile(ctx, bkapp)
			Expect(ret.err).To(BeNil())
			Expect(ret.endReconcile).To(BeFalse())
		})
	})

	Describe("test getCurrentState", func() {
		It("gpa not exists", func() {
			client := builder.WithObjects(bkapp).Build()
			r := NewAutoscalingReconciler(client)
			gpaList, err := r.getCurrentState(ctx, bkapp)
			Expect(err).To(BeNil())
			Expect(len(gpaList)).To(Equal(0))
		})

		It("gpa exists", func() {
			client := builder.WithObjects(bkapp, fakeGPA).Build()
			r := NewAutoscalingReconciler(client)
			gpaList, err := r.getCurrentState(ctx, bkapp)
			Expect(err).To(BeNil())
			Expect(len(gpaList)).To(Equal(1))
		})
	})
	//
	Describe("test updateCondition", func() {
		It("gpa not exists", func() {
			client := builder.WithObjects(bkapp).Build()
			r := NewAutoscalingReconciler(client)
			err := r.updateCondition(ctx, bkapp)
			Expect(err).To(BeNil())
			cond := apimeta.FindStatusCondition(bkapp.Status.Conditions, v1alpha1.AutoscalingAvailable)
			Expect(cond.Status).To(Equal(metav1.ConditionUnknown))
			Expect(cond.Reason).To(Equal("Disabled"))
		})

		It("gpa error", func() {
			fakeGPA.Status.Conditions = []autoscaling.GeneralPodAutoscalerCondition{{
				Type:    autoscaling.ScalingActive,
				Status:  v1.ConditionFalse,
				Reason:  "FailedGetResourceMetric",
				Message: "the GPA was unable to compute the replica count: unable to get metrics for resource cpu.",
			}}
			client := builder.WithObjects(bkapp, fakeGPA).Build()
			r := NewAutoscalingReconciler(client)
			err := r.updateCondition(ctx, bkapp)
			Expect(err).To(BeNil())
			cond := apimeta.FindStatusCondition(bkapp.Status.Conditions, v1alpha1.AutoscalingAvailable)
			Expect(cond.Status).To(Equal(metav1.ConditionFalse))
			Expect(cond.Reason).To(Equal("AutoscalerFailure"))
		})

		It("gpa ready", func() {
			fakeGPA.Status.Conditions = []autoscaling.GeneralPodAutoscalerCondition{{
				Type:    autoscaling.ScalingActive,
				Status:  v1.ConditionTrue,
				Reason:  "ValidMetricFound",
				Message: "the GPA was able to successfully calculate a replica count from.",
			}}
			client := builder.WithObjects(bkapp, fakeGPA).Build()
			r := NewAutoscalingReconciler(client)
			err := r.updateCondition(ctx, bkapp)
			Expect(err).To(BeNil())
			cond := apimeta.FindStatusCondition(bkapp.Status.Conditions, v1alpha1.AutoscalingAvailable)
			Expect(cond.Status).To(Equal(metav1.ConditionTrue))
			Expect(cond.Reason).To(Equal("AutoscalingAvailable"))
		})
	})
})
