/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) Tencent. All rights reserved.
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
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	"k8s.io/apimachinery/pkg/runtime"

	sandboxv1beta1 "bk.tencent.com/paas-app-operator/api/sandbox/v1beta1"
	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	componentsMgr "bk.tencent.com/paas-app-operator/pkg/components/manager"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/processes/components"
)

// sidecarTemplate mirrors operator/components/sidecar/v1/template.yaml (and the
// apiserver support-files copy). Keep them in sync.
const sidecarTemplate = `spec:
  podTemplate:
    containers:
      - name: {{ .name }}
        image: {{ .image | printf "%q" }}
        imagePullPolicy: IfNotPresent
        {{- with .command }}
        command:
          {{- range . }}
          - {{ . | printf "%q" }}
          {{- end }}
        {{- end }}
        {{- with .args }}
        args:
          {{- range . }}
          - {{ . | printf "%q" }}
          {{- end }}
        {{- end }}
        {{- with .env }}
        env:
          {{- range . }}
          - name: {{ .name | printf "%q" }}
            value: {{ .value | printf "%q" }}
          {{- end }}
        {{- end }}
        {{- with .ports }}
        ports:
          {{- range . }}
          - containerPort: {{ .containerPort }}
            {{- with .name }}
            name: {{ . | printf "%q" }}
            {{- end }}
            protocol: {{ with .protocol }}{{ . }}{{ else }}TCP{{ end }}
          {{- end }}
        {{- end }}
        {{- with .resources }}
        resources:
          {{- with .limits }}
          limits:
            {{- with .cpu }}
            cpu: {{ . | printf "%q" }}
            {{- end }}
            {{- with .memory }}
            memory: {{ . | printf "%q" }}
            {{- end }}
          {{- end }}
          {{- with .requests }}
          requests:
            {{- with .cpu }}
            cpu: {{ . | printf "%q" }}
            {{- end }}
            {{- with .memory }}
            memory: {{ . | printf "%q" }}
            {{- end }}
          {{- end }}
        {{- end }}
        {{- with .volumeMounts }}
        volumeMounts:
          {{- range . }}
          - name: {{ .name | printf "%q" }}
            mountPath: {{ .mountPath | printf "%q" }}
            {{- if .readOnly }}
            readOnly: true
            {{- end }}
          {{- end }}
        {{- end }}
      {{- with .mainContainerVolumeMounts }}
      - name: {{ $.procName | printf "%q" }}
        volumeMounts:
          {{- range . }}
          - name: {{ .name | printf "%q" }}
            mountPath: {{ .mountPath | printf "%q" }}
            {{- if .readOnly }}
            readOnly: true
            {{- end }}
          {{- end }}
      {{- end }}
    {{- with .sharedVolumes }}
    volumes:
      {{- range . }}
      - name: {{ .name | printf "%q" }}
        {{- if or .medium .sizeLimit }}
        emptyDir:
          {{- with .medium }}
          medium: {{ . | printf "%q" }}
          {{- end }}
          {{- with .sizeLimit }}
          sizeLimit: {{ . | printf "%q" }}
          {{- end }}
        {{- else }}
        emptyDir: {}
        {{- end }}
      {{- end }}
    {{- end }}
`

