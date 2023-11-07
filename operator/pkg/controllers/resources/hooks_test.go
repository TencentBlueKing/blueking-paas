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
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/config"
)

var _ = Describe("HookUtils", func() {
	var bkapp *paasv1alpha2.BkApp
	var builder *fake.ClientBuilder
	var scheme *runtime.Scheme

	BeforeEach(func() {
		bkapp = &paasv1alpha2.BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       paasv1alpha2.KindBkApp,
				APIVersion: "paas.bk.tencent.com/v1alpha2",
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      "fake-app",
				Namespace: "default",
				Annotations: map[string]string{
					paasv1alpha2.ImageCredentialsRefAnnoKey: "image-pull-secrets",
				},
			},
			Spec: paasv1alpha2.AppSpec{
				Build: paasv1alpha2.BuildConfig{
					Image: "bar",
				},
				Processes: []paasv1alpha2.Process{
					{
						Name:         "web",
						Replicas:     paasv1alpha2.ReplicasOne,
						TargetPort:   80,
						ResQuotaPlan: paasv1alpha2.ResQuotaPlanDefault,
					},
				},
				Hooks: &paasv1alpha2.AppHooks{
					PreRelease: &paasv1alpha2.Hook{
						Command: []string{"/bin/bash"},
						Args:    []string{"-c", "echo foo $VAR_1;"},
					},
				},
				Configuration: paasv1alpha2.AppConfig{},
			},
		}

		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		Expect(paasv1alpha2.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(corev1.AddToScheme(scheme)).NotTo(HaveOccurred())
		builder.WithScheme(scheme)
	})

	Describe("TestParsePreReleaseHook", func() {
		It("no hooks", func() {
			bkapp.Spec.Hooks = nil
			hook := BuildPreReleaseHook(bkapp, nil)
			Expect(hook).To(BeNil())
		})

		It("no pre-release-hook", func() {
			bkapp.Spec.Hooks.PreRelease = nil
			hook := BuildPreReleaseHook(bkapp, nil)
			Expect(hook).To(BeNil())
		})

		It("normal case", func() {
			hook := BuildPreReleaseHook(bkapp, nil)

			Expect(hook.Pod.ObjectMeta.Name).To(Equal("pre-rel-fake-app-1"))
			Expect(hook.Pod.ObjectMeta.Labels[paasv1alpha2.HookTypeKey]).To(Equal(string(paasv1alpha2.HookPreRelease)))
			Expect(len(hook.Pod.Spec.Containers)).To(Equal(1))
			Expect(hook.Pod.Spec.Containers[0].Image).To(Equal(bkapp.Spec.Build.Image))
			Expect(hook.Pod.Spec.Containers[0].Command).To(Equal(bkapp.Spec.Hooks.PreRelease.Command))
			By("Check the env variables in the args have been replaced")
			Expect(hook.Pod.Spec.Containers[0].Args).To(Equal([]string{"-c", "echo foo $(VAR_1);"}))
			Expect(len(hook.Pod.Spec.Containers[0].Env)).To(Equal(0))
			// 容器资源配额
			hookRes := hook.Pod.Spec.Containers[0].Resources
			Expect(hookRes.Limits.Cpu().String()).To(Equal(config.Global.GetProcDefaultCpuLimits()))
			Expect(
				hookRes.Limits.Memory().String(),
			).To(Equal(config.Global.GetProcDefaultMemLimits()))

			// 镜像拉取密钥
			Expect(hook.Pod.Spec.ImagePullSecrets[0].Name).To(Equal(paasv1alpha2.DefaultImagePullSecretName))
			Expect(hook.Status.Phase).To(Equal(paasv1alpha2.HealthUnknown))
		})

		It("complex case - override Pod.name by DeployID and Status.Phase by PreRelease.Status", func() {
			bkapp.Status.DeployId = "100"
			bkapp.Status.SetHookStatus(paasv1alpha2.HookStatus{Type: paasv1alpha2.HookPreRelease})

			hook := BuildPreReleaseHook(bkapp, bkapp.Status.FindHookStatus(paasv1alpha2.HookPreRelease))
			Expect(hook.Pod.ObjectMeta.Name).To(Equal("pre-rel-fake-app-100"))
			Expect(hook.Status.Phase).To(Equal(paasv1alpha2.HealthPhase("")))
		})

		It("complex case - with env vars", func() {
			bkapp.Spec.Configuration.Env = append(bkapp.Spec.Configuration.Env, paasv1alpha2.AppEnvVar{Name: "FOO"})

			hook := BuildPreReleaseHook(bkapp, nil)
			Expect(len(hook.Pod.Spec.Containers[0].Env)).To(Equal(1))
		})

		It("test build pre-release hook for cnb runtime image", func() {
			bkapp.Annotations[paasv1alpha2.UseCNBAnnoKey] = "true"
			bkapp.Spec.Hooks.PreRelease.Args = []string{"-c", "echo foo"}
			hook := BuildPreReleaseHook(bkapp, nil)
			c := hook.Pod.Spec.Containers[0]
			By("test prepend 'launcher' to Command")
			Expect(len(c.Command)).To(Equal(1 + len(bkapp.Spec.Hooks.PreRelease.Command)))
			Expect(c.Command).To(Equal([]string{"launcher", "/bin/bash"}))
			By("test Args is unchanged")
			Expect(c.Args).To(Equal(bkapp.Spec.Hooks.PreRelease.Args))
		})
	})
})
