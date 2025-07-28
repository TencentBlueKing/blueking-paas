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

// Package hooks ...
package hooks

import (
	"context"
	"strconv"
	"time"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"github.com/onsi/gomega/types"
	"github.com/pkg/errors"
	"github.com/samber/lo"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/labels"
	hookres "bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/hooks/resources"
)

var _ = Describe("Test HookReconciler", func() {
	var bkapp *paasv1alpha2.BkApp
	var builder *fake.ClientBuilder
	var scheme *runtime.Scheme
	var ctx context.Context

	BeforeEach(func() {
		bkapp = &paasv1alpha2.BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       paasv1alpha2.KindBkApp,
				APIVersion: "paas.bk.tencent.com/v1alpha2",
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:        "fake-app",
				Namespace:   "default",
				Annotations: map[string]string{},
			},
			Spec: paasv1alpha2.AppSpec{
				Build: paasv1alpha2.BuildConfig{
					Image: "bar",
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
					PreRelease: &paasv1alpha2.Hook{
						Command: []string{"/bin/bash"},
						Args:    []string{"-c", "echo foo;"},
					},
				},
				Configuration: paasv1alpha2.AppConfig{},
			},
			Status: paasv1alpha2.AppStatus{},
		}

		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		Expect(paasv1alpha2.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(appsv1.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(corev1.AddToScheme(scheme)).NotTo(HaveOccurred())
		builder.WithScheme(scheme)

		ctx = context.Background()
	})

	Describe("test Reconcile", func() {
		It("case with no hook", func() {
			bkapp.Spec.Hooks = nil
			r := NewHookReconciler(builder.WithObjects(bkapp).Build())

			ret := r.Reconcile(context.Background(), bkapp)
			Expect(ret.Error()).NotTo(HaveOccurred())
			Expect(ret.IsFinished).To(BeFalse())
		})

		It("test execute hook", func() {
			bkapp.Status.HookStatuses = nil
			r := NewHookReconciler(builder.WithObjects(bkapp).Build())

			ret := r.Reconcile(ctx, bkapp)
			Expect(ret.Error()).NotTo(HaveOccurred())
			Expect(ret.IsFinished).To(BeTrue())
		})

		DescribeTable(
			"test with different phase",
			func(
				phase corev1.PodPhase,
				startTime metav1.Time,
				shouldHangup bool,
				requeueAfter time.Duration,
				errMatcher types.GomegaMatcher,
			) {
				hookStatus := paasv1alpha2.HookStatus{
					Type:      paasv1alpha2.HookPreRelease,
					StartTime: lo.ToPtr(startTime),
				}
				bkapp.Status.SetHookStatus(hookStatus)

				hook, err := hookres.BuildPreReleaseHook(bkapp, &hookStatus)
				Expect(err).To(BeNil())

				hook.Pod.Status.Phase = phase
				hook.Pod.SetCreationTimestamp(startTime)
				r := NewHookReconciler(builder.WithObjects(bkapp, hook.Pod).Build())

				ret := r.Reconcile(ctx, bkapp)
				Expect(ret.ShouldAbort()).To(Equal(shouldHangup))
				Expect(ret.Duration()).To(Equal(requeueAfter))
				Expect(ret.Error()).To(errMatcher)
			},
			Entry("pending", corev1.PodPending, metav1.Now(), true, hookres.HookExecuteTimeoutThreshold, BeNil()),
			Entry("running", corev1.PodRunning, metav1.Now(), true, hookres.HookExecuteTimeoutThreshold, BeNil()),
			Entry(
				"running timeout",
				corev1.PodRunning,
				metav1.NewTime(time.Now().Add(-hookres.HookExecuteTimeoutThreshold)),
				true,
				time.Duration(0),
				BeNil(),
			),
			Entry("success", corev1.PodSucceeded, metav1.Now(), false, time.Duration(0), BeNil()),
			Entry("failed", corev1.PodFailed, metav1.Now(), true, time.Duration(0), HaveOccurred()),
			Entry(
				"failed timeout",
				corev1.PodFailed,
				metav1.NewTime(time.Now().Add(-hookres.HookExecuteFailedTimeoutThreshold)),
				true,
				time.Duration(0),
				BeNil(),
			),
		)
	})

	Describe("test CheckAndUpdatePreReleaseHookStatus", func() {
		var r *HookReconciler

		BeforeEach(func() {
			r = NewHookReconciler(builder.Build())
		})

		It("Pod not found", func() {
			finished, err := CheckAndUpdatePreReleaseHookStatus(
				ctx,
				r.Client,
				bkapp,
				hookres.HookExecuteTimeoutThreshold,
			)

			Expect(finished).To(BeFalse())
			Expect(
				err.Error(),
			).To(Equal("hook failed with: PreReleaseHook not found: pod ends unsuccessfully"))
		})

		It("Pod Execute Failed", func() {
			Expect(r.Client.Create(ctx, bkapp)).To(BeNil())

			hook, err := hookres.BuildPreReleaseHook(bkapp, nil)
			Expect(err).To(BeNil())
			Expect(r.ExecuteHook(ctx, bkapp, hook)).To(BeNil())

			hook.Pod.Status.Phase = corev1.PodFailed
			hook.Pod.Status.Message = "fail message"
			_ = r.Client.Status().Update(ctx, hook.Pod)

			finished, err := CheckAndUpdatePreReleaseHookStatus(
				ctx,
				r.Client,
				bkapp,
				hookres.HookExecuteTimeoutThreshold,
			)

			Expect(finished).To(BeFalse())
			Expect(err.Error()).To(Equal("hook failed with: fail message: pod ends unsuccessfully"))
		})

		// UpdatePreReleaseHook creates app and Pod resource, return the result of "CheckAndUpdatePreReleaseHookStatus"
		// function. "podPhase" is the pre-release pod's status.
		updatePreReleaseHook := func(podPhase corev1.PodPhase, timeout time.Duration) (bool, error) {
			// Create related app and Pod resource
			if err := r.Client.Create(ctx, bkapp); err != nil {
				panic(err)
			}

			hook, err := hookres.BuildPreReleaseHook(bkapp, nil)
			Expect(err).To(BeNil())

			if err := r.ExecuteHook(ctx, bkapp, hook); err != nil {
				panic(err)
			}

			hook.Pod.Status.Phase = podPhase
			hook.Pod.Status.StartTime = lo.ToPtr(metav1.Now())
			hook.Pod.SetCreationTimestamp(*hook.Pod.Status.StartTime)

			if err := r.Client.Status().Update(ctx, hook.Pod); err != nil {
				panic(err)
			}

			return CheckAndUpdatePreReleaseHookStatus(ctx, r.Client, bkapp, timeout)
		}

		DescribeTable(
			"Different phases",
			func(
				phase corev1.PodPhase,
				timeout time.Duration,
				wantFinished bool,
				hasError bool,
				conditionStatus metav1.ConditionStatus,
			) {
				finished, err := updatePreReleaseHook(phase, timeout)

				Expect(finished).To(Equal(wantFinished))
				if hasError {
					Expect(err).To(HaveOccurred())
				} else {
					Expect(err).NotTo(HaveOccurred())
				}

				condHooks := apimeta.FindStatusCondition(bkapp.Status.Conditions, paasv1alpha2.HooksFinished)
				Expect(condHooks.Status).To(Equal(conditionStatus))
			},
			Entry(
				"pending",
				corev1.PodPending,
				hookres.HookExecuteTimeoutThreshold,
				false,
				false,
				metav1.ConditionFalse,
			),
			Entry(
				"running",
				corev1.PodRunning,
				hookres.HookExecuteTimeoutThreshold,
				false,
				false,
				metav1.ConditionFalse,
			),
			Entry(
				"running timeout",
				corev1.PodRunning,
				time.Duration(-1),
				false,
				true,
				metav1.ConditionFalse,
			),
			Entry(
				"success",
				corev1.PodSucceeded,
				hookres.HookExecuteTimeoutThreshold,
				true,
				false,
				metav1.ConditionTrue,
			),
		)

		It("Check succeeded Pod update status", func() {
			finished, err := updatePreReleaseHook(corev1.PodSucceeded, hookres.HookExecuteTimeoutThreshold)

			Expect(finished).To(BeTrue())
			Expect(err).NotTo(HaveOccurred())

			hookStatus := bkapp.Status.FindHookStatus(paasv1alpha2.HookPreRelease)
			condHooks := apimeta.FindStatusCondition(bkapp.Status.Conditions, paasv1alpha2.HooksFinished)
			Expect(condHooks.Status).To(Equal(metav1.ConditionTrue))
			Expect(condHooks.Reason).To(Equal("Finished"))
			Expect(hookStatus.Phase).To(Equal(paasv1alpha2.HealthHealthy))
		})
	})

	Describe("test getCurrentState", func() {
		It("Pod not found", func() {
			r := NewHookReconciler(builder.Build())
			state := r.getCurrentState(ctx, bkapp)
			Expect(state.Pod).To(BeNil())
		})

		DescribeTable("find pod with different phases", func(
			phase corev1.PodPhase,
			timeoutThreshold time.Duration,
			executing, succeeded, failed, timeout bool,
		) {
			hook, err := hookres.BuildPreReleaseHook(bkapp, nil)
			Expect(err).To(BeNil())

			hook.Pod.Status.Phase = phase
			hook.Pod.Status.StartTime = lo.ToPtr(metav1.Now())
			hook.Pod.SetCreationTimestamp(*hook.Pod.Status.StartTime)
			bkapp.Status.SetHookStatus(paasv1alpha2.HookStatus{
				Type:      paasv1alpha2.HookPreRelease,
				StartTime: hook.Pod.Status.StartTime,
			})

			r := NewHookReconciler(builder.WithObjects(bkapp, hook.Pod).Build())

			state := r.getCurrentState(ctx, bkapp)
			Expect(state.Progressing()).To(Equal(executing))
			Expect(state.Succeeded()).To(Equal(succeeded))
			Expect(state.Failed()).To(Equal(failed))
			Expect(state.TimeoutExceededProgressing(timeoutThreshold)).To(Equal(timeout))
		},
			Entry("pending", corev1.PodPending, hookres.HookExecuteTimeoutThreshold, true, false, false, false),
			Entry("running", corev1.PodRunning, hookres.HookExecuteTimeoutThreshold, true, false, false, false),
			Entry("running timeout", corev1.PodRunning, time.Duration(-1), true, false, false, true),
			Entry("success", corev1.PodSucceeded, hookres.HookExecuteTimeoutThreshold, false, true, false, false),
			Entry("failed", corev1.PodFailed, hookres.HookExecuteTimeoutThreshold, false, false, true, false),
		)
	})

	Describe("TestExecuteHook", func() {
		It("normal case", func() {
			r := NewHookReconciler(builder.Build())

			Expect(r.Client.Create(ctx, bkapp)).To(BeNil())
			hook, err := hookres.BuildPreReleaseHook(bkapp, nil)
			Expect(err).To(BeNil())

			err = r.ExecuteHook(ctx, bkapp, hook)
			Expect(err).NotTo(HaveOccurred())

			hookStatus := bkapp.Status.FindHookStatus(paasv1alpha2.HookPreRelease)
			condHooks := apimeta.FindStatusCondition(bkapp.Status.Conditions, paasv1alpha2.HooksFinished)
			Expect(condHooks.Status).To(Equal(metav1.ConditionFalse))
			Expect(hookStatus.Phase).To(Equal(paasv1alpha2.HealthProgressing))
		})

		It("Pod Existed!", func() {
			hook, err := hookres.BuildPreReleaseHook(bkapp, nil)
			Expect(err).To(BeNil())

			r := NewHookReconciler(builder.WithObjects(hook.Pod).Build())

			err = r.ExecuteHook(ctx, bkapp, hook)
			Expect(errors.Is(err, hookres.ErrHookPodExists)).To(BeTrue())
		})
	})

	Describe("test cleanupFinishedHooks", func() {
		It("test clean pre-release hooks", func() {
			r := NewHookReconciler(builder.Build())
			Expect(r.Client.Create(ctx, bkapp)).To(BeNil())

			createdHookPodNames := []string{}
			for i := 0; i < 5; i++ {
				bkapp.Status.DeployId = strconv.FormatInt(int64(i), 10)
				hook, err := hookres.BuildPreReleaseHook(bkapp, nil)
				Expect(err).To(BeNil())

				err = r.ExecuteHook(ctx, bkapp, hook)
				Expect(err).NotTo(HaveOccurred())

				createdHookPodNames = append(createdHookPodNames, hook.Pod.Name)
			}

			getHookPodNames := func(bkapp *paasv1alpha2.BkApp, hookType paasv1alpha2.HookType) []string {
				podList := &corev1.PodList{}
				err := r.Client.List(
					ctx,
					podList,
					client.InNamespace(bkapp.Namespace),
					client.MatchingLabels(labels.HookPodSelector(bkapp, hookType)),
				)
				if err != nil {
					return []string{}
				}
				podNames := []string{}
				for _, pod := range podList.Items {
					podNames = append(podNames, pod.Name)
				}
				return podNames
			}

			podNames := getHookPodNames(bkapp, paasv1alpha2.HookPreRelease)
			Expect(len(podNames)).To(Equal(5))
			Expect(podNames).To(Equal(createdHookPodNames))

			// 注：CreationTimestamp 只读 + fakeClient 不会设置 CreationTimestamp，因此其实算是按名字清理
			Expect(r.cleanupFinishedHooks(ctx, bkapp, paasv1alpha2.HookPreRelease)).To(BeNil())

			podNames = getHookPodNames(bkapp, paasv1alpha2.HookPreRelease)
			Expect(len(podNames)).To(Equal(3))
			Expect(podNames).To(Equal(createdHookPodNames[2:]))
		})
	})
})
