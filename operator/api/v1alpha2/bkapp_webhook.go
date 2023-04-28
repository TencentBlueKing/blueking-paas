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

package v1alpha2

import (
	"fmt"
	"regexp"

	"github.com/getsentry/sentry-go"
	"github.com/pkg/errors"
	"github.com/samber/lo"
	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/util/validation/field"
	ctrl "sigs.k8s.io/controller-runtime"
	logf "sigs.k8s.io/controller-runtime/pkg/log"
	"sigs.k8s.io/controller-runtime/pkg/webhook"

	"bk.tencent.com/paas-app-operator/pkg/config"
)

// log is for logging in this package.
var appLog = logf.Log.WithName("bkapp-resource")

var (
	// AppNameRegex 应用名称格式（与 BK_APP_CODE 相同）
	AppNameRegex = regexp.MustCompile("^[a-z0-9-]{1,16}$")
	// ProcNameRegex 进程名称格式
	ProcNameRegex = regexp.MustCompile("^[a-z0-9]([-a-z0-9]){1,11}$")
)

// SetupWebhookWithManager ...
func (r *BkApp) SetupWebhookWithManager(mgr ctrl.Manager) error {
	return ctrl.NewWebhookManagedBy(mgr).
		For(r).
		Complete()
}

//+kubebuilder:webhook:path=/mutate-paas-bk-tencent-com-v1alpha2-bkapp,mutating=true,failurePolicy=fail,sideEffects=None,groups=paas.bk.tencent.com,resources=bkapps,verbs=create;update,versions=v1alpha2,name=mbkapp-v1alpha2.kb.io,admissionReviewVersions=v1

var _ webhook.Defaulter = &BkApp{}

// Default 实现 webhook.Defaulter 接口用于预设默认值
func (r *BkApp) Default() {
	appLog.Info("default", "name", r.Name)

	// 为镜像构建相关字段配置默认值
	if r.Spec.Build.ImagePullPolicy == "" {
		r.Spec.Build.ImagePullPolicy = corev1.PullIfNotPresent
	}

	// 为进程的端口号、资源配额方案等设置默认值
	for i, proc := range r.Spec.Processes {
		if proc.TargetPort == 0 {
			proc.TargetPort = ProcDefaultTargetPort
		}
		if proc.ResQuotaPlan == "" {
			proc.ResQuotaPlan = "default"
		}
		r.Spec.Processes[i] = proc
	}
}

//+kubebuilder:webhook:path=/validate-paas-bk-tencent-com-v1alpha2-bkapp,mutating=false,failurePolicy=fail,sideEffects=None,groups=paas.bk.tencent.com,resources=bkapps,verbs=create;update;delete,versions=v1alpha2,name=vbkapp-v1alpha2.kb.io,admissionReviewVersions=v1

var _ webhook.Validator = &BkApp{}

// ValidateCreate 应用创建时校验
func (r *BkApp) ValidateCreate() error {
	appLog.Info("validate create", "name", r.Name)
	err := r.validateApp()
	if err != nil {
		sentry.CaptureException(errors.Wrapf(err, "webhook validate bkapp [%s/%s] failed", r.Namespace, r.Name))
	}
	return err
}

// ValidateUpdate 应用更新时校验
func (r *BkApp) ValidateUpdate(old runtime.Object) error {
	appLog.Info("validate update", "name", r.Name)
	// TODO 更新校验逻辑，限制部分不可变字段（若存在）
	err := r.validateApp()
	if err != nil {
		sentry.CaptureException(errors.Wrapf(err, "webhook validate bkapp [%s/%s] failed", r.Namespace, r.Name))
	}
	return err
}

// ValidateDelete 应用删除时校验
func (r *BkApp) ValidateDelete() error {
	appLog.Info("validate delete (do nothing)", "name", r.Name)
	// TODO: 删除时候暂时不做任何校验，后续可以考虑支持删除保护？
	return nil
}

func (r *BkApp) validateApp() error {
	var allErrs field.ErrorList

	if err := r.validateAppName(); err != nil {
		allErrs = append(allErrs, err)
	}
	if err := r.validateAppSpec(); err != nil {
		allErrs = append(allErrs, err)
	}
	if err := r.validateEnvOverlay(); err != nil {
		allErrs = append(allErrs, err)
	}
	if len(allErrs) == 0 {
		return nil
	}
	return apierrors.NewInvalid(GroupKindBkApp, r.Name, allErrs)
}

