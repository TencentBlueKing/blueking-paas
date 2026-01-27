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

package envs

import (
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/kubeutil"
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
						Name:         "web",
						Replicas:     paasv1alpha2.ReplicasTwo,
						ResQuotaPlan: paasv1alpha2.ResQuotaPlanDefault,
						TargetPort:   80,
						Autoscaling: &paasv1alpha2.AutoscalingSpec{
							MinReplicas: 1,
							MaxReplicas: 5,
							Policy:      paasv1alpha2.ScalingPolicyDefault,
						},
					},
					{
						Name:         "worker",
						Replicas:     paasv1alpha2.ReplicasTwo,
						ResQuotaPlan: paasv1alpha2.ResQuotaPlanDefault,
						Autoscaling: &paasv1alpha2.AutoscalingSpec{
							MinReplicas: 2,
							MaxReplicas: 6,
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
			val := NewReplicasGetter(bkapp).GetByProc("web")
			Expect(*val).To(Equal(int32(2)))
		})
		It("process missing", func() {
			val := NewReplicasGetter(bkapp).GetByProc("web-missing")
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
			val := NewReplicasGetter(bkapp).GetByProc("web")
			Expect(*val).To(Equal(int32(10)))
		})
		It("env overlay absent", func() {
			val := NewReplicasGetter(bkapp).GetByProc("worker")
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
			spec := NewAutoscalingSpecGetter(bkapp).GetByProc("web")
			Expect(spec.MinReplicas).To(Equal(int32(1)))
			Expect(spec.MaxReplicas).To(Equal(int32(5)))
			Expect(spec.Policy).To(Equal(paasv1alpha2.ScalingPolicyDefault))
		})
		It("process missing", func() {
			spec := NewAutoscalingSpecGetter(bkapp).GetByProc("web-missing")
			Expect(spec).To(BeNil())
		})
	})

	Context("Test AutoscalingPolicyGetter with env", func() {
		BeforeEach(func() {
			// Set up application to add env overlay related info
			bkapp.SetAnnotations(map[string]string{paasv1alpha2.EnvironmentKey: "stag"})
			bkapp.Spec.EnvOverlay = &paasv1alpha2.AppEnvOverlay{
				Autoscaling: []paasv1alpha2.AutoscalingOverlay{
					{
						EnvName: "stag",
						Process: "web",
						AutoscalingSpec: paasv1alpha2.AutoscalingSpec{
							MinReplicas: 2, MaxReplicas: 5, Policy: "custom",
						},
					},
				},
			}
		})
		It("env overlay hit", func() {
			spec := NewAutoscalingSpecGetter(bkapp).GetByProc("web")
			Expect(spec.MinReplicas).To(Equal(int32(2)))
			Expect(spec.MaxReplicas).To(Equal(int32(5)))
			Expect(spec.Policy).To(Equal(paasv1alpha2.ScalingPolicy("custom")))
		})
		It("env overlay absent", func() {
			spec := NewAutoscalingSpecGetter(bkapp).GetByProc("worker")
			Expect(spec.MinReplicas).To(Equal(int32(2)))
			Expect(spec.MaxReplicas).To(Equal(int32(6)))
			Expect(spec.Policy).To(Equal(paasv1alpha2.ScalingPolicyDefault))
		})
	})

	Context("Test ProcResourcesGetter", func() {
		It("Get Default", func() {
			resReq := NewProcResourcesGetter(bkapp).Default()
			Expect(resReq.Requests.Cpu().Equal(resource.MustParse("200m"))).To(BeTrue())
			Expect(resReq.Requests.Memory().Equal(resource.MustParse("256Mi"))).To(BeTrue())
			Expect(resReq.Limits.Cpu().Equal(resource.MustParse("4"))).To(BeTrue())
			Expect(resReq.Limits.Memory().Equal(resource.MustParse("1024Mi"))).To(BeTrue())
		})

		It("Get Legacy", func() {
			_ = kubeutil.SetJsonAnnotation(
				bkapp, paasv1alpha2.LegacyProcResAnnoKey, paasv1alpha2.LegacyProcConfig{
					"web": {"cpu": "2", "memory": "2Gi"},
				},
			)
			getter := NewProcResourcesGetter(bkapp)
			resReq, _ := getter.GetByProc("web")
			Expect(resReq.Requests.Cpu().Equal(resource.MustParse("200m"))).To(BeTrue())
			Expect(resReq.Requests.Memory().Equal(resource.MustParse("1Gi"))).To(BeTrue())
			Expect(resReq.Limits.Cpu().Equal(resource.MustParse("2"))).To(BeTrue())
			Expect(resReq.Limits.Memory().Equal(resource.MustParse("2Gi"))).To(BeTrue())
		})

		It("Get Overlay", func() {
			bkapp.SetAnnotations(map[string]string{paasv1alpha2.EnvironmentKey: "stag"})
			bkapp.Spec.EnvOverlay = &paasv1alpha2.AppEnvOverlay{
				ResQuotas: []paasv1alpha2.ResQuotaOverlay{
					{EnvName: "stag", Process: "web", Plan: paasv1alpha2.ResQuotaPlan4C1G},
				},
			}
			getter := NewProcResourcesGetter(bkapp)

			resReq, _ := getter.GetByProc("web")
			Expect(resReq.Requests.Cpu().Equal(resource.MustParse("200m"))).To(BeTrue())
			Expect(resReq.Requests.Memory().Equal(resource.MustParse("256Mi"))).To(BeTrue())
			Expect(resReq.Limits.Cpu().Equal(resource.MustParse("4"))).To(BeTrue())
			Expect(resReq.Limits.Memory().Equal(resource.MustParse("1Gi"))).To(BeTrue())
		})

		It("Get Standard", func() {
			bkapp.Spec.Processes[1].ResQuotaPlan = paasv1alpha2.ResQuotaPlan4C2G
			getter := NewProcResourcesGetter(bkapp)

			resReq, _ := getter.GetByProc("web")
			Expect(resReq.Requests.Cpu().Equal(resource.MustParse("200m"))).To(BeTrue())
			Expect(resReq.Requests.Memory().Equal(resource.MustParse("256Mi"))).To(BeTrue())
			Expect(resReq.Limits.Cpu().Equal(resource.MustParse("4"))).To(BeTrue())
			Expect(resReq.Limits.Memory().Equal(resource.MustParse("1024Mi"))).To(BeTrue())

			resReq, _ = getter.GetByProc("worker")
			Expect(resReq.Requests.Cpu().Equal(resource.MustParse("200m"))).To(BeTrue())
			Expect(resReq.Requests.Memory().Equal(resource.MustParse("1Gi"))).To(BeTrue())
			Expect(resReq.Limits.Cpu().Equal(resource.MustParse("4"))).To(BeTrue())
			Expect(resReq.Limits.Memory().Equal(resource.MustParse("2Gi"))).To(BeTrue())
		})

		It("Get Admin Annotation explicit values override everything", func() {
			bkapp.SetAnnotations(map[string]string{paasv1alpha2.EnvironmentKey: string(paasv1alpha2.StagEnv)})
			_ = kubeutil.SetJsonAnnotation(
				bkapp,
				paasv1alpha2.OverrideProcResAnnoKey,
				paasv1alpha2.OverrideProcResConfig{
					"web": {
						Limits: paasv1alpha2.ResourceSpec{
							CPU:    "2",
							Memory: "2Gi",
						},
						Requests: &paasv1alpha2.ResourceSpec{
							CPU:    "500m",
							Memory: "1Gi",
						},
					},
				},
			)
			getter := NewProcResourcesGetter(bkapp)
			resReq, _ := getter.GetByProc("web")
			Expect(resReq.Limits.Cpu().Equal(resource.MustParse("2"))).To(BeTrue())
			Expect(resReq.Limits.Memory().Equal(resource.MustParse("2Gi"))).To(BeTrue())
			Expect(resReq.Requests.Cpu().Equal(resource.MustParse("500m"))).To(BeTrue())
			Expect(resReq.Requests.Memory().Equal(resource.MustParse("1Gi"))).To(BeTrue())
		})

		It("Get Admin Annotation limited values only and derive requests", func() {
			bkapp.SetAnnotations(map[string]string{paasv1alpha2.EnvironmentKey: string(paasv1alpha2.StagEnv)})
			_ = kubeutil.SetJsonAnnotation(
				bkapp,
				paasv1alpha2.OverrideProcResAnnoKey,
				paasv1alpha2.OverrideProcResConfig{
					"web": {
						Limits: paasv1alpha2.ResourceSpec{
							CPU:    "2",
							Memory: "2Gi",
						},
					},
				},
			)
			getter := NewProcResourcesGetter(bkapp)
			resReq, _ := getter.GetByProc("web")
			Expect(resReq.Limits.Cpu().Equal(resource.MustParse("2"))).To(BeTrue())
			Expect(resReq.Limits.Memory().Equal(resource.MustParse("2Gi"))).To(BeTrue())
			// Expect limits are set, requests derived (cpu default 200m, mem default divisor 2 -> 1Gi)
			Expect(resReq.Requests.Cpu().Equal(resource.MustParse("200m"))).To(BeTrue())
			Expect(resReq.Requests.Memory().Equal(resource.MustParse("1Gi"))).To(BeTrue())
		})

		It("Get custom quota plan from annotation - with explicit requests", func() {
			// Define custom plan in annotation
			_ = kubeutil.SetJsonAnnotation(
				bkapp,
				paasv1alpha2.ResQuotaPlansAnnoKey,
				paasv1alpha2.ResQuotaPlans{
					"custom-2c2g": {
						Limits: paasv1alpha2.ResourceSpec{
							CPU:    "2000m",
							Memory: "2Gi",
						},
						Requests: &paasv1alpha2.ResourceSpec{
							CPU:    "500m",
							Memory: "512Mi",
						},
					},
				},
			)
			// Use custom plan in process
			bkapp.Spec.Processes[0].ResQuotaPlan = "custom-2c2g"

			getter := NewProcResourcesGetter(bkapp)
			resReq, _ := getter.GetByProc("web")

			Expect(resReq.Limits.Cpu().Equal(resource.MustParse("2000m"))).To(BeTrue())
			Expect(resReq.Limits.Memory().Equal(resource.MustParse("2Gi"))).To(BeTrue())
			Expect(resReq.Requests.Cpu().Equal(resource.MustParse("500m"))).To(BeTrue())
			Expect(resReq.Requests.Memory().Equal(resource.MustParse("512Mi"))).To(BeTrue())
		})

		It("Get custom quota plan from annotation - limits only, derive requests", func() {
			// Define custom plan in annotation without requests
			_ = kubeutil.SetJsonAnnotation(
				bkapp,
				paasv1alpha2.ResQuotaPlansAnnoKey,
				paasv1alpha2.ResQuotaPlans{
					"custom-1c1g": {
						Limits: paasv1alpha2.ResourceSpec{
							CPU:    "1000m",
							Memory: "1Gi",
						},
					},
				},
			)
			// Use custom plan in process
			bkapp.Spec.Processes[0].ResQuotaPlan = "custom-1c1g"

			getter := NewProcResourcesGetter(bkapp)
			resReq, _ := getter.GetByProc("web")

			Expect(resReq.Limits.Cpu().Equal(resource.MustParse("1000m"))).To(BeTrue())
			Expect(resReq.Limits.Memory().Equal(resource.MustParse("1Gi"))).To(BeTrue())
			// Requests should be derived: cpu 200m default, memory 1Gi/4 = 256Mi
			Expect(resReq.Requests.Cpu().Equal(resource.MustParse("200m"))).To(BeTrue())
			Expect(resReq.Requests.Memory().Equal(resource.MustParse("256Mi"))).To(BeTrue())
		})

		It("Get custom quota plan from annotation in envOverlay", func() {
			// Set environment annotation first
			bkapp.SetAnnotations(map[string]string{paasv1alpha2.EnvironmentKey: "stag"})

			// Define custom plan in annotation
			_ = kubeutil.SetJsonAnnotation(
				bkapp,
				paasv1alpha2.ResQuotaPlansAnnoKey,
				paasv1alpha2.ResQuotaPlans{
					"custom-3c4g": {
						Limits: paasv1alpha2.ResourceSpec{
							CPU:    "3000m",
							Memory: "4Gi",
						},
						Requests: &paasv1alpha2.ResourceSpec{
							CPU:    "1000m",
							Memory: "2Gi",
						},
					},
				},
			)

			// Use custom plan in envOverlay
			bkapp.Spec.EnvOverlay = &paasv1alpha2.AppEnvOverlay{
				ResQuotas: []paasv1alpha2.ResQuotaOverlay{
					{EnvName: "stag", Process: "web", Plan: "custom-3c4g"},
				},
			}

			getter := NewProcResourcesGetter(bkapp)
			resReq, _ := getter.GetByProc("web")

			Expect(resReq.Limits.Cpu().Equal(resource.MustParse("3000m"))).To(BeTrue())
			Expect(resReq.Limits.Memory().Equal(resource.MustParse("4Gi"))).To(BeTrue())
			Expect(resReq.Requests.Cpu().Equal(resource.MustParse("1000m"))).To(BeTrue())
			Expect(resReq.Requests.Memory().Equal(resource.MustParse("2Gi"))).To(BeTrue())
		})

		It("Fallback to default when custom plan not found in annotation", func() {
			// Define custom plan but use different name in process
			_ = kubeutil.SetJsonAnnotation(
				bkapp,
				paasv1alpha2.ResQuotaPlansAnnoKey,
				paasv1alpha2.ResQuotaPlans{
					"custom-plan": {
						Limits: paasv1alpha2.ResourceSpec{
							CPU:    "2000m",
							Memory: "2Gi",
						},
					},
				},
			)
			// Use non-existent plan name
			bkapp.Spec.Processes[0].ResQuotaPlan = "non-existent-plan"

			getter := NewProcResourcesGetter(bkapp)
			resReq, _ := getter.GetByProc("web")

			// Should fallback to default plan
			Expect(resReq.Limits.Cpu().Equal(resource.MustParse("4"))).To(BeTrue())
			Expect(resReq.Limits.Memory().Equal(resource.MustParse("1024Mi"))).To(BeTrue())
			Expect(resReq.Requests.Cpu().Equal(resource.MustParse("200m"))).To(BeTrue())
			Expect(resReq.Requests.Memory().Equal(resource.MustParse("256Mi"))).To(BeTrue())
		})

		It("Use legacy quota plan", func() {
			bkapp.Spec.Processes[0].ResQuotaPlan = paasv1alpha2.ResQuotaPlan4C1G

			getter := NewProcResourcesGetter(bkapp)
			resReq, _ := getter.GetByProc("web")

			Expect(resReq.Limits.Cpu().Equal(resource.MustParse("4000m"))).To(BeTrue())
			Expect(resReq.Limits.Memory().Equal(resource.MustParse("1024Mi"))).To(BeTrue())
			Expect(resReq.Requests.Cpu().Equal(resource.MustParse("200m"))).To(BeTrue())
			Expect(resReq.Requests.Memory().Equal(resource.MustParse("256Mi"))).To(BeTrue())
		})

		It("Use legacy quota plan in envOverlay", func() {
			bkapp.SetAnnotations(map[string]string{paasv1alpha2.EnvironmentKey: "stag"})
			bkapp.Spec.EnvOverlay = &paasv1alpha2.AppEnvOverlay{
				ResQuotas: []paasv1alpha2.ResQuotaOverlay{
					{EnvName: "stag", Process: "web", Plan: paasv1alpha2.ResQuotaPlan4C2G},
				},
			}

			getter := NewProcResourcesGetter(bkapp)
			resReq, _ := getter.GetByProc("web")

			Expect(resReq.Limits.Cpu().Equal(resource.MustParse("4000m"))).To(BeTrue())
			Expect(resReq.Limits.Memory().Equal(resource.MustParse("2048Mi"))).To(BeTrue())
			Expect(resReq.Requests.Cpu().Equal(resource.MustParse("200m"))).To(BeTrue())
			Expect(resReq.Requests.Memory().Equal(resource.MustParse("1024Mi"))).To(BeTrue())
		})
	})
})
