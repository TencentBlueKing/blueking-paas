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

package v1alpha1

import (
	"github.com/getsentry/sentry-go"
	"github.com/pkg/errors"
	"github.com/samber/lo"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/util/validation/field"
	ctrl "sigs.k8s.io/controller-runtime"
	logf "sigs.k8s.io/controller-runtime/pkg/log"
	"sigs.k8s.io/controller-runtime/pkg/webhook"
)

// log is for logging in this package.
var dgmLog = logf.Log.WithName("domaingroupmapping-resource")

// SetupWebhookWithManager ...
func (r *DomainGroupMapping) SetupWebhookWithManager(mgr ctrl.Manager) error {
	return ctrl.NewWebhookManagedBy(mgr).For(r).Complete()
}

//+kubebuilder:webhook:path=/validate-paas-bk-tencent-com-v1alpha1-domaingroupmapping,mutating=false,failurePolicy=fail,sideEffects=None,groups=paas.bk.tencent.com,resources=domaingroupmappings,verbs=create;update;delete,versions=v1alpha1,name=vdomaingroupmapping.kb.io,admissionReviewVersions=v1

var _ webhook.Validator = &DomainGroupMapping{}

// ValidateCreate implements webhook.Validator so a webhook will be registered for the type
func (r *DomainGroupMapping) ValidateCreate() error {
	dgmLog.Info("validate create", "name", r.Name)
	err := r.validateDomainGroupMapping()
	if err != nil {
		sentry.CaptureException(errors.Wrapf(err, "webhook validate dgmapping [%s/%s] failed", r.Namespace, r.Name))
	}
	return err
}

// ValidateUpdate implements webhook.Validator so a webhook will be registered for the type
func (r *DomainGroupMapping) ValidateUpdate(old runtime.Object) error {
	dgmLog.Info("validate update", "name", r.Name)
	err := r.validateDomainGroupMapping()
	if err != nil {
		sentry.CaptureException(errors.Wrapf(err, "webhook validate dgmapping [%s/%s] failed", r.Namespace, r.Name))
	}
	return err
}

// ValidateDelete implements webhook.Validator so a webhook will be registered for the type
func (r *DomainGroupMapping) ValidateDelete() error {
	dgmLog.Info("validate delete (do nothing)", "name", r.Name)
	// TODO: 删除时候暂时不做任何校验，后续可以考虑支持删除保护？
	return nil
}

func (r *DomainGroupMapping) validateDomainGroupMapping() error {
	var allErrs field.ErrorList

	if err := r.validateSpecRef(); err != nil {
		allErrs = append(allErrs, err)
	}
	if err := r.validateDomainGroup(); err != nil {
		allErrs = append(allErrs, err)
	}
	if len(allErrs) == 0 {
		return nil
	}
	return apierrors.NewInvalid(GroupKindDomainGroupMapping, r.Name, allErrs)
}

func (r *DomainGroupMapping) validateSpecRef() *field.Error {
	// 目前只支持 BkApp 作为引用对象
	if !lo.Contains(AllowedDomainGroupMappingRefKinds, r.Spec.Ref.Kind) {
		return field.NotSupported(
			field.NewPath("spec").Child("ref").Child("kind"),
			r.Spec.Ref.Kind, AllowedDomainGroupMappingRefKinds,
		)
	}
	return nil
}

func (r *DomainGroupMapping) validateDomainGroup() *field.Error {
	for idx, dg := range r.Spec.Data {
		dgField := field.NewPath("spec").Child("data").Index(idx)
		if !lo.Contains(AllowedSourceTypes, dg.SourceType) {
			return field.NotSupported(dgField.Child("sourceType"), dg.SourceType, AllowedSourceTypes)
		}
		if len(dg.Domains) == 0 {
			return field.Invalid(dgField.Child("domains"), dg.Domains, "at least one domain required")
		}
	}
	return nil
}
