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

package v1alpha2_test

import (
	"fmt"
	"math"
	"strings"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"

	paasv1alpha1 "bk.tencent.com/paas-app-operator/api/v1alpha1"
	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/config"
	"bk.tencent.com/paas-app-operator/pkg/kubeutil"
	"bk.tencent.com/paas-app-operator/pkg/utils/stringx"
)

var _ = Describe("test webhook.Defaulter", func() {
	It("normal case", func() {
		bkapp := &paasv1alpha2.BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       paasv1alpha2.KindBkApp,
				APIVersion: paasv1alpha2.GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      "bkapp-sample",
				Namespace: "default",
			},
			Spec: paasv1alpha2.AppSpec{
				Processes: []paasv1alpha2.Process{
					{
						Name: "web",
					},
				},
			},
		}

		bkapp.Default()
		Expect(bkapp.Spec.Build.ImagePullPolicy).To(Equal(corev1.PullIfNotPresent))

		web := bkapp.Spec.GetWebProcess()
		Expect(web.TargetPort).To(Equal(int32(5000)))
		Expect(web.ResQuotaPlan).To(Equal(paasv1alpha2.ResQuotaPlanDefault))
	})
})

var _ = Describe("test webhook.Validator", func() {
	var bkapp *paasv1alpha2.BkApp

	BeforeEach(func() {
		bkapp = &paasv1alpha2.BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       paasv1alpha2.KindBkApp,
				APIVersion: paasv1alpha2.GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      "bkapp-sample",
				Namespace: "default",
				Annotations: map[string]string{
					paasv1alpha2.BkAppCodeKey:  "bkapp-sample",
					paasv1alpha2.ModuleNameKey: paasv1alpha2.DefaultModuleName,
				},
			},
			Spec: paasv1alpha2.AppSpec{
				Build: paasv1alpha2.BuildConfig{
					Image:           "nginx:latest",
					ImagePullPolicy: corev1.PullIfNotPresent,
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
			},
		}
	})

	Context("Test BkApp actions", func() {
		It("Create normal", func() {
			err := bkapp.ValidateCreate()
			Expect(err).ShouldNot(HaveOccurred())
		})

		It("Update normal", func() {
			err := bkapp.ValidateUpdate(bkapp)
			Expect(err).ShouldNot(HaveOccurred())
		})

		It("Delete normal", func() {
			err := bkapp.ValidateDelete()
			Expect(err).ShouldNot(HaveOccurred())
		})
	})

	Context("Test app's basic fields", func() {
		It("App name invalid", func() {
			bkapp.Name = "bkapp-sample-very" + strings.Repeat("-long", 20)
			bkapp.Annotations[paasv1alpha2.BkAppCodeKey] = bkapp.Name
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("must match regex"))

			bkapp.Name = "bkapp-sample-UPPER-CASE"
			bkapp.Annotations[paasv1alpha2.BkAppCodeKey] = bkapp.Name
			err = bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("must match regex"))
		})

		DescribeTable(
			"Validate annotations",
			func(appName, appCode, moduleName, errMsgPart string) {
				bkapp.Name = appName
				bkapp.Annotations[paasv1alpha2.BkAppCodeKey] = appCode
				bkapp.Annotations[paasv1alpha2.ModuleNameKey] = moduleName

				err := bkapp.ValidateCreate()
				if errMsgPart != "" {
					Expect(err.Error()).To(ContainSubstring(errMsgPart))
				} else {
					Expect(err).ShouldNot(HaveOccurred())
				}
			},
			Entry("valid", "test-app-m-backend", "test-app", "backend", ""),
			Entry("valid", "test-app", "test-app", paasv1alpha2.DefaultModuleName, ""),
			Entry("invalid", "test-app", "test-app1", paasv1alpha2.DefaultModuleName, "don't match with"),
			Entry("invalid", "test-app-m", "test-app", "backend", "don't match with"),
		)
	})

	Context("Test spec.build fields", func() {
		It("Image pull policy invalid", func() {
			bkapp.Spec.Build.ImagePullPolicy = "ALWAYS"
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("supported values: \"IfNotPresent\", \"Always\""))
		})
	})

	Context("Test process basic", func() {
		It("Processes empty", func() {
			bkapp.Spec.Processes = []paasv1alpha2.Process{}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("processes can't be empty"))
		})

		It("Processes exceed limit", func() {
			processes := make([]paasv1alpha2.Process, 0)

			i := int32(0)
			for ; i < config.Global.GetMaxProcesses()+1; i++ {
				processes = append(processes, paasv1alpha2.Process{
					Name: fmt.Sprintf("web-%d", i),
				})
			}

			bkapp.Spec.Processes = processes
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring(`number of processes has exceeded limit`))
		})

		It("Process name duplicated", func() {
			bkapp.Spec.Processes[1].Name = "web"
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring(`process "web" is duplicated`))
		})

		It("process name invalid", func() {
			bkapp.Spec.Processes[1].Name = "Web"
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("must match regex"))

			bkapp.Spec.Processes[1].Name = "web-hello-hi-too-long"
			err = bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("must match regex"))
		})

		It("replicas is too big", func() {
			var newReplicas int32 = math.MaxUint16
			bkapp.Spec.Processes[0].Replicas = &newReplicas
			err := bkapp.ValidateCreate()
			Expect(
				err.Error(),
			).To(ContainSubstring(fmt.Sprintf("at most support %d replicas", config.Global.GetProcMaxReplicas())))
		})

		It("resource quota plan unsupported", func() {
			bkapp.Spec.Processes[0].ResQuotaPlan = "fake"
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("supported values: \"default\", \"4C1G\""))
		})
	})

	Context("Test process autoscaling", func() {
		It("Invalid minReplicas", func() {
			bkapp.Spec.Processes[0].Autoscaling = &paasv1alpha2.AutoscalingSpec{
				MinReplicas: 0, MaxReplicas: 5, Policy: paasv1alpha2.ScalingPolicyDefault,
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("minReplicas must be greater than 0"))
		})

		It("Invalid maxReplicas", func() {
			bkapp.Spec.Processes[0].Autoscaling = &paasv1alpha2.AutoscalingSpec{
				MinReplicas: 1, MaxReplicas: 6, Policy: paasv1alpha2.ScalingPolicyDefault,
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("at most support 5 replicas"))
		})

		It("maxReplicas < minReplicas", func() {
			bkapp.Spec.Processes[0].Autoscaling = &paasv1alpha2.AutoscalingSpec{
				MinReplicas: 3, MaxReplicas: 2, Policy: paasv1alpha2.ScalingPolicyDefault,
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("maxReplicas must be greater than or equal to minReplicas"))
		})

		It("policy required", func() {
			bkapp.Spec.Processes[0].Autoscaling = &paasv1alpha2.AutoscalingSpec{
				MinReplicas: 1, MaxReplicas: 3, Policy: "",
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("autoscaling policy is required"))
		})

		It("policy must supported", func() {
			bkapp.Spec.Processes[0].Autoscaling = &paasv1alpha2.AutoscalingSpec{
				MinReplicas: 1, MaxReplicas: 3, Policy: "fake",
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("supported values: \"default\""))
		})
	})

	Context("Test mounts", func() {
		It("Normal", func() {
			bkapp.Spec.Mounts = []paasv1alpha2.Mount{
				{
					Name:      "redis-conf",
					MountPath: "/etc/redis",
					Source: &paasv1alpha2.VolumeSource{
						ConfigMap: &paasv1alpha2.ConfigMapSource{Name: "redis-configmap"},
					},
				},
				{
					Name:      "nginx-conf",
					MountPath: "/etc/nginx/conf",
					Source: &paasv1alpha2.VolumeSource{
						ConfigMap: &paasv1alpha2.ConfigMapSource{Name: "nginx-configmap"},
					},
				},
			}

			err := bkapp.ValidateCreate()
			Expect(err).To(BeNil())
		})
		It("Invalid name", func() {
			bkapp.Spec.Mounts = []paasv1alpha2.Mount{{
				Name:      "redis_conf",
				MountPath: "/etc/redis",
				Source: &paasv1alpha2.VolumeSource{
					ConfigMap: &paasv1alpha2.ConfigMapSource{Name: "redis-configmap"},
				},
			}}

			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("a lowercase RFC 1123 label must consist of"))
		})
		It("Invalid mountPath", func() {
			bkapp.Spec.Mounts = []paasv1alpha2.Mount{{
				Name:      "nginx-conf",
				MountPath: "etc",
				Source: &paasv1alpha2.VolumeSource{
					ConfigMap: &paasv1alpha2.ConfigMapSource{Name: "nginx-configmap"},
				},
			}}

			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("must match regex"))
		})
		It("Duplicate name", func() {
			sameName := "sample-conf"
			bkapp.Spec.Mounts = []paasv1alpha2.Mount{
				{
					Name:      sameName,
					MountPath: "/etc/redis",
					Source: &paasv1alpha2.VolumeSource{
						ConfigMap: &paasv1alpha2.ConfigMapSource{Name: "redis-configmap"},
					},
				},
				{
					Name:      sameName,
					MountPath: "/etc/nginx/conf",
					Source: &paasv1alpha2.VolumeSource{
						ConfigMap: &paasv1alpha2.ConfigMapSource{Name: "nginx-configmap"},
					},
				},
			}

			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("Duplicate value"))
		})
		It("Duplicate mountPath", func() {
			samePath := "/etc/sample"
			bkapp.Spec.Mounts = []paasv1alpha2.Mount{
				{
					Name:      "redis-conf",
					MountPath: samePath,
					Source: &paasv1alpha2.VolumeSource{
						ConfigMap: &paasv1alpha2.ConfigMapSource{Name: "redis-configmap"},
					},
				},
				{
					Name:      "nginx-conf",
					MountPath: samePath,
					Source: &paasv1alpha2.VolumeSource{
						ConfigMap: &paasv1alpha2.ConfigMapSource{Name: "nginx-configmap"},
					},
				},
			}

			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("Duplicate value"))
		})

		It("Invalid source", func() {
			bkapp.Spec.Mounts = []paasv1alpha2.Mount{{
				Name:      "redis-conf",
				MountPath: "/etc/redis",
				Source:    &paasv1alpha2.VolumeSource{},
			}}

			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("unknown volume source"))
		})

		It("Source is nil", func() {
			bkapp.Spec.Mounts = []paasv1alpha2.Mount{{
				Name:      "redis-conf",
				MountPath: "/etc/redis",
				Source:    nil,
			}}

			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("Required value"))
		})
	})

	Context("Test DomainResolution nameservers", func() {
		It("Invalid IP address", func() {
			bkapp.Spec.DomainResolution = &paasv1alpha2.DomainResConfig{
				Nameservers: []string{"foo@example!"},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("must be valid IP address"))
		})
		It("Too many entries", func() {
			bkapp.Spec.DomainResolution = &paasv1alpha2.DomainResConfig{
				Nameservers: []string{"8.8.8.8", "8.8.8.9", "1.1.1.1"},
			}
			err := bkapp.ValidateCreate()
			Expect(
				err.Error(),
			).To(ContainSubstring(fmt.Sprintf("must not have more than %v nameservers", paasv1alpha2.MaxDNSNameservers)))
		})
		It("Normal", func() {
			bkapp.Spec.DomainResolution = &paasv1alpha2.DomainResConfig{
				Nameservers: []string{"8.8.8.8", "1.1.1.1"},
			}
			Expect(bkapp.ValidateCreate()).To(BeNil())
		})
	})

	Context("Test DomainResolution hostAliases", func() {
		It("Invalid IP address", func() {
			bkapp.Spec.DomainResolution = &paasv1alpha2.DomainResConfig{
				HostAliases: []paasv1alpha2.HostAlias{
					{IP: "foo@invalid!"},
				},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("must be valid IP address"))
		})
		It("Invalid hostname", func() {
			bkapp.Spec.DomainResolution = &paasv1alpha2.DomainResConfig{
				HostAliases: []paasv1alpha2.HostAlias{
					{IP: "127.0.0.1", Hostnames: []string{"foo@invalid!"}},
				},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("must be valid hostname"))
		})
		It("Normal", func() {
			bkapp.Spec.DomainResolution = &paasv1alpha2.DomainResConfig{
				HostAliases: []paasv1alpha2.HostAlias{
					{
						IP:        "127.0.0.1",
						Hostnames: []string{"foo.localhost", "bar.localhost"},
					},
				},
			}
			Expect(bkapp.ValidateCreate()).To(BeNil())
		})
	})

	Context("Test envOverlay", func() {
		BeforeEach(func() {
			bkapp.Spec.EnvOverlay = &paasv1alpha2.AppEnvOverlay{}
		})
		It("Normal", func() {
			bkapp.Spec.EnvOverlay = &paasv1alpha2.AppEnvOverlay{
				Replicas: []paasv1alpha2.ReplicasOverlay{
					{EnvName: "stag", Process: "web", Count: 1},
				},
				ResQuotas: []paasv1alpha2.ResQuotaOverlay{
					{EnvName: "prod", Process: "web", Plan: paasv1alpha2.ResQuotaPlan4C1G},
				},
				EnvVariables: []paasv1alpha2.EnvVarOverlay{
					{EnvName: "stag", Name: "foo", Value: "foo-value"},
				},
				Autoscaling: []paasv1alpha2.AutoscalingOverlay{
					{
						EnvName: "stag",
						Process: "web",
						AutoscalingSpec: paasv1alpha2.AutoscalingSpec{
							MinReplicas: 2,
							MaxReplicas: 5,
							Policy:      paasv1alpha2.ScalingPolicyDefault,
						},
					},
				},
				Mounts: []paasv1alpha2.MountOverlay{
					{
						Mount: paasv1alpha2.Mount{
							Name:      "nginx-mount",
							MountPath: "/path/nginx",
							Source: &paasv1alpha2.VolumeSource{
								ConfigMap: &paasv1alpha2.ConfigMapSource{Name: "nginx-configmag"},
							},
						},
						EnvName: paasv1alpha2.ProdEnv,
					},
				},
			}

			err := bkapp.ValidateCreate()
			Expect(err).To(BeNil())
		})
		It("[replicas] invalid envName", func() {
			bkapp.Spec.EnvOverlay.Replicas = []paasv1alpha2.ReplicasOverlay{
				{EnvName: "invalid-env", Process: "web", Count: 1},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("envName is invalid"))
		})
		It("[replicas] invalid process name", func() {
			bkapp.Spec.EnvOverlay.Replicas = []paasv1alpha2.ReplicasOverlay{
				{EnvName: "stag", Process: "invalid-proc", Count: 1},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("process name is invalid"))
		})
		It("[replicas] invalid count", func() {
			bkapp.Spec.EnvOverlay.Replicas = []paasv1alpha2.ReplicasOverlay{
				{EnvName: "stag", Process: "web", Count: 100},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("count can't be greater than "))
		})
		It("[resQuota] invalid envName", func() {
			bkapp.Spec.EnvOverlay.ResQuotas = []paasv1alpha2.ResQuotaOverlay{
				{EnvName: "invalid-env", Process: "web", Plan: paasv1alpha2.ResQuotaPlan4C1G},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("envName is invalid"))
		})
		It("[resQuota] invalid process name", func() {
			bkapp.Spec.EnvOverlay.ResQuotas = []paasv1alpha2.ResQuotaOverlay{
				{EnvName: "stag", Process: "invalid-proc", Plan: paasv1alpha2.ResQuotaPlan4C1G},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("process name is invalid"))
		})
		It("[resQuota] invalid resource quota plan", func() {
			bkapp.Spec.EnvOverlay.ResQuotas = []paasv1alpha2.ResQuotaOverlay{
				{EnvName: "stag", Process: "web", Plan: "invalid-plan"},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("supported values: \"default\", \"4C1G\""))
		})
		It("[envVariables] invalid envName", func() {
			bkapp.Spec.EnvOverlay.EnvVariables = []paasv1alpha2.EnvVarOverlay{
				{EnvName: "invalid-env", Name: "foo", Value: "bar"},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("envName is invalid"))
		})
		It("[autoscaling] invalid envName", func() {
			bkapp.Spec.EnvOverlay.Autoscaling = []paasv1alpha2.AutoscalingOverlay{
				{
					EnvName: "invalid-env",
					Process: "web",
					AutoscalingSpec: paasv1alpha2.AutoscalingSpec{
						MinReplicas: 2,
						MaxReplicas: 5,
						Policy:      paasv1alpha2.ScalingPolicyDefault,
					},
				},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("envName is invalid"))
		})
		It("[autoscaling] invalid process name", func() {
			bkapp.Spec.EnvOverlay.Autoscaling = []paasv1alpha2.AutoscalingOverlay{
				{
					EnvName: "stag",
					Process: "invalid-proc",
					AutoscalingSpec: paasv1alpha2.AutoscalingSpec{
						MinReplicas: 2,
						MaxReplicas: 5,
						Policy:      paasv1alpha2.ScalingPolicyDefault,
					},
				},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("process name is invalid"))
		})
		It("[autoscaling] invalid policy", func() {
			bkapp.Spec.EnvOverlay.Autoscaling = []paasv1alpha2.AutoscalingOverlay{
				{
					EnvName: "stag",
					Process: "web",
					AutoscalingSpec: paasv1alpha2.AutoscalingSpec{
						MinReplicas: 2, MaxReplicas: 5, Policy: "fake",
					},
				},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("supported values: \"default\""))
		})
		It("mountOverlay configMap normal", func() {
			bkapp.Spec.EnvOverlay.Mounts = []paasv1alpha2.MountOverlay{
				{
					Mount: paasv1alpha2.Mount{
						Name:      "nginx-mount",
						MountPath: "/path/nginx",
						Source: &paasv1alpha2.VolumeSource{
							ConfigMap: &paasv1alpha2.ConfigMapSource{Name: "nginx-configmag"},
						},
					},
					EnvName: paasv1alpha2.ProdEnv,
				},
				{
					Mount: paasv1alpha2.Mount{
						Name:      "etcd-mount",
						MountPath: "/path/etcd",
						Source: &paasv1alpha2.VolumeSource{
							ConfigMap: &paasv1alpha2.ConfigMapSource{Name: "etcd-configmap"},
						},
					},
					EnvName: paasv1alpha2.ProdEnv,
				},
			}
			err := bkapp.ValidateCreate()
			Expect(err).To(BeNil())
		})
		It("mountOverlay persistentStorage normal", func() {
			bkapp.Spec.EnvOverlay.Mounts = []paasv1alpha2.MountOverlay{
				{
					Mount: paasv1alpha2.Mount{
						Name:      "nginx-mount",
						MountPath: "/path/nginx",
						Source: &paasv1alpha2.VolumeSource{
							PersistentStorage: &paasv1alpha2.PersistentStorage{Name: "nginx-pvc"},
						},
					},
					EnvName: paasv1alpha2.ProdEnv,
				},
				{
					Mount: paasv1alpha2.Mount{
						Name:      "etcd-mount",
						MountPath: "/path/etcd",
						Source: &paasv1alpha2.VolumeSource{
							PersistentStorage: &paasv1alpha2.PersistentStorage{Name: "etcd-pvc"},
						},
					},
					EnvName: paasv1alpha2.ProdEnv,
				},
			}
			err := bkapp.ValidateCreate()
			Expect(err).To(BeNil())
		})
		It("mountOverlay invalid", func() {
			bkapp.Spec.EnvOverlay.Mounts = []paasv1alpha2.MountOverlay{
				{
					Mount: paasv1alpha2.Mount{
						Name:      "nginx-mount",
						MountPath: "/path/nginx",
						Source:    &paasv1alpha2.VolumeSource{},
					},
					EnvName: paasv1alpha2.ProdEnv,
				},
				{
					Mount: paasv1alpha2.Mount{
						Name:      "etcd-mount",
						MountPath: "/path/etcd",
						Source:    &paasv1alpha2.VolumeSource{},
					},
					EnvName: paasv1alpha2.ProdEnv,
				},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("unknown volume source"))
		})
	})

	Context("Test resQuota in annotations", func() {
		It("Normal", func() {
			legacyProcResConfig := make(paasv1alpha2.LegacyProcConfig)
			legacyProcResConfig["web"] = map[string]string{"cpu": "2", "memory": "2G"}
			_ = kubeutil.SetJsonAnnotation(bkapp, paasv1alpha2.LegacyProcResAnnoKey, legacyProcResConfig)

			err := bkapp.ValidateCreate()
			Expect(err).To(BeNil())
		})
		It("Invalid unset", func() {
			legacyProcResConfig := make(paasv1alpha2.LegacyProcConfig)
			legacyProcResConfig["web"] = map[string]string{"cpu": "", "memory": "2G"}
			_ = kubeutil.SetJsonAnnotation(bkapp, paasv1alpha2.LegacyProcResAnnoKey, legacyProcResConfig)

			err := bkapp.ValidateCreate()
			Expect(err).NotTo(BeNil())
		})
		It("Invalid exceed cpu max limit", func() {
			legacyProcResConfig := make(paasv1alpha2.LegacyProcConfig)
			legacyProcResConfig["web"] = map[string]string{"cpu": "6", "memory": "2G"}
			_ = kubeutil.SetJsonAnnotation(bkapp, paasv1alpha2.LegacyProcResAnnoKey, legacyProcResConfig)

			err := bkapp.ValidateCreate()
			Expect(err).NotTo(BeNil())
		})
		It("Invalid exceed memory max limit", func() {
			legacyProcResConfig := make(paasv1alpha2.LegacyProcConfig)
			legacyProcResConfig["web"] = map[string]string{"cpu": "2", "memory": "8G"}
			_ = kubeutil.SetJsonAnnotation(bkapp, paasv1alpha2.LegacyProcResAnnoKey, legacyProcResConfig)

			err := bkapp.ValidateCreate()
			Expect(err).NotTo(BeNil())
		})
	})
})

