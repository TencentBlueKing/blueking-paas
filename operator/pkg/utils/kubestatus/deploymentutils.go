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
	"fmt"

	"github.com/pkg/errors"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"

	paasv1alpha1 "bk.tencent.com/paas-app-operator/api/v1alpha1"
)

// ErrDeploymentStillProgressing indicates the deployment is progressing
var ErrDeploymentStillProgressing = errors.New("deployment is progressing")

// CheckDeploymentHealthStatus check if the deployment is healthy
// For a deployment:
//   healthy means the deployment is available, see also: DeploymentAvailable.
//   unhealthy means the deployment is failed to reconcile.
//   progressing is meaningless for deployment, if you want to know if those pods that
//   associated with this deployment is progressing, you should call GetDeploymentDirectFailMessage.
func CheckDeploymentHealthStatus(deployment *appsv1.Deployment) *HealthStatus {
	if deployment.Generation > deployment.Status.ObservedGeneration {
		return &HealthStatus{
			Status:  paasv1alpha1.HealthProgressing,
			Reason:  "UnobservedDeploy",
			Message: "Waiting for rollout to finish: observed deployment generation less then desired generation",
		}
	} else {
		failureCond := FindDeploymentStatusCondition(deployment.Status.Conditions, appsv1.DeploymentReplicaFailure)
		if failureCond != nil && failureCond.Status == corev1.ConditionTrue {
			return makeStatusFromDeploymentCondition(paasv1alpha1.HealthUnhealthy, failureCond)
		}

		progressingCond := FindDeploymentStatusCondition(deployment.Status.Conditions, appsv1.DeploymentProgressing)
		if progressingCond != nil && progressingCond.Status == corev1.ConditionFalse {
			return makeStatusFromDeploymentCondition(paasv1alpha1.HealthUnhealthy, progressingCond)
		}

		// 只有当前就绪的副本数等于需要的副本数时, Deployment 才完成滚动更新
		if deployment.Status.UpdatedReplicas == *deployment.Spec.Replicas {
			availableCond := FindDeploymentStatusCondition(deployment.Status.Conditions, appsv1.DeploymentAvailable)
			if availableCond != nil {
				if availableCond.Status != corev1.ConditionTrue {
					return makeStatusFromDeploymentCondition(paasv1alpha1.HealthUnhealthy, availableCond)
				}
				return makeStatusFromDeploymentCondition(paasv1alpha1.HealthHealthy, availableCond)
			}
		}

		var message string
		if deployment.Status.UpdatedReplicas < *deployment.Spec.Replicas {
			// Deployment 未完成滚动更新
			message = fmt.Sprintf("Waiting for rollout to finish: %d/%d replicas are updated...", deployment.Status.UpdatedReplicas, deployment.Spec.Replicas)
		} else {
			// Deployment 等待最新的 Pod 就绪
			message = fmt.Sprintf("Waiting for rollout to finish: %d/%d replicas are available...", deployment.Status.AvailableReplicas, deployment.Spec.Replicas)
		}

		return &HealthStatus{
			Status:  paasv1alpha1.HealthProgressing,
			Reason:  "Progressing",
			Message: message,
		}
	}
}

// GetDeploymentDirectFailMessage 从 Deployment 关联的 Pod 获取失败的直接原因
// this method will return the fail message if any pod associated with the given deployment is unhealthy or the container is not creating
// if no any pod is unhealthy, will return ErrDeploymentStillProgressing
func GetDeploymentDirectFailMessage(
	ctx context.Context,
	cli client.Client,
	deployment *appsv1.Deployment,
) (string, error) {
	var pods corev1.PodList
	if err := cli.List(
		ctx,
		&pods,
		client.InNamespace(deployment.Namespace),
		client.MatchingLabels(deployment.Spec.Selector.MatchLabels),
	); err != nil {
		return "", errors.WithStack(err)
	}
	for _, pod := range pods.Items {
		// 忽略已被标记删除的 Pod
		if !pod.DeletionTimestamp.IsZero() {
			continue
		}
		if healthStatus := CheckPodHealthStatus(&pod); healthStatus.Status == paasv1alpha1.HealthUnhealthy {
			return healthStatus.Message, nil
		}
	}
	return "", errors.WithStack(ErrDeploymentStillProgressing)
}

// FindDeploymentStatusCondition finds the conditionType in conditions.
func FindDeploymentStatusCondition(
	conditions []appsv1.DeploymentCondition,
	conditionType appsv1.DeploymentConditionType,
) *appsv1.DeploymentCondition {
	for i := range conditions {
		if conditions[i].Type == conditionType {
			return &conditions[i]
		}
	}
	return nil
}

// a shortcut for making a HealthStatus with given status and condition
func makeStatusFromDeploymentCondition(
	status paasv1alpha1.HealthStatus,
	condition *appsv1.DeploymentCondition,
) *HealthStatus {
	return &HealthStatus{
		Status:  status,
		Reason:  condition.Reason,
		Message: condition.Message,
	}
}
