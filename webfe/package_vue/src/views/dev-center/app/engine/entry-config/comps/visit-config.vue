<template>
  <div class="port-config">
    <div
      class="content"
      style="position: relative;"
    >
      <bk-table
        v-bkloading="{ isLoading: isTableLoading }"
        :data="entryList"
        class="table-cls"
        border
        cell-class-name="table-cell-cls"
      >
        <bk-table-column :label="$t('模块')" :width="200">
          <template slot-scope="{ row, $index }">
            <section
              class="module-container"
              @mouseenter="handleMouseEnter($index)"
              @mouseleave="defaultIndex = ''">
              <div
                style="cursor: pointer;"
                class="flex-row align-items-center"
              >{{ row.name || '--' }}
                <div class="module-default ml10" v-if="row.is_default">{{$t('主模块')}}</div>
              </div>
              <bk-button
                v-if="defaultIndex === $index && !row.is_default" text theme="primary"
                @click="handleSetDefault(row)">
                {{ $t('设为主模块') }}
              </bk-button>
            </section>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('环境')" :width="160">
          <template slot-scope="{ row, $index }">
            <div
              v-for="(item, i) in row.envsData" :key="item"
              :style="{height: `${46 * row.envs[item].length}px`}"
              class="cell-container flex-column justify-content-center"
              @mouseenter="handleEnvMouseEnter($index, i, row, item)"
              @mouseleave="handleEnvMouseLeave">
              <div
                class="env-container"
                :class="i === row.envsData.length - 1 ? 'last-env-container' : ''"
              >
                <div class="text-container">
                  {{ $t(entryEnv[item]) }}
                  <span
                    class="icon-container"
                    v-if="tableIndex === $index && envIndex === i && row.envs[item] && row.envs[item][0].is_running">
                    <i
                      class="paasng-icon paasng-plus-thick add-icon" v-bk-tooltips="$t('添加自定义访问地址')"
                      @click="handleAdd($index, i, row, item)" />
                    <i class="paasng-icon paasng-info-line pl10 info-icon" v-bk-tooltips="configIpTip" />
                  </span>
                </div>
                <div v-if="i !== row.envsData.length - 1" class="line"></div>
              </div>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('访问地址')" :min-width="580">
          <template slot-scope="{ row }">
            <div v-for="(item) in row.envsData" :key="item" class="cell-container">
              <div v-for="(e, i) in row.envs[item]" :key="i" class="url-container flex-column justify-content-center">
                <div v-if="e.isEdit">
                  <bk-form :label-width="0" form-type="inline" :model="e.address" ref="urlInfoForm">
                    <bk-form-item :required="true" :property="'url'" :rules="rules.url">
                      <bk-input v-model="e.address.url" :placeholder="domainInputPlaceholderText" class="url-input-cls">
                        <template slot="prepend">
                          <div class="group-text">http://</div>
                        </template>
                      </bk-input>
                    </bk-form-item>
                    <bk-form-item :required="true" :property="'pathPrefix'" :rules="rules.pathPrefix">
                      <bk-input
                        class="path-input-cls"
                        v-model="e.address.pathPrefix"
                        :placeholder="$t('请输入路径')"></bk-input>
                    </bk-form-item>
                  </bk-form>
                </div>
                <section v-else>
                  <div v-bk-tooltips="{content: $t('该环境未部署，无法访问'), disabled: e.is_running}">
                    <bk-button
                      text theme="primary"
                      :disabled="!e.is_running"
                      @click="handleUrlOpen(e.address.url)"
                    > {{ e.address.url }}</bk-button>
                  </div>
                </section>
                <div class="line"></div>
              </div>
            </div>
          </template>
        </bk-table-column>
        <!-- <bk-table-column :label="$t('进程')" :width="100">
          <template slot-scope="{ row }">
            <div v-for="(item) in row.envsData" :key="item" class="cell-container">
              <div v-for="(e, i) in row.envs[item]" :key="i" class="url-container">
                web
                <div class="line"></div>
              </div>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('类型')" :width="110">
          <template slot-scope="{ row }">
            <div v-for="(item) in row.envsData" :key="item" class="cell-container">
              <div v-for="(e, i) in row.envs[item]" :key="i" class="url-container">
                {{ e.address.type === 'custom' ? $t('自定义') : $t('平台内置')}}
                <div class="line"></div>
              </div>
            </div>
          </template>
        </bk-table-column> -->
        <bk-table-column :label="$t('操作')" :width="130">
          <template slot-scope="{ row, $index }">
            <div v-for="item in row.envsData" :key="item" class="cell-container">
              <div v-for="(e, i) in row.envs[item]" :key="i" class="url-container">
                <div v-if="e.address.type === 'custom'">
                  <section v-if="e.isEdit">
                    <bk-button text theme="primary" @click="handleSubmit($index, i, row, item)">
                      {{ $t('保存') }}
                    </bk-button>
                    <bk-button text theme="primary" class="pl20" @click="handleCancel($index, i, row, item)">
                      {{ $t('取消') }}
                    </bk-button>
                  </section>
                  <section v-else>
                    <bk-button text theme="primary" @click="handleEdit($index, i, row, item)">
                      {{ $t('编辑') }}
                    </bk-button>
                    <bk-button
                      text theme="primary" class="pl20"
                      @click="showRemoveModal(i, row, item)">
                      {{ $t('删除') }}
                    </bk-button>
                  </section>
                </div>
                <div v-else> -- </div>
                <div class="line"></div>
              </div>
            </div>
          </template>
        </bk-table-column>
      </bk-table>
      <!-- <bk-button
        v-if="moduleEntryInfo.type === 1 && canUpdateSubDomain"
        class="toggle-type"
        :text="true"
        theme="primary"
        @click="visitDialog.visiable = true"
      >
        {{ $t('切换为子域名') }}
      </bk-button> -->

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
          <p> {{ $t('注意事项：') }} </p>
          <p> {{ $t('1、应用的主访问路径将会变为子域名方式') }} </p>
          <p> {{ $t('2、如果应用框架代码没有适配过独立域名访问方式，一些静态文件路径可能会出现问题') }} </p>
          <p> {{ $t('3、旧的子路径地址依然有效，可以正常访问') }} </p>
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
          <p> {{ $t('设定后：') }} </p>
          <p>
            1. {{ $t('应用短地址') }}({{ $route.params.id }}{{ getAppRootDomain(curClickAppModule.clusters.prod) }})
            {{ $t('指向到应用') }} {{ domainDialog.moduleName }}
            {{ $t('模块的生产环境') }}
          </p>
          <p>
            2. {{ $t('应用访问限制') }}( {{ accessControlText.join('、') }} ){{ $t('变更为') }}
            {{ $t('对') }} {{ domainDialog.moduleName }} {{ $t('生效') }}
          </p>
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