var _ = Describe("Integrated tests for webhooks, v1alpha1 version", func() {
	var suffix string

	// A shortcut to build a v1alpha1/BkApp object
	buildApp := func(spec paasv1alpha1.AppSpec) *paasv1alpha1.BkApp {
		bkAppName := "bkapp-" + suffix
		ret := &paasv1alpha1.BkApp{
			TypeMeta: metav1.TypeMeta{Kind: paasv1alpha1.KindBkApp, APIVersion: paasv1alpha1.GroupVersion.String()},
			ObjectMeta: metav1.ObjectMeta{
				Name:      bkAppName,
				Namespace: "default",
				Annotations: map[string]string{
					paasv1alpha2.BkAppCodeKey:  bkAppName,
					paasv1alpha2.ModuleNameKey: paasv1alpha2.DefaultModuleName,
				},
			},
		}
		ret.Spec = spec
		return ret
	}

	BeforeEach(func() {
		suffix = strings.ToLower(stringx.RandLetters(6))
	})

	It("Create BkApp with minimal required fields", func() {
		bkapp := buildApp(paasv1alpha1.AppSpec{
			Processes: []paasv1alpha1.Process{
				{Name: "web", Replicas: paasv1alpha1.ReplicasOne, Image: "nginx:latest"},
			},
		})
		Expect(k8sClient.Create(ctx, bkapp)).NotTo(HaveOccurred())
	})

	It("Check default values was set", func() {
		bkapp := buildApp(paasv1alpha1.AppSpec{
			Processes: []paasv1alpha1.Process{
				{Name: "web", Replicas: paasv1alpha1.ReplicasOne, Image: "nginx:latest"},
			},
		})
		Expect(k8sClient.Create(ctx, bkapp)).NotTo(HaveOccurred())

		// Check if default values have been set
		var createdBkApp paasv1alpha2.BkApp
		Expect(k8sClient.Get(ctx, client.ObjectKeyFromObject(bkapp), &createdBkApp)).NotTo(HaveOccurred())
		Expect(createdBkApp.Spec.Processes[0].TargetPort).To(Equal(paasv1alpha2.ProcDefaultTargetPort))
	})

	It("Create BkApp with duplicated processes", func() {
		bkapp := buildApp(paasv1alpha1.AppSpec{
			Processes: []paasv1alpha1.Process{
				{Name: "web", Replicas: paasv1alpha1.ReplicasOne},
				{Name: "web", Replicas: paasv1alpha1.ReplicasOne},
			},
		})
		Expect(k8sClient.Create(ctx, bkapp)).To(HaveOccurred())
	})

	It("Create BkApp with image absent", func() {
		bkapp := buildApp(paasv1alpha1.AppSpec{
			Processes: []paasv1alpha1.Process{
				{Name: "web", Replicas: paasv1alpha1.ReplicasOne},
			},
		})
		Expect(k8sClient.Create(ctx, bkapp)).To(HaveOccurred())
	})

	It("Create BkApp with EnvOverLay.Autoscaling", func() {
		bkapp := buildApp(paasv1alpha1.AppSpec{
			Processes: []paasv1alpha1.Process{
				{Name: "web", Replicas: paasv1alpha1.ReplicasOne, Image: "nginx:latest", Autoscaling: nil},
				{Name: "dev", Replicas: paasv1alpha1.ReplicasOne, Image: "nginx:latest", Autoscaling: nil},
			},
			EnvOverlay: &paasv1alpha1.AppEnvOverlay{
				Autoscaling: []paasv1alpha1.AutoscalingOverlay{
					{
						EnvName: "stag",
						Process: "web",
						AutoscalingSpec: paasv1alpha1.AutoscalingSpec{
							MinReplicas: 3,
							MaxReplicas: 5,
							Policy:      paasv1alpha1.ScalingPolicyDefault,
						},
					},
				},
			},
		})
		Expect(k8sClient.Create(ctx, bkapp)).NotTo(HaveOccurred())
	})
})

