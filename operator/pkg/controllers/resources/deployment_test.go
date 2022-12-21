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

	paasv1alpha1 "bk.tencent.com/paas-app-operator/api/v1alpha1"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/labels"
)

var _ = Describe("DeploymentResources", func() {
	var bkapp *paasv1alpha1.BkApp
	var builder *fake.ClientBuilder
	var scheme *runtime.Scheme

	BeforeEach(func() {
		bkapp = &paasv1alpha1.BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       paasv1alpha1.KindBkApp,
				APIVersion: paasv1alpha1.GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      "bkapp-sample",
				Namespace: "default",
			},
			Spec: paasv1alpha1.AppSpec{
				Processes: []paasv1alpha1.Process{
					{
						Name:       "web",
						Image:      "nginx:latest",
						Replicas:   paasv1alpha1.ReplicasTwo,
						TargetPort: 80,
						CPU:        "100m",
						Memory:     "100Mi",
					},
					{
						Name:     "hi",
						Image:    "busybox:latest",
						Replicas: paasv1alpha1.ReplicasTwo,
						Command:  []string{"/bin/sh"},
						Args:     []string{"-c", "echo hi"},
						CPU:      "50m",
						Memory:   "50Mi",
					},
				},
				Configuration: paasv1alpha1.AppConfig{
					Env: []paasv1alpha1.AppEnvVar{
						{Name: "ENV_NAME_1", Value: "env_value_1"},
						{Name: "ENV_NAME_2", Value: "env_value_2"},
					},
				},
				// Add some overlay configs
				EnvOverlay: &paasv1alpha1.AppEnvOverlay{
					Replicas: []paasv1alpha1.ReplicasOverlay{
						{EnvName: "stag", Process: "web", Count: 10},
					},
					EnvVariables: []paasv1alpha1.EnvVarOverlay{
						{EnvName: "stag", Name: "ENV_NAME_3", Value: "env_value_3"},
						{EnvName: "prod", Name: "ENV_NAME_1", Value: "env_value_1_prod"},
					},
				},
			},
		}

		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		Expect(paasv1alpha1.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(appsv1.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(corev1.AddToScheme(scheme)).NotTo(HaveOccurred())
		builder.WithScheme(scheme)
	})

	Context("TestParseDeploys", func() {
		It("no deploys", func() {
			bkapp.Spec.Processes = []paasv1alpha1.Process{}
			deploys := GetWantedDeploys(bkapp)
			Expect(len(deploys)).To(Equal(0))
		})

		It("common fields", func() {
			deploys := GetWantedDeploys(bkapp)
			Expect(len(deploys)).To(Equal(2))

			webDeploy := deploys[0]
			Expect(webDeploy.APIVersion).To(Equal("apps/v1"))
			Expect(webDeploy.Kind).To(Equal("Deployment"))
			Expect(webDeploy.Name).To(Equal("bkapp-sample--web"))
			Expect(webDeploy.Namespace).To(Equal(bkapp.Namespace))
			Expect(webDeploy.Labels).To(Equal(labels.Deployment(bkapp, "web")))
			Expect(webDeploy.OwnerReferences[0].Kind).To(Equal(bkapp.Kind))
			Expect(webDeploy.OwnerReferences[0].Name).To(Equal(bkapp.Name))
			Expect(len(webDeploy.Spec.Template.Spec.Containers)).To(Equal(1))

			hiDeploy := deploys[1]
			Expect(hiDeploy.Name).To(Equal("bkapp-sample--hi"))
			Expect(hiDeploy.Spec.Selector.MatchLabels).To(Equal(labels.Deployment(bkapp, "hi")))
			Expect(*hiDeploy.Spec.RevisionHistoryLimit).To(Equal(int32(0)))
			Expect(len(hiDeploy.Spec.Template.Spec.Containers)).To(Equal(1))
		})
		It("stag env related fields", func() {
			bkapp.SetAnnotations(map[string]string{paasv1alpha1.EnvironmentKey: "stag"})
			deploys := GetWantedDeploys(bkapp)
			web, hi := deploys[0], deploys[1]
			// Value overwritten by overlay config
			Expect(*web.Spec.Replicas).To(Equal(int32(10)))
			Expect(*hi.Spec.Replicas).To(Equal(int32(2)))
			Expect(web.Spec.Template.Spec.Containers[0].Env).To(Equal(
				[]corev1.EnvVar{
					{Name: "ENV_NAME_1", Value: "env_value_1"},
					{Name: "ENV_NAME_2", Value: "env_value_2"},
					// Env var appended by overlay config
					{Name: "ENV_NAME_3", Value: "env_value_3"},
				},
			))
		})
		It("prod env related fields", func() {
			bkapp.SetAnnotations(map[string]string{paasv1alpha1.EnvironmentKey: "prod"})
			deploys := GetWantedDeploys(bkapp)
			web, hi := deploys[0], deploys[1]
			Expect(*web.Spec.Replicas).To(Equal(int32(2)))
			Expect(*hi.Spec.Replicas).To(Equal(int32(2)))
			Expect(web.Spec.Template.Spec.Containers[0].Env).To(Equal(
				[]corev1.EnvVar{
					// Env var overwritten by overlay config
					{Name: "ENV_NAME_1", Value: "env_value_1_prod"},
					{Name: "ENV_NAME_2", Value: "env_value_2"},
				},
			))
		})
	})

	Context("Make container from process", func() {
		It("Rich spec", func() {
			proc := paasv1alpha1.Process{
				Name:       "web",
				Image:      "busybox:latest",
				Replicas:   paasv1alpha1.ReplicasOne,
				Command:    []string{"/bin/sh"},
				Args:       []string{"-c", "echo hi"},
				TargetPort: 80,
				CPU:        "100m",
				Memory:     "100Mi",
			}
			envs := []corev1.EnvVar{
				{Name: "ENV_NAME_1", Value: "env_value_1"},
				{Name: "ENV_NAME_2", Value: "env_value_2"},
			}

			container := buildContainers(proc, envs)[0]
			Expect(container.Name).To(Equal(proc.Name))
			Expect(container.Image).To(Equal(proc.Image))
			Expect(len(container.Command)).To(Equal(1))
			Expect(len(container.Args)).To(Equal(2))
			Expect(container.Env).To(Equal(envs))
			Expect(container.Ports).To(Equal([]corev1.ContainerPort{{ContainerPort: 80}}))
		})

		It("Simple spec", func() {
			var replicas int32 = 1
			proc := paasv1alpha1.Process{
				Name:     "web",
				Image:    "busybox:latest",
				Replicas: &replicas,
				CPU:      "100m",
				Memory:   "100Mi",
			}
			container := buildContainers(proc, []corev1.EnvVar{})[0]
			Expect(container.Name).To(Equal(proc.Name))
			Expect(len(container.Env)).To(Equal(0))
		})

		It("Resource quota", func() {
			var replicas int32 = 1
			proc := paasv1alpha1.Process{
				Name:     "web",
				Image:    "busybox:latest",
				Replicas: &replicas,
				CPU:      "1",
				Memory:   "2Gi",
			}
			container := buildContainers(proc, []corev1.EnvVar{})[0]

			cpuRequests := container.Resources.Requests[corev1.ResourceCPU]
			Expect(cpuRequests.String()).To(Equal("250m"))

			cpuLimits := container.Resources.Limits[corev1.ResourceCPU]
			Expect(cpuLimits.String()).To(Equal("1"))

			memRequests := container.Resources.Requests[corev1.ResourceMemory]
			Expect(memRequests.String()).To(Equal("1Gi"))

			memLimits := container.Resources.Limits[corev1.ResourceMemory]
			Expect(memLimits.String()).To(Equal("2Gi"))
		})
	})
})
