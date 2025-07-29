<template lang="html">
  <div class="instance-wrapper">
    <app-top-bar
      v-if="!isCloudNativeApp"
      :paths="servicePaths"
      :can-create="canCreateModule"
      :cur-module="curAppModule"
    />

    <section
      :class="['instance-detail', { 'default-instance-detail-cls': !isCloudNativeApp }, { collapsed: isCollapsed }]"
    >
      <bk-resize-layout
        ref="resizeLayoutRef"
        :placement="'right'"
        :max="980"
        :collapsible="true"
        :initial-divide="asideWidth"
        ext-cls="instance-resize-layout-cls"
        style="width: 100%; height: 100%"
      >
        <div
          class="instance-container-cls"
          slot="main"
        >
          <!-- 云原生 -->
          <div
            v-if="isCloudNativeApp"
            @click="handleGoBack"
            class="top-return-bar flex-row align-items-center"
          >
            <i class="paasng-icon paasng-arrows-left icon-cls-back mr5" />
            <h4>{{ $t('返回上一页') }}</h4>
          </div>

          <!-- 功能依赖 -->
          <section
            class="functional-dependency-wrapper"
            v-if="!isEnhancedFeatureEnabled"
          >
            <FunctionalDependency
              mode="partial"
              :title="$t('暂无蓝鲸 APM 增强功能')"
              :functional-desc="
                $t(
                  '应用部署后自动接入蓝鲸监控平台，即可获得应用性能管理（APM）以及 Trace 检索等全面可观测性方案，帮助您实时洞察应用状态并优化用户体验。'
                )
              "
              :guide-title="$t('如需要该功能，需要部署：')"
              :guide-desc-list="[$t('1. 蓝鲸监控：监控日志套餐')]"
              @gotoMore="gotoMore"
            />
          </section>

          <template v-else>
            <bk-alert
              v-if="isGcsMysqlAlert"
              style="margin-bottom: 16px"
              type="warning"
              :show-icon="false"
            >
              <div
                slot="title"
                class="risk-warning flex-row"
              >
                <i class="paasng-icon paasng-remind f14"></i>
                <div>
                  {{
                    $t(
                      '平台提供的 GCS-MySQL 数据库为共享实例，无法支持高级别的可用性。请参考文档申请独立的数据库实例。'
                    )
                  }}
                  <a
                    v-if="GLOBAL.DOC.GCS_MySQL_LINK"
                    :href="GLOBAL.DOC.GCS_MySQL_LINK"
                    target="_blank"
                  >
                    {{ $t('申请独立的数据库指引') }}
                  </a>
                </div>
              </div>
            </bk-alert>

            <bk-alert
              v-if="delAppDialog.moduleList.length > 0"
              style="margin-bottom: 16px"
              type="info"
              :title="pageTips"
            />

            <section class="instance-tab-container">
              <p class="title">{{ $t('实例详情') }}</p>
              <!-- 写入环境变量 -->
              <div class="env-variables-wrapper">
                <span class="sub-title">{{ $t('写入环境变量') }}</span>
                <div @click.stop="handleSwitcherChange">
                  <bk-switcher
                    v-model="credentialsDisabled"
                    theme="primary"
                    size="small"
                    :pre-check="() => false"
                  ></bk-switcher>
                </div>
                <span class="tips">
                  <i class="paasng-icon paasng-info-line mr5"></i>
                  {{ $t('若不写入，将无法从环境变量获取实例的凭证信息') }}
                </span>
              </div>
              <!-- 编辑 -->
              <div
                class="instance-info"
                v-if="Object.keys(servicePlans).length"
              >
                <div
                  v-if="isSamePlan"
                  class="item"
                >
                  {{ $t('方案') }}：{{ servicePlans.stag?.name }}
                </div>
                <div
                  v-else
                  class="item"
                  v-for="(value, key) in servicePlans"
                  :key="key"
                >
                  {{ $t('方案') }}({{ key === 'prod' ? $t('生产环境') : $t('预发布环境') }})：
                  <span class="value">{{ value.name }}</span>
                </div>
              </div>
              <bk-table
                :data="instanceList"
                v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
                size="large"
                style="margin-top: 15px"
                ext-cls="instance-details-table-cls"
                :outer-border="false"
              >
                <div
                  slot="empty"
                  class="paas-loading-panel"
                >
                  <div class="text">
                    <table-empty
                      class="table-empty-cls"
                      :empty-title="$t('暂无增强服务配置信息')"
                      empty
                    />
                    <p class="sub-title">
                      {{ $t('服务启用后，将在下一次部署过程中申请实例，请先进行应用部署。') }}
                    </p>
                  </div>
                </div>
                <bk-table-column
                  :label="$t('实例 ID')"
                  width="100"
                >
                  <template slot-scope="{ $index }">#{{ $index + 1 }}</template>
                </bk-table-column>
                <bk-table-column
                  :label="$t('凭证信息')"
                  prop="ip"
                  min-width="380"
                >
                  <template slot-scope="{ row, $index }">
                    <template
                      v-if="
                        row.service_instance.config.hasOwnProperty('is_done') && !row.service_instance.config.is_done
                      "
                    >
                      <p class="mt15 mb15">
                        {{ $t('服务正在创建中，请通过“管理入口”查看进度') }}
                      </p>
                    </template>
                    <template v-else>
                      <section class="credential-information">
                        <div
                          v-for="(value, key) in row.service_instance.credentials"
                          :key="key"
                          class="config-width"
                          v-bk-overflow-tips
                        >
                          <span class="gray">{{ key }}:</span>
                          <span class="break-all">{{ value }}</span>
                          <br />
                        </div>
                        <div
                          v-for="(key, fieldsIndex) in row.service_instance.sensitive_fields"
                          :key="fieldsIndex"
                        >
                          <span class="gray">{{ key }}:</span>
                          ******
                          <i
                            v-bk-tooltips="$t('敏感字段，请参考右侧使用指南，通过环境变量获取')"
                            class="paasng-icon paasng-question-circle"
                          />
                        </div>
                        <div
                          v-for="(value, key) in row.service_instance.hidden_fields"
                          :key="key"
                          v-bk-overflow-tips
                        >
                          <span class="gray">{{ key }}:</span>
                          <span
                            v-if="hFieldstoggleStatus[$index][key]"
                            class="break-all"
                          >
                            {{ value }}
                          </span>
                          <span
                            v-else
                            class="break-all"
                          >
                            ******
                          </span>
                          <button
                            v-bk-tooltips="$t('敏感字段，点击后显示')"
                            class="btn-display-hidden-field ps-btn ps-btn-default ps-btn-xs"
                            @click="$set(hFieldstoggleStatus[$index], key, !hFieldstoggleStatus[$index][key])"
                          >
                            {{ hFieldstoggleText[hFieldstoggleStatus[$index][key] || false] }}
                          </button>
                        </div>
                      </section>
                      <div
                        v-if="!row.service_instance.sensitive_fields.length"
                        class="copy-container"
                      >
                        <i
                          class="paasng-icon paasng-general-copy"
                          v-copy="handleCopy(row)"
                        />
                      </div>
                    </template>
                  </template>
                </bk-table-column>
                <bk-table-column
                  :label="$t('使用环境')"
                  prop="ip"
                >
                  <template slot-scope="{ row }">
                    {{ row.environment_name }}
                  </template>
                </bk-table-column>
                <bk-table-column
                  :label="$t('操作')"
                  :width="localLanguage === 'en' ? 180 : 150"
                >
                  <template slot-scope="{ row }">
                    <p>
                      <template v-if="row.service_instance.config.admin_url">
                        <a
                          :href="row.service_instance.config.admin_url"
                          class="blue"
                          target="_blank"
                        >
                          {{ $t('查看管理入口') }}
                        </a>
                      </template>
                      <template v-else>--</template>
                    </p>
                  </template>
                </bk-table-column>
              </bk-table>
            </section>

            <div class="delete-service-wrapper mt16">
              <span v-bk-tooltips="{ content: $t('S-mart应用暂不支持删除增强服务'), disabled: !isSmartApp }">
                <bk-button
                  theme="danger"
                  :disabled="isSmartApp"
                  @click="showDeleteServiceDialog"
                >
                  {{ $t('删除服务') }}
                </bk-button>
              </span>
              <p>
                <i class="paasng-icon paasng-paas-remind-fill mr5"></i>
                {{ $t('所有已申请实例的相关数据将被销毁。应用与服务之间的绑定关系也会被解除。') }}
              </p>
            </div>
          </template>
        </div>

        <!-- 使用指南 -->
        <usage-guide
          slot="aside"
          :data="compiledMarkdown"
          :is-cloud-native="isCloudNativeApp"
          :is-loading="isTableLoading"
          @set-collapse="handleSetCollapse"
        />

        <div
          :class="['floating-button', { expand: !isCollapsed }]"
          slot="collapse-trigger"
          @click="handleSetCollapse"
        >
          <span :class="{ 'vertical-rl': localLanguage === 'en' }">{{ $t('使用指南') }}</span>
          <i class="paasng-icon paasng-angle-line-up"></i>
        </div>
      </bk-resize-layout>
    </section>

    <!-- 删除服务 -->
    <bk-dialog
      v-model="delAppDialog.visiable"
      width="540"
      :title="$t('确认删除实例？')"
      :theme="'primary'"
      :mask-close="false"
      :header-position="'left'"
      @after-leave="formRemoveConfirmCode = ''"
    >
      <form
        class="ps-form"
        style="min-height: 63px"
        @submit.prevent="submitRemoveInstance"
      >
        <div class="spacing-x1">
          {{ $t('预发布环境和生产环境的实例都将被删除；该操作不可撤销，请完整输入应用 ID') }}
          <code>{{ appCode }}</code>
          {{ $t('确认：') }}
        </div>
        <div class="ps-form-group">
          <input
            v-model="formRemoveConfirmCode"
            type="text"
            class="ps-form-control"
          />
        </div>
        <bk-alert
          v-if="delAppDialog.moduleList.length > 0"
          style="margin-top: 10px"
          type="error"
          :title="errorTips"
        />
      </form>
      <template slot="footer">
        <bk-button
          theme="primary"
          :disabled="!formRemoveValidated"
          @click="submitRemoveInstance"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          theme="default"
          @click="delAppDialog.visiable = false"
        >
          {{ $t('取消') }}
        </bk-button>
      </template>
    </bk-dialog>
  </div>
