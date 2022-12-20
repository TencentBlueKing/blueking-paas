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

package resources

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	"bk.tencent.com/paas-app-operator/api/v1alpha1"
)

var _ = Describe("HookUtils", func() {
	var bkapp *v1alpha1.BkApp
	var builder *fake.ClientBuilder
	var scheme *runtime.Scheme

	BeforeEach(func() {
		bkapp = &v1alpha1.BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       v1alpha1.KindBkApp,
				APIVersion: "paas.bk.tencent.com/v1alpha1",
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      "fake-app",
				Namespace: "default",
				Annotations: map[string]string{
					v1alpha1.ImageCredentialsRefAnnoKey: "image-pull-secrets",
				},
			},
			Spec: v1alpha1.AppSpec{
				Processes: []v1alpha1.Process{
					{
						Name:       "web",
						Image:      "bar",
						Replicas:   v1alpha1.ReplicasOne,
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
		}

		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		Expect(v1alpha1.AddToScheme(scheme)).NotTo(HaveOccurred())
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

			Expect(hook.Pod.ObjectMeta.Name).To(Equal("pre-release-hook-1"))
			Expect(hook.Pod.ObjectMeta.Labels[v1alpha1.HookTypeKey]).To(Equal(string(v1alpha1.HookPreRelease)))
			Expect(len(hook.Pod.Spec.Containers)).To(Equal(1))
			Expect(hook.Pod.Spec.Containers[0].Image).To(Equal(bkapp.Spec.GetWebProcess().Image))
			Expect(hook.Pod.Spec.Containers[0].Command).To(Equal(bkapp.Spec.Hooks.PreRelease.Command))
			Expect(hook.Pod.Spec.Containers[0].Args).To(Equal(bkapp.Spec.Hooks.PreRelease.Args))
			Expect(len(hook.Pod.Spec.Containers[0].Env)).To(Equal(0))
			// 容器资源配额
			hookRes := hook.Pod.Spec.Containers[0].Resources
			cpuReq, memReq := resource.MustParse("250m"), resource.MustParse("250Mi")
			cpuLimit, memLimit := resource.MustParse("1"), resource.MustParse("500Mi")
			Expect(cpuReq.Cmp(hookRes.Requests[corev1.ResourceCPU])).To(Equal(0))
			Expect(memReq.Cmp(hookRes.Requests[corev1.ResourceMemory])).To(Equal(0))
			Expect(cpuLimit.Cmp(hookRes.Limits[corev1.ResourceCPU])).To(Equal(0))
			Expect(memLimit.Cmp(hookRes.Limits[corev1.ResourceMemory])).To(Equal(0))
			// 镜像拉取密钥
			Expect(hook.Pod.Spec.ImagePullSecrets[0].Name).To(Equal(v1alpha1.DefaultImagePullSecretName))
			Expect(hook.Status.Status).To(Equal(v1alpha1.HealthUnknown))
		})

		It("complex case - override Pod.name by Revision and Status.Status by PreRelease.Status", func() {
			bkapp.Status.Revision = &v1alpha1.Revision{Revision: 100}
			bkapp.Status.SetHookStatus(v1alpha1.HookStatus{Type: v1alpha1.HookPreRelease})

			hook := BuildPreReleaseHook(bkapp, bkapp.Status.FindHookStatus(v1alpha1.HookPreRelease))
			Expect(hook.Pod.ObjectMeta.Name).To(Equal("pre-release-hook-100"))
			Expect(hook.Status.Status).To(Equal(v1alpha1.HealthStatus("")))
		})

		It("complex case - with env vars", func() {
			bkapp.Spec.Configuration.Env = append(bkapp.Spec.Configuration.Env, v1alpha1.AppEnvVar{Name: "FOO"})

			hook := BuildPreReleaseHook(bkapp, nil)
			Expect(len(hook.Pod.Spec.Containers[0].Env)).To(Equal(1))
		})
	})
})
