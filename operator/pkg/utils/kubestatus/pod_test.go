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
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	corev1 "k8s.io/api/core/v1"

	"bk.tencent.com/paas-app-operator/api/v1alpha2"
)

var _ = Describe("Test kubestatus/pod", func() {
	DescribeTable(
		"test CheckPodHealthStatus",
		func(pod *corev1.Pod, phase v1alpha2.HealthPhase, reason, message string) {
			healthStatus := CheckPodHealthStatus(pod)

			Expect(healthStatus.Phase).To(Equal(phase))
			Expect(healthStatus.Reason).To(Equal(reason))
			Expect(healthStatus.Message).To(Equal(message))
		},
		Entry("running pod", &corev1.Pod{
			Status: corev1.PodStatus{Phase: corev1.PodRunning, Reason: "foo", Message: "bar"},
		}, v1alpha2.HealthProgressing, "foo", "bar"),
		Entry("running pod - with always restart policy and ready condition", &corev1.Pod{
			Spec: corev1.PodSpec{RestartPolicy: corev1.RestartPolicyAlways},
			Status: corev1.PodStatus{
				Phase:   corev1.PodRunning,
				Reason:  "foo",
				Message: "bar",
				Conditions: []corev1.PodCondition{
					{Type: corev1.PodReady, Status: corev1.ConditionTrue},
				},
			},
		}, v1alpha2.HealthHealthy, "foo", "bar"),
		Entry("running pod - with always restart policy but some container fails", &corev1.Pod{
			Spec: corev1.PodSpec{RestartPolicy: corev1.RestartPolicyAlways},
			Status: corev1.PodStatus{
				Phase:   corev1.PodRunning,
				Reason:  "---",
				Message: "---",
				ContainerStatuses: []corev1.ContainerStatus{
					{
						LastTerminationState: corev1.ContainerState{
							Waiting: &corev1.ContainerStateWaiting{Reason: "foo", Message: "bar"},
						},
					},
				},
			},
		}, v1alpha2.HealthUnhealthy, "---", "bar"),
		Entry("running pod - with always restart policy only", &corev1.Pod{
			Spec: corev1.PodSpec{RestartPolicy: corev1.RestartPolicyAlways},
			Status: corev1.PodStatus{
				Phase:   corev1.PodRunning,
				Reason:  "foo",
				Message: "bar",
			},
		}, v1alpha2.HealthProgressing, "foo", "bar"),
		Entry("succeeded pod", &corev1.Pod{
			Status: corev1.PodStatus{Phase: corev1.PodSucceeded, Reason: "foo", Message: "bar"},
		}, v1alpha2.HealthHealthy, "foo", "bar"),
		Entry("failed pod - with pod message", &corev1.Pod{
			Status: corev1.PodStatus{Phase: corev1.PodFailed, Reason: "foo", Message: "bar"},
		}, v1alpha2.HealthUnhealthy, "foo", "bar"),
		Entry("failed pod - OOMKilled", &corev1.Pod{
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
		}, v1alpha2.HealthUnhealthy, "---", "OOMKilled"),
		Entry("pending pod", &corev1.Pod{
			Status: corev1.PodStatus{Phase: corev1.PodPending, Reason: "foo", Message: "bar"},
		}, v1alpha2.HealthProgressing, "foo", "bar"),
		Entry("pending pod -  failed to start container", &corev1.Pod{
			Status: corev1.PodStatus{
				Phase:  corev1.PodPending,
				Reason: "---",
				ContainerStatuses: []corev1.ContainerStatus{
					{
						State: corev1.ContainerState{
							Waiting: &corev1.ContainerStateWaiting{Reason: "foo", Message: "bar"},
						},
					},
				},
			},
		}, v1alpha2.HealthUnhealthy, "---", "bar"),
		Entry("pending pod -  wait for create container", &corev1.Pod{
			Status: corev1.PodStatus{
				Phase: corev1.PodPending,
				ContainerStatuses: []corev1.ContainerStatus{
					{
						State: corev1.ContainerState{
							Waiting: &corev1.ContainerStateWaiting{Reason: "ContainerCreating", Message: ""},
						},
					},
				},
			},
		}, v1alpha2.HealthProgressing, "", ""),
	)

	DescribeTable(
		"test GetContainerFailMessage",
		func(ctr corev1.ContainerStatus, expected string) {
			Expect(GetContainerFailMessage(ctr)).To(Equal(expected))
		},
		Entry(
			"terminated container with message",
			corev1.ContainerStatus{
				State: corev1.ContainerState{Terminated: &corev1.ContainerStateTerminated{Message: "foo"}},
			},
			"foo",
		),
		Entry(
			"terminated oom container",
			corev1.ContainerStatus{
				State: corev1.ContainerState{Terminated: &corev1.ContainerStateTerminated{Reason: "OOMKilled"}},
			},
			"OOMKilled",
		),
		Entry(
			"terminated container exit with 127",
			corev1.ContainerStatus{
				State: corev1.ContainerState{Terminated: &corev1.ContainerStateTerminated{ExitCode: 127}},
			},
			"failed with exit code 127",
		),
		Entry(
			"waiting image container",
			corev1.ContainerStatus{
				State: corev1.ContainerState{
					Waiting: &corev1.ContainerStateWaiting{
						Reason:  "ImagePullBackOff",
						Message: "Back-off pulling image",
					},
				},
			},
			"Back-off pulling image",
		),

		Entry(
			"fail to start container",
			corev1.ContainerStatus{
				State: corev1.ContainerState{
					Waiting: &corev1.ContainerStateWaiting{
						Reason:  "CrashLoopBackOff",
						Message: "back-off 5m0s restarting failed container=web",
					},
				},
				LastTerminationState: corev1.ContainerState{
					Terminated: &corev1.ContainerStateTerminated{
						ExitCode: 127,
						Reason:   "ContainerCannotRun",
						Message:  "OCI runtime create failed: starting container process caused: executable file not found in $PATH: unknown",
					},
				},
			},
			"OCI runtime create failed: starting container process caused: executable file not found in $PATH: unknown",
		),
	)
})
