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
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
)

var _ = Describe("Get VolumeMountMap", func() {
	var bkapp *paasv1alpha2.BkApp

	nginxMountName, redisMountName := "nginx-conf", "redis-conf"
	nginxPath, redisPath := "/etc/nginx", "/etc/redis"

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
						Source: &runtime.RawExtension{
							Raw: []byte(`{"type": "configMap", "name": "nginx-configmap"}`),
						},
					},
					{
						Name:      redisMountName,
						MountPath: redisPath,
						Source: &runtime.RawExtension{
							Raw: []byte(`{"type": "configMap", "name": "redis-configmap"}`),
						},
					},
				},
			},
		}
	})

	It("mounts without overlay", func() {
		vmMap := GetVolumeMountMap(bkapp)

		Expect(len(vmMap)).To(Equal(2))

		Expect(vmMap[nginxMountName].VolumeSource.GetType()).To(Equal(paasv1alpha2.ConfigMapType))
		Expect(vmMap[nginxMountName].MountPath).To(Equal(nginxPath))

		Expect(vmMap[redisMountName].MountPath).To(Equal(redisPath))
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
						Source: &runtime.RawExtension{
							Raw: []byte(`{"type": "configMap", "name": "nginx-configmap"}`),
						},
					},
					EnvName: paasv1alpha2.ProdEnv,
				},
				{
					Mount: paasv1alpha2.Mount{
						Name:      etcdName,
						MountPath: etcdPath,
						Source: &runtime.RawExtension{
							Raw: []byte(`{"type": "configMap", "name": "etcd-configmap"}`),
						},
					},
					EnvName: paasv1alpha2.ProdEnv,
				},
				{
					Mount: paasv1alpha2.Mount{
						Name:      etcdName,
						MountPath: etcdPath,
						Source: &runtime.RawExtension{
							Raw: []byte(`{"type": "configMap", "name": "etcd-configmap"}`),
						},
					},
					EnvName: paasv1alpha2.StagEnv,
				},
			},
		}

		vmMap := GetVolumeMountMap(bkapp)

		Expect(len(vmMap)).To(Equal(3))

		Expect(vmMap[nginxMountName].MountPath).To(Equal(overlayPath))
		Expect(vmMap[etcdName].MountPath).To(Equal(etcdPath))
	})

	It("no mounts", func() {
		bkapp.Spec.Mounts = []paasv1alpha2.Mount{}
		vmMap := GetVolumeMountMap(bkapp)
		Expect(len(vmMap)).To(Equal(0))
	})
})
