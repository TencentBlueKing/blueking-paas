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

	"github.com/samber/lo"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime/schema"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/labels"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/names"
)

const (
	// DeployRevisionHistoryLimit 更新 Deployment 时不保留旧 ReplicasSet
	DeployRevisionHistoryLimit = int32(0)

	// DefaultImage 是当无法获取进程镜像时使用的默认镜像
	DefaultImage = "busybox:latest"
)

// log is for logging in this package.
var log = logf.Log.WithName("controllers-resources")

// GetWantedDeploys 根据应用生成对应的 Deployment 配置列表
func GetWantedDeploys(app *paasv1alpha2.BkApp) []*appsv1.Deployment {
	newRevision := int64(0)
	if rev := app.Status.Revision; rev != nil {
		newRevision = rev.Revision
	}
	annotations := map[string]string{paasv1alpha2.RevisionAnnoKey: strconv.FormatInt(newRevision, 10)}
	envs := GetAppEnvs(app)
	deployList := []*appsv1.Deployment{}
	replicasGetter := NewReplicasGetter(app)
	for _, proc := range app.Spec.Processes {
		selector := labels.PodSelector(app, proc.Name)
		objLabels := labels.Deployment(app, proc.Name)

		// TODO: Add error handling
		image, pullPolicy, err := paasv1alpha2.NewProcImageGetter(app).Get(proc.Name)
		if err != nil {
			log.Info("Failed to get image for process %s: %v, use default values.", proc.Name, err)
			image = DefaultImage
			pullPolicy = corev1.PullIfNotPresent
		}

		resGetter := paasv1alpha2.NewProcResourcesGetter(app)
		resReq, err := resGetter.Get(proc.Name)
		if err != nil {
			log.Info("Failed to get resources for process %s: %v, use default values.", proc.Name, err)
			resReq = resGetter.GetDefault()
		}

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
						Group:   paasv1alpha2.GroupVersion.Group,
						Version: paasv1alpha2.GroupVersion.Version,
						Kind:    paasv1alpha2.KindBkApp,
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
						Containers:       buildContainers(proc, envs, image, pullPolicy, resReq),
						ImagePullSecrets: buildImagePullSecrets(app),
					},
				},
			},
		})
	}
	return deployList
}

// buildContainers 根据配置生产对应容器配置列表（目前设计单个 proc 只会有单个容器）
//
// - proc: 应用定义的进程对象
// - envs: 环境变量列表
// - image: 进程的镜像地址
// - pullPolicy: 镜像拉取策略
// - resRequirements: 容器资源限制
func buildContainers(
	proc paasv1alpha2.Process,
	envs []corev1.EnvVar,
	image string,
	pullPolicy corev1.PullPolicy,
	resRequirements corev1.ResourceRequirements,
) []corev1.Container {
	container := corev1.Container{
		Name:            proc.Name,
		Image:           image,
		Resources:       resRequirements,
		ImagePullPolicy: pullPolicy,
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
func buildImagePullSecrets(app *paasv1alpha2.BkApp) []corev1.LocalObjectReference {
	if app.GetAnnotations()[paasv1alpha2.ImageCredentialsRefAnnoKey] == "" {
		return nil
	}
	// DefaultImagePullSecretName 由 workloads 服务负责创建
	return []corev1.LocalObjectReference{
		{
			Name: paasv1alpha2.DefaultImagePullSecretName,
		},
	}
}
