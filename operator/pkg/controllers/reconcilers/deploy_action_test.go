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

var _ = Describe("Test DeployActionReconciler", func() {
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
				Generation: 2,
				Name:       "bkapp-sample",
				Namespace:  "default",
			},
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
				Hooks: &paasv1alpha2.AppHooks{
					PreRelease: &paasv1alpha2.Hook{},
				},
			},
		}

		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		Expect(paasv1alpha2.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(appsv1.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(corev1.AddToScheme(scheme)).NotTo(HaveOccurred())
		builder.WithScheme(scheme)
	})

	// A shortcut function to expect the deploy action has been initialized.
	expectDeployActionInitialized := func(ret Result, bkapp *paasv1alpha2.BkApp, deployID string) {
		Expect(ret.ShouldAbort()).To(BeFalse())
		Expect(bkapp.Status.Phase).To(Equal(paasv1alpha2.AppPending))
		Expect(bkapp.Status.DeployId).To(Equal(deployID))
	}
	// A shortcut function to expect the deploy action has been ignored.
	expectDeployActionIgnored := func(ret Result, bkapp *paasv1alpha2.BkApp, deployID string) {
		Expect(ret.ShouldAbort()).To(BeFalse())
		Expect(bkapp.Status.Phase).To(BeEmpty())
		Expect(bkapp.Status.DeployId).To(Equal(deployID))
	}

	Context("test Reconcile", func() {
		It("initial deploy action", func() {
			bkapp.SetAnnotations(map[string]string{paasv1alpha2.DeployIDAnnoKey: "1"})
			ret := NewDeployActionReconciler(builder.WithObjects(bkapp).Build()).Reconcile(context.Background(), bkapp)

			expectDeployActionInitialized(ret, bkapp, "1")
		})

		It("deploy ID changed", func() {
			bkapp.SetAnnotations(map[string]string{paasv1alpha2.DeployIDAnnoKey: "2"})
			bkapp.Status.DeployId = "1"
			ret := NewDeployActionReconciler(builder.WithObjects(bkapp).Build()).Reconcile(context.Background(), bkapp)

			expectDeployActionInitialized(ret, bkapp, "2")
		})

		It("deploy ID unchanged", func() {
			bkapp.SetAnnotations(map[string]string{paasv1alpha2.DeployIDAnnoKey: "1"})
			bkapp.Status.DeployId = "1"
			ret := NewDeployActionReconciler(builder.WithObjects(bkapp).Build()).Reconcile(context.Background(), bkapp)

			expectDeployActionIgnored(ret, bkapp, "1")
		})

		It("deploy ID changed but observedGeneration is not behind", func() {
			bkapp.SetAnnotations(map[string]string{paasv1alpha2.DeployIDAnnoKey: "2"})
			bkapp.Status.DeployId = "1"
			bkapp.Status.ObservedGeneration = 2
			ret := NewDeployActionReconciler(builder.WithObjects(bkapp).Build()).Reconcile(context.Background(), bkapp)

			expectDeployActionIgnored(ret, bkapp, "1")
		})

		It("deploy ID changed with finished hook", func() {
			bkapp.SetAnnotations(map[string]string{paasv1alpha2.DeployIDAnnoKey: "2"})
			bkapp.Status.DeployId = "1"
			bkapp.Status.SetHookStatus(paasv1alpha2.HookStatus{
				Type:      paasv1alpha2.HookPreRelease,
				Phase:     paasv1alpha2.HealthHealthy,
				StartTime: lo.ToPtr(metav1.Now()),
			})
			ret := NewDeployActionReconciler(builder.WithObjects(bkapp).Build()).Reconcile(context.Background(), bkapp)

			expectDeployActionInitialized(ret, bkapp, "2")
		})

		It("deploy ID changed with failed hook", func() {
			bkapp.SetAnnotations(map[string]string{paasv1alpha2.DeployIDAnnoKey: "2"})
			bkapp.Status.DeployId = "1"
			bkapp.Status.SetHookStatus(paasv1alpha2.HookStatus{
				Type:      paasv1alpha2.HookPreRelease,
				Phase:     paasv1alpha2.HealthUnhealthy,
				StartTime: lo.ToPtr(metav1.Now()),
			})
			hook := resources.BuildPreReleaseHook(
				bkapp, bkapp.Status.FindHookStatus(paasv1alpha2.HookPreRelease),
			)

			client := builder.WithObjects(bkapp, hook.Pod).Build()
			ret := NewDeployActionReconciler(client).Reconcile(context.Background(), bkapp)

			expectDeployActionInitialized(ret, bkapp, "2")
		})

		It("deploy ID changed with running hook", func() {
			bkapp.SetAnnotations(map[string]string{paasv1alpha2.DeployIDAnnoKey: "2"})
			bkapp.Status.DeployId = "1"
			bkapp.Status.SetHookStatus(paasv1alpha2.HookStatus{
				Type:      paasv1alpha2.HookPreRelease,
				Phase:     paasv1alpha2.HealthProgressing,
				StartTime: lo.ToPtr(metav1.Now()),
			})

			hook := resources.BuildPreReleaseHook(bkapp, bkapp.Status.FindHookStatus(paasv1alpha2.HookPreRelease))
			Expect(hook.Pod).NotTo(BeNil())

			client := builder.WithObjects(bkapp, hook.Pod).Build()
			ret := NewDeployActionReconciler(client).Reconcile(context.Background(), bkapp)

			Expect(ret.ShouldAbort()).To(BeTrue())
			Expect(ret.err).To(HaveOccurred())
			// The phase is failed because the hook's pod is failed.
			Expect(bkapp.Status.Phase).To(Equal(paasv1alpha2.AppFailed))
			Expect(bkapp.Status.DeployId).To(Equal("1"))
		})
	})
})
