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

package volumes

import (
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/testing"
)

var _ = Describe("Get VolumeMounterMap", func() {
	var bkapp *paasv1alpha2.BkApp

	nginxMountName, redisMountName := "nginx-conf", "redis-conf"
	nginxPath, redisPath := "/etc/nginx", "/etc/redis"
	nginxConfigName, redisConfigName := "nginx-configmap", "redis-configmap"

	BeforeEach(func() {
		bkapp = &paasv1alpha2.BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       paasv1alpha2.KindBkApp,
				APIVersion: paasv1alpha2.GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:        "bkapp-sample",
				Namespace:   "default",
				Annotations: map[string]string{paasv1alpha2.EnvironmentKey: string(paasv1alpha2.ProdEnv)},
			},
			Spec: paasv1alpha2.AppSpec{
				Mounts: []paasv1alpha2.Mount{
					{
						Name:      nginxMountName,
						MountPath: nginxPath,
						Source: &paasv1alpha2.VolumeSource{
							ConfigMap: &paasv1alpha2.ConfigMapSource{Name: nginxConfigName},
						},
					},
					{
						Name:      redisMountName,
						MountPath: redisPath,
						Source: &paasv1alpha2.VolumeSource{
							ConfigMap: &paasv1alpha2.ConfigMapSource{Name: redisConfigName},
						},
					},
				},
			},
		}
	})

	It("mounts without overlay", func() {
		volMountMap := GetGenericVolumeMountMap(bkapp)

		Expect(len(volMountMap)).To(Equal(2))
		Expect(volMountMap[nginxMountName].GetMountPath()).To(Equal(nginxPath))
		Expect(volMountMap[redisMountName].GetMountPath()).To(Equal(redisPath))
	})

	It("mounts with overlay", func() {
		overlayPath := nginxPath + "/test"

		etcdName := "etcd-conf"
		etcdPath := "/etc/etcd"

		bkapp.Spec.EnvOverlay = &paasv1alpha2.AppEnvOverlay{
			Mounts: []paasv1alpha2.MountOverlay{
				{
					Mount: paasv1alpha2.Mount{
						Name:      nginxMountName,
						MountPath: overlayPath,
						Source: &paasv1alpha2.VolumeSource{
							ConfigMap: &paasv1alpha2.ConfigMapSource{Name: nginxConfigName},
						},
					},
					EnvName: paasv1alpha2.ProdEnv,
				},
				{
					Mount: paasv1alpha2.Mount{
						Name:      etcdName,
						MountPath: etcdPath,
						Source: &paasv1alpha2.VolumeSource{
							ConfigMap: &paasv1alpha2.ConfigMapSource{Name: "etcd-configmap"},
						},
					},
					EnvName: paasv1alpha2.ProdEnv,
				},
				{
					Mount: paasv1alpha2.Mount{
						Name:      etcdName,
						MountPath: etcdPath,
						Source: &paasv1alpha2.VolumeSource{
							ConfigMap: &paasv1alpha2.ConfigMapSource{Name: "etcd-configmap"},
						},
					},
					EnvName: paasv1alpha2.StagEnv,
				},
			},
		}

		volMountMap := GetGenericVolumeMountMap(bkapp)

		Expect(len(volMountMap)).To(Equal(3))

		Expect(volMountMap[nginxMountName].GetMountPath()).To(Equal(overlayPath))
		Expect(volMountMap[etcdName].GetMountPath()).To(Equal(etcdPath))
	})

	It("no mounts", func() {
		bkapp.Spec.Mounts = []paasv1alpha2.Mount{}
		volMountMap, _ := GetAllVolumeMounterMap(bkapp)
		Expect(len(volMountMap)).To(Equal(0))
	})
})