</template>

<script>
import { marked } from 'marked';
import appBaseMixin from '@/mixins/app-base-mixin';
import appTopBar from '@/components/paas-app-bar';
import usageGuide from '@/components/usage-guide';
import FunctionalDependency from '@blueking/functional-dependency/vue2/index.umd.min.js';
import $ from 'jquery';
import { mapState } from 'vuex';

export default {
  components: {
    appTopBar,
    usageGuide,
    FunctionalDependency,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      instanceList: [],
      service: this.$route.params.service,
      hFieldstoggleStatus: [],
      hFieldstoggleText: {
        true: this.$t('隐藏'),
        false: this.$t('显示'),
      },
      serviceExtraMsgMap: {
        'GCS-MySQL': this.$t('每个应用默认开启MySQL服务，并默认分配两个服务实例'),
        MySQL: this.$t('每个应用默认开启MySQL服务，并默认分配两个服务实例'),
        RabbitMQ: this.$t('开启RabbitMQ服务，系统默认分配两个服务实例'),
        Sentry: this.$t('服务开启后，应用错误将自动上报到Sentry服务'),
      },
      serviceMarkdown: `## ${this.$t('暂无使用说明')}`,
      // detail: 实例详情 manager: 管理实例
      delAppDialog: {
        visiable: false,
        isLoading: false,
        moduleList: [],
      },
      formRemoveConfirmCode: '',
      servicePaths: [],
      servicePlans: {},
      requestQueue: ['init', 'enabled'],
      isTableLoading: false,
      credentialsDisabled: false,
      isEnhancedFeatureEnabled: true,
      isEnabled: false,
      isCollapsed: false,
      serviceDetail: {},
    };
  },
  computed: {
    ...mapState(['localLanguage', 'userFeature']),
    compiledMarkdown() {
      this.$nextTick(() => {
        $('#markdown')
          .find('a')
          .each(function () {
            $(this).attr('target', '_blank');
          });
      });
      return marked(this.serviceMarkdown);
    },
    region() {
      return this.curAppInfo.application.region;
    },
    pageTips() {
      return `${this.$t('实例被以下模块共享：')}${this.delAppDialog.moduleList
        .map((item) => item.name)
        .join('、')}${this.$t('，这些模块将获得实例的所有环境变量。')}`;
    },
    isLoading() {
      return this.requestQueue.length > 0;
    },
    isSmartApp() {
      return this.curAppModule.source_origin === this.GLOBAL.APP_TYPES.SMART_APP;
    },
    formRemoveValidated() {
      return this.appCode === this.formRemoveConfirmCode;
    },
    errorTips() {
      return `${this.$t('该实例被以下模块共享：')}${this.delAppDialog.moduleList
        .map((item) => item.name)
        .join('、')}${this.$t('，删除后这些模块也将无法获取相关的环境变量。')}`;
    },
    asideWidth() {
      return window.innerWidth <= 1366 ? '28%' : '32%';
    },
    isSamePlan() {
      return this.servicePlans.prod?.name === this.servicePlans.stag?.name;
    },
    isGcsMysqlAlert() {
      return (
        this.serviceDetail.name === 'gcs_mysql' &&
        this.userFeature.APP_AVAILABILITY_LEVEL &&
        this.curAppInfo.application?.extra_info?.availability_level === 'premium'
      );
    },
  },
  watch: {
    $route() {
      this.requestQueue = ['init', 'enabled'];
      this.init();
      this.fetchServicesShareDetail();
    },
    compiledMarkdown() {
      this.$emit('set-markdown', this.compiledMarkdown);
    },
    'delAppDialog.moduleList'() {
      this.$emit('set-tooltips', { isShow: this.delAppDialog.moduleList.length > 0, tips: this.pageTips });
    },
    isTableLoading(value) {
      this.$emit('set-loading', value);
    },
  },
  created() {
    this.init();
    this.fetchServicesShareDetail();
    this.getCredentialsEnabled();
  },
  beforeRouteLeave(to, from, next) {
    if (to.name === 'cloudAppDeployForBuild') {
      this.$emit('show-tab', (that) => {
        that.active = to.name;
      });
    }
    next();
  },
  methods: {
    async fetchServicesShareDetail() {
      try {
        const res = await this.$store.dispatch('service/getServicesShareDetail', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          serviceId: this.service,
        });
        this.delAppDialog.moduleList = [...res];
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.requestQueue.shift();
      }
    },

    async init() {
      this.isTableLoading = true;
      await this.getServiceDetail();
      await this.getServiceInstances();
    },

    // 获取服务详情
    async getServiceDetail() {
      try {
        const res = await this.$store.dispatch('service/getServiceDetail', {
          service: this.service,
        });
        const resData = res.result;
        this.serviceDetail = resData;
        if (resData.instance_tutorial && resData.instance_tutorial.length > 0) {
          this.serviceMarkdown = resData.instance_tutorial;
        }
        this.servicePaths.push({
          title: this.$t(resData.category.name_zh_cn),
          routeName: 'appService',
        });
        this.servicePaths.push({
          title: this.curModuleId,
        });
        this.servicePaths.push({
          title: resData.display_name,
        });
        this.isEnabled = resData.is_ready || false;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 获取服务详情列表
    async getServiceInstances() {
      try {
        const res = await this.$store.dispatch('service/getServiceInstances', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          service: this.service,
        });
        const { results, plans = {} } = res;
        this.instanceList = results;
        this.servicePlans = plans;
        for (const instanceIndex in results) {
          this.hFieldstoggleStatus.push({});
          // eslint-disable-next-line max-len
          this.instanceList[instanceIndex].service_instance.credentials = JSON.parse(
            this.instanceList[instanceIndex].service_instance.credentials
          );
          this.instanceList[instanceIndex].usage = JSON.parse(this.instanceList[instanceIndex].usage);
        }
      } catch (e) {
        this.$router.push({
          name: 'appService',
          params: {
            id: this.appCode,
            moduleId: this.curModuleId,
          },
        });
      } finally {
        this.requestQueue.shift();
        // 延时关闭loading防止页面闪动
        setTimeout(() => {
          this.isTableLoading = false;
          this.isEnhancedFeatureEnabled = this.isEnabled;
        }, 1000);
      }
    },

    // 处理复制内容
    handleCopy(payload) {
      const { credentials } = payload.service_instance;
      const hiddenFields = payload.service_instance.hidden_fields;
      let copyContent = '';
      for (const key in credentials) {
        copyContent += `${key}:${credentials[key]}\n`;
      }
      for (const key in hiddenFields) {
        copyContent += `${key}:${hiddenFields[key]}\n`;
      }
      return copyContent;
    },

    async getCredentialsEnabled() {
      try {
        const res = await this.$store.dispatch('service/getCredentialsEnabled', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          service: this.service,
        });
        // 第一版不考虑环境情况默认取第一项
        this.credentialsDisabled = res.length ? res[0].credentials_enabled : false;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 写入环境变量启用/禁用
    handleSwitcherChange() {
      if (!this.credentialsDisabled) {
        this.updateCredentialsEnabled();
        return;
      }
      this.$bkInfo({
        width: 460,
        title: this.$t('确认不写入环境变量'),
        subTitle: this.$t('选择不写入将无法通过环境变量获取实例凭证信息，请确保您了解此操作的影响。'),
        confirmFn: () => {
          this.updateCredentialsEnabled();
        },
      });
    },

    // 启用/停用写入环境变量
    async updateCredentialsEnabled() {
      try {
        const { credentialsDisabled } = this;
        await this.$store.dispatch('service/updateCredentialsEnabled', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          service: this.service,
          data: { credentials_enabled: !credentialsDisabled },
        });
        const successtTips = credentialsDisabled ? this.$t('已配置为不写入环境变量') : this.$t('已配置为写入环境变量');
        this.$paasMessage({
          theme: 'success',
          message: successtTips,
        });
        this.getCredentialsEnabled();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 返回上一级
    handleGoBack() {
      this.$emit('route-back', 'appServices');
    },

    handleSetCollapse() {
      this.isCollapsed = !this.isCollapsed;
    },

    showDeleteServiceDialog() {
      this.delAppDialog.visiable = true;
      this.fetchServicesShareDetail();
    },

    async submitRemoveInstance() {
      try {
        await this.$store.dispatch('service/deleteService', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          service: this.service,
        });
        this.delAppDialog.visiable = false;
        this.$paasMessage({
          theme: 'success',
          message: this.$t('删除服务实例成功'),
        });
        if (this.isCloudNativeApp) {
          this.handleGoBack();
          return;
        }
        this.$router.push({
          name: 'appService',
          params: {
            id: this.$route.params.id,
          },
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
        this.delAppDialog.visiable = false;
      }
    },

    gotoMore() {
      window.open(this.GLOBAL.DOC.APM_FEATURE_DOC, '_blank');
    },
  },
};
</script>

<style lang="scss" scoped>
.functional-dependency-wrapper {
  background: #fff;
  box-shadow: 0 2px 4px 0 #1919290d;
  border-radius: 2px;
  padding: 24px 0;
}
.markdown-body {
  box-sizing: border-box;
  min-width: 200px;
  margin: 0 auto;
  padding: 5px 20px;

  h2,
  h3 {
    color: var(--color-fg-default);
  }
}

.paasng-question-circle {
  color: #ffc349;
}

.dataStore-middle-h3 {
  position: relative;
  top: 2px;
}

.paasng-empty {
  font-size: 34px;
  color: #ffc349;
}

.dataStore-icon {
  font-size: 16px;
  position: relative;
  top: 2px;
}

.break-all {
  word-break: break-all;
}

.datastore-alink {
  line-height: 40px;
  color: #666;
  height: 40px;
  overflow: hidden;
  width: 208px;
  position: absolute;
  left: 0;
  bottom: 0;
  border-top: solid 1px #e6e9ea;
  display: inline-block;
  transition: all 0.3s;
  cursor: pointer;
}

.service-list li:hover .datastore-alink {
  background: #3a84ff;
  border-top: solid 1px #3a84ff;
  color: #fff;
}

.dataStore-h2 {
  display: block;
  line-height: 30px;
  padding: 14px 0;
}

.dataStore-h2 img.dataStore-icon {
  position: relative;
  top: 3px;
  padding-right: 7px;
}

.gray {
  margin-right: 6px;
  color: #b7b8be;
}

.dataStore-middle h3 {
  line-height: 36px;
  padding-top: 18px;
}

.data-store-use {
  border: solid 1px #e6e9ea;
  position: relative;
}

.use-text {
  width: 444px;
  display: inline-block;
  vertical-align: top;
}

.pt30 {
  padding-top: 30px;
}

.btn-display-hidden-field {
  font-size: 12px;
  line-height: 18px;
}

.hide {
  opacity: 0;
}
.health-wrapper {
  .ps-table-default {
    background: rgba(255, 255, 255, 1);
    border-radius: 2px;
    border: 1px solid rgba(220, 222, 229, 1);
    th {
      border-top: none;
      border-right: none;
      border-bottom: 1px solid rgba(220, 222, 229, 1);
    }
    td {
      border-bottom: 1px solid rgba(220, 222, 229, 1);
    }
  }
  .ps-table-slide-up {
    color: #63656e;
    background: #fff;
    i {
      font-style: normal;
    }
  }
}

.service-tab-wrapper {
  padding: 20px 0 0 0;
  line-height: 32px;
  .tab-content {
    border-bottom: 1px solid #dcdee5;
    .detail-tab {
      display: inline-block;
      position: relative;
      padding: 0 3px;
      text-align: center;
      cursor: pointer;
      margin-right: 20px;
    }
    .manager-tab {
      display: inline-block;
      position: relative;
      text-align: center;
      padding: 0 3px;
      cursor: pointer;
    }
    .border {
      position: absolute;
      bottom: -1px;
      left: 0;
      width: 100%;
      height: 2px;
      background: #3a84ff;
    }
    .active {
      color: #3a84ff;
    }
  }
}

.manager-example {
  .config-info {
    margin-bottom: 40px;
  }
  .delete-title {
    padding-bottom: 10px;
    font-size: 14px;
    color: #1b1f23;
    font-weight: bold;
  }
  .delete-tips {
    padding-bottom: 10px;
    color: #63656e;
  }
}

.instance-detail {
  .bk-resize-layout-border {
    border-top-color: transparent;
    border-bottom-color: transparent;
  }
  .instance-container-cls {
    margin: 16px 24px 0;
    .top-return-bar {
      background: #f5f7fa;
      cursor: pointer;
      margin-bottom: 16px;
      h4 {
        font-size: 14px;
        color: #313238;
        font-weight: 400;
        padding: 0;
      }
      .icon-cls-back {
        color: #3a84ff;
        font-size: 14px;
        font-weight: bold;
        transform: translateY(0px);
      }
    }

    .delete-service-wrapper {
      display: flex;
      align-items: center;
      margin-top: 16px;
      p {
        color: #63656e;
        font-size: 12px;
        margin-left: 13px;
        i {
          font-size: 14px;
          color: #ffb848;
        }
      }
    }

    .risk-warning {
      display: flex;
      .paasng-remind {
        margin: 3px 9px 0 0;
        color: #f59500;
      }
    }
  }
}

.default-instance-detail-cls {
  display: flex;
  .instance-container-cls {
    flex: 1;
  }
}
.instance-tab-container {
  box-shadow: 0 2px 4px 0 #1919290d;
  border-radius: 2px;
  .title {
    font-weight: 700;
    font-size: 14px;
    color: #313238;
    line-height: 22px;
  }
  .instance-info {
    position: relative;
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    min-height: 40px;
    margin: 16px 0px;
    padding: 0 16px;
    background: #f0f5ff;
    border-radius: 2px;
    gap: 0px 38px;
    font-size: 12px;
    .item {
      flex-shrink: 0;
      line-height: 32px;
      color: #4d4f56;
      .value {
        color: #313238;
      }
    }
  }
  .env-variables-wrapper {
    display: flex;
    align-items: center;
    margin-top: 16px;
    font-size: 12px;
    color: #63656e;
    line-height: 20px;
    .sub-title {
      margin-right: 12px;
    }
    .tips {
      margin-left: 16px;
    }
    i {
      font-size: 14px;
      color: #979ba5;
    }
  }
}
.instance-wrapper {
  height: 100%;
  .instance-detail {
    height: 100%;
  }
}
.instance-alert-cls {
  margin-bottom: 16px;
}
</style>
<style lang="scss">
#markdown h2 {
  padding-bottom: 0.3em;
  font-size: 1.5em;
  border-bottom: 1px solid #eaecef;
  padding: 0;
  padding-bottom: 10px;
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
}

#markdown h2 .octicon-link {
  color: #1b1f23;
  vertical-align: middle;
  visibility: hidden;
}

