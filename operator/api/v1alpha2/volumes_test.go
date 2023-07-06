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
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
)

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

		source := &runtime.RawExtension{Raw: []byte(`{"type":"configMap","name":"nginx-configmap"}`)}
		vs, _ := paasv1alpha2.ConvertToVolumeSource(source)
		_ = vs.ApplyToDeployment(deployment, mountName, mountPath)

		Expect(deployment.Spec.Template.Spec.Containers[0].VolumeMounts[0].Name).To(Equal(mountName))
		Expect(deployment.Spec.Template.Spec.Containers[0].VolumeMounts[0].MountPath).To(Equal(mountPath))

		Expect(deployment.Spec.Template.Spec.Volumes[0].ConfigMap.Name).To(Equal("nginx-configmap"))
	})
})
