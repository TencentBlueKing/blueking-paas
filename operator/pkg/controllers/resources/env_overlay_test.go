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
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
)

var _ = Describe("Environment overlay related functions", func() {
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
				Build: paasv1alpha2.BuildConfig{
					Image: "nginx:latest",
				},
				Processes: []paasv1alpha2.Process{
					{
						Name:       "web",
						Replicas:   paasv1alpha2.ReplicasTwo,
						TargetPort: 80,
						Autoscaling: &paasv1alpha2.AutoscalingSpec{
							Enabled:     true,
							MinReplicas: 1,
							MaxReplicas: 5,
							Policy:      paasv1alpha2.ScalingPolicyDefault,
						},
					},
					{
						Name:     "worker",
						Replicas: paasv1alpha2.ReplicasTwo,
						Autoscaling: &paasv1alpha2.AutoscalingSpec{
							Enabled:     true,
							MinReplicas: 1,
							MaxReplicas: 5,
							Policy:      paasv1alpha2.ScalingPolicyDefault,
						},
					},
				},
				Configuration: paasv1alpha2.AppConfig{
					Env: []paasv1alpha2.AppEnvVar{
						{Name: "ENV_1", Value: "value_1"},
						{Name: "ENV_2", Value: "value_2"},
					},
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

	Context("Test GetEnvName", func() {
		It("missing", func() {
			envName := GetEnvName(bkapp)
			Expect(envName.IsEmpty()).To(BeTrue())
		})
		It("invalid value", func() {
			bkapp.SetAnnotations(map[string]string{paasv1alpha2.EnvironmentKey: "invalid-env"})
			envName := GetEnvName(bkapp)
			Expect(envName.IsEmpty()).To(BeTrue())
		})
		It("normal", func() {
			bkapp.SetAnnotations(map[string]string{paasv1alpha2.EnvironmentKey: "stag"})
			envName := GetEnvName(bkapp)
			Expect(envName.IsEmpty()).To(BeFalse())
			Expect(envName).To(Equal(paasv1alpha2.StagEnv))
		})
	})

	Context("Test ReplicasGetter without env", func() {
		It("process normal", func() {
			val := NewReplicasGetter(bkapp).Get("web")
			Expect(*val).To(Equal(int32(2)))
		})
		It("process missing", func() {
			val := NewReplicasGetter(bkapp).Get("web-missing")
			Expect(val).To(BeNil())
		})
	})

	Context("Test ReplicasGetter with env", func() {
		BeforeEach(func() {
			// Set up application to add env overlay related info
			bkapp.SetAnnotations(map[string]string{paasv1alpha2.EnvironmentKey: "stag"})
			bkapp.Spec.EnvOverlay = &paasv1alpha2.AppEnvOverlay{
				Replicas: []paasv1alpha2.ReplicasOverlay{
					{EnvName: "stag", Process: "web", Count: 10},
					{EnvName: "prod", Process: "web", Count: 20},
				},
			}
		})
		It("env overlay hit", func() {
			val := NewReplicasGetter(bkapp).Get("web")
			Expect(*val).To(Equal(int32(10)))
		})
		It("env overlay absent", func() {
			val := NewReplicasGetter(bkapp).Get("worker")
			Expect(*val).To(Equal(int32(2)))
		})
	})

	Context("Test EnvVarsGetter without env", func() {
		It("normal", func() {
			vars := NewEnvVarsGetter(bkapp).Get()
			Expect(vars).To(Equal([]corev1.EnvVar{
				{Name: "ENV_1", Value: "value_1"},
				{Name: "ENV_2", Value: "value_2"},
			}))
		})
	})

	Context("Test EnvVarsGetter with env", func() {
		BeforeEach(func() {
			// Set up application to add env overlay related info
			bkapp.Spec.EnvOverlay = &paasv1alpha2.AppEnvOverlay{
				EnvVariables: []paasv1alpha2.EnvVarOverlay{
					{EnvName: "stag", Name: "ENV_3", Value: "value_3"},
					{EnvName: "prod", Name: "ENV_4", Value: "value_4"},
					{EnvName: "stag", Name: "ENV_2", Value: "value_new_2"},
				},
			}
		})
		It("stag env", func() {
			bkapp.SetAnnotations(map[string]string{paasv1alpha2.EnvironmentKey: "stag"})
			vars := NewEnvVarsGetter(bkapp).Get()
			Expect(vars).To(Equal([]corev1.EnvVar{
				{Name: "ENV_1", Value: "value_1"},
				{Name: "ENV_2", Value: "value_new_2"},
				{Name: "ENV_3", Value: "value_3"},
			}))
		})
		It("prod env", func() {
			bkapp.SetAnnotations(map[string]string{paasv1alpha2.EnvironmentKey: "prod"})
			vars := NewEnvVarsGetter(bkapp).Get()
			Expect(vars).To(Equal([]corev1.EnvVar{
				{Name: "ENV_1", Value: "value_1"},
				{Name: "ENV_2", Value: "value_2"},
				{Name: "ENV_4", Value: "value_4"},
			}))
		})
	})

	Context("Test AutoscalingPolicyGetter without env", func() {
		It("process normal", func() {
			val := NewAutoscalingPolicyGetter(bkapp).Get("web")
			Expect(val).To(Equal(paasv1alpha2.ScalingPolicyDefault))
		})
		It("process missing", func() {
			val := NewAutoscalingPolicyGetter(bkapp).Get("web-missing")
			Expect(val).To(Equal(paasv1alpha2.ScalingPolicy("")))
		})
	})

	Context("Test AutoscalingPolicyGetter with env", func() {
		BeforeEach(func() {
			// Set up application to add env overlay related info
			bkapp.SetAnnotations(map[string]string{paasv1alpha2.EnvironmentKey: "stag"})
			bkapp.Spec.EnvOverlay = &paasv1alpha2.AppEnvOverlay{
				Autoscaling: []paasv1alpha2.AutoscalingOverlay{
					{EnvName: "stag", Process: "web", Policy: "custom"},
				},
			}
		})
		It("env overlay hit", func() {
			val := NewAutoscalingPolicyGetter(bkapp).Get("web")
			Expect(val).To(Equal(paasv1alpha2.ScalingPolicy("custom")))
		})
		It("env overlay absent", func() {
			val := NewAutoscalingPolicyGetter(bkapp).Get("worker")
			Expect(val).To(Equal(paasv1alpha2.ScalingPolicyDefault))
		})
	})
})