#markdown h2:hover .anchor {
  text-decoration: none;
}

#markdown h2:hover .anchor .octicon-link {
  visibility: visible;
}

#markdown code,
#markdown kbd,
#markdown pre {
  font-size: 1em;
}

#markdown code {
  font-size: 12px;
}

#markdown pre {
  margin-top: 0;
  margin-bottom: 16px;
  font-size: 12px;
}

#markdown pre {
  word-wrap: normal;
}

#markdown code {
  padding: 0.2em 0.4em;
  margin: 0;
  font-size: 85%;
  background-color: rgba(27, 31, 35, 0.05);
  border-radius: 3px;
  color: inherit;
}

#markdown pre > code {
  padding: 0;
  margin: 0;
  font-size: 100%;
  word-break: normal;
  white-space: pre;
  background: transparent;
  border: 0;
}

#markdown .highlight {
  margin-bottom: 16px;
}

#markdown .highlight pre {
  margin-bottom: 0;
  word-break: normal;
}

#markdown .highlight pre,
#markdown pre {
  padding: 16px;
  overflow: auto;
  font-size: 85%;
  line-height: 1.45;
  background-color: var(--color-canvas-subtle);
  border-radius: 3px;
}

#markdown pre code {
  display: inline;
  max-width: auto;
  padding: 0;
  margin: 0;
  overflow: visible;
  line-height: inherit;
  word-wrap: normal;
  background-color: transparent;
  border: 0;
}

