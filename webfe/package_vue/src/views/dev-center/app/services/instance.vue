<template lang="html">
  <div>
    <app-top-bar
      v-if="!isCloudNativeApp"
      :paths="servicePaths"
      :can-create="canCreateModule"
      :cur-module="curAppModule"
    />

    <div class="instance-container">
      <section class="instance-tab-container">
        <bk-tab
          class="mt5"
          :active.sync="curServiceTab"
          type="unborder-card"
        >
          <bk-tab-panel
            name="detail"
            :label="$t('实例详情')"
          >
            <paas-content-loader
              :is-loading="isLoading"
              placeholder="data-inner-loading"
              :height="600"
              :offset-top="0"
            >
              <div
                class="dataStore-middle health-wrapper"
                style="min-height: 200px;"
              >
                <bk-alert
                  v-if="delAppDialog.moduleList.length > 0"
                  style="margin-bottom: 10px;"
                  type="info"
                  :title="pageTips"
                />
                <div v-if="!isLoading">
                  <table
                    class="ps-table ps-table-default"
                    style="width: 100%;"
                  >
                    <tr class="ps-table-environment-header">
                      <th style="width: 120px">
                        {{ $t('实例ID') }}
                      </th>
                      <th style="width: 420px;">
                        {{ $t('配置信息') }}
                      </th>
                      <th style="width: 180px">
                        {{ $t('使用环境') }}
                      </th>
                      <th
                        v-if="hasAdminUrl"
                        style="width: 120px"
                      >
                        {{ $t('管理入口') }}
                      </th>
                    </tr>
                    <template v-if="instanceCount !== 0">
                      <tr
                        v-for="(item, index) in instanceList"
                        :key="index"
                        class="ps-table-slide-up"
                      >
                        <td>#{{ index + 1 }}</td>
                        <template
                          v-if="item.service_instance.config.hasOwnProperty('is_done')
                            && !item.service_instance.config.is_done">
                          <td>
                            <p class="mt15 mb15">
                              {{ $t('服务正在创建中，请通过“管理入口”查看进度') }}
                            </p>
                          </td>
                        </template>
                        <template v-else>
                          <td>
                            <div
                              v-for="(value, key) in item.service_instance.credentials"
                              :key="key"
                              class="config-width"
                            >
                              <i class="gray">{{ key }}: </i><span class="break-all">{{ value }}</span><br>
                            </div>
                            <div
                              v-for="(key, fieldsIndex) in item.service_instance.sensitive_fields"
                              :key="fieldsIndex"
                            >
                              <i class="gray">{{ key }}: </i>******
                              <i
                                v-bk-tooltips="$t('敏感字段，请参考下方使用指南，通过环境变量获取')"
                                class="paasng-icon paasng-question-circle"
                              />
                            </div>
                            <div
                              v-for="(value, key) in item.service_instance.hidden_fields"
                              :key="key"
                            >
                              <i class="gray">{{ key }}: </i>
                              <span
                                v-if="hFieldstoggleStatus[index][key]"
                                class="break-all"
                              >
                                {{ value }}
                              </span>
                              <span
                                v-else
                                class="break-all"
                              >******</span>
                              <button
                                v-bk-tooltips="$t('敏感字段，点击后显示')"
                                class="btn-display-hidden-field ps-btn ps-btn-default ps-btn-xs"
                                @click="$set(hFieldstoggleStatus[index], key, !hFieldstoggleStatus[index][key])"
                              >
                                {{ hFieldstoggleText[hFieldstoggleStatus[index][key] || false] }}
                              </button>
                            </div>
                            <div
                              v-if="!item.service_instance.sensitive_fields.length"
                              class="copy-container"
                            >
                              <span @click="handleCopy(item)"> {{ $t('复制') }} </span>
                            </div>
                          </td>
                        </template>
                        <td>{{ item.environment_name }}</td>
                        <td v-if="hasAdminUrl">
                          <p>
                            <template v-if="item.service_instance.config.admin_url">
                              <a
                                :href="item.service_instance.config.admin_url"
                                class="blue"
                                target="_blank"
                              > {{ $t('查看') }} </a>
                            </template>
                            <template v-else>
                              --
                            </template>
                          </p>
                        </td>
                      </tr>
                    </template>
                    <tr
                      v-if="instanceCount === 0"
                      class="ps-table-slide-up"
                    >
                      <td :colspan="hasAdminUrl ? 4 : 3">
                        <div class="paas-loading-panel">
                          <div class="text">
                            <table-empty
                              class="table-empty-cls"
                              :empty-title="$t('暂无增强服务配置信息')"
                              empty
                            />
                            {{ $t('服务启用后，将在重新部署时申请实例，请先') }}
                            <span
                              class="blue pl27"
                              style="cursor: pointer;"
                              @click="toAppDeploy"
                            >{{ $t('部署应用') }}</span>
                          </div>
                        </div>
                      </td>
                    </tr>
                  </table>
                </div>
              </div>

              <div
                v-if="!isLoading"
                class="middle"
              >
                <div class="dataStore-middle">
                  <h3 style="font-size: 16px;">
                    {{ $t('使用指南') }}
                  </h3>
                  <div v-if="!isGuardLoading">
                    <div
                      id="markdown"
                      class="data-store-use"
                    >
                      <div
                        class="markdown-body"
                        v-html="compiledMarkdown"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </paas-content-loader>
          </bk-tab-panel>
          <bk-tab-panel
            name="manager"
            :label="$t('管理实例')"
          >
            <div class="manager-example">
              <section
                v-if="specifications.length"
                class="config-info"
              >
                <template v-if="showConfigInfo">
                  <config-view
                    :can-edit="canEditConfig"
                    :loading="editLoading"
                    :list="specifications"
                    @on-edit="handleConfigEdit"
                  />
                </template>
                <template v-else>
                  <config-edit
                    mode="edit"
                    :list="definitions"
                    :guide="serviceMarkdown"
                    :value="values"
                    :save-loading="saveLoading"
                    @on-change="handleConfigChange"
                  />
                </template>
              </section>
              <div class="delete-title">
                {{ $t('删除服务') }}
              </div>
              <p class="delete-tips">
                {{ $t('所有已申请实例的相关数据将被销毁。应用与服务之间的绑定关系也会被解除。') }}
              </p>
              <div class="delete-button">
                <bk-popover
                  v-if="isSmartApp"
                  :content="$t('S-mart应用暂不支持删除增强服务')"
                >
                  <bk-button
                    theme="danger"
                    disabled
                  >
                    {{ $t('删除服务') }}
                  </bk-button>
                </bk-popover>
                <bk-button
                  v-else
                  theme="danger"
                  @click="showRemovePrompt"
                >
                  {{ $t('删除服务') }}
                </bk-button>
              </div>
            </div>
          </bk-tab-panel>
        </bk-tab>
      </section>
    </div>

    <bk-dialog
      v-model="delAppDialog.visiable"
      width="540"
      :title="$t('确认删除实例？')"
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

