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
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/labels"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/names"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/envs"
	"bk.tencent.com/paas-app-operator/pkg/kubeutil"
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

// TimeoutExceededProgressing 根据参数 timeout 判断 Pod 是否执行超时
func (i *HookInstance) TimeoutExceededProgressing(timeout time.Duration) bool {
	return i.Progressing() && i.Status != nil && !i.Status.StartTime.IsZero() &&
		i.Status.StartTime.Add(timeout).Before(time.Now())
}

// TimeoutExceededFailed 判断 Pod 在 timeout 时是否执行失败
func (i *HookInstance) TimeoutExceededFailed(timeout time.Duration) bool {
	return i.Failed() && i.Status != nil && !i.Status.StartTime.IsZero() &&
		i.Status.StartTime.Add(timeout).Before(time.Now())
}

// IsPreReleaseProgressing checks if the pre-release hook of the current app is in "progressing" status.
// Return false if the app does not have any pre-release hook.
func IsPreReleaseProgressing(bkapp *paasv1alpha2.BkApp) bool {
	if bkapp.Spec.Hooks == nil || bkapp.Spec.Hooks.PreRelease == nil {
		return false
	}
	status := bkapp.Status.FindHookStatus(paasv1alpha2.HookPreRelease)
	return status != nil && status.Phase == paasv1alpha2.HealthProgressing
}

// BuildPreReleaseHook 从应用描述中解析 Pre-Release-Hook 对象
func BuildPreReleaseHook(bkapp *paasv1alpha2.BkApp, status *paasv1alpha2.HookStatus) *HookInstance {
	if bkapp.Spec.Hooks == nil || bkapp.Spec.Hooks.PreRelease == nil {
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

	// Generate the environment variables and render the "{{bk_var_*}}" var placeholder which
	// might be used in the values.
	envVars := common.GetAppEnvs(bkapp)
	envVars = common.RenderAppVars(envVars, common.VarsRenderContext{ProcessType: "sys-pre-rel"})

	return &HookInstance{
		Pod: &corev1.Pod{
			TypeMeta: metav1.TypeMeta{
				Kind:       "Pod",
				APIVersion: "v1",
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      names.PreReleaseHook(bkapp),
				Namespace: bkapp.Namespace,
				Labels:    labels.Hook(bkapp, paasv1alpha2.HookPreRelease),
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
						Image:           bkapp.Spec.Build.Image,
						Command:         kubeutil.ReplaceCommandEnvVariables(command),
						Args:            kubeutil.ReplaceCommandEnvVariables(args),
						Env:             envVars,
						Name:            "hook",
						ImagePullPolicy: bkapp.Spec.Build.ImagePullPolicy,
						// pre-hook 使用默认资源配置
						Resources: envs.NewProcResourcesGetter(bkapp).Default(),
						// TODO: 挂载点
						VolumeMounts: nil,
					},
				},
				RestartPolicy: "Never",
				// TODO: 挂载卷
				Volumes: nil,
				// TODO: 亲和性、污点
				NodeSelector: paasv1alpha2.BuildEgressNodeSelector(bkapp),
				Tolerations:  nil,
				// 镜像拉取凭证
				ImagePullSecrets: common.BuildImagePullSecrets(bkapp),
			},
		},
		Status: status,
	}
}