#markdown p {
  margin-top: 0;
  margin-bottom: 10px;
}

#markdown a {
  background-color: transparent;
}

#markdown a:active,
#markdown a:hover {
  outline-width: 0;
}

#markdown a {
  color: #0366d6;
  text-decoration: none;
}

#markdown a:hover {
  text-decoration: underline;
}

#markdown a:not([href]) {
  color: inherit;
  text-decoration: none;
}

#markdown ul,
#markdown ol {
  padding-left: 0;
  margin-top: 0;
  margin-bottom: 0;
  list-style: unset !important;
}

#markdown ol ol,
#markdown ul ol {
  list-style-type: lower-roman;
}

#markdown ul ul ol,
#markdown ul ol ol,
#markdown ol ul ol,
#markdown ol ol ol {
  list-style-type: lower-alpha;
}

#markdown ul,
#markdown ol {
  padding-left: 2em;
}

#markdown ul ul,
#markdown ul ol,
#markdown ol ol,
#markdown ol ul {
  margin-top: 0;
  margin-bottom: 0;
}
.copy-container {
  position: absolute;
  right: 45px;
  top: 50%;
  margin-top: -12px;
  color: #3a84ff;
  &:hover {
    cursor: pointer;
  }
}
.config-width {
  width: 85%;
  display: inline-block;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}
