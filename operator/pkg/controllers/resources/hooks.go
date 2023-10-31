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
	"strconv"
	"time"

	"github.com/pkg/errors"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime/schema"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/names"
	"bk.tencent.com/paas-app-operator/pkg/utils/kubetypes"
)

const (
	// HookExecuteTimeoutThreshold Hook执行超时时间阈值
	HookExecuteTimeoutThreshold = time.Minute * 15

	// HookExecuteFailedTimeoutThreshold 失败 Hook 的超时时间阈值
	HookExecuteFailedTimeoutThreshold = time.Minute * 2
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
	Status *paasv1alpha2.HookStatus
}

// Progressing 返回当前 hook 是否执行中
func (i *HookInstance) Progressing() bool {
	return i.Status.Phase == paasv1alpha2.HealthProgressing
}

// Succeeded 返回当前 hook 是否执行成功
func (i *HookInstance) Succeeded() bool {
	return i.Status.Phase == paasv1alpha2.HealthHealthy
}

// Failed 返回当前 hook 是否执行失败
func (i *HookInstance) Failed() bool {
	return !(i.Progressing() || i.Succeeded())
}

// Timeout 根据参数 timeout 判断 Pod 是否执行超时
func (i *HookInstance) Timeout(timeout time.Duration) bool {
	return i.Progressing() && i.Status != nil && !i.Status.StartTime.IsZero() &&
		i.Status.StartTime.Add(timeout).Before(time.Now())
}

// FailedUntilTimeout 判断 Pod 在 timeout 之前是否执行失败
func (i *HookInstance) FailedUntilTimeout(timeout time.Duration) bool {
	return i.Failed() && i.Status != nil && !i.Status.StartTime.IsZero() &&
		i.Status.StartTime.Add(timeout).Before(time.Now())
}

// BuildPreReleaseHook 从应用描述中解析 Pre-Release-Hook 对象
func BuildPreReleaseHook(bkapp *paasv1alpha2.BkApp, status *paasv1alpha2.HookStatus) *HookInstance {
	if bkapp.Spec.Hooks == nil || bkapp.Spec.Hooks.PreRelease == nil {
		return nil
	}

	proc := bkapp.Spec.GetWebProcess()
	if proc == nil {
		return nil
	}

	// Use the web process's image and pull policy to run the hook.
	// This behavior might be changed in the future when paasv1alpha1.BkApp is fully removed.
	image, pullPolicy, err := paasv1alpha2.NewProcImageGetter(bkapp).Get("web")
	if err != nil {
		return nil
	}

	if status == nil {
		status = &paasv1alpha2.HookStatus{
			Type:  paasv1alpha2.HookPreRelease,
			Phase: paasv1alpha2.HealthUnknown,
		}
	}

	useCNB, _ := strconv.ParseBool(bkapp.Annotations[paasv1alpha2.UseCNBAnnoKey])
	command := bkapp.Spec.Hooks.PreRelease.Command
	args := bkapp.Spec.Hooks.PreRelease.Args
	if useCNB {
		// cnb 运行时执行其他命令需要用 `launcher` 进入 buildpack 上下
		// See: https://github.com/buildpacks/lifecycle/blob/main/cmd/launcher/cli/launcher.go
		command = append([]string{"launcher"}, command...)
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
					// 由于 Process 一开始没添加 ResourceTypeKey label, 通过命名空间过滤 Pod 会查询到 HookInstance 的 Pod
					// 所以 HookInstance 暂时不添加 ModuleNameKey, 以区分 Process 创建的 pod 和 HookInstance 创建的 pod
					paasv1alpha2.BkAppNameKey:    bkapp.GetName(),
					paasv1alpha2.ResourceTypeKey: "hook",
					paasv1alpha2.HookTypeKey:     string(paasv1alpha2.HookPreRelease),
				},
				OwnerReferences: []metav1.OwnerReference{
					*metav1.NewControllerRef(bkapp, schema.GroupVersionKind{
						Group:   paasv1alpha2.GroupVersion.Group,
						Version: paasv1alpha2.GroupVersion.Version,
						Kind:    paasv1alpha2.KindBkApp,
					}),
				},
			},
			Spec: corev1.PodSpec{
				Containers: []corev1.Container{
					{
						Image:           image,
						Command:         kubetypes.ReplaceCommandEnvVariables(command),
						Args:            kubetypes.ReplaceCommandEnvVariables(args),
						Env:             GetAppEnvs(bkapp),
						Name:            "hook",
						ImagePullPolicy: pullPolicy,
						// pre-hook 使用默认资源配置
						Resources: NewProcResourcesGetter(bkapp).Default(),
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
				// 镜像拉取凭证
				ImagePullSecrets: buildImagePullSecrets(bkapp),
			},
		},
		Status: status,
	}
}
