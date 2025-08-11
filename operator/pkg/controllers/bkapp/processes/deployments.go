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

package processes

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/pkg/errors"
	"github.com/samber/lo"
	appsv1 "k8s.io/api/apps/v1"
	apiequality "k8s.io/apimachinery/pkg/api/equality"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	kuberuntime "k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	clientsetscheme "k8s.io/client-go/kubernetes/scheme"
	"sigs.k8s.io/controller-runtime/pkg/client"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/controllers/base"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/processes/components"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/processes/resources"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/svcdisc"
	"bk.tencent.com/paas-app-operator/pkg/health"
	"bk.tencent.com/paas-app-operator/pkg/kubeutil"
	"bk.tencent.com/paas-app-operator/pkg/metrics"
)

// NewDeploymentReconciler will return a DeploymentReconciler with given k8s client
func NewDeploymentReconciler(client client.Client) *DeploymentReconciler {
	return &DeploymentReconciler{Client: client}
}

// DeploymentReconciler 负责处理 Deployment 相关的调和逻辑
type DeploymentReconciler struct {
	Client client.Client
	Result base.Result
}

// Reconcile ...
func (r *DeploymentReconciler) Reconcile(ctx context.Context, bkapp *paasv1alpha2.BkApp) base.Result {
	log := logf.FromContext(ctx)
	currentDeploys, err := r.getCurrentDeployments(ctx, bkapp)
	if err != nil {
		return r.Result.WithError(err)
	}

	// Get deployments synced with the current bkapp, new deployment resource might be created and old deployments
	// might be updated.
	newDeployMap, err := r.getNewDeployments(ctx, bkapp, currentDeploys)
	if err != nil {
		return r.Result.WithError(err)
	}
	// Clean up the deployments which are not in the new deploys
	newDeployNames := []string{}
	for _, d := range newDeployMap {
		newDeployNames = append(newDeployNames, d.Name)
	}
	if err = r.cleanUpDeployments(ctx, bkapp, currentDeploys, newDeployNames); err != nil {
		return r.Result.WithError(err)
	}

	// Modify conditions in status
	if err = r.updateCondition(ctx, bkapp); err != nil {
		return r.Result.WithError(err)
	}
	// The statuses of the deployments is not ready yet, reconcile later.
	if bkapp.Status.Phase == paasv1alpha2.AppPending {
		log.V(1).Info("bkapp is still pending, reconcile later", "bkapp", bkapp.Name)
		return r.Result.Requeue(paasv1alpha2.DefaultRequeueAfter)
	}
	return r.Result
}

// get all deployment objects owned by the given bkapp
func (r *DeploymentReconciler) getCurrentDeployments(
	ctx context.Context,
	bkapp *paasv1alpha2.BkApp,
) (result []*appsv1.Deployment, err error) {
	deployList := appsv1.DeploymentList{}
	if err = r.Client.List(
		ctx, &deployList, client.InNamespace(bkapp.Namespace),
		client.MatchingFields{paasv1alpha2.KubeResOwnerKey: bkapp.Name},
	); err != nil {
		return nil, errors.Wrap(err, "failed to list app's deployments")
	}

	return lo.ToSlicePtr(deployList.Items), nil
}

// Get the deployments which match the given bkapp's specifications. Main behaviour:
//
// - Create new deployments if does not exist;
// - Update existing deployments if the resource exists but don't match current bkapp;
// - Use existing deployments if it match current bkapp.
func (r *DeploymentReconciler) getNewDeployments(
	ctx context.Context,
	bkapp *paasv1alpha2.BkApp,
	deployList []*appsv1.Deployment,
) (results map[string]*appsv1.Deployment, err error) {
	log := logf.FromContext(ctx)
	results = make(map[string]*appsv1.Deployment)
	existingNewDeployMap := r.findNewDeployments(ctx, bkapp, deployList)
	for _, proc := range bkapp.Spec.Processes {
		// Use existing deployment directly
		if existingDeploy, exists := existingNewDeployMap[proc.Name]; exists {
			results[proc.Name] = existingDeploy
			continue
		}

		// The new deployment does not exist or has not been up to date, perform upsert
		deployment, err := resources.BuildProcDeployment(bkapp, proc.Name)
		if err != nil {
			return nil, errors.Wrapf(err, "get new deployment error, build failed for %s:%s.", bkapp.Name, proc.Name)
		}
		// Apply service discovery related changes
		if ok := svcdisc.NewWorkloadsMutator(r.Client, bkapp).ApplyToDeployment(ctx, deployment); ok {
			log.V(1).
				Info("Applied svc-discovery related changes to deployments", "bkapp", bkapp.Name, "proc", proc.Name)
		}

		// patch components to deployment
		if err = components.PatchToDeployment(&proc, deployment); err != nil {
			return nil, errors.Wrap(err, "get new deployment error")
		}
		if err = kubeutil.UpsertObject(ctx, r.Client, deployment, r.updateHandler); err != nil {
			return nil, errors.Wrap(err, "get new deployment error")
		}
		results[proc.Name] = deployment
	}
	return results, nil
}