var _ = Describe("test apply to deployment", func() {
	var deployment *appsv1.Deployment

	BeforeEach(func() {
		deployment = &appsv1.Deployment{
			TypeMeta: metav1.TypeMeta{
				APIVersion: "apps/v1",
				Kind:       "Deployment",
			},
			ObjectMeta: metav1.ObjectMeta{
				Name: "test-deployment",
			},
			Spec: appsv1.DeploymentSpec{
				Replicas: paasv1alpha2.ReplicasOne,
				Selector: &metav1.LabelSelector{},
				Template: corev1.PodTemplateSpec{
					Spec: corev1.PodSpec{Containers: []corev1.Container{{Name: "nginx", Image: "nginx:latest"}}},
				},
			},
		}
	})

	It("subPaths", func() {
		mountName, mountPath := "nginx-conf", "/etc/nginx/conf"
		subPaths := []string{"nginx.conf", "nginx2.conf"}

		vm := GenericVolumeMount{
			Volume: Volume{
				Name: mountName,
				Source: &paasv1alpha2.VolumeSource{
					ConfigMap: &paasv1alpha2.ConfigMapSource{Name: "nginx-configmap"},
				},
			},
			MountPath: mountPath,
			SubPaths:  subPaths,
		}
		_ = vm.ApplyToDeployment(nil, deployment)
		volumeMounts := deployment.Spec.Template.Spec.Containers[0].VolumeMounts
		for idx, mount := range volumeMounts {
			Expect(mount.Name).To(Equal(mountName))
			Expect(mount.MountPath).To(Equal(filepath.Join(mountPath, subPaths[idx])))
			Expect(mount.SubPath).To(Equal(subPaths[idx]))
		}
	})

	It("configmap source", func() {
		mountName, mountPath := "nginx-conf", "/etc/nginx/conf"

		vm := GenericVolumeMount{
			Volume: Volume{
				Name:   mountName,
				Source: &paasv1alpha2.VolumeSource{ConfigMap: &paasv1alpha2.ConfigMapSource{Name: "nginx-configmap"}},
			},
			MountPath: mountPath,
		}
		_ = vm.ApplyToDeployment(nil, deployment)

		Expect(deployment.Spec.Template.Spec.Containers[0].VolumeMounts[0].Name).To(Equal(mountName))
		Expect(deployment.Spec.Template.Spec.Containers[0].VolumeMounts[0].MountPath).To(Equal(mountPath))

		Expect(deployment.Spec.Template.Spec.Volumes[0].ConfigMap.Name).To(Equal("nginx-configmap"))
	})

	It("secret source", func() {
		mountName, mountPath := "nginx-tls-certs", "/etc/nginx/tls"

		vm := GenericVolumeMount{
			Volume: Volume{
				Name: mountName,
				Source: &paasv1alpha2.VolumeSource{
					Secret: &paasv1alpha2.SecretSource{Name: "nginx-tls-secret"},
				},
			},
			MountPath: mountPath,
		}
		_ = vm.ApplyToDeployment(nil, deployment)

		Expect(deployment.Spec.Template.Spec.Containers[0].VolumeMounts[0].Name).To(Equal(mountName))
		Expect(deployment.Spec.Template.Spec.Containers[0].VolumeMounts[0].MountPath).To(Equal(mountPath))

		Expect(deployment.Spec.Template.Spec.Volumes[0].Secret.SecretName).To(Equal("nginx-tls-secret"))
	})

	It("pvc source", func() {
		mountName, mountPath := "nginx-conf", "/etc/nginx/conf"

		vm := GenericVolumeMount{
			Volume: Volume{
				Name: mountName,
				Source: &paasv1alpha2.VolumeSource{
					PersistentStorage: &paasv1alpha2.PersistentStorage{Name: "nginx-pvc"},
				},
			},
			MountPath: mountPath,
		}
		_ = vm.ApplyToDeployment(nil, deployment)

		Expect(deployment.Spec.Template.Spec.Containers[0].VolumeMounts[0].Name).To(Equal(mountName))
		Expect(deployment.Spec.Template.Spec.Containers[0].VolumeMounts[0].MountPath).To(Equal(mountPath))

		Expect(deployment.Spec.Template.Spec.Volumes[0].PersistentVolumeClaim.ClaimName).To(Equal("nginx-pvc"))
	})
})

var _ = Describe("test apply to pod", func() {
	var pod *corev1.Pod

	BeforeEach(func() {
		pod = &corev1.Pod{
			TypeMeta: metav1.TypeMeta{
				APIVersion: "v1",
				Kind:       "Pod",
			},
			ObjectMeta: metav1.ObjectMeta{
				Name: "test-pod",
			},
			Spec: corev1.PodSpec{
				Containers: []corev1.Container{
					{Name: "nginx", Image: "nginx:latest"},
				},
			},
		}
	})

	It("subPaths", func() {
		mountName, mountPath := "nginx-conf", "/etc/nginx/conf"
		subPaths := []string{"nginx.conf", "nginx-tls.crt", "nginx-tls.key"}

		vm := GenericVolumeMount{
			Volume: Volume{
				Name: mountName,
				Source: &paasv1alpha2.VolumeSource{
					ConfigMap: &paasv1alpha2.ConfigMapSource{Name: "nginx-configmap"},
				},
			},
			MountPath: mountPath,
			SubPaths:  subPaths,
		}
		_ = vm.ApplyToPod(nil, pod)
		volumeMounts := pod.Spec.Containers[0].VolumeMounts
		for idx, mount := range volumeMounts {
			Expect(mount.Name).To(Equal(mountName))
			Expect(mount.MountPath).To(Equal(filepath.Join(mountPath, subPaths[idx])))
			Expect(mount.SubPath).To(Equal(subPaths[idx]))
		}
	})

	It("configmap source", func() {
		mountName, mountPath := "nginx-conf", "/etc/nginx/conf"

		vm := GenericVolumeMount{
			Volume: Volume{
				Name: mountName,
				Source: &paasv1alpha2.VolumeSource{
					ConfigMap: &paasv1alpha2.ConfigMapSource{Name: "nginx-configmap"},
				},
			},
			MountPath: mountPath,
		}
		_ = vm.ApplyToPod(nil, pod)

		Expect(pod.Spec.Containers[0].VolumeMounts[0].Name).To(Equal(mountName))
		Expect(pod.Spec.Containers[0].VolumeMounts[0].MountPath).To(Equal(mountPath))

		Expect(pod.Spec.Volumes[0].ConfigMap.Name).To(Equal("nginx-configmap"))
	})

	It("secret source", func() {
		mountName, mountPath := "nginx-tls-certs", "/etc/nginx/tls"

		vm := GenericVolumeMount{
			Volume: Volume{
				Name: mountName,
				Source: &paasv1alpha2.VolumeSource{
					Secret: &paasv1alpha2.SecretSource{Name: "nginx-tls-secret"},
				},
			},
			MountPath: mountPath,
		}
		_ = vm.ApplyToPod(nil, pod)

		Expect(pod.Spec.Containers[0].VolumeMounts[0].Name).To(Equal(mountName))
		Expect(pod.Spec.Containers[0].VolumeMounts[0].MountPath).To(Equal(mountPath))

		Expect(pod.Spec.Volumes[0].Secret.SecretName).To(Equal("nginx-tls-secret"))
	})

	It("pvc source", func() {
		mountName, mountPath := "nginx-conf", "/etc/nginx/conf"

		vm := GenericVolumeMount{
			Volume: Volume{
				Name: mountName,
				Source: &paasv1alpha2.VolumeSource{
					PersistentStorage: &paasv1alpha2.PersistentStorage{Name: "nginx-pvc"},
				},
			},
			MountPath: mountPath,
		}
		_ = vm.ApplyToPod(nil, pod)

		Expect(pod.Spec.Containers[0].VolumeMounts[0].Name).To(Equal(mountName))
		Expect(pod.Spec.Containers[0].VolumeMounts[0].MountPath).To(Equal(mountPath))

		Expect(pod.Spec.Volumes[0].PersistentVolumeClaim.ClaimName).To(Equal("nginx-pvc"))
	})
})

