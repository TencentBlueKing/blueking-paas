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
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"

	sandboxv1beta1 "bk.tencent.com/paas-app-operator/api/sandbox/v1beta1"
	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	componentsMgr "bk.tencent.com/paas-app-operator/pkg/components/manager"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/processes/components"
)

var _ = Describe("persistent_rootfs component", func() {
	const workloadName = "bkapp-agent-sample--web"

	var sbi *sandboxv1beta1.SandboxInstance

	rootfsComponent := func(props string) paasv1alpha2.Component {
		return paasv1alpha2.Component{
			Name:       "persistent_rootfs",
			Version:    "v1",
			Properties: runtime.RawExtension{Raw: []byte(props)},
		}
	}

	volumesByName := func(instance *sandboxv1beta1.SandboxInstance) map[string]corev1.Volume {
		indexed := map[string]corev1.Volume{}
		for _, v := range instance.Spec.PodTemplate.Volumes {
			indexed[v.Name] = v
		}
		return indexed
	}

	BeforeEach(func() {
		// Render from the shipped component directory so a broken template fails here.
		// From this package the operator root is five levels up.
		componentsMgr.DefaultComponentDir = filepath.Join(
			"..", "..", "..", "..", "..", "components",
		)

		sbi = &sandboxv1beta1.SandboxInstance{
			ObjectMeta: metav1.ObjectMeta{Name: workloadName},
			Spec: sandboxv1beta1.SandboxInstanceSpec{
				// Leave domain.cpu/memory empty; sandbox-controller sizes the guest.
				Domain: sandboxv1beta1.SandboxDomain{},
				PodTemplate: sandboxv1beta1.SandboxPodTemplate{
					Containers: []corev1.Container{
						{Name: "web", Image: "my-agent:latest"},
					},
				},
			},
		}
	})

	AfterEach(func() {
		componentsMgr.DefaultComponentDir = "/components"
	})

	It("should declare the rootfs disk, its volume and its PVC template", func() {
		proc := &paasv1alpha2.Process{
			Name: "web",
			Components: []paasv1alpha2.Component{
				rootfsComponent(`{"diskSize": "50Gi", "pvcSize": "60Gi"}`),
			},
		}

		Expect(components.PatchToSandboxInstance(proc, sbi)).To(Succeed())

		Expect(sbi.Spec.Domain.Devices).NotTo(BeNil())
		Expect(sbi.Spec.Domain.Devices.Disks).To(HaveLen(1))
		disk := sbi.Spec.Domain.Devices.Disks[0]
		Expect(disk.Name).To(Equal("rootfs"))
		// Omitting containerName binds the disk to the process main container.
		Expect(disk.ContainerName).To(Equal("web"))
		Expect(disk.VolumeName).To(Equal("state-web"))
		Expect(disk.Role).To(Equal("rootfsDisk"))
		Expect(disk.Image).To(Equal("rootdisk.img"))
		Expect(disk.SourcePath).To(Equal("rootfs"))
		Expect(disk.FsType).To(Equal("ext4"))
		Expect(disk.Size).To(Equal("50Gi"))

		volumeName := "state-web"
		claimName := workloadName + "-" + volumeName + "-pvc"
		volumes := volumesByName(sbi)
		Expect(volumes).To(HaveKey(volumeName))
		Expect(volumes[volumeName].PersistentVolumeClaim).NotTo(BeNil())
		Expect(volumes[volumeName].PersistentVolumeClaim.ClaimName).To(Equal(claimName))

		Expect(sbi.Spec.VolumeClaimTemplates).To(HaveLen(1))
		pvc := sbi.Spec.VolumeClaimTemplates[0]
		Expect(pvc.Name).To(Equal(claimName))
		Expect(pvc.Spec.AccessModes).To(Equal([]corev1.PersistentVolumeAccessMode{corev1.ReadWriteOnce}))
		Expect(pvc.Spec.Resources.Requests.Storage().Equal(resource.MustParse("60Gi"))).To(BeTrue())
	})

	// persistent_rootfs only patches domain.devices; cpu/memory stay empty so
	// sandbox-controller can derive the guest size from containers.
	It("should keep cpu/memory empty when injecting rootfs disks", func() {
		proc := &paasv1alpha2.Process{
			Name: "web",
			Components: []paasv1alpha2.Component{
				rootfsComponent(`{"diskSize": "50Gi", "pvcSize": "60Gi"}`),
			},
		}

		Expect(components.PatchToSandboxInstance(proc, sbi)).To(Succeed())

		Expect(sbi.Spec.Domain.CPU).To(Equal(sandboxv1beta1.SandboxCPU{}))
		Expect(sbi.Spec.Domain.Memory).To(BeEmpty())
		Expect(sbi.Spec.Domain.Devices).NotTo(BeNil())
		Expect(sbi.Spec.Domain.Devices.Disks).To(HaveLen(1))
		Expect(sbi.Spec.Domain.Devices.Disks[0].Size).To(Equal("50Gi"))
	})

	It("should leave the rootfs ephemeral when the component is absent", func() {
		proc := &paasv1alpha2.Process{Name: "web"}

		Expect(components.PatchToSandboxInstance(proc, sbi)).To(Succeed())

		Expect(sbi.Spec.Domain).To(Equal(sandboxv1beta1.SandboxDomain{}))
		Expect(sbi.Spec.VolumeClaimTemplates).To(BeEmpty())
		Expect(sbi.Spec.PodTemplate.Volumes).To(BeEmpty())
	})

	It("should coexist with a sidecar component", func() {
		proc := &paasv1alpha2.Process{
			Name: "web",
			Components: []paasv1alpha2.Component{
				rootfsComponent(`{"diskSize": "50Gi", "pvcSize": "60Gi"}`),
				{
					Name:    "sidecar",
					Version: "v1",
					Properties: runtime.RawExtension{Raw: []byte(`{
						"name": "log-collector",
						"image": "fluentd:latest",
						"sharedVolumes": [{"name": "app-logs"}],
						"volumeMounts": [{"name": "app-logs", "mountPath": "/var/log/app"}]
					}`)},
				},
			},
		}

		Expect(components.PatchToSandboxInstance(proc, sbi)).To(Succeed())

		volumes := volumesByName(sbi)
		Expect(volumes).To(HaveLen(2))
		Expect(volumes["state-web"].PersistentVolumeClaim).NotTo(BeNil())
		Expect(volumes["app-logs"].EmptyDir).NotTo(BeNil())

		Expect(sbi.Spec.Domain.Devices.Disks).To(HaveLen(1))
		Expect(sbi.Spec.PodTemplate.Containers).To(HaveLen(2))
	})

	// One persistent_rootfs entry binds one container. Main + sidecar each get
	// their own disk when two entries are declared; disks / PVCs merge by
	// containerName / claim name so neither overwrites the other.
	It("should give each container its own rootfs when declared separately", func() {
		proc := &paasv1alpha2.Process{
			Name: "web",
			Components: []paasv1alpha2.Component{
				rootfsComponent(`{"diskSize": "50Gi", "pvcSize": "60Gi"}`),
				{
					Name:       "sidecar",
					Version:    "v1",
					Properties: runtime.RawExtension{Raw: []byte(`{"name": "worker", "image": "worker:v1"}`)},
				},
				rootfsComponent(`{"containerName": "worker", "diskSize": "20Gi", "pvcSize": "30Gi"}`),
			},
		}

		Expect(components.PatchToSandboxInstance(proc, sbi)).To(Succeed())

		disksByContainer := map[string]sandboxv1beta1.SandboxDisk{}
		for _, d := range sbi.Spec.Domain.Devices.Disks {
			disksByContainer[d.ContainerName] = d
		}
		Expect(disksByContainer).To(HaveLen(2))

		Expect(disksByContainer["web"].VolumeName).To(Equal("state-web"))
		Expect(disksByContainer["web"].Size).To(Equal("50Gi"))
		Expect(disksByContainer["worker"].VolumeName).To(Equal("state-worker"))
		Expect(disksByContainer["worker"].Size).To(Equal("20Gi"))

		volumes := volumesByName(sbi)
		Expect(volumes).To(HaveLen(2))
		Expect(volumes["state-web"].PersistentVolumeClaim.ClaimName).To(
			Equal(workloadName + "-state-web-pvc"))
		Expect(volumes["state-worker"].PersistentVolumeClaim.ClaimName).To(
			Equal(workloadName + "-state-worker-pvc"))

		pvcByName := map[string]corev1.PersistentVolumeClaim{}
		for _, pvc := range sbi.Spec.VolumeClaimTemplates {
			pvcByName[pvc.Name] = pvc
		}
		Expect(pvcByName).To(HaveLen(2))
		webPVC := pvcByName[workloadName+"-state-web-pvc"]
		workerPVC := pvcByName[workloadName+"-state-worker-pvc"]
		Expect(webPVC.Spec.Resources.Requests.Storage().Equal(resource.MustParse("60Gi"))).To(BeTrue())
		Expect(workerPVC.Spec.Resources.Requests.Storage().Equal(resource.MustParse("30Gi"))).To(BeTrue())
	})
})
