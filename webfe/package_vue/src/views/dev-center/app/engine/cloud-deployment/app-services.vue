<template>
  <div class="services-container">
    <paas-content-loader
      class="app-container image-content"
      :is-loading="tableLoading"
      :is-transition="false"
      :offset-top="0"
      :offset-left="0"
      placeholder="roles-loading"
    >
      <div class="ps-main">
        <bk-alert
          v-if="recyclingCount"
          type="warning"
          :show-icon="false"
          class="recycle-alert-cls"
        >
          <div slot="title">
            <i class="paasng-icon paasng-remind mr5"></i>
            <span>
              {{
                $t('您有 {n} 个已解绑但未回收的增强服务实例，未回收的实例仍会计入应用成本，请及时回收。', {
                  n: recyclingCount,
                })
              }}
            </span>
            <bk-button
              text
              size="small"
              @click="isShowSideslider = true"
            >
              {{ $t('立即回收') }}
            </bk-button>
          </div>
        </bk-alert>
        <bk-table
          v-bkloading="{ isLoading: tableLoading, opacity: 1 }"
          :data="pgPaginatedData"
          size="small"
          :outer-border="false"
          :pagination="pagination"
          @page-change="pageChange"
          @page-limit-change="limitChange"
          @row-mouse-enter="handleRowMouseEnter"
          @row-mouse-leave="handleRowMouseLeave"
        >
          <div slot="empty">
            <table-empty empty />
          </div>
          <bk-table-column
            :label="$t('服务名称')"
            width="300"
          >
            <template slot-scope="{ row, $index }">
              <div class="flex-row align-items-center">
                <img
                  class="row-img"
                  :src="row.logo"
                  alt=""
                />
                <p
                  class="row-title-text text-ellipsis"
                  :class="row.isStartUp ? '' : 'text-disabled'"
                  v-bk-overflow-tips
                  @click="handleToPage(row)"
                >
                  {{ row.display_name || '--' }}
                </p>
                <bk-popover
                  v-if="hasGcsMysqlAlert(row.name)"
                  placement="top"
                  width="220"
                >
                  <i class="paasng-icon paasng-remind mysql-tip-icon ml5"></i>
                  <div slot="content">
                    {{
                      $t(
                        '平台提供的 GCS-MySQL 数据库为共享实例，无法支持高级别的可用性。请参考文档申请独立的数据库实例。'
                      )
                    }}
                    <a
                      v-if="GLOBAL.DOC.GCS_MySQL_LINK"
                      :href="GLOBAL.DOC.GCS_MySQL_LINK"
                      target="_blank"
                      class="f12"
                    >
                      {{ $t('申请独立的数据库指引') }}
                    </a>
                  </div>
                </bk-popover>
                <i
                  v-if="$index === rowIndex"
                  class="row-icon paasng-icon paasng-process-file ml5 f14"
                  v-bk-tooltips="{ content: $t('使用指南') }"
                  @click="handleShowGuideDialog(row)"
                />
              </div>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('服务介绍')"
            show-overflow-tooltip
            :render-header="$renderHeader"
          >
            <template slot-scope="{ row }">
              {{ row.description || '--' }}
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('配置信息')"
            :render-header="$renderHeader"
          >
            <template slot-scope="{ row }">
              <div
                v-if="row.isStartUp && row.plans"
                class="config-info-tag"
              >
                <span
                  class="g-tag-default text-ellipsis"
                  v-if="row.plans?.stag?.name === row.plans?.prod?.name"
                  v-bk-overflow-tips
                >
                  {{ row.plans.stag?.name }}
                </span>
                <span
                  class="g-tag-default text-ellipsis"
                  v-else
                  v-for="(value, key) in row.plans"
                  :key="key"
                  v-bk-overflow-tips
                >
                  {{ getEnvironmentName(key) }}：{{ value.name }}
                </span>
              </div>
              <span v-else>{{ $t('无') }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            width="160"
            :label="$t('启/停')"
            class-name="services-table-cloumn"
            :render-header="$renderHeader"
          >
            <template slot-scope="{ row, $index }">
              <div
                class="ps-switcher-wrapper"
                @click="toggleSwitch(row, $index)"
                v-bk-tooltips="{
                  content: $t('S-mart 应用不支持停用增强服务'),
                  disabled: !isSmartApp,
                  allowHTML: true,
                }"
                v-if="row.isStartUp"
              >
                <bk-switcher
                  v-model="row.isStartUp"
                  :theme="row.type === 'shared' ? 'success' : 'primary'"
                  class="bk-small-switcher"
                  :disabled="isSmartApp"
                />
              </div>
              <div
                class="ps-switcher-wrapper"
                v-else
                @click="toggleSwitch(row, $index)"
                v-bk-tooltips="{ ...enableTooltipsConfig, allowHTML: true }"
                :ref="`tooltipsHtml${$index}`"
              >
                <bk-switcher
                  v-model="row.isStartUp"
                  class="bk-small-switcher"
                  :disabled="isSmartApp"
                />
              </div>
              <!-- 解决单元格溢出问题 ... -->
              <div v-show="false">
                <div id="switcher-tooltip">
                  <div
                    v-for="item in startData"
                    :key="item.id"
                    class="item"
                    @click="handleSwitcherOpen(item)"
                  >
                    {{ item.label }}
                  </div>
                </div>
              </div>
            </template>
          </bk-table-column>
        </bk-table>
      </div>

      <shared-dialog
        :data="curData"
        :show.sync="isShowDialog"
        @on-success="handleExportSuccess"
      />

      <bk-dialog
        v-model="isShowStartDialog"
        width="600"
        :title="$t('方案信息')"
        :mask-close="false"
        ext-cls="paasng-service-export-dialog-cls"
        header-position="left"
        @confirm="handleConfigChange"
      >
        <bk-form
          :model="startFormData"
          :label-width="150"
          ext-cls="config-info-box"
        >
          <bk-form-item
            :label="$t('方案')"
            v-if="serviceConfig.static_plans?.length"
          >
            <bk-radio-group
              v-model="startFormData.plan"
              class="config-group"
            >
              <bk-radio
                v-for="item in serviceConfig.static_plans"
                :key="item.uuid"
                :value="item.uuid"
                ext-cls="config-radio-cls"
              >
                <span class="ml5">{{ item.name }}</span>
              </bk-radio>
            </bk-radio-group>
          </bk-form-item>
          <template v-else>
            <bk-form-item
              v-for="(value, key) in serviceConfig.env_specific_plans"
              :label="getEnvironmentName(key)"
              :key="key"
            >
              <bk-radio-group
                v-model="startFormData[key]"
                class="config-group"
              >
                <bk-radio
                  v-for="item in value"
                  :key="item.uuid"
                  :value="item.uuid"
                  ext-cls="config-radio-cls"
                >
                  <span class="ml5">{{ item.name }}</span>
                </bk-radio>
              </bk-radio-group>
            </bk-form-item>
          </template>
        </bk-form>
      </bk-dialog>

      <!-- 直接启动删除实例 -->
      <bk-dialog
        v-model="delAppDialog.visiable"
        width="540"
        :title="`${$t('确认停用')} ${curData.display_name}`"
        :theme="'primary'"
        :mask-close="false"
        :header-position="'left'"
        :loading="delAppDialog.isLoading"
        @after-leave="hookAfterClose"
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
            class="mt10"
            type="error"
            :title="errorTips"
          />
        </form>
        <template slot="footer">
          <bk-button
            theme="primary"
            :disabled="!formRemoveValidated"
            @click="submitRemoveInstance"
            class="mr10"
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

      <!-- 关联实例需要解绑 -->
      <bk-dialog
        v-model="removeSharedDialog.visiable"
        width="540"
        :title="$t('确认解除服务共享')"
        :header-position="'left'"
        :theme="'primary'"
        :mask-close="false"
        :loading="removeSharedDialog.isLoading"
        @after-leave="hookAfterClose"
      >
        <form
          class="ps-form"
          @submit.prevent="submitRemoveShared"
        >
          <bk-alert
            type="error"
            :title="errorTips"
            class="mb20"
          />
          <div class="spacing-x1">
            {{ $t('请完整输入应用 ID ') }}
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
        </form>
        <template slot="footer">
          <bk-button
            theme="primary"
            :loading="removeSharedDialog.isLoading"
            :disabled="!formRemoveValidated"
            @click="submitRemoveShared"
            class="mr10"
          >
            {{ $t('确定') }}
          </bk-button>
          <bk-button
            theme="default"
            @click="removeSharedDialog.visiable = false"
          >
            {{ $t('取消') }}
          </bk-button>
        </template>
      </bk-dialog>

      <!-- 使用指南 -->
      <bk-sideslider
        :is-show.sync="isShowGuideDialog"
        :title="$t('使用指南')"
        :width="640"
        :quick-close="true"
        @hidden="hookAfterClose"
      >
        <div slot="content">
          <div
            id="markdown"
            v-bkloading="{ isLoading: guideLoading, opacity: 1 }"
          >
            <div
              class="markdown-body"
              v-html="compiledMarkdown"
            />
          </div>
        </div>
      </bk-sideslider>

      <RecycleSideslider
        ref="recycleSideslider"
        :show.sync="isShowSideslider"
        :list="instanceList"
        :count="recyclingCount"
        @refresh="getServicesUnboundAttachments"
      />
    </paas-content-loader>
  </div>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin';
