<template>
  <div
    class="port-config app-entry-config-cls"
    v-bkloading="{ isLoading: setModuleLoading, title: $t('正在设置主模块') }"
  >
    <div
      class="content"
      style="position: relative"
    >
      <div :class="['table-title', { 'cloud-cls': isCloudNativeApp }]">
        <div class="tips">
          <i class="paasng-icon paasng-info-line info-icon" />
          {{ $t('平台为应用提供了内置的访问地址，也可以添加自定义地址来配置额外的访问入口。') }}
          <a
            :href="GLOBAL.DOC.APP_ENTRY_INTRO"
            target="blank"
          >
            {{ $t('详细使用说明-simple') }}
          </a>
        </div>
        <div
          v-if="isIpConsistent"
          :key="tipIndex"
          class="ip-tips"
          :class="isCloudNativeApp ? 'ip-cloud-tips' : 'ip-app-tips'"
          v-bk-tooltips.bottom-start="configIpTip"
        >
          {{ $t('如何配置域名解析') }}
          <i class="paasng-icon paasng-info-fill"></i>
        </div>
      </div>
      <bk-table
        ref="portConfigRef"
        v-bkloading="{ isLoading: isTableLoading }"
        :data="entryList"
        class="table-cls"
        border
        cell-class-name="table-cell-cls"
        @row-mouse-enter="handleRowMouseEnter"
        @row-mouse-leave="handleRowMouseLeave"
      >
        <bk-table-column
          :label="$t('模块')"
          :width="190"
          class-name="table-colum-module-cls"
        >
          <template slot-scope="{ row, $index }">
            <section
              class="module-container"
              :class="rowIndex === $index && !row.is_default ? 'module-cursor' : ''"
            >
              <div class="flex-row align-items-center">
                {{ row.name || '--' }}
                <img
                  :class="['module-default', 'ml10', { en: localLanguage === 'en' }]"
                  v-if="row.is_default"
                  :src="`/static/images/${localLanguage === 'en' ? 'main_en.png' : 'main.png'}`"
                />
              </div>
              <bk-button
                v-if="rowIndex === $index && !row.is_default"
                text
                theme="primary"
                class="set-module-btn"
                @click="handleSetDefault(row)"
              >
                {{ $t('设为主模块') }}
              </bk-button>
            </section>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('环境')"
          :width="160"
          class-name="table-colum-cls table-colum-stag-cls"
        >
          <template slot-scope="{ row, $index }">
            <div
              class="cell-container-width"
              v-for="(item, i) in row.envsData"
              :key="item"
            >
              <div
                v-if="row.envs[item].length"
                :style="{ height: `${46 * row.envs[item].length}px` }"
                class="cell-container flex-column justify-content-center"
                @mouseenter="handleEnvMouseEnter($index, i, row, item)"
                @mouseleave="handleEnvMouseLeave"
              >
                <div class="env-container">
                  <div class="text-container">
                    <!--  tooltips有bug，需要隐藏一下，html内容才会更新-->
                    <div
                      :class="['ml15', 'mr15', { text: configIpTip }]"
                      v-if="tableIndex === $index && envIndex === i && row.envs[item]"
                      v-bk-tooltips="isIpConsistent ? { disabled: true } : configIpTip"
                    >
                      {{ $t(entryEnv[item]) }}
                    </div>
                    <div
                      class="ml15 mr15"
                      v-else
                    >
                      {{ $t(entryEnv[item]) }}
                    </div>
                    <span
                      :class="['btn-container', { en: localLanguage === 'en' }]"
                      v-bk-tooltips="{
                        content: $t(
                          row.envs[item][0].is_running
                            ? '添加自定义访问地址'
                            : '需要先部署该环境后，才能添加自定义访问地址'
                        ),
                      }"
                      v-if="rowIndex === $index && row.envs[item]"
                    >
                      <i
                        class="paasng-icon paasng-plus-thick"
                        :class="!row.envs[item][0].is_running ? 'disable-add-icon' : ''"
                      />
                      <bk-button
                        :disabled="!row.envs[item][0].is_running"
                        text
                        theme="primary"
                        @click="handleAdd($index, i, row, item)"
                      >
                        {{ $t('添加') }}
                      </bk-button>
                    </span>
                  </div>
                  <div
                    v-if="i !== row.envsData.length - 1"
                    class="stag-line"
                  ></div>
                </div>
              </div>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('访问地址')"
          :min-width="600"
          class-name="custom-line-column"
        >
          <template slot-scope="{ row, $index }">
            <div
              v-for="item in row.envsData"
              :key="item"
              class="cell-container"
            >
              <div
                v-for="(e, i) in row.envs[item]"
                :key="i"
                class="url-container flex-column justify-content-center"
              >
                <div v-if="e.isEdit">
                  <bk-form
                    :label-width="0"
                    form-type="inline"
                    :model="e.address"
                    ref="urlInfoForm"
                    class="url-from-cls"
                  >
                    <bk-form-item
                      :required="true"
                      :property="'url'"
                      :rules="rules.url"
                    >
                      <bk-input
                        v-model="e.address.url"
                        :placeholder="$t('请输入有效域名')"
                        class="url-input-cls"
                      >
                        <bk-dropdown-menu
                          class="group-text"
                          ref="dropdown"
                          slot="prepend"
                          trigger="click"
                          font-size="normal"
                          @show="$set(e, 'isDropdownShow', true)"
                          @hide="$set(e, 'isDropdownShow', false)"
                        >
                          <bk-button
                            class="f12"
                            type="primary"
                            slot="dropdown-trigger"
                            v-bk-tooltips="getProtocolTipConfig(e)"
                          >
                            {{ e.editProtocol || 'http' }}://
                            <i :class="['bk-icon icon-angle-down', { 'icon-flip': e.isDropdownShow }]"></i>
                          </bk-button>
                          <ul
                            class="bk-dropdown-list"
                            slot="dropdown-content"
                          >
                            <li
                              v-for="protocol in ['http', 'https']"
                              :key="protocol"
                            >
                              <a
                                href="javascript:;"
                                @click="handleProtocolChange(protocol, e)"
                              >
                                {{ protocol }}://
                              </a>
                            </li>
                          </ul>
                        </bk-dropdown-menu>
                      </bk-input>
                    </bk-form-item>
                    <bk-form-item
                      :required="true"
                      :property="'pathPrefix'"
                      :rules="rules.pathPrefix"
                    >
                      <bk-input
                        class="path-input-cls"
                        v-model="e.address.pathPrefix"
                        :placeholder="$t('请输入路径')"
                        @change="handlePathChange($event, i)"
                      ></bk-input>
                    </bk-form-item>
                  </bk-form>
                </div>
                <section v-else>
                  <div
                    v-bk-tooltips="{
                      content: $t(rowIndex === $index ? '该环境未部署，无法访问' : ''),
                      disabled: e.is_running,
                    }"
                    class="flex-row align-items-center"
                  >
                    <bk-button
                      text
                      theme="primary"
                      class="address-btn-cls"
                      :disabled="!e.is_running"
                      @click="handleUrlOpen(e.address.url)"
                    >
                      {{ e.address.url }}
                    </bk-button>
                    <img
                      class="custom-image ml10"
                      v-if="e.address.type === 'custom'"
                      :src="`/static/images/${localLanguage === 'en' ? 'custom_en.png' : 'custom.png'}`"
                    />
                  </div>
                </section>
                <div class="line"></div>
              </div>
            </div>
          </template>
        </bk-table-column>
        <!-- 云原生应用暂不支持 -->
        <bk-table-column
          v-if="!isCloudNativeApp"
          :label="$t('进程')"
          :width="110"
          class-name="custom-line-column"
        >
          <template slot-scope="{ row }">
            <div
              v-for="item in row.envsData"
              :key="item"
              class="cell-container"
            >
              <div
                v-for="(e, i) in row.envs[item]"
                :key="i"
                class="url-container flex-column justify-content-center"
              >
                <div v-if="e.isEdit">
                  <bk-select
                    :disabled="true"
                    v-model="defaultProcess"
                  >
                    <bk-option
                      v-for="option in processList"
                      :key="option.name"
                      :id="option.name"
                      :name="option.name"
                    ></bk-option>
                  </bk-select>
                </div>
                <section v-else>
                  <div class="flex-row align-items-center">web</div>
                </section>
                <div class="line"></div>
              </div>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column
          v-if="!isMigrationStatus"
          :label="$t('操作')"
          :width="120"
          fixed="right"
          class-name="custom-line-column"
        >
          <template slot-scope="{ row, $index }">
            <div
              v-for="item in row.envsData"
              :key="item"
              class="cell-container"
            >
              <div
                v-for="(e, i) in row.envs[item]"
                :key="i"
                class="url-container"
              >
                <div v-if="e.address.type === 'custom'">
                  <section v-if="e.isEdit">
                    <bk-button
                      text
                      theme="primary"
                      :loading="isSaveLoading"
                      @click="handleSubmit($index, i, row, item)"
                    >
                      {{ $t('保存') }}
                    </bk-button>
                    <bk-button
                      text
                      theme="primary"
                      class="ml10"
                      @click="handleCancel($index, i, row, item)"
                    >
                      {{ $t('取消') }}
                    </bk-button>
                  </section>
                  <section v-else>
                    <bk-button
                      text
                      theme="primary"
                      @click="handleEdit($index, i, row, item)"
                    >
                      {{ $t('编辑') }}
                    </bk-button>
                    <bk-button
                      text
                      theme="primary"
                      class="ml10"
                      @click="showRemoveModal(i, row, item)"
                    >
                      {{ $t('删除') }}
                    </bk-button>
                  </section>
                </div>
                <div v-else>--</div>
                <div :class="['line', { 'show-last-line': entryList.length === $index + 1 }]"></div>
              </div>
            </div>
          </template>
        </bk-table-column>
      </bk-table>

      <bk-dialog
        v-model="visitDialog.visiable"
        width="600"
        :title="visitDialog.title"
        :theme="'primary'"
        :header-position="'left'"
        :mask-close="false"
        :loading="isLoading"
        @confirm="handleConfirm"
        @cancel="visitDialog.visiable = false"
      >
        <div class="tl">
          <p>{{ $t('注意事项：') }}</p>
          <p>{{ $t('1、应用的主访问路径将会变为子域名方式') }}</p>
          <p>{{ $t('2、如果应用框架代码没有适配过独立域名访问方式，一些静态文件路径可能会出现问题') }}</p>
          <p>{{ $t('3、旧的子路径地址依然有效，可以正常访问') }}</p>
        </div>
      </bk-dialog>

      <bk-dialog
        width="500"
        v-model="domainDialog.visiable"
        :title="domainDialog.title"
        :theme="'primary'"
        :header-position="'left'"
        :mask-close="false"
      >
        <div class="tl">
          <p>{{ $t('设定后：') }}</p>
          <div class="flex-row mt5">
            <p>1.</p>
            <p class="pl10">
              {{ $t('应用短地址') }}{{ $t('（') }}{{ $route.params.id }}
              {{ getAppRootDomain(curClickAppModule.clusters.prod) }}{{ $t('）') }} {{ $t('指向到应用') }}
              {{ domainDialog.moduleName }}
              {{ $t('模块的生产环境') }}
            </p>
          </div>
          <div class="flex-row mt5">
            <p>2.</p>
            <p class="pl10">
              {{ $t('应用访问限制') }}{{ $t('（') }}{{ accessControlText.join('、') }}{{ $t('）') }}{{ $t('变更为') }}
              {{ $t('对') }}{{ domainDialog.moduleName }} {{ $t('生效') }}
            </p>
          </div>
        </div>

        <div slot="footer">
          <bk-button
            theme="primary"
            @click="submitSetModule"
            :loading="setModuleLoading"
          >
            {{ $t('确定') }}
          </bk-button>
          <bk-button
            theme="default"
            class="ml10"
            @click="domainDialog.visiable = false"
          >
            {{ $t('取消') }}
          </bk-button>
        </div>
      </bk-dialog>
    </div>
  </div>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin';
