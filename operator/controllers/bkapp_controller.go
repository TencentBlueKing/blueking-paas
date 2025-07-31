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

package controllers

import (
	"context"
	"time"

	"github.com/getsentry/sentry-go"
	"github.com/modern-go/reflect2"
	"github.com/pkg/errors"
	"github.com/samber/lo"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/builder"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	logf "sigs.k8s.io/controller-runtime/pkg/log"
	"sigs.k8s.io/controller-runtime/pkg/predicate"
	"sigs.k8s.io/controller-runtime/pkg/reconcile"

	autoscaling "github.com/Tencent/bk-bcs/bcs-runtime/bcs-k8s/bcs-component/bcs-general-pod-autoscaler/pkg/apis/autoscaling/v1alpha1"

	paasv1alpha1 "bk.tencent.com/paas-app-operator/api/v1alpha1"
	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/controllers/base"
	"bk.tencent.com/paas-app-operator/pkg/config"
	bkappctrl "bk.tencent.com/paas-app-operator/pkg/controllers/bkapp"
	autoscalingctrl "bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/autoscaling"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/hooks"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/processes"
	"bk.tencent.com/paas-app-operator/pkg/metrics"
)

// NewBkAppReconciler will return a BkAppReconciler with given k8s client and scheme
func NewBkAppReconciler(cli client.Client, scheme *runtime.Scheme) *BkAppReconciler {
	return &BkAppReconciler{client: cli, scheme: scheme}
}

// BkAppReconciler reconciles a BkApp object
type BkAppReconciler struct {
	client client.Client
	scheme *runtime.Scheme
}

//+kubebuilder:rbac:groups=paas.bk.tencent.com,resources=bkapps,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=paas.bk.tencent.com,resources=bkapps/status,verbs=get;update;patch
//+kubebuilder:rbac:groups=paas.bk.tencent.com,resources=bkapps/finalizers,verbs=update
//+kubebuilder:rbac:groups=apps,resources=deployments,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=apps,resources=deployments/status,verbs=get
//+kubebuilder:rbac:groups=core,resources=pods,verbs=get;list;watch;create;update;patch;delete;deletecollection
//+kubebuilder:rbac:groups=core,resources=pods/status,verbs=get
//+kubebuilder:rbac:groups=core,resources=services,verbs=get;list;watch;create;update;patch;delete;deletecollection
//+kubebuilder:rbac:groups=core,resources=services/status,verbs=get
//+kubebuilder:rbac:groups=core,resources=configmaps,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=networking.k8s.io,resources=ingresses,verbs=get;list;watch;create;update;patch;delete;deletecollection
//+kubebuilder:rbac:groups=networking.k8s.io,resources=ingresses/status,verbs=get
//+kubebuilder:rbac:groups=autoscaling.tkex.tencent.com,resources=generalpodautoscalers,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=autoscaling.tkex.tencent.com,resources=generalpodautoscalers/status,verbs=get

// Reconcile is part of the main kubernetes reconciliation loop which aims to
// move the current state of the cluster closer to the desired state.
//
// For more details, check Reconcile and its Result here:
// - https://pkg.go.dev/sigs.k8s.io/controller-runtime@v0.12.1/pkg/reconcile
func (r *BkAppReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	result, err := r.reconcile(ctx, req)
	if err != nil {
		sentry.CaptureException(
			errors.WithMessagef(
				err,
				"error found while executing BkApp (%s/%s) reconciler loop",
				req.Namespace,
				req.Name,
			),
		)
	}
	return result, err
}

