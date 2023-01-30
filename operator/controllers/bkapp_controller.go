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

	"github.com/getsentry/sentry-go"
	"github.com/modern-go/reflect2"
	"github.com/pkg/errors"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	logf "sigs.k8s.io/controller-runtime/pkg/log"
	"sigs.k8s.io/controller-runtime/pkg/reconcile"

	"bk.tencent.com/paas-app-operator/api/v1alpha1"
	"bk.tencent.com/paas-app-operator/pkg/controllers/reconcilers"
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
//+kubebuilder:rbac:groups=networking.k8s.io,resources=ingresses,verbs=get;list;watch;create;update;patch;delete;deletecollection
//+kubebuilder:rbac:groups=networking.k8s.io,resources=ingresses/status,verbs=get

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
	log := logf.FromContext(ctx)

	app := &v1alpha1.BkApp{}
	err := r.client.Get(ctx, req.NamespacedName, app)
	if err != nil {
		log.Error(err, "unable to fetch bkapp", "NamespacedName", req.NamespacedName)
		return reconcile.Result{}, client.IgnoreNotFound(err)
	}

	if app.DeletionTimestamp.IsZero() {
		// The object is not being deleted, so if it does not have our finalizer,
		// then lets add the finalizer and update the object. This is equivalent
		// registering our finalizer.
		if !controllerutil.ContainsFinalizer(app, v1alpha1.BkAppFinalizerName) {
			controllerutil.AddFinalizer(app, v1alpha1.BkAppFinalizerName)
			if err = r.client.Update(ctx, app); err != nil {
				return reconcile.Result{}, err
			}
		}
	}

	var ret reconcilers.Result
	for _, reconciler := range []reconcilers.Reconciler{
		reconcilers.NewBkappFinalizer(r.client),
		reconcilers.NewRevisionReconciler(r.client),
		reconcilers.NewAddonReconciler(r.client),
		reconcilers.NewHookReconciler(r.client),
		reconcilers.NewDeploymentReconciler(r.client),
		reconcilers.NewServiceReconciler(r.client),
	} {
		if reflect2.IsNil(reconciler) {
			continue
		}
		ret = reconciler.Reconcile(ctx, app)
		if ret.ShouldAbort() {
			return ret.ToRepresentation()
		}
	}
	return ret.End().ToRepresentation()
}

// SetupWithManager sets up the controller with the Manager.
func (r *BkAppReconciler) SetupWithManager(ctx context.Context, mgr ctrl.Manager, opts controller.Options) error {
	err := mgr.GetFieldIndexer().IndexField(ctx, &appsv1.Deployment{}, v1alpha1.WorkloadOwnerKey, getOwnerNames)
	if err != nil {
		return err
	}

	err = mgr.GetFieldIndexer().IndexField(ctx, &corev1.Pod{}, v1alpha1.WorkloadOwnerKey, getOwnerNames)
	if err != nil {
		return err
	}

	return ctrl.NewControllerManagedBy(mgr).
		For(&v1alpha1.BkApp{}).
		WithOptions(opts).
		Owns(&appsv1.Deployment{}).
		Owns(&corev1.Pod{}).
		Complete(r)
}

func getOwnerNames(rawObj client.Object) []string {
	// 提取 Owner 名称
	owner := metav1.GetControllerOf(rawObj)
	if owner == nil {
		return nil
	}
	// 确保 Owner 类型为 BkApp
	if owner.APIVersion == v1alpha1.GroupVersion.String() && owner.Kind == v1alpha1.KindBkApp {
		return []string{owner.Name}
	}
	return nil
}
