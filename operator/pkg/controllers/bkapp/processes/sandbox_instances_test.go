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

package processes

import (
	"context"
	"os"
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	sandboxv1beta1 "bk.tencent.com/paas-app-operator/api/sandbox/v1beta1"
	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	componentsMgr "bk.tencent.com/paas-app-operator/pkg/components/manager"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/names"
	"bk.tencent.com/paas-app-operator/pkg/kubeutil"
)

// sidecarTemplate mirrors support-files/components/sidecar/v1/template.yaml in
// the apiserver repo, which is the template shipped to the operator's component
// directory. Keep the two in sync.
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

var _ = Describe("Test SandboxInstanceReconciler", func() {
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
				Name:      "bkapp-agent-sample",
				Namespace: "default",
				Annotations: map[string]string{
					paasv1alpha2.BkAppRegionKey:   "default",
					paasv1alpha2.BkAppCodeKey:     "agent-sample",
					paasv1alpha2.BkAppNameKey:     "agent-sample",
					paasv1alpha2.ModuleNameKey:    "default",
					paasv1alpha2.EnvironmentKey:   "stag",
					paasv1alpha2.WlAppNameKey:     "bkapp-agent-sample-stag",
					paasv1alpha2.BkAppTenantIDKey: "system",
				},
			},
			Spec: paasv1alpha2.AppSpec{
				Build: paasv1alpha2.BuildConfig{
					Image: "my-agent:latest",
				},
				WorkloadType: paasv1alpha2.WorkloadTypeSandboxInstance,
				Processes: []paasv1alpha2.Process{
					{
						Name:         "web",
						Replicas:     paasv1alpha2.ReplicasOne,
						ResQuotaPlan: paasv1alpha2.ResQuotaPlanDefault,
						TargetPort:   8080,
					},
				},
			},
			Status: paasv1alpha2.AppStatus{
				DeployId: "deploy-123",
			},
		}

		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		Expect(paasv1alpha2.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(sandboxv1beta1.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(corev1.AddToScheme(scheme)).NotTo(HaveOccurred())
		builder.WithScheme(scheme)
	})

	Context("when workloadType is not sandboxInstance", func() {
		It("should skip reconciliation", func() {
			bkapp.Spec.WorkloadType = paasv1alpha2.WorkloadTypeDeployment
			cli := builder.WithObjects(bkapp).Build()
			r := NewSandboxInstanceReconciler(cli)

			result := r.Reconcile(context.Background(), bkapp)
			Expect(result.ShouldAbort()).To(BeFalse())
			Expect(result.Error()).To(BeNil())
		})

		It("should skip when workloadType is empty", func() {
			bkapp.Spec.WorkloadType = ""
			cli := builder.WithObjects(bkapp).Build()
			r := NewSandboxInstanceReconciler(cli)

			result := r.Reconcile(context.Background(), bkapp)
			Expect(result.ShouldAbort()).To(BeFalse())
			Expect(result.Error()).To(BeNil())
		})
	})

	Context("when workloadType is sandboxInstance", func() {
		It("should create SandboxInstance", func() {
			cli := builder.WithObjects(bkapp).Build()
			r := NewSandboxInstanceReconciler(cli)
			ctx := context.Background()

			result := r.Reconcile(ctx, bkapp)
			// After creation, SandboxInstance has no status yet, so the reconciler
			// sets BkApp to Pending and requests requeue — this is expected behavior.
			Expect(result.Error()).To(BeNil())

			// Verify SandboxInstance was created
			sbi := &sandboxv1beta1.SandboxInstance{}
			sbiName := names.Deployment(bkapp, "web")
			err := cli.Get(ctx, types.NamespacedName{
				Name: sbiName, Namespace: "default",
			}, sbi)
			Expect(err).NotTo(HaveOccurred())
			Expect(sbi.Spec.RuntimeClassName).To(Equal("cube"))
			Expect(sbi.Spec.Network.Mode).To(Equal("direct-cni"))
			Expect(sbi.Spec.DesiredState).To(Equal(sandboxv1beta1.SandboxDesiredStateRunning))
			// BkApp status should be Pending (waiting for sandbox to become Running)
			Expect(bkapp.Status.Phase).To(Equal(paasv1alpha2.AppPending))
		})

		It("should set owner reference", func() {
			cli := builder.WithObjects(bkapp).Build()
			r := NewSandboxInstanceReconciler(cli)
			ctx := context.Background()

			r.Reconcile(ctx, bkapp)

			sbi := &sandboxv1beta1.SandboxInstance{}
			sbiName := names.Deployment(bkapp, "web")
			err := cli.Get(ctx, types.NamespacedName{
				Name: sbiName, Namespace: "default",
			}, sbi)
			Expect(err).NotTo(HaveOccurred())
			Expect(sbi.OwnerReferences).To(HaveLen(1))
			Expect(sbi.OwnerReferences[0].Name).To(Equal(bkapp.Name))
			Expect(sbi.OwnerReferences[0].Kind).To(Equal(paasv1alpha2.KindBkApp))
		})

		It("should inject pod selector labels into PodTemplate", func() {
			cli := builder.WithObjects(bkapp).Build()
			r := NewSandboxInstanceReconciler(cli)
			ctx := context.Background()

			r.Reconcile(ctx, bkapp)

			sbi := &sandboxv1beta1.SandboxInstance{}
			sbiName := names.Deployment(bkapp, "web")
			err := cli.Get(ctx, types.NamespacedName{
				Name: sbiName, Namespace: "default",
			}, sbi)
			Expect(err).NotTo(HaveOccurred())
			Expect(sbi.Spec.PodTemplate.Labels).To(HaveKeyWithValue(
				paasv1alpha2.BkAppNameKey, "bkapp-agent-sample",
			))
			Expect(sbi.Spec.PodTemplate.Labels).To(HaveKeyWithValue(
				paasv1alpha2.ProcessNameKey, "web",
			))
			Expect(sbi.Spec.PodTemplate.Labels).To(HaveKeyWithValue(
				paasv1alpha2.ResourceTypeKey, "process",
			))
			Expect(sbi.Spec.PodTemplate.Labels).To(HaveKeyWithValue(
				paasv1alpha2.ModuleNameKey, "default",
			))
		})

		It("should set container image and command", func() {
			bkapp.Spec.Processes[0].Command = []string{"/bin/sh", "-c", "python main.py"}
			cli := builder.WithObjects(bkapp).Build()
			r := NewSandboxInstanceReconciler(cli)
			ctx := context.Background()

			r.Reconcile(ctx, bkapp)

			sbi := &sandboxv1beta1.SandboxInstance{}
			sbiName := names.Deployment(bkapp, "web")
			_ = cli.Get(ctx, types.NamespacedName{
				Name: sbiName, Namespace: "default",
			}, sbi)
			Expect(sbi.Spec.PodTemplate.Containers).To(HaveLen(1))
			Expect(sbi.Spec.PodTemplate.Containers[0].Image).To(Equal("my-agent:latest"))
			Expect(sbi.Spec.PodTemplate.Containers[0].Command).To(Equal([]string{"/bin/sh", "-c", "python main.py"}))
		})
	})

	Context("test buildSandboxInstance", func() {
		It("should return error when no process defined", func() {
			bkapp.Spec.Processes = nil
			r := NewSandboxInstanceReconciler(nil)
			_, err := r.buildSandboxInstance(context.Background(), bkapp)
			Expect(err).To(HaveOccurred())
			Expect(err.Error()).To(ContainSubstring("no process defined"))
		})

		It("should use first process if web not found", func() {
			bkapp.Spec.Processes = []paasv1alpha2.Process{
				{
					Name:         "worker",
					Replicas:     paasv1alpha2.ReplicasOne,
					ResQuotaPlan: paasv1alpha2.ResQuotaPlanDefault,
					TargetPort:   9090,
				},
			}
			r := NewSandboxInstanceReconciler(nil)
			sbi, err := r.buildSandboxInstance(context.Background(), bkapp)
			Expect(err).NotTo(HaveOccurred())
			Expect(sbi.Name).To(Equal(names.Deployment(bkapp, "worker")))
		})
	})

	Context("test updateBkAppStatus", func() {
		It("should map Running phase", func() {
			sbi := &sandboxv1beta1.SandboxInstance{
				Status: sandboxv1beta1.SandboxInstanceStatus{
					Phase: sandboxv1beta1.SandboxPhaseRunning,
				},
			}
			r := NewSandboxInstanceReconciler(nil)
			r.updateBkAppStatus(bkapp, sbi)
			Expect(bkapp.Status.Phase).To(Equal(paasv1alpha2.AppRunning))
		})

		It("should map Failed phase", func() {
			sbi := &sandboxv1beta1.SandboxInstance{
				Status: sandboxv1beta1.SandboxInstanceStatus{
					Phase:   sandboxv1beta1.SandboxPhaseFailed,
					Message: "OOM killed",
				},
			}
			r := NewSandboxInstanceReconciler(nil)
			r.updateBkAppStatus(bkapp, sbi)
			Expect(bkapp.Status.Phase).To(Equal(paasv1alpha2.AppFailed))
		})

		It("should map Pending/Creating phase", func() {
			sbi := &sandboxv1beta1.SandboxInstance{
				Status: sandboxv1beta1.SandboxInstanceStatus{
					Phase: sandboxv1beta1.SandboxPhaseCreating,
				},
			}
			r := NewSandboxInstanceReconciler(nil)
			r.updateBkAppStatus(bkapp, sbi)
			Expect(bkapp.Status.Phase).To(Equal(paasv1alpha2.AppPending))
		})
	})

	Context("test container resources and domain", func() {
		// Process quota lands on podTemplate.containers[].resources. Domain is
		// left empty ({}); sandbox-controller derives the guest size from the
		// first container when cpu/memory are omitted.
		It("should keep the quota plan's resources on the container", func() {
			r := NewSandboxInstanceReconciler(nil)
			sbi, err := r.buildSandboxInstance(context.Background(), bkapp)
			Expect(err).NotTo(HaveOccurred())

			// The "default" quota plan resolves to 4000m CPU / 1024Mi memory limits
			// and 200m CPU / 256Mi memory requests.
			res := sbi.Spec.PodTemplate.Containers[0].Resources
			Expect(res.Limits.Cpu().Equal(resource.MustParse("4"))).To(BeTrue())
			Expect(res.Limits.Memory().Equal(resource.MustParse("1024Mi"))).To(BeTrue())
			Expect(res.Requests.Cpu().Equal(resource.MustParse("200m"))).To(BeTrue())
			Expect(res.Requests.Memory().Equal(resource.MustParse("256Mi"))).To(BeTrue())
		})

		It("should leave domain empty so guest size can be derived", func() {
			r := NewSandboxInstanceReconciler(nil)
			sbi, err := r.buildSandboxInstance(context.Background(), bkapp)
			Expect(err).NotTo(HaveOccurred())
			Expect(sbi.Spec.Domain).To(Equal(sandboxv1beta1.SandboxDomain{}))
			Expect(sbi.Spec.Domain.CPU.Cores).To(BeZero())
			Expect(sbi.Spec.Domain.Memory).To(BeEmpty())
		})

		It("should keep sub-core CPU limits untouched on the container", func() {
			Expect(kubeutil.SetJsonAnnotation(
				bkapp, paasv1alpha2.LegacyProcResAnnoKey, paasv1alpha2.LegacyProcConfig{
					"web": {"cpu": "1500m", "memory": "512Mi"},
				},
			)).To(Succeed())

			r := NewSandboxInstanceReconciler(nil)
			sbi, err := r.buildSandboxInstance(context.Background(), bkapp)
			Expect(err).NotTo(HaveOccurred())

			limits := sbi.Spec.PodTemplate.Containers[0].Resources.Limits
			Expect(limits.Cpu().Equal(resource.MustParse("1500m"))).To(BeTrue())
			Expect(limits.Memory().Equal(resource.MustParse("512Mi"))).To(BeTrue())
			Expect(sbi.Spec.Domain).To(Equal(sandboxv1beta1.SandboxDomain{}))
		})
	})

	Context("test DeploymentReconciler skips isolated", func() {
		It("should skip when workloadType is sandboxInstance", func() {
			bkapp.Spec.WorkloadType = paasv1alpha2.WorkloadTypeSandboxInstance
			cli := builder.WithObjects(bkapp).Build()
			r := NewDeploymentReconciler(cli)
			ctx := context.Background()

			result := r.Reconcile(ctx, bkapp)
			Expect(result.ShouldAbort()).To(BeFalse())
			// No deployments should be created
		})
	})

	Context("test sidecar component support", func() {
		var tempDir string

		// sidecarComponent builds a Component entry carrying the given properties.
		sidecarComponent := func(props string) paasv1alpha2.Component {
			return paasv1alpha2.Component{
				Name:       "sidecar",
				Version:    "v1",
				Properties: runtime.RawExtension{Raw: []byte(props)},
			}
		}

		// containersByName indexes the rendered containers by name. A strategic
		// merge patch does not preserve list order, so containers must never be
		// looked up by position.
		containersByName := func(sbi *sandboxv1beta1.SandboxInstance) map[string]corev1.Container {
			indexed := map[string]corev1.Container{}
			for _, c := range sbi.Spec.PodTemplate.Containers {
				indexed[c.Name] = c
			}
			return indexed
		}

		// getSandboxInstance fetches the SandboxInstance built for the "web" process.
		getSandboxInstance := func(cli client.Client, ctx context.Context) *sandboxv1beta1.SandboxInstance {
			sbi := &sandboxv1beta1.SandboxInstance{}
			Expect(cli.Get(ctx, types.NamespacedName{
				Name: names.Deployment(bkapp, "web"), Namespace: "default",
			}, sbi)).To(Succeed())
			return sbi
		}

		BeforeEach(func() {
			// Point the component loader at a copy of the real sidecar component,
			// so these tests exercise the template that actually ships.
			tempDir, _ = os.MkdirTemp("", "sandbox_components_test")
			componentsMgr.DefaultComponentDir = tempDir
			versionDir := filepath.Join(tempDir, "sidecar", "v1")
			Expect(os.MkdirAll(versionDir, 0o755)).To(Succeed())
			Expect(
				os.WriteFile(filepath.Join(versionDir, "template.yaml"), []byte(sidecarTemplate), 0o644),
			).To(Succeed())
		})

		AfterEach(func() {
			Expect(os.RemoveAll(tempDir)).To(Succeed())
			componentsMgr.DefaultComponentDir = "/components"
		})

		It("should include sidecar containers in SandboxInstance", func() {
			bkapp.Spec.Processes[0].Components = []paasv1alpha2.Component{
				sidecarComponent(`{
					"name": "log-collector",
					"image": "fluentd:latest",
					"command": ["/bin/sh", "-c", "fluentd"],
					"env": [{"name": "LOG_LEVEL", "value": "info"}]
				}`),
			}
			cli := builder.WithObjects(bkapp).Build()
			r := NewSandboxInstanceReconciler(cli)
			ctx := context.Background()

			r.Reconcile(ctx, bkapp)

			sbi := getSandboxInstance(cli, ctx)
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
			bkapp.Spec.Processes[0].Components = []paasv1alpha2.Component{
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
			}
			cli := builder.WithObjects(bkapp).Build()
			r := NewSandboxInstanceReconciler(cli)
			ctx := context.Background()

			r.Reconcile(ctx, bkapp)

			sbi := getSandboxInstance(cli, ctx)

			volumesByName := map[string]corev1.Volume{}
			for _, v := range sbi.Spec.PodTemplate.Volumes {
				volumesByName[v.Name] = v
			}
			Expect(volumesByName).To(HaveLen(2))
			Expect(volumesByName["shared-data"].EmptyDir).NotTo(BeNil())
			Expect(volumesByName["shared-data"].EmptyDir.SizeLimit.String()).To(Equal("1Gi"))
			Expect(volumesByName["tmpfs-cache"].EmptyDir.Medium).To(Equal(corev1.StorageMediumMemory))

			containers := containersByName(sbi)
			// The main container receives its own mount of the shared volume.
			Expect(containers["web"].VolumeMounts).To(HaveLen(1))
			Expect(containers["web"].VolumeMounts[0].Name).To(Equal("shared-data"))
			Expect(containers["web"].VolumeMounts[0].MountPath).To(Equal("/app/data"))

			Expect(containers["worker"].VolumeMounts).To(HaveLen(1))
			Expect(containers["worker"].VolumeMounts[0].Name).To(Equal("shared-data"))
			Expect(containers["worker"].VolumeMounts[0].MountPath).To(Equal("/data"))
		})

		It("should support multiple sidecar components", func() {
			bkapp.Spec.Processes[0].Components = []paasv1alpha2.Component{
				sidecarComponent(`{"name": "first", "image": "first:v1"}`),
				sidecarComponent(`{"name": "second", "image": "second:v1"}`),
			}
			cli := builder.WithObjects(bkapp).Build()
			r := NewSandboxInstanceReconciler(cli)
			ctx := context.Background()

			r.Reconcile(ctx, bkapp)

			sbi := getSandboxInstance(cli, ctx)
			Expect(sbi.Spec.PodTemplate.Containers).To(HaveLen(3))

			containers := containersByName(sbi)
			Expect(containers).To(HaveLen(3))
			Expect(containers).To(HaveKey("web"))
			Expect(containers["first"].Image).To(Equal("first:v1"))
			Expect(containers["second"].Image).To(Equal("second:v1"))
		})

		It("should have no sidecars or volumes when no component is configured", func() {
			cli := builder.WithObjects(bkapp).Build()
			r := NewSandboxInstanceReconciler(cli)
			ctx := context.Background()

			r.Reconcile(ctx, bkapp)

			sbi := getSandboxInstance(cli, ctx)
			Expect(sbi.Spec.PodTemplate.Containers).To(HaveLen(1))
			Expect(sbi.Spec.PodTemplate.Containers[0].Name).To(Equal("web"))
			Expect(sbi.Spec.PodTemplate.Volumes).To(BeEmpty())
		})

		// A strategic merge patch grows a "merge" list by seeding new entries from
		// the existing ones, so a sidecar can silently inherit the main container's
		// command / env / resources / workingDir. That would make the sidecar run
		// the app's entrypoint and claim a second full resource quota, so the
		// injection must isolate the two containers.
		It("should not let a sidecar inherit main container fields", func() {
			// Give the main container the full set of fields the operator builds
			// in production; a bare name/image main container hides the problem.
			bkapp.Spec.Processes[0].Command = []string{"/bin/sh", "-c", "python main.py"}
			bkapp.Spec.Processes[0].Components = []paasv1alpha2.Component{
				// Only name and image are declared: everything else must stay unset.
				sidecarComponent(`{"name": "log-collector", "image": "fluentd:latest"}`),
			}
			cli := builder.WithObjects(bkapp).Build()
			r := NewSandboxInstanceReconciler(cli)
			ctx := context.Background()

			r.Reconcile(ctx, bkapp)

			sbi := getSandboxInstance(cli, ctx)
			Expect(sbi.Spec.PodTemplate.Containers).To(HaveLen(2))

			containers := containersByName(sbi)
			main := containers["web"]
			sidecar := containers["log-collector"]

			// The main container keeps everything the operator gave it.
			Expect(main.Image).To(Equal("my-agent:latest"))
			Expect(main.Command).To(Equal([]string{"/bin/sh", "-c", "python main.py"}))
			Expect(main.Resources.Limits).NotTo(BeEmpty())

			// The sidecar keeps only what it declared.
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
})
