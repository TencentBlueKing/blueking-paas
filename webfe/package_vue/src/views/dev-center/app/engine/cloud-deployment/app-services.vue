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
      <div class="middle ps-main">
        <bk-table
          v-bkloading="{ isLoading: tableLoading, opacity: 1 }"
          :data="tableList"
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
          <bk-table-column :label="$t('服务名称')" width="300">
            <template slot-scope="{row, $index}">
              <div class="flex-row align-items-center">
                <img class="row-img" :src="row.logo" alt="">
                <p
                  class="row-title-text"
                  :class="row.isStartUp ? '' : 'text-disabled'" @click="handleToPage(row)">
                  {{ row.display_name || '--' }}
                </p>
                <i
                  v-if="$index === rowIndex"
                  class="row-icon paasng-icon paasng-process-file pl5"
                  v-bk-tooltips="{content: $t('使用指南')}"
                  @click="handleShowGuideDialog(row)" />
              </div>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('预发布环境')"
            width="100"
            :render-header="$renderHeader"
          >
            <template slot-scope="{row}">
              <span v-if="row.type === 'bound' && row.provision_infos && row.provision_infos.stag">
                <i class="paasng-icon paasng-correct success-icon" />
              </span>
              <span v-else>--</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('生产环境')"
            width="100"
            :render-header="$renderHeader"
          >
            <template slot-scope="{row}">
              <span v-if="row.type === 'bound' && row.provision_infos && row.provision_infos.prod">
                <i class="paasng-icon paasng-correct success-icon" />
              </span>
              <span v-else>--</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('配置信息')"
            :render-header="$renderHeader"
          >
            <template slot-scope="{row}">
              <span v-if="row.isStartUp && row.specifications && row.specifications.length">
                <bk-tag v-for="(item) in row.specifications" :key="item.recommended_value">
                  <span>
                    {{ $t(item.display_name) }} {{ getVersionValue(item.name, row?.specificationsData || []) }}
                  </span>
                </bk-tag>
              </span>
              <span v-else>{{ $t('无') }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('共享信息')"
            :render-header="$renderHeader"
          >
            <template slot-scope="{row}">
              <span v-if="row.type === 'bound' && row.ref_modules && row.ref_modules.length">
                {{ $t('被') }} {{ row.ref_modules.map(e => e.name).join(',') }} {{ $t('共享') }}
              </span>
              <span v-else-if="row.type === 'shared' && row.ref_module">
                {{ $t('共享来自') }} {{row.ref_module.name }}
              </span>
              <span v-else>--</span>
            </template>
          </bk-table-column>
          <bk-table-column
            width="180"
            :label="$t('启/停')"
            class-name="services-table-cloumn"
            :render-header="$renderHeader"
          >
            <template slot-scope="{row, $index}">
              <div
                class="ps-switcher-wrapper"
                @click="toggleSwitch(row, $index)"
                v-bk-tooltips="{
                  content: $t('S-mart 应用不支持停用增强服务'),
                  disabled: !isSmartApp,
                  allowHTML: true
                }"
                v-if="row.isStartUp">
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
                    @click="handleSwitcherOpen(item)">
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
        width="480"
        :title="$t('配置信息')"
        :mask-close="false"
        ext-cls="paasng-service-export-dialog-cls"
        header-position="left"
        @confirm="handleConfigChange">
        <bk-form
          :model="startFormData">
          <bk-form-item
            v-for="(item, index) in definitions" :key="index"
            :label="$t(item.display_name)"
          >
            <!-- <span class="form-text">{{ artifactType || '--' }}</span> -->
            <bk-radio-group
              v-model="item.active"
            >
              <bk-radio
                v-for="childrenItem in item.children"
                :key="childrenItem"
                :value="childrenItem"
              >
                {{ $t(childrenItem) }}
              </bk-radio>
            </bk-radio-group>
          </bk-form-item>
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
          style="min-height: 63px;"
          @submit.prevent="submitRemoveInstance"
        >
          <div class="spacing-x1">
            {{ $t('预发布环境和生产环境的实例都将被删除；该操作不可撤销，请完整输入应用 ID') }} <code>{{ appCode }}</code> {{ $t('确认：') }}
          </div>
          <div class="ps-form-group">
            <input
              v-model="formRemoveConfirmCode"
              type="text"
              class="ps-form-control"
            >
          </div>
          <bk-alert
            v-if="delAppDialog.moduleList.length > 0"
            style="margin-top: 10px;"
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
            {{ $t('请完整输入应用 ID ') }}<code>{{ appCode }}</code> {{ $t('确认：') }}
          </div>
          <div class="ps-form-group">
            <input
              v-model="formRemoveConfirmCode"
              type="text"
              class="ps-form-control"
            >
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
          <div id="markdown" v-bkloading="{ isLoading: guideLoading, opacity: 1 }">
            <div
              class="markdown-body"
              v-html="compiledMarkdown"
            />
          </div>
        </div>
      </bk-sideslider>
    </paas-content-loader>
  </div>
</template>

<script>import appBaseMixin from '@/mixins/app-base-mixin';
import SharedDialog from './comps/shared-dialog';
import { marked } from 'marked';

