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

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	sandboxv1beta1 "bk.tencent.com/paas-app-operator/api/sandbox/v1beta1"
	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/names"
	"bk.tencent.com/paas-app-operator/pkg/kubeutil"
)

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

	Context("test container resources", func() {
		// Process quota lands on podTemplate.containers[].resources.
		// Spec.Domain is left empty; guest sizing is handled by sandbox-controller.
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
			Expect(sbi.Spec.Domain).To(Equal(sandboxv1beta1.SandboxDomain{}))
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
})
