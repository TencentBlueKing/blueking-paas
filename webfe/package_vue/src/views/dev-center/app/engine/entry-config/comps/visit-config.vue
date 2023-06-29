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
        <bk-table-column :label="$t('模块')">
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
        <bk-table-column :label="$t('环境')" :min-width="150">
          <template slot-scope="{ row, $index }">
            <div
              v-for="(item, i) in row.envsData" :key="item"
              :style="{height: `${46 * row.envs[item].length}px`}"
              class="cell-container flex-column justify-content-center"
              @mouseenter="handleEnvMouseEnter($index, i, row, item)">
              <div
                class="env-container"
                :class="i === row.envsData.length - 1 ? 'last-env-container' : ''"
              >
                <div class="text-container">
                  {{ entryEnv[item] }}
                  <span class="icon-container" v-if="tableIndex === $index && envIndex === i">
                    <i
                      class="paasng-icon paasng-plus-thick add-icon" v-bk-tooltips="'添加自定义访问地址'"
                      @click="handleAdd($index, i, row, item)" />
                    <i class="paasng-icon paasng-info-line pl10 info-icon" v-bk-tooltips="configIpTip" />
                  </span>
                </div>
                <div v-if="i !== row.envsData.length - 1" class="line"></div>
              </div>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('访问地址')" :width="600">
          <template slot-scope="{ row }">
            <div v-for="(item) in row.envsData" :key="item" class="cell-container">
              <div v-for="(e, i) in row.envs[item]" :key="i" class="url-container flex-column justify-content-center">
                <div v-if="e.isEdit">
                  <bk-input v-model="e.address.url" :placeholder="domainInputPlaceholderText">
                    <template slot="prepend">
                      <div class="group-text">http://</div>
                    </template>
                    <template slot="append">
                      <bk-input
                        class="append-input-cls"
                        v-model="e.address.pathPrefix"
                        :placeholder="$t('请输入路径')"></bk-input>
                    </template>
                  </bk-input>
                </div>
                <section v-else class="flex-row align-items-center">
                  <a
                    :href="e.address.url"
                    target="blank"
                  > {{ e.address.url}}</a>
                  <div class="module-market ml10" v-if="row.is_market">{{$t('应用市场地址')}}</div>
                </section>
                <div class="line"></div>
              </div>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('进程')" :width="100">
          <template slot-scope="{ row }">
            <div v-for="(item) in row.envsData" :key="item" class="cell-container">
              <div v-for="(e, i) in row.envs[item]" :key="i" class="url-container">
                web
                <div class="line"></div>
              </div>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('类型')">
          <template slot-scope="{ row }">
            <div v-for="(item) in row.envsData" :key="item" class="cell-container">
              <div v-for="(e, i) in row.envs[item]" :key="i" class="url-container">
                {{ e.address.type === 'custom' ? $t('自定义') : $t('平台内置')}}
                <div class="line"></div>
              </div>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('操作')" :width="130">
          <template slot-scope="{ row, $index }">
            <div v-for="item in row.envsData" :key="item" class="cell-container">
              <div v-for="(e, i) in row.envs[item]" :key="i" class="url-container">
                <div v-if="e.address.type === 'custom'">
                  <section v-if="e.isEdit">
                    <bk-button text theme="primary" @click="handleSubmit(i, row, item)">
                      {{ $t('保存') }}
                    </bk-button>
                    <bk-button text theme="primary" class="pl20" @click="handleCancel">
                      {{ $t('取消') }}
                    </bk-button>
                  </section>
                  <section v-else>
                    <bk-button text theme="primary" @click="handleEdit($index, i, row, item)">
                      {{ $t('编辑') }}
                    </bk-button>
                    <bk-button
                      text theme="primary" class="pl20"
                      :disabled="row.is_market"
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
        :value="domainDialog.visiable"
        :title="domainDialog.title"
        :theme="'primary'"
        :header-position="'left'"
        :mask-close="false"
        @confirm="updateRootDomain"
        @cancel="domainDialog.visiable = false"
      >
        <div class="tl">
          <p> {{ $t('设定后：') }} </p>
          <p>{{ $t('应用短地址：（http://apps.example.com/appid/）') }}
            {{ $t('指向') }} {{ domainDialog.moduleName }}{{ $t('模块的') }}{{ entryEnv[domainDialog.env] }}</p>
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
      isEdited: false,
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
        content: this.$t('提示信息'),
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
      };
    },

    domainInputPlaceholderText() {
      if (this.domainConfig.valid_domain_suffixes.length) {
        this.placeholderText = this.domainConfig.valid_domain_suffixes.join(',');
        return this.$t('请输入有效域名，并以这些后缀结尾：') + this.placeholderText;
      }
      return this.$t('请输入有效域名');
    },
  },
  watch: {
    '$route'() {
      this.init();
    },
  },
  created() {
    this.init();
  },
  methods: {
    /**
     * 数据初始化入口
     */
    init() {
      this.getAppRegion();
      this.getEntryList();
      this.getDefaultDomainInfo();
      this.loadDomainConfig();
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

    async getEntryList() {
      try {
        this.isTableLoading = true;
        const res = await this.$store.dispatch('entryConfig/getEntryDataList', {
          appCode: this.appCode,
        });
        this.entryList = res;
        this.entryList = res.map((e) => {
          e.envsData = Object.keys(e.envs);
          return e;
        }, []);

        console.log('this.entryList', this.entryList);
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

    async updateRootDomain() {
      try {
        await this.$store.dispatch('entryConfig/updateRootDomain', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          data: {
            preferred_root_domain: this.rootDomainDefault,
          },
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('修改成功'),
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message || e.detail || this.$t('接口异常'),
        });
      } finally {
        this.isEdited = false;
        this.domainDialog.visiable = false;
        this.getDefaultDomainInfo();
      }
    },

    showEdit() {
      this.isEdited = true;
    },

    // 取消
    handleCancel() {
      this.getEntryList();    // 重新请求数据
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
        .find(e => e.environment === env && e.module === payload.moduleName)
      || { frontend_ingress_ip: '暂无ip地址信息' };   // ip地址信息
    },

    // 设置为主模块
    handleSetDefault(payload) {
      this.domainDialog.visiable = true;
      this.domainDialog.moduleName = payload.moduleName;
      this.domainDialog.env = payload?.envsData[0];   // 默认取第一个环境
      this.domainDialog.title = this.$t(`是否设定${payload.moduleName}模块为主模块`);
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

    // 保存
    async handleSubmit(envIndex, payload, envType) {
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
        await this.$store.dispatch(fetchUrl, params);
        this.$paasMessage({
          theme: 'success',
          message: `${curUrlParams.id ? this.$t('更新') : this.$t('添加')}${this.$t('成功')}`,
        });
        this.getEntryList();    // 重新请求数据
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
        await this.$store.dispatch('entryConfig/deleteDomainInfo', { appCode: this.appCode, id: payload.envs[envType][envIndex].address.id });
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
          // e.envs[envType][envIndex].address.url =
        }
        return e;
      });
      console.log('this.entryList', this.entryList);
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
          width: 52px;
          height: 22px;
          font-size: 12px;
          color: #3A84FF;
          line-height: 20px;
          background: #EDF4FF;
          border: 1px solid #3a84ff4d;
          border-radius: 11px;
          text-align: center;
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

    .append-input-cls{
      /deep/ .bk-form-input{
        border: none;
        border-bottom: 1px solid #c4c6cc;
        height: 31px;
        width: 130px;
      }
    }
</style>