import SharedDialog from './comps/shared-dialog';
import RecycleSideslider from '../../services/comps/recycle-sideslider.vue';
import { marked } from 'marked';
import { paginationFun } from '@/common/utils';
import { mapState } from 'vuex';

export default {
  components: {
    SharedDialog,
    RecycleSideslider,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      tableList: [],
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },
      tableLoading: false,
      isLoading: false,
      rowIndex: '',
      isShowDate: false,
      isShowStartDialog: false,
      switcherTips: {
        allowHtml: true,
        offset: '40, 0',
        trigger: 'click',
        theme: 'light',
        content: '#switcher-tooltip',
        placement: 'bottom',
        extCls: 'services-tips-cls',
      },
      startData: [
        { value: 'start', label: this.$t('直接启用') },
        { value: 'shared', label: this.$t('从其他模块共享') },
      ],
      isShowDialog: false,
      curData: {},
      curIndex: '',
      startFormData: {
        plan: '',
        prod: '',
        stag: '',
      },
      definitions: [],
      delAppDialog: {
        visiable: false,
        isLoading: false,
        moduleList: [],
      },
      removeSharedDialog: {
        visiable: false,
        isLoading: false,
      },
      formRemoveConfirmCode: '',
      isShowGuideDialog: false,
      serviceMarkdown: `## ${this.$t('暂无使用说明')}`,
      guideLoading: false,
      serviceConfig: {},
      isShowSideslider: false,
      instanceList: [],
      recyclingCount: 0,
    };
  },
  computed: {
    ...mapState(['curAppCode', 'userFeature']),
    appCode() {
      return this.$route.params.id;
    },
    region() {
      return this.curAppInfo.application.region;
    },
    formRemoveValidated() {
      return this.appCode === this.formRemoveConfirmCode;
    },
    errorTips() {
      if (this.curData.type === 'bound' && this.delAppDialog.moduleList.length) {
        return '该实例被共享，删除后这些模块将无法获取相关环境变量；删除会导致预发布环境和生产环境的实例都将被删除，且该操作不可撤销，请谨慎操作';
      }
      return `${this.$t('解除后，当前模块将无法获取 ')}${this.curModuleId} ${this.$t('模块的')} ${
        this.curData.display_name
      } ${this.$t('服务的所有环境变量')}`;
    },

    compiledMarkdown() {
      // eslint-disable-next-line vue/no-async-in-computed-properties
      this.$nextTick(() => {
        $('#markdown')
          .find('a')
          .each(function () {
            $(this).attr('target', '_blank');
          });
      });
      return marked(this.serviceMarkdown, { sanitize: true });
    },
    getVersionValue() {
      return function (name, data) {
        const versionData = data.find((e) => e.name === name) || {};
        return versionData?.value || '';
      };
    },
    isSmartApp() {
      return this.curAppInfo.application?.is_smart_app;
    },
    enableTooltipsConfig() {
      this.switcherTips.disabled = this.isSmartApp;
      if (this.isSmartApp) {
        return {
          content: this.$t('S-mart 应用请在应用描述文件中启用增强服务'),
        };
      }
      return this.switcherTips;
    },
    // 当前页数据
    pgPaginatedData() {
      const { pageData } = paginationFun(this.tableList, this.pagination.current, this.pagination.limit);
      return pageData;
    },
  },
  watch: {
    curAppCode() {
      this.gettableList();
      this.isLoading = true;
    },
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      this.gettableList();
      this.getServicesUnboundAttachments();
    },

    // 获取表格列表
    async gettableList() {
      this.tableLoading = true;
      try {
        const { appCode } = this;
        const res = await this.$store.dispatch('service/getServicesList', { appCode, moduleId: this.curModuleId });
        // 新增一个字段isStartUp true代表是启动状态 false代表停止状态
        // 改造bound数据
        res.bound = (res.bound || []).reduce((p, v) => {
          p.push({ ...v, ...v.service, type: 'bound', isStartUp: true });
          return p;
        }, []);

        // 改造shared数据
        res.shared = (res.shared || []).reduce((p, v) => {
          p.push({ ...v, ...v.service, type: 'shared', isStartUp: true });
          return p;
        }, []);

        // 改造shared数据
        res.unbound = (res.unbound || []).map((e) => {
          e.type = 'unbound';
          e.isStartUp = false;
          return e;
        });
        this.tableList = [...res.bound, ...res.shared, ...res.unbound];
        this.pagination.count = this.tableList.length;

        // 处理服务->数据存储服务详情跳转
        const redirectData = this.tableList.find((v) => v.uuid === this.$route.params?.service);
        if (redirectData) {
          this.handleToPage(redirectData);
        }
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || this.$t('接口异常'),
        });
      } finally {
        this.tableLoading = false;
        setTimeout(() => {
          this.isLoading = false;
        }, 500);
      }
    },
    pageChange(page) {
      if (this.currentBackup === page) {
        return;
      }
      this.pagination.current = page;
    },

    limitChange(currentLimit) {
      this.pagination.limit = currentLimit;
      this.pagination.current = 1;
    },

    // 表格鼠标移入
    handleRowMouseEnter(index) {
      this.rowIndex = index;
    },

    // 表格鼠标移出
    handleRowMouseLeave() {
      this.rowIndex = '';
    },

    toggleSwitch(payload, index) {
      if (this.isSmartApp) {
        return;
      }
      this.curData = payload;
      this.curIndex = index;
      if (payload.isStartUp) {
        // 已经启动的状态
        if (payload.type === 'shared') {
          // 解绑弹窗
          this.removeSharedDialog.visiable = true;
        } else {
          this.delAppDialog.visiable = true; // 停用弹窗
          this.fetchServicesShareDetail();
        }
      }
    },

    // 设置配置信息默认值数据
    formatConfig(data) {
      if (data.static_plans?.length) {
        // 选择方案
        this.startFormData.plan = data.static_plans[0]?.uuid;
      } else {
        // 环境
        Object.keys(data.env_specific_plans).forEach((key) => {
          this.startFormData[key] = data.env_specific_plans[key][0]?.uuid;
        });
      }
      this.serviceConfig = data;
    },

    // 启用服务
    async handleSwitcherOpen(payload) {
      this.$refs[`tooltipsHtml${this.curIndex}`]._tippy.hide();
      if (payload.value === 'start') {
        // 获取启动时需要的配置信息
        const res = await this.getServicePossiblePlans();
        if (res.has_multiple_plans) {
          // 无配置信息
          if (!res.static_plans && !res.env_specific_plans) {
            this.$bkMessage({
              theme: 'error',
              message: this.$t('获取增强服务配置信息出错，请联系管理员。'),
            });
            return;
          }
          this.formatConfig(res);
          this.isShowStartDialog = true;
        } else {
          // 直接启动 （无需弹窗）
          this.handleConfigChange(true);
        }
      } else {
        // 从其他模块中共享
        this.isShowDialog = true;
      }
    },

    handleExportSuccess() {
      this.init();
    },

    // 确认启动服务
    async handleConfigChange(isEnableDirectly = false) {
      this.loading = true;
      const params = {
        service_id: this.curData.uuid,
        module_name: this.curModuleId,
        code: this.curAppCode,
      };
      // 配置信息
      if (!isEnableDirectly) {
        const { plan, prod, stag } = this.startFormData;
        if (this.serviceConfig.static_plans?.length) {
          params.plan_id = plan;
        } else {
          params.env_plan_id_map = {
            prod,
            stag,
          };
        }
      }
      try {
        await this.$store.dispatch('service/enableServices', params);
        this.$paasMessage({
          limit: 1,
          theme: 'success',
          message: this.$t('服务启用成功'),
        });
        this.init();
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.detail || res.message || this.$t('接口异常'),
        });
      } finally {
        this.loading = false;
      }
    },

    hookAfterClose() {
      this.formRemoveConfirmCode = '';
      this.serviceMarkdown = `## ${this.$t('暂无使用说明')}`;
    },

    // 删除实例确认
    submitRemoveInstance() {
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/services/${this.curData.uuid}/`;

      this.$http.delete(url).then(
        () => {
          this.delAppDialog.visiable = false;
          this.$paasMessage({
            theme: 'success',
            message: this.$t('删除服务实例成功'),
          });
          this.init();
        },
        (res) => {
          this.$paasMessage({
            theme: 'error',
            message: res.detail,
          });
          this.delAppDialog.visiable = false;
        }
      );
    },

    // 解绑实例确认
    async submitRemoveShared() {
      this.removeSharedDialog.isLoading = true;
      try {
        await this.$store.dispatch('service/deleteSharedAttachment', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          serviceId: this.curData.uuid,
        });
        this.removeSharedDialog.visiable = false;
        this.$paasMessage({
          theme: 'success',
          message: this.$t('解除服务共享成功'),
          delay: 1500,
        });
        this.init();
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.removeSharedDialog.isLoading = false;
      }
    },

    // 停用服务时需要展示的error数据
    async fetchServicesShareDetail() {
      try {
        const res = await this.$store.dispatch('service/getServicesShareDetail', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          serviceId: this.curData.uuid,
        });
        this.delAppDialog.moduleList = [...res];
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.detail || res.message || this.$t('接口异常'),
        });
      }
    },

    // 处理跳转逻辑
    handleToPage(payload) {
      if (payload.isStartUp) {
        this.isCloudNativeApp && this.$emit('hide-tab');
        if (payload.type === 'shared') {
          // 共享
          if (this.isCloudNativeApp) {
            this.$router.push({
              name: 'cloudAppServiceInnerShared',
              params: { id: this.appCode, service: payload.uuid, category_id: payload.category.id },
            });
            return;
          }
          this.$router.push({
            name: 'appServiceInnerShared',
            params: { id: this.appCode, service: payload.uuid, category_id: payload.category.id },
          });
        } else {
          // 直接启动
          if (this.isCloudNativeApp) {
            this.$router.push({
              name: 'cloudAppServiceInnerWithModule',
              params: { id: this.appCode, service: payload.uuid, category_id: payload.category.id },
            });
            return;
          }
          this.$router.push({
            name: 'appServiceInner',
            params: { id: this.appCode, service: payload.uuid, category_id: payload.category.id },
          });
        }
      }
      // this.$router.push({
      //   name: 'serviceInnerPage',
      //   params: { category_id: payload.category ? payload.category.id : '', name: payload.name },
      //   query: { name: payload.display_name },
      // });
    },

    // 获取使用指南
    getGuideData() {
      this.guideLoading = true;
      this.$http.get(`${BACKEND_URL}/api/services/${this.curData.uuid}/`).then((response) => {
        const resData = response.result;
        if (resData.instance_tutorial && resData.instance_tutorial.length > 0) {
          this.serviceMarkdown = resData.instance_tutorial;
        }
        this.guideLoading = false;
        this.isShowGuideDialog = true;
      });
    },

    // 处理使用指南侧边栏
    handleShowGuideDialog(payload) {
      this.curData = payload;
      this.getGuideData();
    },

    getEnvironmentName(key) {
      return key === 'prod' ? this.$t('方案（生产环境）') : this.$t('方案（预发布环境）');
    },

    // 获取应用模块绑定服务时，可能的详情方案
    async getServicePossiblePlans() {
      try {
        const res = await this.$store.dispatch('service/getServicePossiblePlans', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          service: this.curData.uuid,
        });
        return res;
      } catch (e) {
        this.catchErrorHandler(e);
        return {};
      }
    },
    // 获取服务回收数据
    async getServicesUnboundAttachments() {
      this.$refs.recycleSideslider?.toggleLoading(true);
      try {
        const res = await this.$store.dispatch('service/getServicesUnboundAttachments', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        res.forEach((item) => {
          item.unbound_instances.forEach((instance) => {
            instance.service_instance.credentials = JSON.parse(instance.service_instance.credentials);
          });
        });
        this.instanceList = res;
        this.recyclingCount = res.reduce((accumulator, currentItem) => {
          return accumulator + currentItem.count;
        }, 0);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.$refs.recycleSideslider?.toggleLoading(false);
      }
    },
    // 是否展示GcsMysql警告提示
    hasGcsMysqlAlert(name) {
      return (
        name === 'gcs_mysql' &&
        this.userFeature.APP_AVAILABILITY_LEVEL &&
        this.curAppInfo.application?.extra_info?.availability_level === 'premium'
      );
    },
  },
};
</script>

<style lang="scss" scoped>
.services-container {
  .ps-top-bar {
    padding: 0 20px;
  }
  .image-content {
    background: #fff;
    padding: 0 0 24px;
  }
  .row-img {
    width: 22px;
    height: 22px;
    border-radius: 2px;
  }
  .ps-switcher-wrapper {
    margin-left: 0;
  }
  .row-title-text {
    margin-left: 8px;
    cursor: pointer;
    color: #3a84ff;
  }
  .text-disabled {
    color: #63656e;
    cursor: unset;
  }
  .row-icon {
    color: #63656e;

    &:hover {
      cursor: pointer;
      color: #3a84ff;
    }
  }

  .success-icon {
    font-size: 24px;
    color: #2dcb56;
    transform: translateX(-6px);
  }

  .mysql-tip-icon {
    font-size: 14px;
    color: #ea3636;
  }
}
.header-title {
  display: flex;
  align-items: center;
  .app-code {
    color: #979ba5;
  }
  .arrows {
    margin: 0 9px;
    transform: rotate(-90deg);
    font-size: 12px;
    font-weight: 600;
    color: #979ba5;
  }
}
#switcher-tooltip {
  border: 1px solid #dcdee5;
  border-radius: 2px;
  .item {
    padding: 0 12px;
    cursor: pointer;
    height: 32px;
    line-height: 32px;
    color: #63656e;
    font-size: 12px;
    &:hover {
      background: #f5f7fa;
    }
    &:first-child {
      margin-top: 4px;
    }
    &:last-child {
      margin-bottom: 4px;
    }
  }
}
.paasng-service-export-dialog-cls {
  .config-group {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0px 20px;
    .config-radio-cls {
      margin-left: 0px !important;
      line-height: 32px;
    }
  }
}
.config-info-tag {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 10px 0;
  .g-tag-default {
    margin: 0px;
  }
}
.recycle-alert-cls {
  margin-bottom: 16px;
  .paasng-remind {
    transform: translateY(0px);
    font-size: 14px;
    color: #f59500;
  }
  .bk-button-text {
    line-height: 1 !important;
    height: 12px !important;
    padding: 0;
  }
}
</style>
<style lang="scss">
.services-tips-cls {
  .tippy-tooltip.light-theme {
    padding: 0 !important;
    .tippy-arrow {
      display: none !important;
    }
    .tippy-content {
      padding: 0 !important;
    }
  }
}

.markdown-body {
  h2 {
    color: var(--color-fg-default);
  }
}

#markdown {
  padding: 20px;
}

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

#markdown h3 {
  color: var(--color-fg-default);
  line-height: 52px;
  font-size: 14px;
  position: relative;
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
</style>