var _ = Describe("Integrated tests for webhooks, v1alpha2 version", func() {
	var suffix string

	// A shortcut to build a v1alpha2/BkApp object
	buildApp := func(spec paasv1alpha2.AppSpec) *paasv1alpha2.BkApp {
		bkAppName := "bkapp-" + suffix
		ret := &paasv1alpha2.BkApp{
			TypeMeta: metav1.TypeMeta{Kind: paasv1alpha2.KindBkApp, APIVersion: paasv1alpha2.GroupVersion.String()},
			ObjectMeta: metav1.ObjectMeta{
				Name:      bkAppName,
				Namespace: "default",
				Annotations: map[string]string{
					paasv1alpha2.BkAppCodeKey:  bkAppName,
					paasv1alpha2.ModuleNameKey: paasv1alpha2.DefaultModuleName,
				},
			},
		}
		ret.Spec = spec
		return ret
	}

	BeforeEach(func() {
		suffix = strings.ToLower(stringx.RandLetters(6))
	})

	It("Create BkApp with minimal required fields", func() {
		bkapp := buildApp(paasv1alpha2.AppSpec{
			Build:     paasv1alpha2.BuildConfig{Image: "nginx:latest"},
			Processes: []paasv1alpha2.Process{{Name: "web", Replicas: paasv1alpha2.ReplicasOne}},
		})
		Expect(k8sClient.Create(ctx, bkapp)).NotTo(HaveOccurred())
	})

	It("Create BkApp with image missing", func() {
		bkapp := buildApp(paasv1alpha2.AppSpec{
			Processes: []paasv1alpha2.Process{{Name: "web", Replicas: paasv1alpha2.ReplicasOne}},
		})
		Expect(k8sClient.Create(ctx, bkapp)).To(HaveOccurred())
	})
})
