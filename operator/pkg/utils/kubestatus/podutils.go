/*
 * Tencent is pleased to support the open source community by making BlueKing - PaaS System available.
 * Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * 	http://opensource.org/licenses/MIT
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
	"fmt"

	corev1 "k8s.io/api/core/v1"

	paasv1alpha1 "bk.tencent.com/paas-app-operator/api/v1alpha1"
)

const (
	// ContainerCreating is a waiting reason when the container still creating,
	// we should regard as the pod is in progressing but not unhealthy
	ContainerCreating = "ContainerCreating"
	// OOMKilled is a terminated reason when the container is killed by system for OOM
	OOMKilled = "OOMKilled"
)

// CheckPodHealthStatus check if the pod is healthy
// For a Pod, healthy is meaning that the Pod is successfully complete or is Ready
//            unhealthy is meaning that the Pod is restarting or is Failed
//            progressing is meaning that the Pod is still running and condition `PodReady` is False.
func CheckPodHealthStatus(pod *corev1.Pod) *HealthStatus {
	healthyStatus := &HealthStatus{
		Status:  paasv1alpha1.HealthHealthy,
		Reason:  pod.Status.Reason,
		Message: pod.Status.Message,
	}
	unhealthyStatus := &HealthStatus{
		Status:  paasv1alpha1.HealthUnhealthy,
		Reason:  pod.Status.Reason,
		Message: pod.Status.Message,
	}
	progressingStatus := &HealthStatus{
		Status:  paasv1alpha1.HealthProgressing,
		Reason:  pod.Status.Reason,
		Message: pod.Status.Message,
	}

	switch pod.Status.Phase {
	case corev1.PodRunning:
		switch pod.Spec.RestartPolicy {
		case corev1.RestartPolicyAlways:
			// if pod is ready, k8s will set PodReady to True
			condReady := FindPodStatusCondition(pod.Status.Conditions, corev1.PodReady)
			if condReady != nil && condReady.Status == corev1.ConditionTrue {
				return healthyStatus
			}
			// if it's not ready, check to see if any container terminated, if so, it's unhealthy
			for _, ctr := range pod.Status.ContainerStatuses {
				if failMessage := GetContainerFailMessage(ctr); failMessage != "" && failMessage != ContainerCreating {
					return unhealthyStatus.withMessage(failMessage)
				}
			}
			// otherwise we are progressing towards a ready state
			return progressingStatus
		default:
			// pods set with a restart policy of OnFailure or Never, have a finite life.
			// These pods are typically resource hooks. Thus, we consider these as Progressing
			// instead of healthy.
			return progressingStatus
		}
	case corev1.PodSucceeded:
		return healthyStatus
	case corev1.PodFailed:
		// Pod has a nice error message. Use that.
		if pod.Status.Message != "" {
			return unhealthyStatus
		}
		// try to get fail message from ContainerStatuses
		for _, ctr := range pod.Status.ContainerStatuses {
			if failMessage := GetContainerFailMessage(ctr); failMessage != "" {
				return unhealthyStatus.withMessage(failMessage)
			}
		}
		// we don't know why pod failed
		return unhealthyStatus.withMessage("unknown")
	case corev1.PodPending:
		// check if failed to start container
		for _, ctr := range pod.Status.ContainerStatuses {
			if failMessage := GetContainerFailMessage(ctr); failMessage != "" && failMessage != ContainerCreating {
				return unhealthyStatus.withMessage(failMessage)
			}
		}
		// pod is progressing
		return progressingStatus
	default:
		// unknown pod phase
		return &HealthStatus{
			Status:  paasv1alpha1.HealthUnknown,
			Reason:  string(pod.Status.Phase),
			Message: pod.Status.Message,
		}
	}
}

// GetContainerFailMessage 获取容器的失败信息
func GetContainerFailMessage(ctr corev1.ContainerStatus) string {
	if failMessage := getContainerFailedMessageFromState(ctr.LastTerminationState); failMessage != "" {
		return failMessage
	}
	if failMessage := getContainerFailedMessageFromState(ctr.State); failMessage != "" {
		return failMessage
	}
	return ""
}

func getContainerFailedMessageFromState(state corev1.ContainerState) string {
	if state.Terminated != nil {
		if state.Terminated.Message != "" {
			return state.Terminated.Message
		}
		if state.Terminated.Reason == OOMKilled {
			return state.Terminated.Reason
		}
		if state.Terminated.ExitCode != 0 {
			return fmt.Sprintf("failed with exit code %d", state.Terminated.ExitCode)
		}
	}
	// such as 'ImagePullBackOff'
	if state.Waiting != nil {
		if state.Waiting.Message != "" {
			return state.Waiting.Message
		}
		return state.Waiting.Reason
	}
	return ""
}

// FindPodStatusCondition finds the conditionType in conditions.
func FindPodStatusCondition(
	conditions []corev1.PodCondition,
	conditionType corev1.PodConditionType,
) *corev1.PodCondition {
	for i := range conditions {
		if conditions[i].Type == conditionType {
			return &conditions[i]
		}
	}
	return nil
}