<script>import { marked } from 'marked';
import appBaseMixin from '@/mixins/app-base-mixin';
import appTopBar from '@/components/paas-app-bar';
import ConfigView from './comps/config-view';
import ConfigEdit from './comps/config-edit';
import $ from 'jquery';

export default {
  components: {
    appTopBar,
    ConfigView,
    ConfigEdit,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      categoryId: 0,
      instanceList: [],
      instanceCount: 0,
      name: '',
      appName: this.$route.query.appName,
      title: '',
      // isLoading: true,
      isGuardLoading: true,
      service: this.$route.params.service,
      hFieldstoggleStatus: [],
      hFieldstoggleText: {
        true: this.$t('隐藏'),
        false: this.$t('显示'),
      },
      serviceExtraMsg: '',
      serviceExtraMsgMap: {
        'GCS-MySQL': this.$t('每个应用默认开启MySQL服务，并默认分配两个服务实例'),
        MySQL: this.$t('每个应用默认开启MySQL服务，并默认分配两个服务实例'),
        RabbitMQ: this.$t('开启RabbitMQ服务，系统默认分配两个服务实例'),
        Sentry: this.$t('服务开启后，应用错误将自动上报到Sentry服务'),
      },
      serviceMarkdown: `## ${this.$t('暂无使用说明')}`,
      // detail: 实例详情 manager: 管理实例
      curServiceTab: 'detail',
      delAppDialog: {
        visiable: false,
        isLoading: false,
        moduleList: [],
      },
      formRemoveConfirmCode: '',
      servicePaths: [],
      showConfigInfo: true,
      canEditConfig: false,
      specifications: [],
      definitions: [],
      values: [],
      editLoading: false,
      saveLoading: false,
      requestQueue: ['init', 'enabled', 'shareModule'],
      copyContent: '',
    };
  },
  computed: {
    compiledMarkdown() {
      this.$nextTick(() => {
        $('#markdown').find('a')
          .each(function () {
            $(this).attr('target', '_blank');
          });
      });
      console.log('marked', marked);
      return marked(this.serviceMarkdown, { sanitize: true });
    },
    hasAdminUrl() {
      const hasUrlItems = this.instanceList.filter(item => item.service_instance.config.admin_url);
      if (hasUrlItems && hasUrlItems.length) {
        return true;
      }
      return false;
    },
    formRemoveValidated() {
      return this.appCode === this.formRemoveConfirmCode;
    },
    region() {
      return this.curAppInfo.application.region;
    },
    errorTips() {
      return `${this.$t('该实例被以下模块共享：')}${this.delAppDialog.moduleList.map(item => item.name).join('、')}${this.$t('，删除后这些模块也将无法获取相关的环境变量。')}`;
    },
    pageTips() {
      return `${this.$t('实例被以下模块共享：')}${this.delAppDialog.moduleList.map(item => item.name).join('、')}${this.$t('，这些模块将获得实例的所有环境变量。')}`;
    },
    isLoading() {
      return this.requestQueue.length > 0;
    },
  },
  watch: {
    '$route'() {
      this.requestQueue = ['init', 'enabled', 'shareModule'];
      this.init();
      this.fetchEnableSpecs();
      this.fetchServicesShareDetail();
    },
    curServiceTab(value) {
      if (value === 'detail') {
        this.init();
      }
    },
  },
  created() {
    this.init();
    this.fetchEnableSpecs();
    this.fetchServicesShareDetail();
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

    fliter(str) {
      if (str.substr(str.length - 1, str.length) === '_') {
        str = str.substr(0, str.length - 1);
      }
    },

    init() {
      this.isGuardLoading = true;

      this.$http.get(`${BACKEND_URL}/api/services/${this.service}/`).then((response) => {
        this.servicePaths = [];
        const resData = response.result;
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
        this.categoryId = resData.category.id;
      })
        .finally(() => {
          this.isGuardLoading = false;
        });

      const relatedInformationUrl = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/services/${this.service}/`;
      this.$http.get(relatedInformationUrl).then((response) => {
        const resData = response;
        this.instanceList = resData.results;
        this.instanceCount = resData.count;
        this.canEditConfig = resData.count === 0;
        // eslint-disable-next-line no-restricted-syntax
        for (const instanceIndex in resData.results) {
          this.hFieldstoggleStatus.push({});
          // eslint-disable-next-line max-len
          this.instanceList[instanceIndex].service_instance.credentials = JSON.parse(this.instanceList[instanceIndex].service_instance.credentials);
          this.instanceList[instanceIndex].usage = JSON.parse(this.instanceList[instanceIndex].usage);
        }
      })
        .catch(() => {
          this.$router.push({
            name: 'appService',
            params: {
              id: this.appCode,
              moduleId: this.curModuleId,
            },
          });
        })
        .finally(() => {
          this.requestQueue.shift();
        });
    },

    async fetchEnableSpecs() {
      try {
        const res = await this.$store.dispatch('service/getEnableSpecs', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          service: this.service,
        });
        this.specifications = (res.results || []).map(({ display_name, value }) => ({
          // eslint-disable-next-line camelcase
          name: display_name,
          value,
        }));
      } catch (_) {

      } finally {
        this.requestQueue.shift();
      }
    },

    async fetchServicesSpecsDetail() {
      this.editLoading = true;
      try {
        const res = await this.$store.dispatch('service/getServicesSpecsDetail', {
          id: this.service,
          region: this.region,
        })
                    ;(res.definitions || []).forEach((item, index) => {
          let values = [];
          res.values.forEach((val) => {
            values.push(val[index]);
          });
          values = [...new Set(values)].filter(Boolean);
          this.$set(item, 'children', values);
          this.$set(item, 'active', this.specifications[index].value);
          this.$set(item, 'showError', false);
        });
        this.definitions = [...res.definitions];
        this.values = [...res.values];
        this.showConfigInfo = false;
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.editLoading = false;
      }
    },

    showExtraMsg(serviceName) {
      if (!(serviceName in this.serviceExtraMsgMap)) {
        return false;
      }
      this.serviceExtraMsg = this.serviceExtraMsgMap[serviceName];
      return true;
    },

    curTabSwitch(tab) {
      this.curServiceTab = tab;
    },

    showRemovePrompt() {
      this.delAppDialog.visiable = true;
      this.fetchServicesShareDetail();
    },

    hookAfterClose() {
      this.formRemoveConfirmCode = '';
    },

    submitRemoveInstance() {
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/services/${this.service}/`;

      this.$http.delete(url).then(
        () => {
          this.delAppDialog.visiable = false;
          this.$paasMessage({
            theme: 'success',
            message: this.$t('删除服务实例成功'),
          });
          this.$router.push({
            name: 'appService',
            params: {
              category_id: this.$route.params.category_id,
              id: this.$route.params.id,
            },
          });
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

    handleConfigEdit() {
      this.fetchServicesSpecsDetail();
    },

    async handleConfigChange(action, payload) {
      if (action === 'cancel') {
        this.showConfigInfo = true;
        return;
      }
      this.saveLoading = true;
      const params = {
        specs: payload,
        service_id: this.service,
        module_name: this.curModuleId,
        code: this.appCode,
      };
      try {
        await this.$store.dispatch('service/enableServices', params);
        this.$paasMessage({
          limit: 1,
          theme: 'success',
          message: this.$t('配置信息修改成功'),
        });
        const specifications = [];
        for (const key in payload) {
          const curObj = this.definitions.find(item => item.name === key);
          specifications.push({
            name: curObj.display_name,
            value: payload[key],
          });
        }
        const specificationsNames = this.specifications.map(item => item.name);
        const notHasNames = specificationsNames.filter((item) => {
          const arr = this.definitions.map(item => item.display_name);
          return !arr.includes(item);
        });
        notHasNames.forEach((item) => {
          const obj = this.specifications.find(spec => spec.name === item);
          specifications.push({
            name: obj.name,
            value: obj.value,
          });
        });
        this.specifications = specifications;
        this.showConfigInfo = true;
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.saveLoading = false;
      }
    },
    handleCopy(payload) {
      const { credentials } = payload.service_instance;
      const hiddenFields = payload.service_instance.hidden_fields;

      for (const key in credentials) {
        this.copyContent += `${key}:${credentials[key]}\n`;
      }
      for (const key in hiddenFields) {
        this.copyContent += `${key}:${hiddenFields[key]}\n`;
      }

      const el = document.createElement('textarea');
      el.value = this.copyContent;
      el.setAttribute('readonly', '');
      el.style.position = 'absolute';
      el.style.left = '-9999px';
      document.body.appendChild(el);
      const selected = document.getSelection().rangeCount > 0 ? document.getSelection().getRangeAt(0) : false;
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      if (selected) {
        document.getSelection().removeAllRanges();
        document.getSelection().addRange(selected);
      }
      this.$bkMessage({ theme: 'success', message: this.$t('复制成功'), delay: 2000, dismissable: false });
    },

    toAppDeploy() {
      const type = this.curAppInfo.application.type || '';
      if (type === 'cloud_native') {
        this.$router.push({
          name: 'cloudAppDeployForProcess',
          params: {
            moduleId: this.curAppModule.name,
            id: this.appCode,
          },
        });
        return;
      }
      this.$router.push({
        name: 'appDeploy',
        params: { id: this.appCode },
        query: { focus: 'stag' },
      });
    },
  },
};

</script>

<style lang="scss" scoped>
    .markdown-body {
        box-sizing: border-box;
        min-width: 200px;
        margin: 0 auto;
        padding: 5px 20px;

        h2,h3 {
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
        word-break: break-all
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
        transition: all .3s;
        cursor: pointer;
    }

    .service-list li:hover .datastore-alink {
        background: #3A84FF;
        border-top: solid 1px #3A84FF;
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
            background: rgba(255,255,255,1);
            border-radius: 2px;
            border: 1px solid rgba(220,222,229,1);
            th {
                border-top: none;
                border-right: none;
                border-bottom: 1px solid rgba(220,222,229,1);
            }
            td {
                border-bottom: 1px solid rgba(220,222,229,1);
            }
        }
        .ps-table-slide-up {
            color: #63656E;
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
    .copy-container{
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
        width: 88%;
    }
    .ps-table-slide-up .paas-loading-panel .table-empty-cls .empty-tips {
        color: #999;
    }
    .instance-tab-container{
      background: #fff;
      margin-top: 16px;
    }

    .instance-container{
      margin: 0px 24px;
    }
</style>