import { ENV_ENUM } from '@/common/constants';
import { copy } from '@/common/tools';
import { mapState } from 'vuex';
export default {
  mixins: [appBaseMixin],
  props: {
    // 是否为迁移状态
    isMigrationStatus: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      type: '',
      canUpdateSubDomain: false,
      isLoading: false,
      visitDialog: {
        visiable: false,
        title: this.$t('确认切换为子域名访问地址？'),
      },
      region: '',
      rootDomains: [],
      rootDomainDefault: '',
      domainDialog: {
        visiable: false,
        title: '',
        moduleName: '',
      },
      rootDomainDefaultDiff: '',
      isTableLoading: false,
      entryList: [],
      entryEnv: ENV_ENUM,
      rowIndex: '',
      tableIndex: '',
      envIndex: '',
      ipConfigInfo: { frontend_ingress_ip: '' },
      rules: {
        url: [
          {
            required: true,
            message: this.$t('域名不能为空'),
            trigger: 'blur',
          },
          {
            validator: (value) => {
              const domainReg = /^[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})*$/;
              return domainReg.test(value);
            },
            message: () => `${this.$t('请输入有效域名')}`,
            trigger: 'blur',
          },
        ],
        pathPrefix: [
          {
            validator: (value) => {
              const pathPrefix = this.curPathPrefix[this.curInputIndex];
              const val = pathPrefix === undefined ? value : pathPrefix;
              const reg = /^(\/[a-z0-9_\-]*)*\/?$/;
              return reg.test(val);
            },
            message: () => this.$t('路径必须以"/"开头、且路径只能包含小写字母、数字、下划线(_)和连接符(-)'),
            trigger: 'blur',
          },
        ],
      },
      curClickAppModule: { clusters: {} },
      setModuleLoading: false,
      hostInfo: {},
      curDataId: '',
      curIngressIpConfigs: [],
      defaultItem: {},
      tipIndex: 0,
      isIpConsistent: true,
      isSaveLoading: false,
      curPathPrefix: {},
      defaultProcess: 'web',
      processList: [{ name: 'web' }],
    };
  },
  computed: {
    ...mapState(['platformFeature', 'localLanguage']),
    configIpTip() {
      let displayIp = this.defaultIp;
      if (!this.isIpConsistent) {
        displayIp = this.ipConfigInfo.frontend_ingress_ip;
      }
      return {
        theme: 'light',
        allowHtml: true,
        content: this.$t('提示信息'),
        html: `<div style="padding: 10px 0px;color: #313238;">
          <div>${this.$t('IP 信息：')}</div>
          <div
            class="mt10 ip-view-wrapper"
            style="height: 32px;background: #F0F1F5;border-radius: 2px;line-height: 32px;">
            ${displayIp}
            <i class="paasng-icon paasng-general-copy ip-icon-customize-cls"></i>
          </div>
          <div class="mt10 mb10" style="color: #979BA5;">${this.$t('推荐操作流程: ')}</div>
          <div>1. ${this.$t('首先在页面上添加好自定义访问地址')} </div>
          <div>2. ${this.$t('将您的自定义域名解析到表格中的 IP')} </div>
          </div>`,
        placements: ['bottom'],
        onHidden: () => {
          this.tipShow = false;
          if (this.mouseEnter) return;
          this.tableIndex = '';
          this.envIndex = '';
        },
        onShown: () => {
          this.tipShow = true;
          this.ipCopy();
        },
      };
    },
    defaultIp() {
      return this.defaultItem.frontend_ingress_ip;
    },
    // 根据数据提示不同内容
    accessControlText() {
      const textData = { user_access_control: this.$t('用户限制'), ip_access_control: this.$t('IP限制') };
      return (this.$store.state.region?.access_control?.module || []).reduce((prev, v) => {
        prev.push(textData[v]);
        return prev;
      }, []);
    },
  },
  watch: {
    $route() {
      this.init();
    },
  },
  mounted() {
    this.init();
  },
  methods: {
    /**
     * 数据初始化入口
     */
    init() {
      this.getAppRegion(); // 环境信息
      this.getEntryList(); // 列表信息
      // this.getDefaultDomainInfo();
      this.loadDomainConfig(); // 域名信息
    },

    // 获取域名信息
    async getAppRegion() {
      this.canUpdateSubDomain = false;
      try {
        const { region } = this.curAppInfo.application;
        const res = await this.$store.dispatch('getAppRegion', region);
        this.canUpdateSubDomain = res.entrance_config.manually_upgrade_to_subdomain_allowed;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.$emit('data-ready', 'visit-config');
      }
    },

    // 访问地址列表数据
    async getEntryList() {
      try {
        // 迁移应用请求旧数据快照
        const dispatchName = this.isMigrationStatus ? 'migration/getEntrances' : 'entryConfig/getEntryDataList';
        this.isTableLoading = true;
        const res = await this.$store.dispatch(dispatchName, {
          appCode: this.appCode,
        });
        this.entryList = (res || []).map((e) => {
          if (!e.envs.prod?.length && !e.envs.stag?.length) {
            e.envsData = [];
          } else {
            e.envsData = Object.keys(e.envs);
          }
          return e;
        }, []);
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isTableLoading = false;
      }
    },

    async handleConfirm() {
      this.isLoading = true;
      try {
        await this.$store.dispatch('entryConfig/updateEntryType', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          type: 2,
        });
        this.$bkMessage({
          theme: 'success',
          message: this.$t('修改成功'),
        });
        this.$store.commit('updateCurAppModuleExposed', 2);
        this.visitDialog.visiable = false;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isLoading = false;
      }
    },

    async getDefaultDomainInfo() {
      try {
        const res = await this.$store.dispatch('entryConfig/getDefaultDomainInfo', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        this.rootDomains = res.root_domains || [];
        this.rootDomainDefault = res.preferred_root_domain;
        this.rootDomainDefaultDiff = res.preferred_root_domain;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 设置主模块
    async submitSetModule() {
      this.domainDialog.visiable = false;
      this.setModuleLoading = true;
      try {
        await this.$store.dispatch('module/setMainModule', {
          appCode: this.appCode,
          modelName: this.curClickAppModule.name,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('主模块设置成功'),
        });
        this.$store.commit('updateCurAppModuleIsDefault', this.curClickAppModule.id);
        this.getEntryList(); // 重新请求数据
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.detail || res.message || this.$t('接口异常'),
        });
      } finally {
        this.setModuleLoading = false;
      }
    },

    // 取消
    handleCancel(index, envIndex, payload, envType) {
      const isEditCancel = payload.envs[envType][envIndex].address.id;
      // 如果是编辑的时候取消则改变状态 如果是新增时取消则删除当前这条数据
      if (isEditCancel) {
        this.entryList = this.entryList.map((e, i) => {
          if (index === i) {
            const envItem = e.envs[envType][envIndex];
            envItem.isEdit = false;
            // 恢复原始的完整URL
            if (envItem.originalUrl) {
              envItem.address.url = envItem.originalUrl;
            }
            // 清理编辑状态的字段
            this.clearEditFields(envItem);
          }
          return e;
        });
      } else {
        payload.envs[envType].splice(envIndex, 1);
      }
    },

    // 环境鼠标移入事件
    handleEnvMouseEnter(index, envIndex, payload, env) {
      this.ipConfigInfo = (this.curIngressIpConfigs || []).find(
        (e) => e.environment === env && e.module === payload.name
      ) || { frontend_ingress_ip: '暂无ip地址信息' }; // ip地址信息
      this.tableIndex = index;
      this.envIndex = envIndex;
      this.mouseEnter = true;
    },

    // 环境鼠标移出事件
    handleEnvMouseLeave() {
      this.mouseEnter = false;
      if (this.tipShow) return;
      this.tableIndex = '';
      this.envIndex = '';
    },

    // 设置为主模块
    handleSetDefault(payload) {
      this.curClickAppModule = this.curAppModuleList.find((e) => e.name === payload.name) || {}; // 当前点击的模块的所有信息
      this.domainDialog.visiable = true;
      this.domainDialog.moduleName = payload.name;
      this.domainDialog.title = this.$t(`是否设定${payload.name}模块为主模块`);
    },

    // tips数据
    loadDomainConfig() {
      this.$http.get(`${BACKEND_URL}/api/bkapps/applications/${this.appCode}/domains/configs/`).then(
        (res) => {
          this.curIngressIpConfigs = res;
          this.defaultItem = res[0] || { frontend_ingress_ip: '暂无ip地址信息' };
          // eslint-disable-next-line no-plusplus
          this.tipIndex++;
          // 判断ip是否一致
          const firstIp = this.defaultItem?.frontend_ingress_ip || '';
          this.isIpConsistent = (res || []).every((item) => firstIp === item.frontend_ingress_ip);
        },
        (res) => {
          this.$paasMessage({
            theme: 'error',
            message: `${this.$t('无法获取域名解析目标IP，错误：')}${res.detail}`,
          });
        }
      );
    },

    // 新增一条数据
    handleAdd(index, envIndex, payload, envType) {
      this.entryList = this.entryList.map((e, i) => {
        if (index === i) {
          e.envs[envType].push({
            isEdit: true,
            editProtocol: 'http', // 新增时默认协议
            isDropdownShow: false, // 下拉框状态
            address: {
              type: 'custom',
              url: '',
              pathPrefix: '/',
            },
          });
        }
        return e;
      });
    },

    // 保存一条数据
    async handleSubmit(index, envIndex, payload, envType) {
      this.curInputIndex = envIndex;
      const currentProtocol = payload.envs[envType][envIndex].editProtocol || 'http';
      // 需要过滤查看状态的数据才能获取到需要校验输入框的下标
      const readDataLength = (payload?.envs[envType] || []).filter(
        (e, readIndex) => !e.isEdit && readIndex <= envIndex
      ).length;
      const validateFromIndex = envIndex - readDataLength; // 当前点击保存的输入框下标
      await this.$refs.urlInfoForm[validateFromIndex].validate(); // 校验
      const curUrlParams = {
        environment_name: envType,
        domain_name: payload.envs[envType][envIndex].address.url,
        path_prefix: payload.envs[envType][envIndex].address.pathPrefix,
        module_name: payload.name,
        id: payload.envs[envType][envIndex].address.id || '',
        https_enabled: currentProtocol === 'https',
      };
      // 接口响应时，防止多次请求
      if (this.isSaveLoading) {
        return;
      }
      this.isSaveLoading = true;
      try {
        const params = {
          data: curUrlParams,
          appCode: this.appCode,
        };
        const fetchUrl = curUrlParams.id ? 'entryConfig/updateDomainInfo' : 'entryConfig/addDomainInfo';
        const res = await this.$store.dispatch(fetchUrl, params);
        // 当前保存的这条数据返回的id
        this.curDataId = res.id;
        this.$paasMessage({
          theme: 'success',
          message: `${curUrlParams.id ? this.$t('更新') : this.$t('添加')}${this.$t('成功')}`,
        });
        this.entryList = this.entryList.map((e, i) => {
          if (index === i) {
            const envItem = e.envs[envType][envIndex];
            envItem.isEdit = false; // 改变本条数据的状态
            envItem.is_running = true; // 能保存和编辑这代表已经部署过了
            envItem.address.url = `${currentProtocol}://${curUrlParams.domain_name}${curUrlParams.path_prefix}`;
            envItem.address.id = this.curDataId; // 成功添加，将响应id保存
            // 清理编辑状态的字段
            this.clearEditFields(envItem);
          }
          return e;
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isSaveLoading = false;
      }
    },

    // 删除域名弹窗
    showRemoveModal(envIndex, payload, envType) {
      this.$bkInfo({
        title: `${this.$t('确定要删除该域名')}?`,
        maskClose: true,
        confirmLoading: true,
        confirmFn: async () => {
          const result = await this.handleDelete(envIndex, payload, envType);
          delete this.curPathPrefix[envIndex];
          return result;
        },
      });
    },

    // 处理删除域名
    async handleDelete(envIndex, payload, envType) {
      try {
        await this.$store.dispatch('entryConfig/deleteDomainInfo', {
          appCode: this.appCode,
          id: payload.envs[envType][envIndex].address.id || this.curDataId,
        });
        this.getEntryList(); // 重新请求数据
        this.$paasMessage({
          theme: 'success',
          message: `${this.$t('删除成功')}`,
        });
        return true;
      } catch (error) {
        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('删除失败')},${error.message}`,
        });
        return false;
      }
    },

    // 编辑
    handleEdit(index, envIndex, payload, envType) {
      this.entryList = this.entryList.map((item, itemIndex) => {
        if (itemIndex !== index) return item;

        const targetEnvItem = item.envs[envType][envIndex];
        const currentUrl = targetEnvItem.address.url;

        // 进入编辑状态
        targetEnvItem.isEdit = true;

        // 保存原始URL用于取消时恢复
        targetEnvItem.originalUrl = currentUrl;

        // 解析URL获取协议和地址信息
        const { protocol, hostname, port, pathname } = this.parseUrl(currentUrl);

        // 设置编辑状态的协议和下拉框状态
        this.$set(targetEnvItem, 'editProtocol', protocol);
        this.$set(targetEnvItem, 'isDropdownShow', false);

        // 更新地址信息
        targetEnvItem.address.url = hostname + (port ? `:${port}` : '');
        targetEnvItem.address.pathPrefix = pathname;

        // 更新主机信息和路径前缀缓存
        this.updateHostInfo(targetEnvItem.address.url, targetEnvItem.address.pathPrefix, envIndex);

        return item;
      });
    },

    // 解析URL的辅助方法
    parseUrl(url) {
      const urlObj = new URL(url);
      return {
        protocol: urlObj.protocol.replace(':', ''),
        hostname: urlObj.hostname,
        port: urlObj.port,
        pathname: urlObj.pathname,
      };
    },

    // 更新主机信息的辅助方法
    updateHostInfo(hostname, pathname, envIndex) {
      this.hostInfo.hostName = hostname;
      this.hostInfo.pathName = pathname;
      this.curPathPrefix[envIndex] = pathname;
    },

    // 清理编辑状态字段的辅助方法
    clearEditFields(envItem) {
      const fieldsToDelete = ['editProtocol', 'isDropdownShow', 'originalUrl'];
      fieldsToDelete.forEach((field) => {
        if (envItem.hasOwnProperty(field)) {
          delete envItem[field];
        }
      });
    },

    // 获取展示用的应用根域名，优先使用非保留的，如果没有，则选择第一个
    getAppRootDomain(clusterConf = {}) {
      const domains = clusterConf?.ingress_config?.app_root_domains || [];
      if (domains.length === 0) {
        return '';
      }

      for (const domain of domains) {
        if (!domain.reversed) {
          return domain.name;
        }
      }
      return domains[0].name;
    },

    handleUrlOpen(url) {
      window.open(url, '_blank');
    },

    // 表格鼠标移入
    handleRowMouseEnter(index) {
      this.rowIndex = index;
    },

    // 表格鼠标移出
    handleRowMouseLeave() {
      this.rowIndex = '';
    },

    ipCopy() {
      const ioncEl = document.querySelector('.ip-icon-customize-cls');
      ioncEl.addEventListener('click', this.handleCopyIp);
    },

    handleCopyIp() {
      copy(this.defaultIp, this);
    },

    // 路径change，保存当前值用于校验使用
    handlePathChange(val, i) {
      this.curPathPrefix[i] = val;
      this.curInputIndex = i;
    },

    // 协议选择变更
    handleProtocolChange(protocol, e) {
      this.$set(e, 'editProtocol', protocol);
      this.$set(e, 'isDropdownShow', false);
    },

    // 获取https协议提示配置
    getProtocolTipConfig(e) {
      return {
        width: '570',
        theme: 'protocol-alert',
        placements: ['bottom-start'],
        allowHtml: true,
        content: this.$t('提示信息'),
        showOnInit: true,
        html: `<div class="tooltips-content flex-row">
          <i class="paasng-icon paasng-remind mt-4 mr-8"></i>
          <div class="tips-content f12">
            <span>
              ${this.$t('开发者中心目前不支持托管自定义访问地址的 HTTPS 证书，请确保已经在外部网关中配置好证书。')}
            </span>
            <a target="_blank" href="${this.GLOBAL.DOC.HTTPS_CONFIG_GUIDE}">${this.$t('配置说明')}</a>
          </div>
        </div>`,
        disabled: (e.editProtocol || 'http') !== 'https',
      };
    },
  },
};
</script>

<style lang="scss" scoped>
.toggle-type {
  position: absolute;
  right: 20px;
  top: 11px;
}

.root-domains-row {
  display: flex;
  justify-content: space-between;
}

.root-domains-wrapper {
  display: flex;
  .root-domain:nth-child(n + 2) {
    margin-left: 20px;
  }
}

.action-box {
  line-height: 40px;
  margin-right: 20px;
}

.root-url {
  font-size: 13px;
}

.td-focus {
  border: 1px solid #3a84ff;
  transition: all 0.1s;
  transform: translateY(-1px);
}
.td-title {
  width: 180px;
  text-align: center;
  padding: 0;
}

.table-title {
  font-size: 12px;
  color: #63656e;
  padding-bottom: 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  &.cloud-cls {
    background: #f5f7fa;
  }

  .ip-tips {
    white-space: nowrap;
    cursor: pointer;
    font-size: 12px;
    color: #63656e;
    i {
      transform: translateY(0px);
      font-size: 14px;
      color: #979ba5;
    }
    &.ip-app-tips {
      i {
        color: #3a84ff;
      }
    }
    &.ip-cloud-tips {
      background: #ffffff;
      box-shadow: 0 2px 4px 0 #1919290d;
      border-radius: 2px;
      padding: 4px 8px;
    }
  }
}

.table-cls {
  /deep/ td.is-last {
    border-right: none;
  }

  /deep/ th.is-last {
    border-right: none;
  }

  /deep/ .cell {
    overflow: visible;
    display: flex;
    flex-flow: column;
    align-items: flex-start;
  }

  .module-container {
    position: relative;
    height: 46px;
    display: flex;
    flex-flow: column;
    justify-content: center;
    .module-default {
      height: 22px;
      width: 38px;
      &.en {
        width: 81px;
      }
    }
    .module-cursor {
      cursor: pointer;
    }
    .set-module-btn {
      position: absolute;
      bottom: -7px;
      white-space: nowrap;
    }
  }

  .cell-container-width {
    width: 159px;
  }

  .cell-container {
    width: 100%;
    position: relative;
  }
  .env-container {
    font-size: 12px;
  }

  .text-container {
    position: relative;
    display: flex;
    align-items: center;
  }
  .btn-container {
    position: absolute;
    left: 80px;
    color: #3a84ff;
    cursor: pointer;
    width: 50px;
    .disable-add-icon {
      color: #dcdee5;
    }
    &.en {
      left: 100px;
    }
  }

  .line {
    height: 1px;
    background: #dfe0e5;
    width: calc(100% + 30px);
    position: absolute;
    top: 100%;
    left: -15px;
    z-index: 1;
    &.show-last-line {
      top: calc(100% - 0.5%);
    }
  }

  .custom-line-column .cell .cell-container:last-child {
    .url-container:last-child {
      .line {
        display: none;
        &.show-last-line {
          display: block;
        }
      }
    }
  }

  .url-container {
    position: relative;
    height: 46px;
    line-height: 46px;
    width: 100%;
    .module-market {
      width: 88px;
      height: 22px;
      font-size: 12px;
      color: #14a568;
      text-align: center;
      line-height: 20px;
      background: #e4faf0;
      border: 1px solid #14a5684d;
      border-radius: 11px;
    }
    .address-btn-cls {
      height: 46px !important;
    }
    .custom-image {
      height: 22px;
    }
  }
}

.url-input-cls {
  /deep/ .bk-form-input {
    width: 380px;
  }
  @media (max-width: 1366px) {
    /deep/ .bk-form-input {
      width: 280px;
    }
  }
}
.path-input-cls {
  /deep/ .bk-form-input {
    width: 100px;
  }
}

.port-config {
  overflow-x: auto;
}

/deep/ .bk-table-body-wrapper .table-colum-cls :nth-child(even) {
  padding: 0;
  z-index: 1;
}

/deep/ .bk-table-body-wrapper .hover-row .table-colum-cls :nth-child(even) {
  padding: 0;
  background: #f5f7fa;
  z-index: 1;
}

/deep/ .bk-table-body-wrapper .table-colum-cls .cell-container:nth-child(2) {
  border-top: 1px solid #dfe0e5;
}
/deep/ .bk-table-body-wrapper .table-colum-cls .cell {
  padding: 0 !important;
}

/deep/ .bk-table-body-wrapper .table-colum-cls.table-colum-stag-cls .cell {
  div {
    width: 100%;
    .stag-line {
      height: 1px;
      background: #dfe0e5;
      position: absolute;
      top: 100%;
      left: 0;
      z-index: 3;
    }
  }
}

/deep/ .bk-table-body-wrapper .table-colum-module-cls {
  background: #fafbfd;
}

.btn-container {
  text-align: center;
}
</style>
<style lang="scss">
.ip-view-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 10px;
}
.ip-icon-customize-cls {
  color: #3a84ff;
  cursor: pointer;
}
/* 组件库table滚动条样式设置为8px */
.app-entry-config-cls .bk-table.table-cls .bk-table-body-wrapper::-webkit-scrollbar {
  height: 8px;
}
/* 自定义 tooltips 样式 */
.tippy-tooltip.protocol-alert-theme {
  color: #4d4f56;
  border-radius: 2px;
  background: #fdeed8;
  border: 1px solid #f59500;
  box-shadow: 0 2px 6px 0 #0000001a;
  &::before {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: -1;
    border-radius: inherit;
    background: inherit;
  }
  .tooltips-content i {
    color: #f59500;
  }
  .tippy-content {
    max-width: unset;
  }
  .tippy-arrow {
    z-index: -2;
    top: -4px;
    width: 11px;
    height: 11px;
    border: 1px solid #f59500;
    box-shadow: inherit;
    background: inherit;
    transform-origin: center center;
    transform: rotate(45deg);
  }
}
</style>