// Find deployments which match the given bkapp's specifications, accept a list fo deployment objects,
// return {process name: *deployment}.
func (r *DeploymentReconciler) findNewDeployments(
	ctx context.Context,
	bkapp *paasv1alpha2.BkApp,
	deployList []*appsv1.Deployment,
) map[string]*appsv1.Deployment {
	log := logf.FromContext(ctx)
	results := make(map[string]*appsv1.Deployment)
	for _, d := range deployList {
		// Ignore deployment which does not contain the serialized bkapp in annotation, which means the object was
		// created by legacy controller.
		serializedBkApp, exists := d.Annotations[paasv1alpha2.LastSyncedSerializedBkAppAnnoKey]
		if !exists {
			log.V(1).Info("Deployment does not contain the serialized bkapp in annots", "name", d.Name)
			continue
		}
		// Decode the serialized BkApp into object
		// TODO: Handle changes across different api versions which introduces backward-incompatible schema changes.
		// In that case, the "converter" might be needed.
		var syncedBkApp paasv1alpha2.BkApp
		if err := kuberuntime.DecodeInto(clientsetscheme.Codecs.UniversalDecoder(), []byte(serializedBkApp), &syncedBkApp); err != nil {
			log.Error(err, "Unmarshal serialized bkapp failed", "name", d.Name)
			continue
		}

		// If the deployment ID has been changed, always treat current deployment as outdated.
		if bkapp.Annotations[paasv1alpha2.DeployIDAnnoKey] != syncedBkApp.Annotations[paasv1alpha2.DeployIDAnnoKey] {
			log.V(1).Info("Deploy ID changed, current deployment is outdated", "name", d.Name)
			continue
		}
		if BkAppSemanticEqual(bkapp, &syncedBkApp) {
			procName := d.Labels[paasv1alpha2.ProcessNameKey]
			results[procName] = d
			continue
		}
	}
	return results
}

// Clean up deployments which are not needed anymore. Args:
// - deployList: A list of deployment resources.
// - newDeployNames: The names of deployment that are synced with the current bkapp.
func (r *DeploymentReconciler) cleanUpDeployments(ctx context.Context,
	bkapp *paasv1alpha2.BkApp,
	deployList []*appsv1.Deployment,
	newDeployNames []string,
) error {
	for _, d := range deployList {
		if lo.Contains(newDeployNames, d.Name) {
			continue
		}
		if err := r.Client.Delete(ctx, d); err != nil {
			metrics.IncDeleteOutdatedDeployFailures(bkapp, d.Name)
			return errors.Wrapf(err, "cleaning up deployments")
		}
	}
	return nil
}

// update condition `AppAvailable`
func (r *DeploymentReconciler) updateCondition(ctx context.Context, bkapp *paasv1alpha2.BkApp) error {
	current, err := r.getCurrentDeployments(ctx, bkapp)
	if err != nil {
		return err
	}
	if len(current) == 0 {
		// TODO: Phase 应该是应用下架、休眠？
		bkapp.Status.Phase = paasv1alpha2.AppFailed
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:               paasv1alpha2.AppAvailable,
			Status:             metav1.ConditionFalse,
			Reason:             "Teardown",
			Message:            "No running processes",
			ObservedGeneration: bkapp.Generation,
		})
		return nil
	}

	availableCount := 0
	anyFailed := false
	for _, deployment := range current {
		healthStatus := health.CheckDeploymentHealthStatus(deployment)
		if healthStatus.Phase == paasv1alpha2.HealthHealthy {
			availableCount += 1
			continue
		}

		if healthStatus.Phase == paasv1alpha2.HealthProgressing {
			continue
		}

		failMessage, err := health.GetDeploymentDirectFailMessage(ctx, r.Client, deployment)
		if errors.Is(err, health.ErrDeploymentStillProgressing) {
			continue
		}
		if healthStatus.Phase == paasv1alpha2.HealthUnhealthy {
			failMessage = deployment.Name + ": " + healthStatus.Message
		}

		if failMessage != "" {
			anyFailed = true
			bkapp.Status.Phase = paasv1alpha2.AppFailed
			apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
				Type:               paasv1alpha2.AppAvailable,
				Status:             metav1.ConditionFalse,
				Reason:             "ReplicaFailure",
				Message:            failMessage,
				ObservedGeneration: bkapp.Generation,
			})
			break
		}
	}

	if !anyFailed {
		if availableCount == len(current) {
			// AppAvailable means the BkApp is available and ready to service requests,
			// but now we set AppAvailable to ConditionTrue before create Service when first time deploy.
			// TODO: fix this problem, should we create service before reconcile processes?
			bkapp.Status.Phase = paasv1alpha2.AppRunning
			apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
				Type:               paasv1alpha2.AppAvailable,
				Status:             metav1.ConditionTrue,
				Reason:             "AppAvailable",
				Message:            "Rolling upgrade",
				ObservedGeneration: bkapp.Generation,
			})
		} else {
			bkapp.Status.Phase = paasv1alpha2.AppPending
			apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
				Type:   paasv1alpha2.AppAvailable,
				Status: metav1.ConditionFalse,
				Reason: "Progressing",
				Message: fmt.Sprintf(
					"Waiting for deployment finish: %d/%d Process are available...", availableCount, len(current),
				),
				ObservedGeneration: bkapp.Generation,
			})
		}
	}
	return nil
}