// 应用名称必须符合正则（规则同 BK_APP_CODE）
func (r *BkApp) validateAppName() *field.Error {
	if matched := AppNameRegex.MatchString(r.Name); !matched {
		return field.Invalid(
			field.NewPath("metadata").Child("name"), r.Name, "must match regex "+AppNameRegex.String(),
		)
	}
	return nil
}

func (r *BkApp) validateAppSpec() *field.Error {
	procsField := field.NewPath("spec").Child("processes")
	if len(r.Spec.Processes) == 0 {
		return field.Invalid(procsField, r.Spec.Processes, "processes can't be empty")
	}

	if err := r.validateBuildConfig(); err != nil {
		return err
	}

	procCounter := map[string]int{}
	for idx, proc := range r.Spec.Processes {
		if err := r.validateAppProc(proc, idx); err != nil {
			return err
		}
		// 检查进程是否被重复定义
		procCounter[proc.Name]++
		if procCounter[proc.Name] > 1 {
			return field.Invalid(procsField, r.Spec.Processes, fmt.Sprintf(`process "%s" is duplicated`, proc.Name))
		}
	}
	// 至少需要包含一个 web 进程
	if procCounter[WebProcName] == 0 {
		return field.Invalid(procsField, r.Spec.Processes, `"web" process is required`)
	}

	// 环境变量中的键不能为空
	for idx, env := range r.Spec.Configuration.Env {
		path := field.NewPath("spec").Child("configuration").Child("env").Index(idx)
		if env.Name == "" {
			return field.Invalid(path.Child("name"), env.Name, "name can't be empty")
		}
	}
	return nil
}

// Get all process names
func (r *BkApp) getProcNames() []string {
	items := []string{}
	for _, proc := range r.Spec.Processes {
		items = append(items, proc.Name)
	}
	return items
}

// Validate the part of Spec which is related with image build and images
func (r *BkApp) validateBuildConfig() *field.Error {
	// Use procImageGetter to handle both legacy and hub API versions because the webhook
	// is configured with "MatchPolicy: Equivalent", which means it will be called for every
	// possible API version of "BkApp".
	//
	// NewProcImageGetter handles both API versions.
	imageGetter := NewProcImageGetter(r)
	for _, proc := range r.Spec.Processes {
		_, _, err := imageGetter.Get(proc.Name)
		if err != nil {
			return field.Invalid(
				field.NewPath(""),
				proc.Name,
				fmt.Sprintf("image not configured for process %s", proc.Name),
			)
		}
	}
	return nil
}

func (r *BkApp) validateAppProc(proc Process, idx int) *field.Error {
	pField := field.NewPath("spec").Child("processes").Index(idx)
	// 1. 进程名称必须符合正则
	if matched := ProcNameRegex.MatchString(proc.Name); !matched {
		return field.Invalid(
			pField.Child("name"),
			proc.Name,
			"must match regex "+ProcNameRegex.String(),
		)
	}
	// 2. 副本数量不能超过上限
	if *proc.Replicas > config.Global.GetProcMaxReplicas() {
		return field.Invalid(
			pField.Child("replicas"),
			*proc.Replicas,
			fmt.Sprintf("at most support %d replicas", config.Global.GetProcMaxReplicas()),
		)
	}
	// 3. TODO: Check ResQuotaPlan is valid
	return nil
}

// Validate Spec.EnvOverlay field
func (r *BkApp) validateEnvOverlay() *field.Error {
	if r.Spec.EnvOverlay == nil {
		return nil
	}

	f := field.NewPath("spec").Child("envOverlay")

	// Validate "envVariables": envName
	for i, env := range r.Spec.EnvOverlay.EnvVariables {
		envField := f.Child("envVariables").Index(i)
		if !CheckEnvName(env.EnvName) {
			return field.Invalid(envField.Child("envName"), env.EnvName, "envName is invalid")
		}
	}

	// Validate "replicas": envName and process
	maxReplicas := config.Global.GetProcMaxReplicas()
	for i, rep := range r.Spec.EnvOverlay.Replicas {
		replicasField := f.Child("replicas").Index(i)
		if !CheckEnvName(rep.EnvName) {
			return field.Invalid(replicasField.Child("envName"), rep.EnvName, "envName is invalid")
		}
		if !lo.Contains(r.getProcNames(), rep.Process) {
			return field.Invalid(replicasField.Child("process"), rep.Process, "process name is invalid")
		}
		if rep.Count > maxReplicas {
			return field.Invalid(
				replicasField.Child("count"),
				rep.Process,
				fmt.Sprintf("count can't be greater than %d", maxReplicas),
			)
		}
	}
	return nil
}