var _ = Describe("sidecar component", func() {
	var sbi *sandboxv1beta1.SandboxInstance
	var tempDir string

	sidecarComponent := func(props string) paasv1alpha2.Component {
		return paasv1alpha2.Component{
			Name:       "sidecar",
			Version:    "v1",
			Properties: runtime.RawExtension{Raw: []byte(props)},
		}
	}

	// containersByName indexes containers by name. A strategic merge patch
	// does not preserve list order, so containers must not be looked up by
	// position.
	containersByName := func(instance *sandboxv1beta1.SandboxInstance) map[string]corev1.Container {
		indexed := map[string]corev1.Container{}
		for _, c := range instance.Spec.PodTemplate.Containers {
			indexed[c.Name] = c
		}
		return indexed
	}

	BeforeEach(func() {
		tempDir, _ = os.MkdirTemp("", "sidecar_component_test")
		componentsMgr.DefaultComponentDir = tempDir
		versionDir := filepath.Join(tempDir, "sidecar", "v1")
		Expect(os.MkdirAll(versionDir, 0o755)).To(Succeed())
		Expect(
			os.WriteFile(filepath.Join(versionDir, "template.yaml"), []byte(sidecarTemplate), 0o644),
		).To(Succeed())

		sbi = &sandboxv1beta1.SandboxInstance{
			Spec: sandboxv1beta1.SandboxInstanceSpec{
				PodTemplate: sandboxv1beta1.SandboxPodTemplate{
					Containers: []corev1.Container{
						{
							Name:       "web",
							Image:      "my-agent:latest",
							Command:    []string{"/bin/sh", "-c", "python main.py"},
							WorkingDir: "/app",
							Env: []corev1.EnvVar{
								{Name: "APP_ENV", Value: "stag"},
							},
							Resources: corev1.ResourceRequirements{
								Limits: corev1.ResourceList{
									corev1.ResourceCPU:    resource.MustParse("1"),
									corev1.ResourceMemory: resource.MustParse("512Mi"),
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
		componentsMgr.DefaultComponentDir = "/components"
	})

	It("should include sidecar containers in SandboxInstance", func() {
		proc := &paasv1alpha2.Process{
			Name: "web",
			Components: []paasv1alpha2.Component{
				sidecarComponent(`{
					"name": "log-collector",
					"image": "fluentd:latest",
					"command": ["/bin/sh", "-c", "fluentd"],
					"env": [{"name": "LOG_LEVEL", "value": "info"}]
				}`),
			},
		}

		Expect(components.PatchToSandboxInstance(proc, sbi)).To(Succeed())
		Expect(sbi.Spec.PodTemplate.Containers).To(HaveLen(2))

		containers := containersByName(sbi)
		Expect(containers).To(HaveKey("web"))
		Expect(containers["web"].Image).To(Equal("my-agent:latest"))

		Expect(containers).To(HaveKey("log-collector"))
		sidecar := containers["log-collector"]
		Expect(sidecar.Image).To(Equal("fluentd:latest"))
		Expect(sidecar.Command).To(Equal([]string{"/bin/sh", "-c", "fluentd"}))
		Expect(sidecar.Env).To(HaveLen(1))
		Expect(sidecar.Env[0].Name).To(Equal("LOG_LEVEL"))
		Expect(sidecar.Env[0].Value).To(Equal("info"))
	})

	It("should include shared volumes and mount them on both containers", func() {
		proc := &paasv1alpha2.Process{
			Name: "web",
			Components: []paasv1alpha2.Component{
				sidecarComponent(`{
					"name": "worker",
					"image": "worker:v1",
					"sharedVolumes": [
						{"name": "shared-data", "sizeLimit": "1Gi"},
						{"name": "tmpfs-cache", "medium": "Memory"}
					],
					"volumeMounts": [{"name": "shared-data", "mountPath": "/data"}],
					"mainContainerVolumeMounts": [{"name": "shared-data", "mountPath": "/app/data"}]
				}`),
			},
		}

		Expect(components.PatchToSandboxInstance(proc, sbi)).To(Succeed())

		volumesByName := map[string]corev1.Volume{}
		for _, v := range sbi.Spec.PodTemplate.Volumes {
			volumesByName[v.Name] = v
		}
		Expect(volumesByName).To(HaveLen(2))
		Expect(volumesByName["shared-data"].EmptyDir).NotTo(BeNil())
		Expect(volumesByName["shared-data"].EmptyDir.SizeLimit.String()).To(Equal("1Gi"))
		Expect(volumesByName["tmpfs-cache"].EmptyDir.Medium).To(Equal(corev1.StorageMediumMemory))

		containers := containersByName(sbi)
		Expect(containers["web"].VolumeMounts).To(HaveLen(1))
		Expect(containers["web"].VolumeMounts[0].Name).To(Equal("shared-data"))
		Expect(containers["web"].VolumeMounts[0].MountPath).To(Equal("/app/data"))

		Expect(containers["worker"].VolumeMounts).To(HaveLen(1))
		Expect(containers["worker"].VolumeMounts[0].Name).To(Equal("shared-data"))
		Expect(containers["worker"].VolumeMounts[0].MountPath).To(Equal("/data"))
	})

	// A strategic merge patch grows a "merge" list by seeding new entries from
	// the existing ones, so a sidecar can silently inherit the main container's
	// command / env / resources / workingDir. That would make the sidecar run
	// the app's entrypoint and claim a second full resource quota, so the
	// injection must isolate the two containers.
	It("should not let a sidecar inherit main container fields", func() {
		proc := &paasv1alpha2.Process{
			Name: "web",
			Components: []paasv1alpha2.Component{
				// Only name and image are declared: everything else must stay unset.
				sidecarComponent(`{"name": "log-collector", "image": "fluentd:latest"}`),
			},
		}

		Expect(components.PatchToSandboxInstance(proc, sbi)).To(Succeed())
		Expect(sbi.Spec.PodTemplate.Containers).To(HaveLen(2))

		containers := containersByName(sbi)
		main := containers["web"]
		sidecar := containers["log-collector"]

		Expect(main.Image).To(Equal("my-agent:latest"))
		Expect(main.Command).To(Equal([]string{"/bin/sh", "-c", "python main.py"}))
		Expect(main.Resources.Limits).NotTo(BeEmpty())

		Expect(sidecar.Image).To(Equal("fluentd:latest"))
		Expect(sidecar.Command).To(BeEmpty(), "sidecar must not inherit the main container's command")
		Expect(sidecar.Args).To(BeEmpty(), "sidecar must not inherit the main container's args")
		Expect(sidecar.Env).To(BeEmpty(), "sidecar must not inherit the main container's env")
		Expect(sidecar.WorkingDir).To(BeEmpty(), "sidecar must not inherit the main container's workingDir")
		Expect(
			sidecar.Resources.Limits,
		).To(BeEmpty(), "sidecar must not inherit the main container's resource limits")
	})
})
