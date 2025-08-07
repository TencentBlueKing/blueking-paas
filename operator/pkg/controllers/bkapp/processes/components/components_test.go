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
	"os"
	"path/filepath"

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

	Describe("PatchToDeployment", func() {
		var deploy *appsv1.Deployment
		var tempDir string

		BeforeEach(func() {
			tempDir, _ = os.MkdirTemp("", "components_test")
			componentsMgr.DefaultComponentDir = tempDir

			// 创建测试组件结构
			schema := `{
  "type": "object",
  "required": ["env"],
  "properties": {
    "env": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "value"],
        "properties": {
          "name": {
            "type": "string",
            "minLength": 1
          },
          "value": {
            "type": "string"
          }
        },
        "additionalProperties": false
      },
      "minItems": 1
    }
  },
  "additionalProperties": false
}`

			template := `
spec:
  template:
    spec:
      containers:
        - name: {{.procName}}
          env:
            {{- range .env }}
            - name: {{.name}}
              value: {{.value}}
            {{- end }}`
			createTestComponent(tempDir, "test_env_overlay", "v1", schema, template)

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

		AfterEach(func() {
			Expect(os.RemoveAll(tempDir)).To(Succeed())
		})

		It("apply component to deployment", func() {
			proc := &paasv1alpha2.Process{
				Name: "web",
				Components: []paasv1alpha2.Component{
					{
						Name:    "test_env_overlay",
						Version: "v1",
						Properties: runtime.RawExtension{
							Raw: []byte(
								`{"env": [{"name":"testKey","value":"testValue"}, {"name":"testKey2","value":"testValue2"}]}`,
							),
						},
					},
				},
			}
			err := components.PatchToDeployment(proc, deploy)
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

		It("should return error and stop processing", func() {
			proc := &paasv1alpha2.Process{
				Name: "web",
				Components: []paasv1alpha2.Component{
					{
						Name:    "non-existent",
						Version: "v1",
						Properties: runtime.RawExtension{
							Raw: []byte(
								`{"env": [{"name":"testKey","value":"testValue"}, {"name":"testKey2","value":"testValue2"}]}`,
							),
						},
					},
				},
			}
			err := components.PatchToDeployment(proc, deploy)
			Expect(err).To(HaveOccurred())
		})
	})
})

func createTestComponent(baseDir, cName, version, schema, template string) {
	versionDir := filepath.Join(baseDir, cName, version)
	Expect(os.MkdirAll(versionDir, 0o755)).To(Succeed())

	// 创建 schema.json
	schemaPath := filepath.Join(versionDir, "schema.json")
	Expect(os.WriteFile(schemaPath, []byte(schema), 0o644)).To(Succeed())

	// 创建 template.yaml
	templatePath := filepath.Join(versionDir, "template.yaml")
	Expect(os.WriteFile(templatePath, []byte(template), 0o644)).To(Succeed())
}