export default {
  components: {
    SharedDialog,
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
      startData: [{ value: 'start', label: this.$t('直接启用') }, { value: 'shared', label: this.$t('从其他模块共享') }],
      isShowDialog: false,
      curData: {},
      curIndex: '',
      startFormData: {},
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
    };
  },
  computed: {
    appCode() {
      return this.$route.params.id;
    },
    curAppCode() {
      return this.$store.state.curAppCode;
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
      return `${this.$t('解除后，当前模块将无法获取 ')}${this.curModuleId} ${this.$t('模块的')} ${this.curData.display_name} ${this.$t('服务的所有环境变量')}`;
    },

    compiledMarkdown() {
      // eslint-disable-next-line vue/no-async-in-computed-properties
      this.$nextTick(() => {
        $('#markdown').find('a')
          .each(function () {
            $(this).attr('target', '_blank');
          });
      });
      return marked(this.serviceMarkdown, { sanitize: true });
    },
    getVersionValue() {
      return function (name, data) {
        const versionData = data.find(e => e.name === name) || {};
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
          v.specificationsData = v.specifications;
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

        // 处理服务->数据存储服务详情跳转
        const redirectData = this.tableList.find(v => v.uuid === this.$route.params?.service);
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
      if (payload.isStartUp) {    // 已经启动的状态
        if (payload.type === 'shared') {    // 解绑弹窗
          this.removeSharedDialog.visiable = true;
        } else {
          this.delAppDialog.visiable = true;    // 停用弹窗
          this.fetchServicesShareDetail();
        }
      }
    },


    handleSwitcherOpen(payload) {
      // eslint-disable-next-line no-underscore-dangle
      this.$refs[`tooltipsHtml${this.curIndex}`]._tippy.hide();
      if (payload.value === 'start') {  // 直接启动
        if (this.curData.specifications.length) { // 配置并启动
          this.isShowStartDialog = true;
          this.fetchServicesSpecsDetail();
        } else {  // 直接启动
          const formData = {
            service_id: this.curData.uuid,
            code: this.appCode,
            module_name: this.curModuleId,
          };
          const url = `${BACKEND_URL}/api/services/service-attachments/`;
          this.$http.post(url, formData).then(() => {
            this.$paasMessage({
              theme: 'success',
              message: this.$t('服务启用成功'),
            });
            this.init();
          }, (resp) => {
            this.$paasMessage({
              theme: 'error',
              message: resp.detail || this.$t('接口异常'),
            });
          });
        }
      } else {    // 从其他模块中共享
        this.isShowDialog = true;
      }
    },

    handleExportSuccess() {
      this.init();
    },


    // 获取启动时需要的配置信息
    async fetchServicesSpecsDetail() {
      try {
        const res = await this.$store.dispatch('service/getServicesSpecsDetail', {
          id: this.curData.uuid,
          region: this.region,
        });
        (res.definitions || []).forEach((item, index) => {
          let values = [];
          res.values.forEach((val) => {
            values.push(val[index]);
          });
          values = [...new Set(values)].filter(Boolean);
          this.$set(item, 'children', values);
          this.$set(item, 'active', res.recommended_values[index]);
          this.$set(item, 'showError', false);
        });
        this.definitions = [...res.definitions];
        this.values = [...res.values];
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.detail || res.message || this.$t('接口异常'),
        });
      } finally {
        this.isLoading = false;
      }
    },


    // 确认启动服务
    async handleConfigChange() {
      this.loading = true;
      const specs = this.definitions.reduce((p, v) => {
        p[v.name] = v.active;
        return p;
      }, {});
      const params = {
        specs,
        service_id: this.curData.uuid,
        module_name: this.curModuleId,
        code: this.curAppCode,
      };
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
        },
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
        if (payload.type === 'shared') {    // 共享
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
        } else {    // 直接启动
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

  },
};
</script>

<style lang="scss" scoped>
  .services-container{
    .ps-top-bar{
      padding: 0 20px;
    }
    .image-content{
      background: #fff;
      padding-top: 0;
    }
    .row-img{
      width: 22px;
      height: 22px;
      border-radius: 50%;
    }
    .ps-switcher-wrapper {
      margin-left: 0;
    }
    .row-title-text{
      margin-left: 8px;
      overflow:hidden; //超出的文本隐藏
      text-overflow:ellipsis; //溢出用省略号显示
      white-space:nowrap; //溢出不换行
      cursor: pointer;
      color: #3A84FF;
    }
    .text-disabled{
      color: #63656e;
      cursor: unset;
    }
    .row-icon{
      color: #63656E;
      margin-top: 3px;

      &:hover {
        cursor: pointer;
        color: #3A84FF;
      }
    }

    .success-icon{
      font-size: 24px;
      color: #2DCB56;
    }
  }
    .header-title {
        display: flex;
        align-items: center;
        .app-code {
            color: #979BA5;
        }
        .arrows {
            margin: 0 9px;
            transform: rotate(-90deg);
            font-size: 12px;
            font-weight: 600;
            color: #979ba5;
        }
    }
    #switcher-tooltip{
      border: 1px solid #DCDEE5;
      border-radius: 2px;
      .item{
        padding: 0 12px;
        cursor: pointer;
        height: 32px;
        line-height: 32px;
        color: #63656E;
        font-size: 12px;
        &:hover {
          background: #F5F7FA;
        }
        &:first-child {
          margin-top: 4px;
        }
        &:last-child {
          margin-bottom: 4px;
        }
      }
    }

</style>
<style lang="scss">
    .services-tips-cls{
      .tippy-arrow{
          display: none !important;
        }
      .tippy-tooltip,
      .tippy-content{
        padding: 0 !important;
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

    #markdown pre>code {
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
