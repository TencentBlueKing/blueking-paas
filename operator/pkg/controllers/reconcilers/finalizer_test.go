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
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	networkingv1 "k8s.io/api/networking/v1"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"

	"bk.tencent.com/paas-app-operator/api/v1alpha1"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/names"
)

var _ = Describe("Test BkappFinalizer", func() {
	var bkapp *v1alpha1.BkApp
	var pod *corev1.Pod
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
			},
		}

		pod = &corev1.Pod{
			TypeMeta: metav1.TypeMeta{
				Kind:       "Pod",
				APIVersion: "v1",
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      names.PreReleaseHook(bkapp),
				Namespace: bkapp.Namespace,
				Labels: map[string]string{
					v1alpha1.BkAppNameKey:    bkapp.GetName(),
					v1alpha1.ResourceTypeKey: "hook",
					v1alpha1.HookTypeKey:     "pre-release",
				},
				OwnerReferences: []metav1.OwnerReference{
					*metav1.NewControllerRef(bkapp, schema.GroupVersionKind{
						Group:   v1alpha1.GroupVersion.Group,
						Version: v1alpha1.GroupVersion.Version,
						Kind:    v1alpha1.KindBkApp,
					}),
				},
			},
		}

		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		_ = v1alpha1.AddToScheme(scheme)
		_ = appsv1.AddToScheme(scheme)
		_ = corev1.AddToScheme(scheme)
		_ = networkingv1.AddToScheme(scheme)
		builder.WithScheme(scheme)
	})

	Context("test hooksFinished", func() {
		It("no any pods", func() {
			r := NewBkappFinalizer(builder.Build())
			finished, err := r.hooksFinished(context.Background(), bkapp)

			Expect(err).NotTo(HaveOccurred())
			Expect(finished).To(BeTrue())
		})

		It("no any running pods", func() {
			pod.Status.Phase = corev1.PodSucceeded
			r := NewBkappFinalizer(builder.WithObjects(pod).Build())

			finished, err := r.hooksFinished(context.Background(), bkapp)

			Expect(err).NotTo(HaveOccurred())
			Expect(finished).To(BeTrue())
		})

		It("with running pods", func() {
			pod.Status.Phase = corev1.PodRunning
			r := NewBkappFinalizer(builder.WithObjects(pod).Build())

			finished, err := r.hooksFinished(context.Background(), bkapp)

			Expect(err).NotTo(HaveOccurred())
			Expect(finished).To(BeFalse())
		})
	})

	Context("test Reconcile", func() {
		BeforeEach(func() {
			controllerutil.AddFinalizer(bkapp, v1alpha1.BkAppFinalizerName)
			deletionTimestamp := metav1.Now()
			bkapp.DeletionTimestamp = &deletionTimestamp
		})

		It("test normal", func() {
			r := NewBkappFinalizer(builder.WithObjects(bkapp).Build())

			ret := r.Reconcile(context.Background(), bkapp)

			Expect(ret.err).NotTo(HaveOccurred())
			Expect(r.Reconcile(context.Background(), bkapp).ShouldAbort()).To(BeFalse())
			Expect(controllerutil.ContainsFinalizer(bkapp, v1alpha1.BkAppFinalizerName)).To(BeFalse())
		})

		It("test be blocked", func() {
			pod.Status.Phase = corev1.PodRunning
			r := NewBkappFinalizer(builder.WithObjects(bkapp, pod).Build())

			ret := r.Reconcile(context.Background(), bkapp)

			Expect(ret.err).NotTo(HaveOccurred())
			Expect(r.Reconcile(context.Background(), bkapp).ShouldAbort()).To(BeTrue())
			Expect(controllerutil.ContainsFinalizer(bkapp, v1alpha1.BkAppFinalizerName)).To(BeTrue())

			cond := apimeta.FindStatusCondition(bkapp.Status.Conditions, v1alpha1.AppAvailable)
			Expect(cond.Reason).To(Equal("Terminating"))
		})
	})
})
