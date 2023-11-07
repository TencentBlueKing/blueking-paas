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

package reconcilers

import (
	"context"
	"fmt"

	"github.com/pkg/errors"
	"github.com/samber/lo"
	appsv1 "k8s.io/api/apps/v1"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources"
	"bk.tencent.com/paas-app-operator/pkg/controllers/svcdisc"
	"bk.tencent.com/paas-app-operator/pkg/utils/kubestatus"
)

// NewDeploymentReconciler will return a DeploymentReconciler with given k8s client
func NewDeploymentReconciler(client client.Client) *DeploymentReconciler {
	return &DeploymentReconciler{Client: client}
}

// DeploymentReconciler 负责处理 Deployment 相关的调和逻辑
type DeploymentReconciler struct {
	Client client.Client
	Result Result
}

// Reconcile ...
func (r *DeploymentReconciler) Reconcile(ctx context.Context, bkapp *paasv1alpha2.BkApp) Result {
	log := logf.FromContext(ctx)

	current, err := r.getCurrentState(ctx, bkapp)
	if err != nil {
		return r.Result.withError(err)
	}
	expected := resources.GetWantedDeploys(bkapp)
	if ok := svcdisc.NewWorkloadsMutator(r.Client, bkapp).ApplyToDeployments(ctx, expected); ok {
		log.V(2).Info("Applied svc-discovery related changes to deployments.")
	}

	outdated := FindExtraByName(current, expected)

	if len(outdated) != 0 {
		for _, deploy := range outdated {
			if err = r.Client.Delete(ctx, deploy); err != nil {
				return r.Result.withError(err)
			}
		}
	}
	for _, deploy := range expected {
		if err = r.deploy(ctx, deploy); err != nil {
			return r.Result.withError(err)
		}
	}

	if err = r.updateCondition(ctx, bkapp); err != nil {
		return r.Result.withError(err)
	}
	// deployment 未就绪, 下次调和循环重新更新状态
	if bkapp.Status.Phase == paasv1alpha2.AppPending {
		return r.Result.requeue(paasv1alpha2.DefaultRequeueAfter)
	}
	return r.Result
}

// 获取应用当前在集群中的状态
func (r *DeploymentReconciler) getCurrentState(
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

// 将给定的 deployment 发布至 k8s, 如果不存在则创建, 如果同名对象已存在且配置发生变化, 则更新
func (r *DeploymentReconciler) deploy(ctx context.Context, deploy *appsv1.Deployment) error {
	return UpsertObject(ctx, r.Client, deploy, r.updateHandler)
}

// updateHandler Deployment 更新策略: 除非在注解中指定了 `bkapp.paas.bk.tencent.com/deployment-skip-update`
// （执行测试代码时会用到）, 或配置内容没有任何变化，否则总是更新
func (r *DeploymentReconciler) updateHandler(
	ctx context.Context,
	cli client.Client,
	current *appsv1.Deployment,
	want *appsv1.Deployment,
) error {
	log := logf.FromContext(ctx)
	if current.Annotations[paasv1alpha2.DeploySkipUpdateAnnoKey] == "true" {
		return nil
	}
	// Skip update if the content of deployment is not changed, unnecessary updates will trigger
	// the reconcile loop of the BkApp again and result infinite loops.
	if want.Annotations[paasv1alpha2.DeployContentHashAnnoKey] == current.Annotations[paasv1alpha2.DeployContentHashAnnoKey] {
		log.V(2).Info("The content of deployment is not changed, skip update.")
		return nil
	}

	if err := cli.Update(ctx, want); err != nil {
		return errors.Wrapf(
			err, "failed to update %s(%s)", want.GetObjectKind().GroupVersionKind().String(), want.GetName(),
		)
	}
	return nil
}

// update condition `AppAvailable`
func (r *DeploymentReconciler) updateCondition(ctx context.Context, bkapp *paasv1alpha2.BkApp) error {
	current, err := r.getCurrentState(ctx, bkapp)
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
			Message:            "no running processes",
			ObservedGeneration: bkapp.Status.ObservedGeneration,
		})
		return r.Client.Status().Update(ctx, bkapp)
	}

	availableCount := 0
	anyFailed := false
	for _, deployment := range current {
		healthStatus := kubestatus.CheckDeploymentHealthStatus(deployment)
		if healthStatus.Phase == paasv1alpha2.HealthHealthy {
			availableCount += 1
			continue
		}

		failMessage, err := kubestatus.GetDeploymentDirectFailMessage(ctx, r.Client, deployment)
		if errors.Is(err, kubestatus.ErrDeploymentStillProgressing) {
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
				ObservedGeneration: bkapp.Status.ObservedGeneration,
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
				ObservedGeneration: bkapp.Status.ObservedGeneration,
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
				ObservedGeneration: bkapp.Status.ObservedGeneration,
			})
		}
	}
	return r.Client.Status().Update(ctx, bkapp)
}
