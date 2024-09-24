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
	"k8s.io/apimachinery/pkg/util/intstr"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/config"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/labels"
	"bk.tencent.com/paas-app-operator/pkg/kubeutil"
)

var _ = Describe("Test build deployments from BkApp", func() {
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
				Name:        "bkapp-sample",
				Namespace:   "default",
				Annotations: map[string]string{},
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
					{
						Name:         "hi",
						Replicas:     paasv1alpha2.ReplicasTwo,
						ResQuotaPlan: paasv1alpha2.ResQuotaPlanDefault,
						Command:      []string{"/bin/sh"},
						Args:         []string{"-c", "echo hi"},
					},
				},
				Configuration: paasv1alpha2.AppConfig{
					Env: []paasv1alpha2.AppEnvVar{
						{Name: "ENV_NAME_1", Value: "env_value_1"},
						{Name: "ENV_NAME_2", Value: "env_value_2"},
					},
				},
				// Add some overlay configs
				EnvOverlay: &paasv1alpha2.AppEnvOverlay{
					Replicas: []paasv1alpha2.ReplicasOverlay{
						{EnvName: "stag", Process: "web", Count: 10},
					},
					EnvVariables: []paasv1alpha2.EnvVarOverlay{
						{EnvName: "stag", Name: "ENV_NAME_3", Value: "env_value_3"},
						{EnvName: "prod", Name: "ENV_NAME_1", Value: "env_value_1_prod"},
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

	Context("basic fields checks", func() {
		It("invalid process name", func() {
			deploy, err := BuildProcDeployment(bkapp, "invalid-name")
			Expect(deploy).To(BeNil())
			Expect(err).To(HaveOccurred())
		})

		It("common base fields", func() {
			webDeploy, _ := BuildProcDeployment(bkapp, "web")
			Expect(webDeploy.APIVersion).To(Equal("apps/v1"))
			Expect(webDeploy.Kind).To(Equal("Deployment"))
			Expect(webDeploy.Name).To(Equal("bkapp-sample--web"))
			Expect(webDeploy.Namespace).To(Equal(bkapp.Namespace))
			Expect(webDeploy.Labels).To(Equal(labels.Deployment(bkapp, "web")))
			Expect(webDeploy.OwnerReferences[0].Kind).To(Equal(bkapp.Kind))
			Expect(webDeploy.OwnerReferences[0].Name).To(Equal(bkapp.Name))
			Expect(webDeploy.Annotations[paasv1alpha2.LastSyncedSerializedBkAppAnnoKey]).To(Not(BeEmpty()))
			Expect(len(webDeploy.Spec.Template.Spec.Containers)).To(Equal(1))
			Expect(*webDeploy.Spec.Template.Spec.AutomountServiceAccountToken).To(Equal(false))

			hiDeploy, _ := BuildProcDeployment(bkapp, "hi")
			Expect(hiDeploy.Name).To(Equal("bkapp-sample--hi"))
			Expect(hiDeploy.Spec.Selector.MatchLabels).To(Equal(labels.PodSelector(bkapp, "hi")))
			Expect(*hiDeploy.Spec.RevisionHistoryLimit).To(Equal(int32(0)))
			Expect(len(hiDeploy.Spec.Template.Spec.Containers)).To(Equal(1))
		})
	})

	Context("container basic fields", func() {
		It("base fields", func() {
			bkapp.Spec.Build = paasv1alpha2.BuildConfig{
				Image: "busybox:latest",
			}
			bkapp.Spec.Processes = []paasv1alpha2.Process{{
				Name:       "web",
				Replicas:   paasv1alpha2.ReplicasOne,
				Command:    []string{"/bin/sh"},
				Args:       []string{"start", "-l", "example.com:$PORT"},
				TargetPort: 8081,
			}}

			d, _ := BuildProcDeployment(bkapp, "web")
			c := d.Spec.Template.Spec.Containers[0]
			Expect(len(c.Command)).To(Equal(1))
			By("Check the env variables in the args have been replaced")
			Expect(c.Args).To(Equal([]string{"start", "-l", "example.com:$(PORT)"}))
			Expect(c.Ports).To(Equal([]corev1.ContainerPort{{ContainerPort: 8081}}))
		})
	})

	Context("container probes field", func() {
		It("no probes", func() {
			d, _ := BuildProcDeployment(bkapp, "web")
			c := d.Spec.Template.Spec.Containers[0]
			Expect(c.LivenessProbe).To(BeNil())
			Expect(c.ReadinessProbe).To(BeNil())
			Expect(c.StartupProbe).To(BeNil())
		})

		It("standard probes", func() {
			bkapp.Spec.Processes[0].Probes = &paasv1alpha2.ProbeSet{
				Liveness: &corev1.Probe{
					ProbeHandler: corev1.ProbeHandler{
						TCPSocket: &corev1.TCPSocketAction{
							Port: intstr.FromInt(8080),
						},
					},
					InitialDelaySeconds: 10,
					TimeoutSeconds:      60,
					PeriodSeconds:       5,
					SuccessThreshold:    1,
					FailureThreshold:    3,
				},
				Readiness: &corev1.Probe{
					ProbeHandler: corev1.ProbeHandler{
						HTTPGet: &corev1.HTTPGetAction{
							Path: "/healthz",
							Port: intstr.FromInt(80),
						},
					},
					InitialDelaySeconds: 10,
					TimeoutSeconds:      60,
					PeriodSeconds:       5,
					SuccessThreshold:    1,
					FailureThreshold:    3,
				},
				Startup: &corev1.Probe{
					ProbeHandler: corev1.ProbeHandler{
						Exec: &corev1.ExecAction{
							Command: []string{"echo", "I'm ready!"},
						},
					},
					InitialDelaySeconds: 10,
					TimeoutSeconds:      60,
					PeriodSeconds:       5,
					SuccessThreshold:    1,
					FailureThreshold:    3,
				},
			}
			d, _ := BuildProcDeployment(bkapp, "web")
			c := d.Spec.Template.Spec.Containers[0]
			Expect(c.LivenessProbe.TCPSocket.Port.IntValue()).To(Equal(8080))
			Expect(c.ReadinessProbe.HTTPGet.Path).To(Equal("/healthz"))
			Expect(c.ReadinessProbe.HTTPGet.Port.IntValue()).To(Equal(80))
			Expect(c.StartupProbe.Exec.Command).To(Equal([]string{"echo", "I'm ready!"}))
		})
	})

	Context("Image related fields", func() {
		It("default version", func() {
			bkapp.Spec.Build = paasv1alpha2.BuildConfig{
				Image:           "busybox:latest",
				ImagePullPolicy: corev1.PullAlways,
			}
			bkapp.Spec.Processes = []paasv1alpha2.Process{
				{
					Name:     "web",
					Replicas: paasv1alpha2.ReplicasOne,
				}, {
					Name:     "worker",
					Replicas: paasv1alpha2.ReplicasOne,
				},
			}

			webDeploy, _ := BuildProcDeployment(bkapp, "web")
			cWeb := webDeploy.Spec.Template.Spec.Containers[0]
			Expect(cWeb.Name).To(Equal("web"))
			Expect(cWeb.Image).To(Equal("busybox:latest"))
			Expect(cWeb.ImagePullPolicy).To(Equal(corev1.PullAlways))

			workerDeploy, _ := BuildProcDeployment(bkapp, "worker")
			cWorker := workerDeploy.Spec.Template.Spec.Containers[0]
			Expect(cWorker.Name).To(Equal("worker"))
			Expect(cWorker.Image).To(Equal(cWeb.Image))
			Expect(cWorker.ImagePullPolicy).To(Equal(cWeb.ImagePullPolicy))
		})

		It("legacy version", func() {
			_ = kubeutil.SetJsonAnnotation(bkapp, paasv1alpha2.LegacyProcImageAnnoKey, paasv1alpha2.LegacyProcConfig{
				"web":    {"image": "busybox:1.0.0", "policy": "Never"},
				"worker": {"image": "busybox:2.0.0", "policy": "Always"},
			})
			bkapp.Spec.Build = paasv1alpha2.BuildConfig{}
			bkapp.Spec.Processes = []paasv1alpha2.Process{
				{
					Name:     "web",
					Replicas: paasv1alpha2.ReplicasOne,
				}, {
					Name:     "worker",
					Replicas: paasv1alpha2.ReplicasOne,
				},
			}

			webDeploy, _ := BuildProcDeployment(bkapp, "web")
			cWeb := webDeploy.Spec.Template.Spec.Containers[0]
			Expect(cWeb.Image).To(Equal("busybox:1.0.0"))
			Expect(cWeb.ImagePullPolicy).To(Equal(corev1.PullNever))

			workerDeploy, _ := BuildProcDeployment(bkapp, "worker")
			cWorker := workerDeploy.Spec.Template.Spec.Containers[0]
			Expect(cWorker.Image).To(Equal("busybox:2.0.0"))
			Expect(cWorker.ImagePullPolicy).To(Equal(corev1.PullAlways))
		})
	})

	Context("Resources related fields", func() {
		BeforeEach(func() {
			bkapp.Spec.Build = paasv1alpha2.BuildConfig{
				Image:           "busybox:latest",
				ImagePullPolicy: corev1.PullAlways,
			}
		})
		It("default version", func() {
			bkapp.Spec.Processes = []paasv1alpha2.Process{
				{
					Name:         "web",
					Replicas:     paasv1alpha2.ReplicasOne,
					ResQuotaPlan: paasv1alpha2.ResQuotaPlanDefault,
				}, {
					Name:         "worker",
					Replicas:     paasv1alpha2.ReplicasOne,
					ResQuotaPlan: paasv1alpha2.ResQuotaPlanDefault,
				},
			}

			webDeploy, _ := BuildProcDeployment(bkapp, "web")
			workerDeploy, _ := BuildProcDeployment(bkapp, "worker")
			cWebRes := webDeploy.Spec.Template.Spec.Containers[0].Resources
			cWorkerRes := workerDeploy.Spec.Template.Spec.Containers[0].Resources
			// The processes should share the same resource requirements
			Expect(cWebRes.Requests).To(Equal(cWorkerRes.Requests))
			Expect(cWebRes.Limits).To(Equal(cWorkerRes.Limits))

			// The resource requirements should be the default value defined in project config
			// TODO: enhance below tests to check real plans
			Expect(cWebRes.Limits.Cpu().String()).To(Equal(config.Global.GetProcDefaultCpuLimit()))
			Expect(cWebRes.Limits.Memory().String()).To(Equal(config.Global.GetProcDefaultMemLimit()))
		})

		It("legacy version", func() {
			_ = kubeutil.SetJsonAnnotation(bkapp, paasv1alpha2.LegacyProcResAnnoKey, paasv1alpha2.LegacyProcConfig{
				"web":    {"cpu": "1", "memory": "1Gi"},
				"worker": {"cpu": "2", "memory": "2Gi"},
			})
			bkapp.Spec.Processes = []paasv1alpha2.Process{
				{
					Name:     "web",
					Replicas: paasv1alpha2.ReplicasOne,
				}, {
					Name:     "worker",
					Replicas: paasv1alpha2.ReplicasOne,
				},
			}

			// Check resource requirements for "web"
			webDeploy, _ := BuildProcDeployment(bkapp, "web")
			cWebRes := webDeploy.Spec.Template.Spec.Containers[0].Resources
			Expect(cWebRes.Requests.Cpu().String()).To(Equal("200m"))
			Expect(cWebRes.Limits.Cpu().String()).To(Equal("1"))
			Expect(cWebRes.Requests.Memory().String()).To(Equal("256Mi"))
			Expect(cWebRes.Limits.Memory().String()).To(Equal("1Gi"))

			// Check resource requirements for "worker"
			workerDeploy, _ := BuildProcDeployment(bkapp, "worker")
			cWorkerRes := workerDeploy.Spec.Template.Spec.Containers[0].Resources
			Expect(cWorkerRes.Requests.Cpu().String()).To(Equal("200m"))
			Expect(cWorkerRes.Limits.Cpu().String()).To(Equal("2"))
			Expect(cWorkerRes.Requests.Memory().String()).To(Equal("1Gi"))
			Expect(cWorkerRes.Limits.Memory().String()).To(Equal("2Gi"))
		})
	})

	Context("environment related fields", func() {
		It("stag env related fields", func() {
			bkapp.SetAnnotations(map[string]string{paasv1alpha2.EnvironmentKey: "stag"})

			// Value overwritten by overlay config
			web, _ := BuildProcDeployment(bkapp, "web")
			hi, _ := BuildProcDeployment(bkapp, "hi")
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
			bkapp.SetAnnotations(map[string]string{paasv1alpha2.EnvironmentKey: "prod"})
			web, _ := BuildProcDeployment(bkapp, "web")
			hi, _ := BuildProcDeployment(bkapp, "hi")
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

	Context("Mounts related fields", func() {
		It("mount configmap", func() {
			configMapName := "nginx-configmap"

			bkapp.Spec.Mounts = []paasv1alpha2.Mount{
				{
					MountPath: "/etc/nginx",
					Name:      "nginx-conf",
					Source: &paasv1alpha2.VolumeSource{
						ConfigMap: &paasv1alpha2.ConfigMapSource{Name: configMapName},
					},
				},
			}
			webDeploy, _ := BuildProcDeployment(bkapp, "web")
			hiDeploy, _ := BuildProcDeployment(bkapp, "hi")

			Expect(webDeploy.Spec.Template.Spec.Containers[0].VolumeMounts).To(HaveLen(1))
			Expect(webDeploy.Spec.Template.Spec.Containers[0].VolumeMounts[0].Name).To(Equal("nginx-conf"))
			Expect(webDeploy.Spec.Template.Spec.Containers[0].VolumeMounts[0].MountPath).To(Equal("/etc/nginx"))
			Expect(webDeploy.Spec.Template.Spec.Volumes[0].ConfigMap.Name).To(Equal(configMapName))

			Expect(hiDeploy.Spec.Template.Spec.Containers[0].VolumeMounts).To(HaveLen(1))
			Expect(hiDeploy.Spec.Template.Spec.Volumes[0].ConfigMap.Name).To(Equal(configMapName))
		})
	})

	Context("DomainResolution field", func() {
		It("with empty values", func() {
			bkapp.Spec.DomainResolution = nil

			web, _ := BuildProcDeployment(bkapp, "web")
			Expect(web.Spec.Template.Spec.HostAliases).To(BeEmpty())
			Expect(web.Spec.Template.Spec.DNSConfig).To(BeNil())
		})
		It("with non-empty HostAliases", func() {
			bkapp.Spec.DomainResolution = &paasv1alpha2.DomainResConfig{
				HostAliases: []paasv1alpha2.HostAlias{
					{IP: "127.0.0.1", Hostnames: []string{"foo.local", "bar.local"}},
					{IP: "192.168.1.1", Hostnames: []string{"foobar.local"}},
				},
			}

			web, _ := BuildProcDeployment(bkapp, "web")
			Expect(len(web.Spec.Template.Spec.HostAliases)).To(Equal(2))
			Expect(web.Spec.Template.Spec.HostAliases[1].IP).To(Equal("192.168.1.1"))
			Expect(web.Spec.Template.Spec.HostAliases[1].Hostnames).To(Equal([]string{"foobar.local"}))
			Expect(web.Spec.Template.Spec.DNSConfig).To(BeNil())
		})
		It("with non-empty Nameservers", func() {
			bkapp.Spec.DomainResolution = &paasv1alpha2.DomainResConfig{Nameservers: []string{"8.8.8.8"}}

			web, _ := BuildProcDeployment(bkapp, "web")
			Expect(web.Spec.Template.Spec.DNSConfig.Nameservers).To(Equal([]string{"8.8.8.8"}))
			Expect(web.Spec.Template.Spec.HostAliases).To(BeEmpty())
		})
	})

	It("test build deployment for cnb runtime image", func() {
		bkapp.Annotations[paasv1alpha2.UseCNBAnnoKey] = "true"
		for _, proc := range bkapp.Spec.Processes {
			deployment, _ := BuildProcDeployment(bkapp, proc.Name)

			Expect(len(deployment.Spec.Template.Spec.Containers)).To(Equal(1))
			c := deployment.Spec.Template.Spec.Containers[0]

			By("test Command should be override by '${proc.Name}'")
			Expect(c.Command).To(Equal([]string{proc.Name}))

			By("test Args should be clear")
			Expect(c.Args).To(BeNil())
		}
	})

	Context("Test build deployment with container port", func() {
		It("has process services", func() {
			bkapp.Spec.Processes[0].Services = []paasv1alpha2.ProcService{
				{Name: "web", TargetPort: 30000},
				{Name: "metric", TargetPort: 30001},
			}

			web, _ := BuildProcDeployment(bkapp, "web")
			Expect(
				web.Spec.Template.Spec.Containers[0].Ports,
			).To(Equal([]corev1.ContainerPort{{ContainerPort: 30000}, {ContainerPort: 30001}}))
		})
		It("has no process services", func() {
			web, _ := BuildProcDeployment(bkapp, "web")
			Expect(
				web.Spec.Template.Spec.Containers[0].Ports,
			).To(Equal([]corev1.ContainerPort{{ContainerPort: 80}}))
		})
	})

	Context("Test getSerializedBkApp", func() {
		It("normal case", func() {
			bkapp = &paasv1alpha2.BkApp{}
			_, err := getSerializedBkApp(bkapp)
			Expect(err).To(Not(HaveOccurred()))
		})
	})
})
