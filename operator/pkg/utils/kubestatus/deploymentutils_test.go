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

package kubestatus

import (
	"context"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"github.com/pkg/errors"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
)

var _ = Describe("Test kubestatus/deploymentutils", func() {
	var deployment *appsv1.Deployment
	var builder *fake.ClientBuilder
	var scheme *runtime.Scheme
	var ctx context.Context

	BeforeEach(func() {
		deployment = &appsv1.Deployment{
			TypeMeta: metav1.TypeMeta{
				APIVersion: "apps/v1",
				Kind:       "Deployment",
			},
			ObjectMeta: metav1.ObjectMeta{
				Name: "fake",
			},
			Spec: appsv1.DeploymentSpec{
				Selector: &metav1.LabelSelector{MatchLabels: map[string]string{"foo": "bar"}},
			},
		}

		ctx = context.Background()
		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		Expect(appsv1.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(corev1.AddToScheme(scheme)).NotTo(HaveOccurred())
		builder.WithScheme(scheme)
	})

	Context("test GetDeploymentDirectFailMessage", func() {
		It("when not pods associated", func() {
			cli := builder.WithObjects(deployment).Build()

			message, err := GetDeploymentDirectFailMessage(ctx, cli, deployment)

			Expect(errors.Is(err, ErrDeploymentStillProgressing)).To(BeTrue())
			Expect(message).To(Equal(""))
		})

		It("when associate with a running pod", func() {
			cli := builder.WithObjects(deployment, &corev1.Pod{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{"foo": "bar"},
				},
				Status: corev1.PodStatus{Phase: corev1.PodSucceeded, Reason: "foo", Message: "bar"},
			}).Build()

			message, err := GetDeploymentDirectFailMessage(ctx, cli, deployment)

			Expect(errors.Is(err, ErrDeploymentStillProgressing)).To(BeTrue())
			Expect(message).To(Equal(""))
		})

		It("when associate with a OOMKilled pod", func() {
			cli := builder.WithObjects(deployment, &corev1.Pod{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{"foo": "bar"},
				},
				Status: corev1.PodStatus{
					Phase:  corev1.PodFailed,
					Reason: "---",
					ContainerStatuses: []corev1.ContainerStatus{
						{
							State: corev1.ContainerState{
								Terminated: &corev1.ContainerStateTerminated{Reason: "OOMKilled"},
							},
						},
					},
				},
			}).Build()

			message, err := GetDeploymentDirectFailMessage(ctx, cli, deployment)

			Expect(err).NotTo(HaveOccurred())
			Expect(message).To(Equal("OOMKilled"))
		})

		It("when associate with a ImagePullBackOff pod", func() {
			cli := builder.WithObjects(deployment, &corev1.Pod{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{"foo": "bar"},
				},
				Status: corev1.PodStatus{
					Phase:  corev1.PodPending,
					Reason: "---",
					ContainerStatuses: []corev1.ContainerStatus{
						{
							State: corev1.ContainerState{
								Waiting: &corev1.ContainerStateWaiting{
									Reason:  "ImagePullBackOff",
									Message: "Back-off pulling image",
								},
							},
						},
					},
				},
			}).Build()

			message, err := GetDeploymentDirectFailMessage(ctx, cli, deployment)

			Expect(err).NotTo(HaveOccurred())
			Expect(message).To(Equal("Back-off pulling image"))
		})
	})
})