var _ = Describe("test builtin logs", func() {
	var bkapp *paasv1alpha2.BkApp
	var deployment *appsv1.Deployment

	BeforeEach(func() {
		bkapp = &paasv1alpha2.BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       paasv1alpha2.KindBkApp,
				APIVersion: paasv1alpha2.GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:        "bkapp-sample",
				Namespace:   "default",
				Annotations: map[string]string{paasv1alpha2.EnvironmentKey: string(paasv1alpha2.ProdEnv)},
			},
			Spec: paasv1alpha2.AppSpec{},
		}

		deployment = &appsv1.Deployment{
			TypeMeta: metav1.TypeMeta{
				APIVersion: "apps/v1",
				Kind:       "Deployment",
			},
			ObjectMeta: metav1.ObjectMeta{
				Name: "test-deployment",
			},
			Spec: appsv1.DeploymentSpec{
				Replicas: paasv1alpha2.ReplicasOne,
				Selector: &metav1.LabelSelector{},
				Template: corev1.PodTemplateSpec{
					Spec: corev1.PodSpec{Containers: []corev1.Container{{Name: "nginx", Image: "nginx:latest"}}},
				},
			},
		}
	})

	It("test builtin logs", func() {
		bkapp = testing.WithAppInfoAnnotations(bkapp)
		_, err := GetBuiltinLogsVolumeMounts(bkapp)
		Expect(err).To(BeNil())
	})

	It("test missing bkapp info", func() {
		_, err := GetBuiltinLogsVolumeMounts(bkapp)
		Expect(err).To(HaveOccurred())
	})

	It("test apply builtin logs volume mount", func() {
		bkapp = testing.WithAppInfoAnnotations(bkapp)
		mounters, _ := GetBuiltinLogsVolumeMounts(bkapp)

		Expect(len(mounters)).To(Equal(2))
		for _, mounter := range mounters {
			_ = mounter.ApplyToDeployment(bkapp, deployment)
		}

		volumeMounts := deployment.Spec.Template.Spec.Containers[0].VolumeMounts
		volumes := deployment.Spec.Template.Spec.Volumes

		Expect(volumeMounts[0].Name).To(Equal(VolumeNameAppLogging))
		Expect(volumeMounts[0].MountPath).To(Equal(VolumeMountAppLoggingDir))
		Expect(volumes[0].HostPath.Path).To(HavePrefix(VolumeHostPathAppLoggingDir))

		Expect(volumeMounts[1].Name).To(Equal(MulModuleVolumeNameAppLogging))
		Expect(volumeMounts[1].MountPath).To(Equal(MulModuleVolumeMountAppLoggingDir))
		Expect(volumes[1].HostPath.Path).To(HavePrefix(MulModuleVolumeHostPathAppLoggingDir))
	})

	DescribeTable(
		"test ShouldApplyBuiltinLogsVolume",
		func(anno string, expected bool) {
			bkapp.Annotations[paasv1alpha2.LogCollectorTypeAnnoKey] = anno
			Expect(ShouldApplyBuiltinLogsVolume(bkapp)).To(Equal(expected))
		},
		Entry("when type = ELK", paasv1alpha2.BuiltinELKCollector, true),
		Entry("when type = BK_LOG", paasv1alpha2.BkLogCollector, false),
		Entry("when type is unknown", "something", false),
	)
})
