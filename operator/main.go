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

package main

import (
	"context"
	"flag"
	"net/http"
	"net/url"
	"os"
	"time"

	// Import all Kubernetes client auth plugins (e.g. Azure, GCP, OIDC, etc.)
	// to ensure that exec-entrypoint and run can make use of them.
	_ "k8s.io/client-go/plugin/pkg/client/auth"

	"github.com/getsentry/sentry-go"
	"github.com/pkg/errors"
	"golang.org/x/time/rate"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	"k8s.io/client-go/util/workqueue"
	ctrl "sigs.k8s.io/controller-runtime"
	cfg "sigs.k8s.io/controller-runtime/pkg/config/v1alpha1"
	"sigs.k8s.io/controller-runtime/pkg/controller"
	"sigs.k8s.io/controller-runtime/pkg/healthz"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"

	paasv1alpha1 "bk.tencent.com/paas-app-operator/api/v1alpha1"
	"bk.tencent.com/paas-app-operator/controllers"
	"bk.tencent.com/paas-app-operator/pkg/client"
	"bk.tencent.com/paas-app-operator/pkg/config"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources"
	"bk.tencent.com/paas-app-operator/pkg/platform/external"
	//+kubebuilder:scaffold:imports
)

var (
	scheme   = runtime.NewScheme()
	setupLog = ctrl.Log.WithName("setup")
	cfgFile  string
)

func init() {
	utilruntime.Must(clientgoscheme.AddToScheme(scheme))
	utilruntime.Must(paasv1alpha1.AddToScheme(scheme))
	//+kubebuilder:scaffold:scheme
}

func main() {
	flag.StringVar(&cfgFile, "config", "",
		"The controller will load its initial configuration from this file. "+
			"Omit this flag to use the default configuration values. "+
			"Command-line flags override configuration from this file.")
	opts := zap.Options{
		Development: true,
	}
	opts.BindFlags(flag.CommandLine)
	flag.Parse()

	ctrl.SetLogger(zap.New(zap.UseFlagOptions(&opts)))

	var err error
	projConf := paasv1alpha1.NewProjectConfig()
	options := ctrl.Options{
		Scheme:         scheme,
		LeaderElection: false,
	}
	if cfgFile != "" {
		options, err = options.AndFrom(ctrl.ConfigFile().AtPath(cfgFile).OfKind(projConf))
		if err != nil {
			setupLog.Error(err, "unable to load the config file")
			os.Exit(1)
		}
	}

	config.SetConfig(projConf)
	// not use global because import cycle
	paasv1alpha1.SetConfig(projConf)

	// ref: how to usage sentry in go -> https://docs.sentry.io/platforms/go/usage/
	sentryDSN := config.Global.PlatformConfig.SentryDSN
	if sentryDSN == "" {
		setupLog.Info("[Sentry] SentryDSN unset, all events waiting for report will be dropped.")
	}
	if err = sentry.Init(sentry.ClientOptions{Dsn: sentryDSN}); err != nil {
		setupLog.Error(err, "unable to set sentry dsn")
		os.Exit(1)
	}

	if err = initExtensionClient(); err != nil {
		setupLog.Error(err, "unable to init extension client")
		os.Exit(1)
	}

	initIngressPlugins()

	setupCtx := context.Background()
	mgr, err := ctrl.NewManager(ctrl.GetConfigOrDie(), options)
	if err != nil {
		setupLog.Error(err, "unable to start manager")
		os.Exit(1)
	}
	mgrCli := client.New(mgr.GetClient())
	mgrScheme := mgr.GetScheme()

	bkappMgrOpts := genGroupKindMgrOpts(paasv1alpha1.GroupKindBkApp, projConf.Controller)
	if err = controllers.NewBkAppReconciler(mgrCli, mgrScheme).
		SetupWithManager(setupCtx, mgr, bkappMgrOpts); err != nil {
		setupLog.Error(err, "unable to create controller", "controller", "BkApp")
		os.Exit(1)
	}
	dgmappingMgrOpts := genGroupKindMgrOpts(paasv1alpha1.GroupKindDomainGroupMapping, projConf.Controller)
	if err = controllers.NewDomainGroupMappingReconciler(mgrCli, mgrScheme).
		SetupWithManager(setupCtx, mgr, dgmappingMgrOpts); err != nil {
		setupLog.Error(err, "unable to create controller", "controller", "DomainGroupMapping")
		os.Exit(1)
	}
	if os.Getenv("ENABLE_WEBHOOKS") != "false" {
		if err = (&paasv1alpha1.BkApp{}).SetupWebhookWithManager(mgr); err != nil {
			setupLog.Error(err, "unable to create webhook", "webhook", "BkApp")
			os.Exit(1)
		}
		if err = (&paasv1alpha1.DomainGroupMapping{}).SetupWebhookWithManager(mgr); err != nil {
			setupLog.Error(err, "unable to create webhook", "webhook", "DomainGroupMapping")
			os.Exit(1)
		}
	}
	//+kubebuilder:scaffold:builder
	if err = mgr.AddHealthzCheck("healthz", healthz.Ping); err != nil {
		setupLog.Error(err, "unable to set up health check")
		os.Exit(1)
	}
	if err = mgr.AddReadyzCheck("readyz", healthz.Ping); err != nil {
		setupLog.Error(err, "unable to set up ready check")
		os.Exit(1)
	}

	setupLog.Info("starting manager")
	if err = mgr.Start(ctrl.SetupSignalHandler()); err != nil {
		setupLog.Error(err, "problem running manager")
		os.Exit(1)
	}
}

func initExtensionClient() error {
	if config.Global.PlatformConfig.BkAPIGatewayURL != "" {
		bkpaasGatewayBaseURL, err := url.Parse(config.Global.PlatformConfig.BkAPIGatewayURL)
		if err != nil {
			return errors.Wrap(err, "failed to parse bkpaas gateway url to net.Url")
		}
		external.SetDefaultClient(
			external.NewClient(
				bkpaasGatewayBaseURL,
				config.Global.PlatformConfig.BkAppCode,
				config.Global.PlatformConfig.BkAppSecret,
				http.DefaultClient,
			),
		)
	} else {
		setupLog.Info("PlatformConfig.BkAPIGateWayURL is not configured, some of Platform-related functionality will be limited")
	}
	return nil
}

func initIngressPlugins() {
	pluginConfig := config.Global.IngressPluginConfig
	if pluginConfig.AccessControlConfig != nil {
		setupLog.Info("[IngressPlugin] access control plugin enabled.")
		resources.RegistryPlugin(&resources.AccessControlPlugin{Config: pluginConfig.AccessControlConfig})
	} else {
		setupLog.Info("[IngressPlugin] Missing access control config, disable access control feature.")
	}
}

// 生成某类组资源管理器配置
func genGroupKindMgrOpts(groupKind schema.GroupKind, ctrlConf *cfg.ControllerConfigurationSpec) controller.Options {
	return controller.Options{
		MaxConcurrentReconciles: ctrlConf.GroupKindConcurrency[groupKind.String()],
		RateLimiter: workqueue.NewMaxOfRateLimiter(
			// 首次重试延迟 1s，后续指数级翻倍，最高延迟 300s
			workqueue.NewItemExponentialFailureRateLimiter(time.Second, 5*time.Minute),
			// 10 qps, 100 bucket size.  This is only for retry speed, and it's only the overall factor (not per item)
			&workqueue.BucketRateLimiter{Limiter: rate.NewLimiter(rate.Limit(10), 100)},
		),
	}
}