func (r *BkAppReconciler) reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	st := time.Now()
	defer metrics.ObserveBkappReconcileDuration(req.NamespacedName.String(), st)

	log := logf.FromContext(ctx)

	bkapp := &paasv1alpha2.BkApp{}
	err := r.client.Get(ctx, req.NamespacedName, bkapp)
	if err != nil {
		log.Error(err, "unable to fetch bkapp", "NamespacedName", req.NamespacedName)
		metrics.IncGetBkappFailures(req.NamespacedName.String())
		return reconcile.Result{}, client.IgnoreNotFound(err)
	}
	// deep copy bkapp to generate merge-patch
	originalBkApp := bkapp.DeepCopy()

	if bkapp.DeletionTimestamp.IsZero() {
		// The object is not being deleted, so if it does not have our finalizer,
		// then lets add the finalizer and update the object. This is equivalent
		// registering our finalizer.
		if !controllerutil.ContainsFinalizer(bkapp, paasv1alpha2.BkAppFinalizerName) {
			controllerutil.AddFinalizer(bkapp, paasv1alpha2.BkAppFinalizerName)
			if err = r.client.Update(ctx, bkapp); err != nil {
				metrics.IncAddFinalizerFailures(bkapp)
				return reconcile.Result{}, err
			}
		}
	}

	if bkapp.Generation > bkapp.Status.ObservedGeneration {
		bkapp.Status.Phase = paasv1alpha2.AppPending
		if err = r.updateStatus(ctx, bkapp, originalBkApp, nil); err != nil {
			return reconcile.Result{}, errors.Wrap(err, "update bkapp status when generation changed")
		}
	}

	var ret base.Result
	for _, reconciler := range []base.Reconciler{
		// NOTE: The order of these reconcilers is important.
		bkappctrl.NewBkappFinalizer(r.client),
		// Check if a new deployment action has been issued.
		bkappctrl.NewDeployActionReconciler(r.client),
		// Make sure the "pre-release" hook has been finished if specified.
		hooks.NewHookReconciler(r.client),

		// Other reconcilers related with workloads
		processes.NewDeploymentReconciler(r.client),
		processes.NewServiceReconciler(r.client),
		autoscalingctrl.NewReconciler(r.client),
	} {
		if reflect2.IsNil(reconciler) {
			continue
		}
		ret = reconciler.Reconcile(ctx, bkapp)
		if ret.ShouldAbort() {
			if err = r.updateStatus(ctx, bkapp, originalBkApp, ret.Error()); err != nil {
				ret = ret.WithError(err)
			}
			return ret.ToRepresentation()
		}
	}

	if err = r.updateStatus(ctx, bkapp, originalBkApp, ret.Error()); err != nil {
		ret = ret.WithError(err)
	}
	return ret.End().ToRepresentation()
}

func (r *BkAppReconciler) updateStatus(
	ctx context.Context,
	after *paasv1alpha2.BkApp,
	before *paasv1alpha2.BkApp,
	reconcileErr error,
) error {
	if reconcileErr == nil {
		// 更新 ObservedGeneration, 表示成功完成了一次新版本的调和流程
		after.Status.ObservedGeneration = after.Generation
	}

	if err := r.client.Status().Patch(ctx, after, client.MergeFrom(before)); err != nil {
		syncErr := errors.Wrap(err, "update bkapp status")
		if reconcileErr == nil {
			return syncErr
		} else {
			// 与调和错误拼接
			return errors.Wrap(reconcileErr, syncErr.Error())
		}
	}

	return nil
}

// SetupWithManager sets up the controller with the Manager.
func (r *BkAppReconciler) SetupWithManager(ctx context.Context, mgr ctrl.Manager, opts controller.Options) error {
	err := mgr.GetFieldIndexer().IndexField(ctx, &appsv1.Deployment{}, paasv1alpha2.KubeResOwnerKey, getOwnerNames)
	if err != nil {
		return err
	}

	err = mgr.GetFieldIndexer().IndexField(ctx, &corev1.Pod{}, paasv1alpha2.KubeResOwnerKey, getOwnerNames)
	if err != nil {
		return err
	}

	controllerBuilder := ctrl.NewControllerManagedBy(mgr).
		// trigger when bkapp .spec changed or annotation changed.
		For(&paasv1alpha2.BkApp{}, builder.WithPredicates(predicate.Or(predicate.GenerationChangedPredicate{},
			predicate.AnnotationChangedPredicate{}))).
		WithOptions(opts).
		// trigger when deployment changed, i.e. when the deployment was deleted by others.
		Owns(&appsv1.Deployment{}, builder.WithPredicates(predicate.Or(predicate.GenerationChangedPredicate{},
			predicate.AnnotationChangedPredicate{}))).
		// trigger when pod run success or failed
		Owns(&corev1.Pod{}, builder.WithPredicates(predicate.Or(bkappctrl.NewHookSuccessPredicate(),
			bkappctrl.NewHookFailedPredicate())))

	if config.Global.IsAutoscalingEnabled() {
		if err = mgr.GetFieldIndexer().IndexField(
			ctx, &autoscaling.GeneralPodAutoscaler{}, paasv1alpha2.KubeResOwnerKey, getOwnerNames,
		); err != nil {
			return err
		}
		controllerBuilder = controllerBuilder.Owns(&autoscaling.GeneralPodAutoscaler{})
	}

	return controllerBuilder.Complete(r)
}

func getOwnerNames(rawObj client.Object) []string {
	// 提取 Owner 名称
	owner := metav1.GetControllerOf(rawObj)
	if owner == nil {
		return nil
	}
	// 确保 Owner 类型为 BkApp，但需要兼容多版本的情况
	ownerApiVersions := []string{
		paasv1alpha1.GroupVersion.String(),
		paasv1alpha2.GroupVersion.String(),
	}
	if lo.Contains(ownerApiVersions, owner.APIVersion) && owner.Kind == paasv1alpha2.KindBkApp {
		return []string{owner.Name}
	}
	return nil
}
