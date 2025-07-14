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

package components_test

import (
	"encoding/json"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	componentsMgr "bk.tencent.com/paas-app-operator/pkg/components/manager"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/processes/components"
)

var _ = Describe("ComponentMutator", func() {
	var scheme *runtime.Scheme

	BeforeEach(func() {
		scheme = runtime.NewScheme()
		_ = corev1.AddToScheme(scheme)
		_ = appsv1.AddToScheme(scheme)
		_ = paasv1alpha2.AddToScheme(scheme)
	})

	Describe("PatchAllComponentToDeployment", func() {
		var deploy *appsv1.Deployment

		BeforeEach(func() {
			componentsMgr.DefaultComponentDir = "../../../../components/components"

			deploy = &appsv1.Deployment{
				ObjectMeta: metav1.ObjectMeta{
					Name: "test-deploy",
				},
				Spec: appsv1.DeploymentSpec{
					Replicas: paasv1alpha2.ReplicasOne,
					Template: corev1.PodTemplateSpec{
						Spec: corev1.PodSpec{
							Containers: []corev1.Container{
								{
									Name:  "web",
									Image: "nginx:latest",
									Ports: []corev1.ContainerPort{
										{
											ContainerPort: 80,
											Protocol:      corev1.ProtocolTCP,
										},
									},
									Env: []corev1.EnvVar{
										{
											Name:  "ENVIRONMENT",
											Value: "test",
										},
									},
								},
							},
						},
					},
				},
			}
		})

		It("apply env_overlay component to deployment", func() {
			proc := &paasv1alpha2.Process{
				Name: "web",
				Components: []paasv1alpha2.Component{
					{
						Type:    "env_overlay",
						Version: "v1",
						Properties: runtime.RawExtension{
							Raw: []byte(
								`{"env": [{"name":"testKey","value":"testValue"}, {"name":"testKey2","value":"testValue2"}]}`,
							),
						},
					},
				},
			}
			err := components.PatchAllComponentToDeployment(proc, deploy)
			Expect(err).NotTo(HaveOccurred())
			Expect(len(deploy.Spec.Template.Spec.Containers)).To(Equal(1))
			Expect(deploy.Spec.Template.Spec.Containers[0].Env).To(
				ContainElement(
					WithTransform(func(e corev1.EnvVar) string {
						return e.Name
					}, Equal("testKey")),
				),
			)
			Expect(deploy.Spec.Template.Spec.Containers[0].Env).To(
				ContainElement(
					WithTransform(func(e corev1.EnvVar) string {
						return e.Value
					}, Equal("testValue")),
				),
			)
		})

		It("apply cl5 component to deployment", func() {
			proc := &paasv1alpha2.Process{
				Name: "web",
				Components: []paasv1alpha2.Component{
					{
						Type:    "cl5",
						Version: "v1",
					},
				},
			}
			err := components.PatchAllComponentToDeployment(proc, deploy)
			Expect(err).NotTo(HaveOccurred())
			Expect(len(deploy.Spec.Template.Spec.Containers)).To(Equal(2))
			jsonBytes, err := json.MarshalIndent(deploy.Spec.Template.Spec.Containers[0], "", "  ")
			Expect(err).NotTo(HaveOccurred())
			cl5Container := `{
  "name": "cl5",
  "image": "mirrors.tencent.com/bkpaas/cl5-agent:4.3.0.3",
  "ports": [
    {
      "name": "l5-config",
      "containerPort": 7778,
      "protocol": "UDP"
    },
    {
      "name": "l5-agent-1",
      "containerPort": 8888,
      "protocol": "UDP"
    },
    {
      "name": "l5-agent-2",
      "containerPort": 8889,
      "protocol": "UDP"
    },
    {
      "name": "l5-agent-3",
      "containerPort": 8890,
      "protocol": "UDP"
    }
  ],
  "env": [
    {
      "name": "ENVIRONMENT",
      "value": "test"
    }
  ],
  "resources": {},
  "livenessProbe": {
    "exec": {
      "command": [
        "/usr/local/services/liveness_check.sh"
      ]
    },
    "timeoutSeconds": 1,
    "periodSeconds": 10,
    "successThreshold": 1,
    "failureThreshold": 3
  },
  "readinessProbe": {
    "exec": {
      "command": [
        "/usr/local/services/readiness_check.sh"
      ]
    },
    "timeoutSeconds": 1,
    "periodSeconds": 10,
    "successThreshold": 1,
    "failureThreshold": 3
  },
  "terminationMessagePath": "/dev/termination-log",
  "terminationMessagePolicy": "File",
  "imagePullPolicy": "Always"
}`
			Expect(string(jsonBytes)).To(Equal(cl5Container))
		})

		It("should return error and stop processing", func() {
			proc := &paasv1alpha2.Process{
				Name: "web",
				Components: []paasv1alpha2.Component{
					{
						Type:    "non-existent",
						Version: "v1",
						Properties: runtime.RawExtension{
							Raw: []byte(
								`{"env": [{"name":"testKey","value":"testValue"}, {"name":"testKey2","value":"testValue2"}]}`,
							),
						},
					},
				},
			}
			err := components.PatchAllComponentToDeployment(proc, deploy)
			Expect(err).To(HaveOccurred())
		})
	})
})
