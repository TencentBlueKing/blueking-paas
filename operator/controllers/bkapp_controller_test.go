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

package controllers

import (
	"bytes"
	"io"
	"net/http"
	"time"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"github.com/samber/lo"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/names"
	"bk.tencent.com/paas-app-operator/pkg/platform/external"
	"bk.tencent.com/paas-app-operator/pkg/testing"
	"bk.tencent.com/paas-app-operator/pkg/utils/kubestatus"
)

var _ = Describe("", func() {
	var bkapp *paasv1alpha2.BkApp
	var podCounter func() int
	var isSvcExists func(types.NamespacedName) bool

	const (
		timeout  = time.Second * 10
		interval = time.Millisecond * 250
	)

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
						Replicas:     paasv1alpha2.ReplicasOne,
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
				Addons:        []paasv1alpha2.Addon{{Name: "fake-addon"}},
			},
		}
		bkapp = testing.WithAppInfoAnnotations(bkapp)

		podCounter = func() int {
			pods := &corev1.PodList{}
			err := k8sClient.List(ctx, pods,
				client.InNamespace(bkapp.GetNamespace()),
				client.MatchingLabels{
					paasv1alpha2.ResourceTypeKey: "hook",
					paasv1alpha2.BkAppNameKey:    bkapp.GetName(),
				},
			)
			Expect(err).NotTo(HaveOccurred())
			return len(pods.Items)
		}
		isSvcExists = func(lookupKey types.NamespacedName) bool {
			err := k8sClient.Get(ctx, lookupKey, &corev1.Service{})
			return err == nil
		}
		external.SetDefaultClient(
			external.NewTestClient("", "", external.RoundTripFunc(func(req *http.Request) *http.Response {
				switch req.Method {
				case "GET":
					// 查询增强服务环境变量
					return &http.Response{
						StatusCode: 200,
						Body:       io.NopCloser(bytes.NewBufferString(`{"credentials": {"FAKE_FOO": "FOO"}}`)),
						Header:     make(http.Header),
					}
				case "POST":
					// 分配增强服务
					return &http.Response{
						StatusCode: 200,
						Body:       io.NopCloser(bytes.NewBufferString(`{"service_id": "foo-id"}`)),
						Header:     make(http.Header),
					}
				}
				return &http.Response{
					StatusCode: 400,
					Body:       io.NopCloser(bytes.NewBufferString(``)),
					Header:     make(http.Header),
				}
			})),
		)
	})

	It("Should Update Status.DeployID when a bkapp was created", func() {
		By("By creating a new bkapp")
		Expect(k8sClient.Create(ctx, bkapp)).NotTo(HaveOccurred())

		bkappLookupKey := client.ObjectKeyFromObject(bkapp)
		createdBkApp := &paasv1alpha2.BkApp{}

		// We'll need to retry getting this newly created BkApp, given that creation may not immediately happen.
		Eventually(func() bool {
			if err := k8sClient.Get(ctx, bkappLookupKey, createdBkApp); err != nil {
				return false
			}
			return createdBkApp.Status.DeployId != ""
		}, timeout, interval).Should(BeTrue())

		Expect(createdBkApp.Status.DeployId).To(Equal("0"))
		Expect(controllerutil.ContainsFinalizer(createdBkApp, paasv1alpha2.BkAppFinalizerName)).To(BeTrue())

		By("By checking the pre-release-hook pod is dispatched")
		preReleaseHook1LookupKey := types.NamespacedName{Namespace: "default", Name: "pre-rel-fake-app-0"}
		preReleaseHookPod := &corev1.Pod{}

		// We'll need to retry getting this newly created Pod, given that creation may not immediately happen.
		Eventually(func() bool {
			err := k8sClient.Get(ctx, preReleaseHook1LookupKey, preReleaseHookPod)
			if err != nil {
				return false
			}
			err = k8sClient.Get(ctx, bkappLookupKey, createdBkApp)
			return err == nil
		}, timeout, interval).Should(BeTrue())

		// Check status
		condAvailable := apimeta.FindStatusCondition(createdBkApp.Status.Conditions, paasv1alpha2.AppAvailable)
		Expect(condAvailable.Status).To(Equal(metav1.ConditionFalse))

		hookStatus := createdBkApp.Status.FindHookStatus(paasv1alpha2.HookPreRelease)
		condHooks := apimeta.FindStatusCondition(createdBkApp.Status.Conditions, paasv1alpha2.HooksFinished)
		Expect(condHooks.Reason).To(Equal("Progressing"))
		Expect(condHooks.Status).To(Equal(metav1.ConditionFalse))
		Expect(hookStatus.Phase).To(Equal(paasv1alpha2.HealthProgressing))

		// Check addons envs
		Expect(
			lo.Contains(preReleaseHookPod.Spec.Containers[0].Env, corev1.EnvVar{Name: "FAKE_FOO", Value: "FOO"}),
		).To(BeTrue())

		By("By update the pre-release-hook pod Status.Phase to Succeeded")
		preReleaseHookPod.Status.Phase = corev1.PodSucceeded
		Expect(k8sClient.Status().Update(ctx, preReleaseHookPod)).NotTo(HaveOccurred())

		// We'll need to retry getting this newly updated bkapp, given that each Reconcile loop will take a rest.
		Eventually(func() bool {
			err := k8sClient.Get(ctx, bkappLookupKey, createdBkApp)
			if err != nil {
				return false
			}
			condHooks := apimeta.FindStatusCondition(createdBkApp.Status.Conditions, paasv1alpha2.HooksFinished)
			return (condHooks.Status == metav1.ConditionTrue && condHooks.Reason == "Finished")
		}, timeout, interval).Should(BeTrue())

		By("By checking the processes is dispatched")
		deploymentLookupKey := types.NamespacedName{Namespace: "default", Name: names.Deployment(bkapp, "web")}
		createdDeployment := &appsv1.Deployment{}

		// We'll need to retry getting this newly created Deployment, given that creation may not immediately happen.
		Eventually(func() bool {
			err := k8sClient.Get(ctx, deploymentLookupKey, createdDeployment)
			if err != nil {
				return false
			}
			condProgressing := apimeta.FindStatusCondition(createdBkApp.Status.Conditions, paasv1alpha2.AppProgressing)
			return condProgressing.Status == metav1.ConditionTrue
		}, timeout, interval).Should(BeTrue())

		_ = k8sClient.Get(ctx, bkappLookupKey, createdBkApp)
		condAvailable = apimeta.FindStatusCondition(createdBkApp.Status.Conditions, paasv1alpha2.AppAvailable)
		Expect(condAvailable.Status).To(Equal(metav1.ConditionFalse))

		By(
			"update Condition(Available) and ObservedGeneration of deployment to make condition AppAvailable to be True",
			func() {
				_ = k8sClient.Get(ctx, deploymentLookupKey, createdDeployment)

				createdDeployment.Status.ObservedGeneration = createdDeployment.Generation
				createdDeployment.Status.Replicas = *createdDeployment.Spec.Replicas
				createdDeployment.Status.UpdatedReplicas = *createdDeployment.Spec.Replicas
				cond := kubestatus.FindDeploymentStatusCondition(
					createdDeployment.Status.Conditions,
					appsv1.DeploymentAvailable,
				)
				if cond == nil {
					createdDeployment.Status.Conditions = append(
						createdDeployment.Status.Conditions,
						appsv1.DeploymentCondition{
							Status: corev1.ConditionTrue,
							Type:   appsv1.DeploymentAvailable,
						},
					)
				} else {
					cond.Status = corev1.ConditionTrue
				}
				Expect(k8sClient.Status().Update(ctx, createdDeployment)).NotTo(HaveOccurred())
			},
		)

		By("check the AppAvailable Condition to be True", func() {
			Eventually(func() bool {
				err := k8sClient.Get(ctx, bkappLookupKey, createdBkApp)
				if err != nil {
					return false
				}
				condAvailable = apimeta.FindStatusCondition(createdBkApp.Status.Conditions, paasv1alpha2.AppAvailable)
				return condAvailable.Status == metav1.ConditionTrue &&
					createdBkApp.Status.Phase == paasv1alpha2.AppRunning
			}, timeout, interval*10).Should(BeTrue())
		})

		// service will be created after all processes available
		serviceLookupKey := types.NamespacedName{Namespace: "default", Name: names.Service(bkapp, "web")}
		By("By checking the service is created", func() {
			Eventually(func() bool {
				return isSvcExists(serviceLookupKey)
			}, timeout, interval).Should(BeTrue())
		})

		By("By update the Application.Spec and make a new Deploy")
		Eventually(func() error {
			err := k8sClient.Get(ctx, bkappLookupKey, createdBkApp)
			if err != nil {
				return err
			}
			createdBkApp.Annotations[paasv1alpha2.DeployIDAnnoKey] = "2"
			createdBkApp.Spec.Configuration.Env = append(
				createdBkApp.Spec.Configuration.Env,
				paasv1alpha2.AppEnvVar{Name: "foo"},
			)
			return k8sClient.Update(ctx, createdBkApp)
		}, timeout, interval).ShouldNot(HaveOccurred())

		// We'll need to retry getting this newly updated bkapp, given that update may not immediately happen.
		Eventually(func() bool {
			err := k8sClient.Get(ctx, bkappLookupKey, createdBkApp)
			if err != nil {
				return false
			}
			return createdBkApp.Status.DeployId == "2"
		}, timeout, interval).Should(BeTrue())

		condAvailable = apimeta.FindStatusCondition(createdBkApp.Status.Conditions, paasv1alpha2.AppAvailable)
		Expect(condAvailable.Status).To(Equal(metav1.ConditionUnknown))
		Expect(podCounter()).To(Equal(2))

		By("By update the pre-release-hook pod Status.Phase to Running to block the BkApp finalizer", func() {
			preReleaseHook1LookupKey.Name = "pre-rel-fake-app-2"
			Expect(k8sClient.Get(ctx, preReleaseHook1LookupKey, preReleaseHookPod)).NotTo(HaveOccurred())
			preReleaseHookPod.Status.Phase = corev1.PodRunning
			Expect(k8sClient.Status().Update(ctx, preReleaseHookPod)).NotTo(HaveOccurred())
		})

		// Stop Reconcile Loop by deleting, but the finalizer should be blocked because some hook not finished
		By("By delete the bkapp to finalizer the BkApp", func() {
			Expect(k8sClient.Delete(ctx, createdBkApp)).NotTo(HaveOccurred())
		})

		// Validate if the Finalizer is blocking
		Eventually(func() bool {
			err := k8sClient.Get(ctx, bkappLookupKey, createdBkApp)
			if err != nil {
				return false
			}
			cond := apimeta.FindStatusCondition(createdBkApp.Status.Conditions, paasv1alpha2.AppAvailable)
			if cond.Status == metav1.ConditionFalse && cond.Reason != "Terminating" {
				return false
			}
			return podCounter() == 2
		}, timeout, interval).Should(BeTrue())

		By("By update the pre-release-hook pod Status.Phase to Failed to unblock the BkApp finalizer", func() {
			preReleaseHookPod.Status.Phase = corev1.PodSucceeded
			Expect(k8sClient.Status().Update(ctx, preReleaseHookPod)).NotTo(HaveOccurred())
		})

		// We'll need to retry getting this existed pod and service, given that finalize may not immediately happen.
		Eventually(func() bool {
			return podCounter() == 0 && !isSvcExists(serviceLookupKey)
		}, timeout, interval).Should(BeTrue())
	})
})
