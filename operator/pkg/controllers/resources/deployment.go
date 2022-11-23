/*
 * Tencent is pleased to support the open source community by making
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

	"github.com/samber/lo"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime/schema"

	"bk.tencent.com/paas-app-operator/api/v1alpha1"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/labels"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/names"
	"bk.tencent.com/paas-app-operator/pkg/utils/quota"
)

const (
	// DeployRevisionHistoryLimit 更新 Deployment 时不保留旧 ReplicasSet
	DeployRevisionHistoryLimit = int32(0)
)

// GetWantedDeploys 根据应用生成对应的 Deployment 配置列表
func GetWantedDeploys(app *v1alpha1.BkApp) []*appsv1.Deployment {
	newRevision := int64(0)
	if rev := app.Status.Revision; rev != nil {
		newRevision = rev.Revision
	}
	annotations := map[string]string{v1alpha1.RevisionAnnoKey: strconv.FormatInt(newRevision, 10)}
	envs := GetAppEnvs(app)
	deployList := []*appsv1.Deployment{}
	replicasGetter := NewReplicasGetter(app)
	for _, proc := range app.Spec.Processes {
		selector := labels.PodSelector(app, proc.Name)
		objLabels := labels.Deployment(app, proc.Name)

		deployList = append(deployList, &appsv1.Deployment{
			TypeMeta: metav1.TypeMeta{
				APIVersion: "apps/v1",
				Kind:       "Deployment",
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:        names.Deployment(app, proc.Name),
				Namespace:   app.Namespace,
				Labels:      objLabels,
				Annotations: annotations,
				OwnerReferences: []metav1.OwnerReference{
					*metav1.NewControllerRef(app, schema.GroupVersionKind{
						Group:   v1alpha1.GroupVersion.Group,
						Version: v1alpha1.GroupVersion.Version,
						Kind:    v1alpha1.KindBkApp,
					}),
				},
			},
			Spec: appsv1.DeploymentSpec{
				Selector:             &metav1.LabelSelector{MatchLabels: selector},
				RevisionHistoryLimit: lo.ToPtr(DeployRevisionHistoryLimit),
				Replicas:             replicasGetter.Get(proc.Name),
				Template: corev1.PodTemplateSpec{
					ObjectMeta: metav1.ObjectMeta{
						Labels:      objLabels,
						Annotations: annotations,
					},
					Spec: corev1.PodSpec{
						Containers:       buildContainers(proc, envs),
						ImagePullSecrets: buildImagePullSecrets(app),
					},
				},
			},
		})
	}
	return deployList
}

// buildContainers 根据配置生产对应容器配置列表（目前设计单个 proc 只会有单个容器）
func buildContainers(proc v1alpha1.Process, envs []corev1.EnvVar) []corev1.Container {
	// 由于 webhook 中已做校验，因此这里不会有 err，可以忽略
	cpuQuota, _ := quota.NewQuantity(proc.CPU, quota.CPU)
	memQuota, _ := quota.NewQuantity(proc.Memory, quota.Memory)

	container := corev1.Container{
		Name:  proc.Name,
		Image: proc.Image,
		Resources: corev1.ResourceRequirements{
			// 目前 Requests 配额策略：CPU 为 Limits 1/4，内存为 Limits 的 1/2
			Requests: corev1.ResourceList{
				corev1.ResourceCPU:    *quota.Div(cpuQuota, 4),
				corev1.ResourceMemory: *quota.Div(memQuota, 2),
			},
			Limits: corev1.ResourceList{
				corev1.ResourceCPU:    *cpuQuota,
				corev1.ResourceMemory: *memQuota,
			},
		},
		ImagePullPolicy: proc.ImagePullPolicy,
		Env:             envs,
		Command:         proc.Command,
		Args:            proc.Args,
	}
	// TODO P3 理论上所有进程都需要对外提供服务（暴露端口？）
	if proc.TargetPort != 0 {
		container.Ports = []corev1.ContainerPort{{ContainerPort: proc.TargetPort}}
	}
	return []corev1.Container{container}
}

// buildImagePullSecrets 返回拉取镜像的 Secrets 列表
func buildImagePullSecrets(app *v1alpha1.BkApp) []corev1.LocalObjectReference {
	if app.GetAnnotations()[v1alpha1.ImageCredentialsRefAnnoKey] == "" {
		return nil
	}
	// DefaultImagePullSecretName 由 workloads 服务负责创建
	return []corev1.LocalObjectReference{
		{
			Name: v1alpha1.DefaultImagePullSecretName,
		},
	}
}