.ps-table-slide-up .paas-loading-panel .table-empty-cls .empty-tips {
  color: #999;
}
.instance-tab-container {
  background: #fff;
  padding: 16px 24px;
}

.instance-container-cls {
  min-width: 0;
}

.instance-details-table-cls {
  .bk-table-row.bk-table-row-last td {
    border-bottom: none;
  }
  .credential-information {
    overflow: hidden;
  }
  .gray {
    color: #c4c6cc;
    margin-right: 6px;
  }
  .break-all {
    color: #63656e;
    font-size: 12px;
    line-height: 20px;
  }
  .paas-loading-panel .text {
    .sub-title {
      font-size: 12px;
    }
  }
}
.collapsed .instance-resize-layout-cls aside.bk-resize-layout-aside {
  .bk-resize-trigger {
    display: none;
  }
  width: 0px !important;
}
.instance-resize-layout-cls {
  .bk-resize-layout-aside .bk-resize-layout-aside-content {
    overflow: unset;
  }
  .floating-button {
    position: absolute;
    left: -24px;
    top: 50%;
    transform: translateY(-50%);
    width: 24px;
    padding: 11px 0;
    text-align: center;
    font-size: 12px;
    color: #63656e;
    line-height: 13px;
    background: #fafbfd;
    border: 1px solid #dcdee5;
    border-radius: 8px 0 0 8px;
    cursor: pointer;
    &.expand {
      i {
        transform: rotateZ(90deg);
      }
    }
    i {
      margin-top: 5px;
      color: #979ba5;
      transform: rotateZ(-90deg);
    }
    &:hover {
      color: #3a84ff;
      i {
        color: #3a84ff;
      }
    }
    .vertical-rl {
      writing-mode: vertical-rl;
    }
  }
}
</style>
