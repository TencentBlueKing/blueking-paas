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
	"errors"
	"time"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime/schema"

	paasv1alpha1 "bk.tencent.com/paas-app-operator/api/v1alpha1"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/names"
)

const (
	// HookExecuteTimeoutThreshold Hook执行超时时间阈值
	HookExecuteTimeoutThreshold = time.Minute * 15
)

var (
	// ErrHookPodExists 用于指定 Hook 的 Pod 已经存在
	ErrHookPodExists = errors.New("hook pod existed")

	// ErrExecuteTimeout 指示当前 Hook 执行超时
	ErrExecuteTimeout = errors.New("hook execute timeout")

	// ErrPodEndsUnsuccessfully Pod 未成功退出
	ErrPodEndsUnsuccessfully = errors.New("pod ends unsuccessfully")

	// ErrLastHookStillRunning 最近一个 Hook 仍在运行状态
	ErrLastHookStillRunning = errors.New("the last pre-release-hook is still running")
)

// HookInstance 指示解析后的 Hook 实例
type HookInstance struct {
	Pod    *corev1.Pod
	Status *paasv1alpha1.HookStatus
}

// Progressing 返回当前 hook 是否执行中
func (i *HookInstance) Progressing() bool {
	return i.Status.Status == paasv1alpha1.HealthProgressing
}

// Succeeded 返回当前 hook 是否执行成功
func (i *HookInstance) Succeeded() bool {
	return i.Status.Status == paasv1alpha1.HealthHealthy
}

// Failed 返回当前 hook 是否执行失败
func (i *HookInstance) Failed() bool {
	return !i.Progressing() && !i.Succeeded()
}

// Timeout 根据参数 timeout 判断 Pod 是否执行超时
func (i *HookInstance) Timeout(timeout time.Duration) bool {
	return i.Progressing() && i.Status != nil && !i.Status.StartTime.IsZero() &&
		i.Status.StartTime.Add(timeout).Before(time.Now())
}

// BuildPreReleaseHook 从应用描述中解析 Pre-Release-Hook 对象
func BuildPreReleaseHook(bkapp *paasv1alpha1.BkApp, status *paasv1alpha1.HookStatus) *HookInstance {
	if bkapp.Spec.Hooks == nil || bkapp.Spec.Hooks.PreRelease == nil {
		return nil
	}

	proc := bkapp.Spec.GetWebProcess()
	if proc == nil {
		return nil
	}

	if status == nil {
		status = &paasv1alpha1.HookStatus{
			Type:   paasv1alpha1.HookPreRelease,
			Status: paasv1alpha1.HealthUnknown,
		}
	}

	return &HookInstance{
		Pod: &corev1.Pod{
			TypeMeta: metav1.TypeMeta{
				Kind:       "Pod",
				APIVersion: "v1",
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      names.PreReleaseHook(bkapp),
				Namespace: bkapp.Namespace,
				Labels: map[string]string{
					paasv1alpha1.BkAppNameKey:    bkapp.GetName(),
					paasv1alpha1.ResourceTypeKey: "hook",
					paasv1alpha1.HookTypeKey:     "pre-release",
				},
				OwnerReferences: []metav1.OwnerReference{
					*metav1.NewControllerRef(bkapp, schema.GroupVersionKind{
						Group:   paasv1alpha1.GroupVersion.Group,
						Version: paasv1alpha1.GroupVersion.Version,
						Kind:    paasv1alpha1.KindBkApp,
					}),
				},
			},
			Spec: corev1.PodSpec{
				Containers: []corev1.Container{
					{
						Image:           proc.Image,
						Command:         bkapp.Spec.Hooks.PreRelease.Command,
						Args:            bkapp.Spec.Hooks.PreRelease.Args,
						Env:             GetAppEnvs(bkapp),
						Name:            "hook",
						ImagePullPolicy: proc.ImagePullPolicy,
						Resources:       corev1.ResourceRequirements{},
						// TODO: 挂载点
						VolumeMounts: nil,
					},
				},
				RestartPolicy: "Never",
				// TODO: 挂载卷
				Volumes: nil,
				// TODO: 亲和性、污点
				NodeSelector: nil,
				Tolerations:  nil,
				// TODO: 镜像拉取凭证
				ImagePullSecrets: nil,
			},
		},
		Status: status,
	}
}