// The handler for updating a deployment resource.
func (r *DeploymentReconciler) updateHandler(
	ctx context.Context,
	cli client.Client,
	current *appsv1.Deployment,
	want *appsv1.Deployment,
) error {
	// Respect an annotation to skip update, useful for testing
	if current.Annotations[paasv1alpha2.DeploySkipUpdateAnnoKey] == "true" {
		return nil
	}

	// Only patch the serialized bkapp in annotations to avoid unnecessary updates, this happens when we upgrade
	// the operator from an older version which does not write "last-synced-serialized-bkapp" annotation.
	//
	// WARNING: After the patch successfully applied, updates on the deployment will be skipped until the
	// bkapp resource spec from the input has been changed.
	_, currentHasBkappAnnot := current.Annotations[paasv1alpha2.LastSyncedSerializedBkAppAnnoKey]
	if !currentHasBkappAnnot {
		patchBody, _ := json.Marshal(map[string]any{
			"metadata": map[string]any{
				"annotations": map[string]string{
					paasv1alpha2.LastSyncedSerializedBkAppAnnoKey: want.Annotations[paasv1alpha2.LastSyncedSerializedBkAppAnnoKey],
				},
			},
		})
		if err := cli.Patch(ctx, current, client.RawPatch(types.MergePatchType, patchBody)); err != nil {
			return errors.Wrapf(
				err,
				"patch serialized bkapp annotation for %s(%s) error.",
				want.GetObjectKind().GroupVersionKind().String(),
				want.GetName(),
			)
		}
		return nil
	}

	// Perform the resource update
	if err := cli.Update(ctx, want); err != nil {
		return errors.Wrapf(
			err, "update %s(%s)", want.GetObjectKind().GroupVersionKind().String(), want.GetName(),
		)
	}
	return nil
}

// BkAppSemanticEqual checks if two bkapp resources are semantically equal, it respect the default values.
// Args:
// - bkApp: The bkapp resource.
// - syncBkApp: The bkapp stored in the annotation, not mutated by the default webhook.
func BkAppSemanticEqual(bkApp, syncedBkApp *paasv1alpha2.BkApp) bool {
	bkAppCopy := bkApp.DeepCopy()
	syncedBkAppCopy := syncedBkApp.DeepCopy()
	// Remove unrelated content before comparing
	delete(bkAppCopy.Annotations, paasv1alpha2.DeployIDAnnoKey)
	delete(syncedBkAppCopy.Annotations, paasv1alpha2.DeployIDAnnoKey)

	// Compare the given and the synced BkApp
	if apiequality.Semantic.DeepEqual(bkAppCopy.Spec, syncedBkAppCopy.Spec) &&
		apiequality.Semantic.DeepEqual(bkAppCopy.Annotations, syncedBkAppCopy.Annotations) {
		return true
	}
	// Also compare with the synced BkApp whose "nil" values have been set to default values, this can
	// handle the situation when BkApp's schema has been updated and the given app has been mutated by
	// the webhook. In this case, the former comparison will fail because new fields in the synced bkapp have
	// not been set to the default values but the given bkapp has.
	syncedBkAppCopy.Default()
	if apiequality.Semantic.DeepEqual(bkAppCopy.Spec, syncedBkAppCopy.Spec) &&
		apiequality.Semantic.DeepEqual(bkAppCopy.Annotations, syncedBkAppCopy.Annotations) {
		return true
	}
	return false
}
