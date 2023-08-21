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

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
)

var _ = Describe("Get VolumeMountMap", func() {
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
		volMountMap := GetVolumeMountMap(bkapp)

		Expect(len(volMountMap)).To(Equal(2))
		Expect(volMountMap[nginxMountName].MountPath).To(Equal(nginxPath))
		Expect(volMountMap[redisMountName].MountPath).To(Equal(redisPath))
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

		volMountMap := GetVolumeMountMap(bkapp)

		Expect(len(volMountMap)).To(Equal(3))

		Expect(volMountMap[nginxMountName].MountPath).To(Equal(overlayPath))
		Expect(volMountMap[etcdName].MountPath).To(Equal(etcdPath))
	})

	It("no mounts", func() {
		bkapp.Spec.Mounts = []paasv1alpha2.Mount{}
		volMountMap := GetVolumeMountMap(bkapp)
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

	It("configmap source", func() {
		mountName, mountPath := "nginx-conf", "/etc/nginx/conf"

		vs := &paasv1alpha2.VolumeSource{ConfigMap: &paasv1alpha2.ConfigMapSource{Name: "nginx-configmap"}}
		cfg, _ := ToVolumeSourceConfigurer(vs)
		_ = cfg.ApplyToDeployment(deployment, mountName, mountPath)

		Expect(deployment.Spec.Template.Spec.Containers[0].VolumeMounts[0].Name).To(Equal(mountName))
		Expect(deployment.Spec.Template.Spec.Containers[0].VolumeMounts[0].MountPath).To(Equal(mountPath))

		Expect(deployment.Spec.Template.Spec.Volumes[0].ConfigMap.Name).To(Equal("nginx-configmap"))
	})
})
