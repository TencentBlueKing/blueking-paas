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
	"time"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"github.com/onsi/gomega/types"
	"github.com/samber/lo"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	"bk.tencent.com/paas-app-operator/api/v1alpha1"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources"
)

var _ = Describe("Test HookReconciler", func() {
	var bkapp *v1alpha1.BkApp
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
						Name:       "web",
						Image:      "bar",
						Replicas:   v1alpha1.ReplicasTwo,
						TargetPort: 80,
						CPU:        "1",
						Memory:     "500Mi",
					},
				},
				Hooks: &v1alpha1.AppHooks{
					PreRelease: &v1alpha1.Hook{
						Command: []string{"/bin/bash"},
						Args:    []string{"-c", "echo foo;"},
					},
				},
				Configuration: v1alpha1.AppConfig{},
			},
			Status: v1alpha1.AppStatus{},
		}

		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		Expect(v1alpha1.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(appsv1.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(corev1.AddToScheme(scheme)).NotTo(HaveOccurred())
		builder.WithScheme(scheme)

		ctx = context.Background()
	})

	Describe("test Reconcile", func() {
		It("case with no hook", func() {
			bkapp.Spec.Hooks = nil
			r := HookReconciler{
				Client: builder.WithObjects(bkapp).Build(),
			}

			ret := r.Reconcile(context.Background(), bkapp)
			Expect(ret.err).NotTo(HaveOccurred())
			Expect(ret.endReconcile).To(BeFalse())
		})

		It("test execute hook", func() {
			bkapp.Status.HookStatuses = nil
			r := HookReconciler{
				Client: builder.WithObjects(bkapp).Build(),
			}

			ret := r.Reconcile(ctx, bkapp)
			Expect(ret.err).NotTo(HaveOccurred())
			Expect(ret.endReconcile).To(BeTrue())
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
				hookStatus := v1alpha1.HookStatus{
					Type:      v1alpha1.HookPreRelease,
					StartTime: lo.ToPtr(startTime),
				}
				bkapp.Status.SetHookStatus(hookStatus)

				hook := resources.BuildPreReleaseHook(bkapp, &hookStatus)
				hook.Pod.Status.Phase = phase
				r := HookReconciler{
					Client: builder.WithObjects(bkapp, hook.Pod).Build(),
				}

				ret := r.Reconcile(ctx, bkapp)
				Expect(ret.ShouldAbort()).To(Equal(shouldHangup))
				Expect(ret.duration).To(Equal(requeueAfter))
				Expect(ret.err).To(errMatcher)
			},
			Entry("pending", corev1.PodPending, metav1.Now(), true, v1alpha1.DefaultRequeueAfter, BeNil()),
			Entry("running", corev1.PodRunning, metav1.Now(), true, v1alpha1.DefaultRequeueAfter, BeNil()),
			Entry(
				"running timeout",
				corev1.PodRunning,
				metav1.NewTime(time.Now().Add(-resources.HookExecuteTimeoutThreshold)),
				true,
				time.Duration(0),
				HaveOccurred(),
			),
			Entry("success", corev1.PodSucceeded, metav1.Now(), false, time.Duration(0), BeNil()),
			Entry("failed", corev1.PodFailed, metav1.Now(), true, time.Duration(0), HaveOccurred()),
		)
	})

	Describe("test CheckAndUpdatePreReleaseHookStatus", func() {
		var r *HookReconciler

		BeforeEach(func() {
			r = &HookReconciler{
				Client: builder.Build(),
			}
		})

		It("Pod not found", func() {
			finished, err := CheckAndUpdatePreReleaseHookStatus(
				ctx,
				r.Client,
				bkapp,
				resources.HookExecuteTimeoutThreshold,
			)

			Expect(finished).To(BeFalse())
			Expect(err.Error()).To(Equal("pre-release-hook not found"))
		})

		It("Pod Execute Failed", func() {
			Expect(r.Create(ctx, bkapp)).To(BeNil())

			hook := resources.BuildPreReleaseHook(bkapp, nil)
			Expect(r.ExecuteHook(ctx, bkapp, hook)).To(BeNil())

			hook.Pod.Status.Phase = corev1.PodFailed
			hook.Pod.Status.Message = "fail message"
			_ = r.Status().Update(ctx, hook.Pod)

			finished, err := CheckAndUpdatePreReleaseHookStatus(
				ctx,
				r.Client,
				bkapp,
				resources.HookExecuteTimeoutThreshold,
			)

			Expect(finished).To(BeFalse())
			Expect(err.Error()).To(Equal("pod ends unsuccessfully: hook failed with: fail message"))
		})

		// UpdatePreReleaseHook creates app and Pod resource, return the result of "CheckAndUpdatePreReleaseHookStatus"
		// function. "podPhase" is the pre-release pod's status.
		updatePreReleaseHook := func(podPhase corev1.PodPhase, timeout time.Duration) (bool, error) {
			// Create related app and Pod resource
			if err := r.Create(ctx, bkapp); err != nil {
				panic(err)
			}

			hook := resources.BuildPreReleaseHook(bkapp, nil)
			if err := r.ExecuteHook(ctx, bkapp, hook); err != nil {
				panic(err)
			}

			hook.Pod.Status.Phase = podPhase
			hook.Pod.Status.StartTime = lo.ToPtr(metav1.Now())
			if err := r.Status().Update(ctx, hook.Pod); err != nil {
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

				condHooks := apimeta.FindStatusCondition(bkapp.Status.Conditions, v1alpha1.HooksFinished)
				Expect(condHooks.Status).To(Equal(conditionStatus))
			},
			Entry(
				"pending",
				corev1.PodPending,
				resources.HookExecuteTimeoutThreshold,
				false,
				false,
				metav1.ConditionFalse,
			),
			Entry(
				"running",
				corev1.PodRunning,
				resources.HookExecuteTimeoutThreshold,
				false,
				false,
				metav1.ConditionFalse,
			),
			Entry("running timeout", corev1.PodRunning, time.Duration(-1), false, true, metav1.ConditionFalse),
			Entry(
				"success",
				corev1.PodSucceeded,
				resources.HookExecuteTimeoutThreshold,
				true,
				false,
				metav1.ConditionTrue,
			),
		)

		It("Check succeeded Pod update status", func() {
			finished, err := updatePreReleaseHook(corev1.PodSucceeded, resources.HookExecuteTimeoutThreshold)

			Expect(finished).To(BeTrue())
			Expect(err).NotTo(HaveOccurred())

			hookStatus := bkapp.Status.FindHookStatus(v1alpha1.HookPreRelease)
			condHooks := apimeta.FindStatusCondition(bkapp.Status.Conditions, v1alpha1.HooksFinished)
			Expect(condHooks.Status).To(Equal(metav1.ConditionTrue))
			Expect(condHooks.Reason).To(Equal("Finished"))
			Expect(hookStatus.Status).To(Equal(v1alpha1.HealthHealthy))
		})
	})

	Describe("test getCurrentState", func() {
		It("Pod not found", func() {
			r := HookReconciler{
				Client: builder.Build(),
			}
			state := r.getCurrentState(ctx, bkapp)
			Expect(state.Pod).To(BeNil())
		})

		DescribeTable("find pod with different phases", func(
			phase corev1.PodPhase,
			timeoutThreshold time.Duration,
			executing, succeeded, failed, timeout bool,
		) {
			hook := resources.BuildPreReleaseHook(bkapp, nil)
			hook.Pod.Status.Phase = phase
			hook.Pod.Status.StartTime = lo.ToPtr(metav1.Now())
			bkapp.Status.SetHookStatus(v1alpha1.HookStatus{
				Type:      v1alpha1.HookPreRelease,
				StartTime: hook.Pod.Status.StartTime,
			})

			r := HookReconciler{
				Client: builder.WithObjects(bkapp, hook.Pod).Build(),
			}

			state := r.getCurrentState(ctx, bkapp)
			Expect(state.Progressing()).To(Equal(executing))
			Expect(state.Succeeded()).To(Equal(succeeded))
			Expect(state.Failed()).To(Equal(failed))
			Expect(state.Timeout(timeoutThreshold)).To(Equal(timeout))
		},
			Entry("pending", corev1.PodPending, resources.HookExecuteTimeoutThreshold, true, false, false, false),
			Entry("running", corev1.PodRunning, resources.HookExecuteTimeoutThreshold, true, false, false, false),
			Entry("running timeout", corev1.PodRunning, time.Duration(-1), true, false, false, true),
			Entry("success", corev1.PodSucceeded, resources.HookExecuteTimeoutThreshold, false, true, false, false),
			Entry("failed", corev1.PodFailed, resources.HookExecuteTimeoutThreshold, false, false, true, false),
		)
	})

	Describe("TestExecuteHook", func() {
		It("normal case", func() {
			r := HookReconciler{
				Client: builder.Build(),
			}
			Expect(r.Create(ctx, bkapp)).To(BeNil())
			hook := resources.BuildPreReleaseHook(bkapp, nil)

			err := r.ExecuteHook(ctx, bkapp, hook)
			Expect(err).NotTo(HaveOccurred())

			hookStatus := bkapp.Status.FindHookStatus(v1alpha1.HookPreRelease)
			condHooks := apimeta.FindStatusCondition(bkapp.Status.Conditions, v1alpha1.HooksFinished)
			Expect(condHooks.Status).To(Equal(metav1.ConditionFalse))
			Expect(hookStatus.Status).To(Equal(v1alpha1.HealthProgressing))
		})

		It("Pod Existed!", func() {
			hook := resources.BuildPreReleaseHook(bkapp, nil)
			r := HookReconciler{
				Client: builder.WithObjects(hook.Pod).Build(),
			}

			err := r.ExecuteHook(ctx, bkapp, hook)
			Expect(err).To(Equal(resources.ErrHookPodExists))
		})
	})
})