<script>import appBaseMixin from '@/mixins/app-base-mixin';
import { ENV_ENUM } from '@/common/constants';
export default {
  mixins: [appBaseMixin],
  data() {
    return {
      type: '',
      example: '',
      canUpdateSubDomain: false,
      isLoading: false,
      visitDialog: {
        visiable: false,
        title: this.$t('确认切换为子域名访问地址？'),
      },
      moduleEntryInfo: {
        entrances: [],
        type: 1,
        entrancesTemplate: {},
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
      defaultIndex: '',
      tableIndex: '',
      envIndex: '',
      ipConfigInfo: { frontend_ingress_ip: '' },
      domainConfig: {},
      placeholderText: '',
      rules: {
        url: [
          {
            required: true,
            message: this.$t('域名不能为空'),
            trigger: 'blur',
          },
          {
            validator: (value) => {
              const validDomainsPart = this.domainConfig.valid_domain_suffixes.join('|').replace('.', '\\.');
              // eslint-disable-next-line no-useless-escape
              const domainReg = new RegExp(`^[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})*?(${validDomainsPart})$`);
              return domainReg.test(value);
            },
            message: () => `${this.$t('请输入有效域名，并以这些后缀结尾：')}${this.placeholderText}`,
            trigger: 'blur',
          },
        ],
        pathPrefix: [
          {
            regex: /^\/[a-z-z0-9_-]*\/?$/,
            message: `${this.$t('路径必须以')}"/"${this.$t('开头、且路径只能包含小写字母、数字、下划线(_)和连接符(-)')}`,
            trigger: 'blur',
          },
        ],
      },
      curClickAppModule: { clusters: {} },
      setModuleLoading: false,
      hostInfo: {},
      tipShow: false,
      curDataId: '',
    };
  },
  computed: {
    platformFeature() {
      return this.$store.state.platformFeature;
    },
    configIpTip() {
      return {
        theme: 'light',
        allowHtml: true,
        html: `<div>
          <div>域名解析目标IP</div>
          <div
            class="mt10"
            style="height: 32px;background: #F0F1F5;border-radius: 2px;line-height: 32px; text-align: center;">
            ${this.ipConfigInfo.frontend_ingress_ip}
          </div>
          <div class="mt10 mb10">推荐操作流程: </div>
          <div>1. 首先在“域名管理”添加域名</div>
          <div>2. 修改本机 Hosts 文件，将域名解析到表格中的 IP </div>
          <div>3. 打开浏览器，测试访问是否正常 </div>
          <div>4. 修改域名解析记录，将其永久解析到目标 IP </div>
          </div>`,
        placements: ['bottom'],
        onHidden: () => {
          this.tipShow = false;
          this.tableIndex = '';
          this.envIndex = '';
        },
        onShown: () => {
          this.tipShow = true;
        },
      };
    },
    // 域名规则placeholder
    domainInputPlaceholderText() {
      if (this.domainConfig?.valid_domain_suffixes?.length) {
        this.placeholderText = this.domainConfig.valid_domain_suffixes.join(',');
        return this.$t('请输入有效域名，并以这些后缀结尾：') + this.placeholderText;
      }
      return this.$t('请输入有效域名');
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
    '$route'() {
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
      this.getAppRegion();    // 环境信息
      this.getEntryList();    // 列表信息
      // this.getDefaultDomainInfo();
      this.loadDomainConfig();    // 域名信息
    },

    // 获取域名信息
    async getAppRegion() {
      this.canUpdateSubDomain = false;
      try {
        const { region } = this.curAppInfo.application;
        const res = await this.$store.dispatch('getAppRegion', region);
        this.domainConfig = res.module_custom_domain;
        this.canUpdateSubDomain = res.entrance_config.manually_upgrade_to_subdomain_allowed;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message || e.detail || this.$t('接口异常'),
        });
      } finally {
        this.$emit('data-ready', 'visit-config');
      }
    },

    // 访问地址列表数据
    async getEntryList() {
      try {
        this.isTableLoading = true;
        const res = await this.$store.dispatch('entryConfig/getEntryDataList', {
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
          message: e.message || e.detail || this.$t('接口异常'),
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
          message: e.message || e.detail || this.$t('接口异常'),
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
          message: e.message || e.detail || this.$t('接口异常'),
        });
      }
    },

    // async updateRootDomain() {
    //   try {
    //     await this.$store.dispatch('entryConfig/updateRootDomain', {
    //       appCode: this.appCode,
    //       moduleId: this.curModuleId,
    //       data: {
    //         preferred_root_domain: this.rootDomainDefault,
    //       },
    //     });
    //     this.$paasMessage({
    //       theme: 'success',
    //       message: this.$t('修改成功'),
    //     });
    //   } catch (e) {
    //     this.$paasMessage({
    //       theme: 'error',
    //       message: e.message || e.detail || this.$t('接口异常'),
    //     });
    //   } finally {
    //     this.isEdited = false;
    //     this.domainDialog.visiable = false;
    //     this.getDefaultDomainInfo();
    //   }
    // },

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
        this.getEntryList();    // 重新请求数据
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.message,
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
            e.envs[envType][envIndex].isEdit = false;
            e.envs[envType][envIndex].address.url = `http://${this.hostInfo.hostName}${this.hostInfo.pathName}`; // 拼接地址和路径
          }
          return e;
        });
      } else {
        payload.envs[envType].splice(envIndex, 1);
      }
    },

    // 处理鼠标移入事件
    handleMouseEnter(index) {
      this.defaultIndex = index;
    },

    // 环境鼠标移入事件
    handleEnvMouseEnter(index, envIndex, payload, env) {
      this.tableIndex = index;
      this.envIndex = envIndex;
      this.ipConfigInfo = (this.curIngressIpConfigs || [])
        .find(e => e.environment === env && e.module === payload.name)
      || { frontend_ingress_ip: '暂无ip地址信息' };   // ip地址信息
    },

    // 环境鼠标移出事件
    handleEnvMouseLeave() {
    },

    // 设置为主模块
    handleSetDefault(payload) {
      this.curClickAppModule = this.curAppModuleList.find(e => e.name === payload.name) || {}; // 当前点击的模块的所有信息
      this.domainDialog.visiable = true;
      this.domainDialog.moduleName = payload.name;
      this.domainDialog.title = this.$t(`是否设定${payload.name}模块为主模块`);
    },

    // tips数据
    loadDomainConfig() {
      this.$http.get(`${BACKEND_URL}/api/bkapps/applications/${this.appCode}/custom_domains/config/`).then(
        (res) => {
          this.curIngressIpConfigs = res;
        },
        (res) => {
          this.$paasMessage({
            theme: 'error',
            message: `${this.$t('无法获取域名解析目标IP，错误：')}${res.detail}`,
          });
        },
      );
    },

    // 新增一条数据
    handleAdd(index, envIndex, payload, envType) {
      this.entryList = this.entryList.map((e, i) => {
        if (index === i) {
          e.envs[envType].push({
            isEdit: true,
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
      // 需要过滤查看状态的数据才能获取到需要校验输入框的下标
      const readDataLength =  (payload?.envs[envType] || [])
        .filter((e, readIndex) => !e.isEdit && readIndex <= envIndex).length;
      const validateFromIndex = envIndex - readDataLength;    // 当前点击保存的输入框下标
      await this.$refs.urlInfoForm[validateFromIndex].validate();   // 校验
      const curUrlParams = {
        environment_name: envType,
        domain_name: payload.envs[envType][envIndex].address.url,
        path_prefix: payload.envs[envType][envIndex].address.pathPrefix,
        module_name: payload.name,
        id: payload.envs[envType][envIndex].address.id || '',
      };
      try {
        const params = {
          data: curUrlParams,
          appCode: this.appCode,
        };
        let fetchUrl = 'entryConfig/addDomainInfo';
        if (curUrlParams.id) {
          fetchUrl = 'entryConfig/updateDomainInfo';
        }
        const res = await this.$store.dispatch(fetchUrl, params);
        // 当前保存的这条数据返回的id
        this.curDataId = res.id;
        this.$paasMessage({
          theme: 'success',
          message: `${curUrlParams.id ? this.$t('更新') : this.$t('添加')}${this.$t('成功')}`,
        });
        this.entryList = this.entryList.map((e, i) => {
          if (index === i) {
            e.envs[envType][envIndex].isEdit = false;       // 改变本条数据的状态
            e.envs[envType][envIndex].is_running = true;    // 能保存和编辑这代表已经部署过了
            e.envs[envType][envIndex].address.url = `http://${curUrlParams.domain_name}${curUrlParams.path_prefix}`; // 拼接地址和路径
          }
          return e;
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message || e.detail || this.$t('接口异常'),
        });
      }
    },

    // 删除域名弹窗
    showRemoveModal(envIndex, payload, envType) {
      this.$bkInfo({
        title: `${this.$t('确定要删除该域名')}?`,
        maskClose: true,
        confirmFn: () => {
          this.handleDelete(envIndex, payload, envType);
        },
      });
    },

    // 处理删除域名
    async handleDelete(envIndex, payload, envType) {
      try {
        await this.$store.dispatch(
          'entryConfig/deleteDomainInfo',
          { appCode: this.appCode, id: payload.envs[envType][envIndex].address.id || this.curDataId },
        );
        this.getEntryList();    // 重新请求数据
        this.$paasMessage({
          theme: 'success',
          message: `${this.$t('删除成功')}`,
        });
      } catch (error) {
        const errorMsg = error.message;

        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('删除失败')},${errorMsg}`,
        });
      }
    },

    // 编辑
    handleEdit(index, envIndex, payload, envType) {
      this.entryList = this.entryList.map((e, i) => {
        if (index === i) {
          e.envs[envType][envIndex].isEdit = true;
          const u = e.envs[envType][envIndex].address.url ? new URL(e.envs[envType][envIndex].address.url) : '';   // 格式化地址
          e.envs[envType][envIndex].address.url = u.hostname;
          e.envs[envType][envIndex].address.pathPrefix = u.pathname;
          this.hostInfo.hostName = u.hostname;
          this.hostInfo.pathName = u.pathname;
        }
        return e;
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
        transition: all .1s;
        transform: translateY(-1px);
    }
    .td-title {
        width: 180px;
        text-align: center;
        padding: 0;
    }

    .table-cls {
      /deep/ .cell{
        overflow:visible;
        display: flex;
        flex-flow: column;
        align-items: flex-start;
      }

      .module-container{
        height: 46px;
        display: flex;
        flex-flow: column;
        justify-content: center;
        .module-default{
          height: 22px;
          font-size: 12px;
          color: #3A84FF;
          line-height: 20px;
          background: #EDF4FF;
          border: 1px solid #3a84ff4d;
          border-radius: 11px;
          text-align: center;
          padding: 0 5px;
        }
      }

      .cell-container{
        width: 100%;
        position: relative;
      }
      .env-container{
        background: #D8F4F5;
        color: #45A0A5;
        padding: 5px;
        width: 76px;
        font-size: 12px;
        margin: 10px 0px;
        text-align: center;
        border-radius: 2px;
      }

      .last-env-container{
        color: #E68D00;
        background: #FFF2C9;
        margin-bottom: 10px;
        margin-top: 10px;
      }

      .text-container{
        position: relative;
      }
      .icon-container{
        position: absolute;
        left: 80px;
        display: flex;
        align-items: center;
        top: 4px;
        color: #989ca6;
        cursor: pointer;
        .add-icon{
          font-size: 14px;
          &:hover {
            color: #3A84FF;
          }
        }
      }

      .line{
        height: 1px;
        background: #dfe0e5;
        width: calc(100% + 30px);
        position: absolute;
        top: 100%;
        left: -15px;
      }

      .url-container{
        position: relative;
        height: 46px;
        line-height: 46px;
        width: 100%;
        .module-market{
          width: 88px;
          height: 22px;
          font-size: 12px;
          color: #14A568;
          text-align: center;
          line-height: 20px;
          background: #E4FAF0;
          border: 1px solid #14a5684d;
          border-radius: 11px;
        }
      }
    }

    .url-input-cls{
      /deep/ .bk-form-input{
        width: 350px;
      }
    }
    .path-input-cls{
      /deep/ .bk-form-input{
        width: 120px;
      }
    }

    .port-config{
      width: calc(100vw - 290px);
      overflow-x: auto;
    }
</style>
