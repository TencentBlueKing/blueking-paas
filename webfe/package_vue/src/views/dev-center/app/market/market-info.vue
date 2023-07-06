<template>
  <section v-show="!isDataLoading">
    <div class="ps-action-header mark-info">
      <div class="release-info flex-row align-items-center">
        <strong class="release-info-title">{{ $t('发布状态') }}</strong>
        <div class="release-info-status">{{ appMarketConfig.enabled ? $t('已发布') : $t('未发布') }}</div>
        <bk-switcher
          v-model="appMarketConfig.enabled"
          :disabled="isDisabled"
          @change="handlerSwitch"
        />
        <bk-alert v-if="fillInfo" type="warning" class="release-info-alert" :title="$t(fillInfo.message)"></bk-alert>
        <bk-alert v-else-if="deployInfo" type="error" class="release-info-alert">
          <div slot="title">
            {{ $t(deployInfo.message) }}
            <bk-button
              theme="primary"
              class="pl10"
              text
              @click.native.stop
              @click="handleEditCondition(deployInfo)"
            >
              {{ $t('去部署生产环境') }}
            </bk-button>
          </div>
        </bk-alert>
        <bk-alert
          v-else-if="confirmRequiredWhenPublish && !appMarketConfig.enabled && !isSureRisk"
          class="release-info-alert" type="error">
          <div slot="title">
            <p>
              {{ $t('无法发布到应用市场') }}
              {{ $t('当前应用主模块创建时未使用蓝鲸开发框架初始化') }}
              <section
                class="visit-link"
                @click="viewRisk"
              >
                {{ $t('查看风险并跳过') }}
              </section>
            </p>
          </div>
        </bk-alert>
        <bk-alert v-else-if="appMarketConfig.enabled" class="release-info-alert" type="success">
          <div slot="title">
            <p>
              {{ $t('应用已成功发布到蓝鲸应用市场') }}
              <section
                v-if="marketAddress"
                class="visit-link"
                @click="visitAppMarket"
              >
                {{ $t('立即访问') }}
              </section>
            </p>
          </div>
        </bk-alert>
      </div>
    </div>

    <template v-if="engineAbled">
      <div
        v-if="!confirmRequiredWhenPublish || isSureRisk || appMarketConfig.enabled"
        class="address-info mt15 flex-row align-items-center">
        <strong class="address-info-title">{{ $t('访问地址') }}</strong>
        <!-- 编辑态 -->
        <div class="address-info-url" v-if="isEditAddress">
          <div class="flex-row align-items-center">
            <bk-select
              v-model="curModule"
              class="module-select-cls"
              :clearable="false"
            >
              <bk-option
                v-for="item in moduleList"
                :id="item"
                :key="item"
                :name="item"
              />
            </bk-select>
            <bk-select
              v-model="curAddress"
              style="width: 360px;"
              :clearable="false"
            >
              <bk-option-group
                v-for="(group, index) in addressList"
                :name="group.name"
                :key="index">
                <bk-option
                  v-for="option in group.children"
                  :key="option.address.url"
                  :id="option.address.url"
                  :name="option.address.url">
                </bk-option>
              </bk-option-group>
            </bk-select>
          </div>
        </div>
        <!-- 查看态 -->
        <div class="address-info-url" v-if="avaliableAddress[0] && !isEditAddress">
          {{ avaliableAddress[0].address }}
        </div>
        <bk-button
          class="address-info-btn"
          theme="primary"
          text
          @click="handlerAddress"
        >
          {{ isEditAddress ? $t( '确定') : $t( '编辑') }}
        </bk-button>
        <bk-button
          v-if="isEditAddress"
          class="pl10"
          theme="primary"
          text
          @click="isEditAddress = false3"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
    </template>
    <template v-else>
      <bk-form
        ref="visitInfoForm"
        :key="appMarketConfig.source_url_type"
        :label-width="130"
        :class="['pt10 pb10', { 'flash': isVisitFormFocus }]"
        style="position: relative; margin-top: -10px;"
        :model="appMarketConfig"
      >
        <bk-form-item
          v-if="curAppInfo.web_config.engine_enabled"
          :label="$t('访问地址类型：')"
        >
          <bk-radio
            :value="3"
            style="margin-top: 7px;"
            checked
            disabled
          >
            {{ $t('第三方') }}
          </bk-radio>
        </bk-form-item>

        <bk-form-item
          v-if="appMarketConfig.source_url_type === 3"
          :label="$t('访问地址：')"
          :required="true"
          :property="'source_tp_url'"
          :rules="visitInfoRules.sourceUrl"
        >
          <bk-input
            ref="urlInput"
            v-model="appMarketConfig.source_tp_url"
            :placeholder="`${$t('请输入第三方地址，例如')}: http://example.com)`"
          />
          <p class="tip mt10">
            {{ $t('用户从桌面打开应用时的访问地址') }}
          </p>
        </bk-form-item>

        <bk-form-item>
          <bk-button
            v-show="!engineAbled"
            theme="primary"
            class="mr10 mt5"
            :title="$t('保存')"
            :loading="isConfigSaving"
            @click.stop.prevent="submitVisitInfo"
          >
            {{ $t('保存') }}
          </bk-button>
        </bk-form-item>
      </bk-form>
    </template>

    <bk-dialog
      v-model="viewRiskDialog.visiable"
      theme="primary"
      :mask-close="false"
      :header-position="'center'"
      :width="viewRiskDialog.width"
      :title="$t('确认风险')"
      @after-leave="afterDialogClose"
    >
      <div>
        <p style="margin-bottom: 10px;">
          {{ $t('为了提升开发效率和应用的安全性，蓝鲸开发框架为应用提供了一套完整的用户鉴权体系。') }}
        </p>
        <p style="margin-bottom: 10px;">
          {{ $t('由于当前应用主模块') }} <span style="font-weight: bold;">({{ curModuleId }})</span>
          {{ $t('没有使用蓝鲸开发框架进行初始化，我们无法确认应用是否已经正常接入用户认证与鉴权。') }}
        </p>
        <p> {{ $t('你仍然可以继续将应用上线到蓝鲸市场，不过你需要确保应用已经自行接入安全的鉴权体系。') }} </p>
        <p style="margin-top: 10px;">
          <bk-checkbox
            v-model="riskChecked"
            :true-value="true"
            :false-value="false"
          >
            {{ $t('我确认模块已经接入了安全的用户鉴权体系') }}
          </bk-checkbox>
        </p>
      </div>
      <div slot="footer">
        <bk-button
          theme="primary"
          :disabled="!riskChecked"
          @click="goOn"
        >
          {{ $t('继续') }}
        </bk-button>
        <bk-button
          style="margin-left: 6px;"
          @click="viewRiskDialog.visiable = false"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="switchAddressDialog.visiable"
      width="540"
      header-position="left"
      :title="$t('确认更改访问地址？')"
      :theme="'primary'"
      :mask-close="false"
      @after-leave="afterAddressDialogClose"
    >
      <div>
        <p>{{ $t('请确认将访问地址更改为：') + curAddress }}</p>
      </div>
      <div slot="footer">
        <bk-button
          theme="primary"
          :loading="switchAddressDialog.loading"
          @click="sureSwitchAddress"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          theme="default"
          @click="switchAddressDialog.visiable = false"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
    </bk-dialog>
  </section>
</template>

<script>import appBaseMixin from '@/mixins/app-base-mixin.js';
import { bus } from '@/common/bus';

export default {
  mixins: [appBaseMixin],
  data() {
    return {
      isDataLoading: true,
      isConfigSaving: false,
      isInfoSaving: false,
      active: 'visitInfo',
      engineAbled: false,
      isVisitFormFocus: false,
      appStatus: '',
      appMarketConfig: {
        enabled: false,
        source_module_id: '',
        source_tp_url: '',
        source_url_type: 2,
      },
      appPreparations: {
        all_conditions_matched: false,
        failed_conditions: [],
      },
      visitInfoRules: {
        sourceUrl: [
          {
            required: true,
            message: this.$t('请输入第三方地址'),
            trigger: 'blur',
          },
          {
            regex: /(http|https):\/\/[\w\-_]+(\.[\w\-_]+)+([\w\-\.,@?^=%&:/~\+#]*[\w\-\@?^=%&/~\+#])?/,
            message: this.$t('请输入正确的URL地址'),
            trigger: 'blur',
          },
        ],
      },
      viewRiskDialog: {
        visiable: false,
        width: 700,
      },
      riskChecked: false,
      isSureRisk: false,
      typeMap: {
        1: this.$t('未开启'),
        2: this.$t('与主模块生产环境一致'),
        3: this.$t('第三方'),
        4: this.$t('主模块生产环境独立域名：'),
        5: this.$t('与主模块生产环境一致，并启用 HTTPS'),
      },
      avaliableAddress: [],
      avaliableAddressValue: 2,
      avaliableAddressValueBackup: null,
      switchAddressDialog: {
        visiable: false,
        loading: false,
      },
      currentAddress: {},
      visitTabLoading: false,
      infoTabLoading: false,
      marketAddress: null,
      isEditAddress: false,
      addressData: [],
      curAddress: '',
      curModule: '',
      moduleList: [],
    };
  },
  computed: {
    // 是否设置第三方地址
    urlHasConfig() {
      return (this.appMarketConfig.source_url_type === 3) && this.appMarketConfig.source_tp_url;
    },

    // 是否无法发布到应用市场
    canUserMarket() {
      // 没有设置第三方
      // 应用下架
      // 应用没部署到正式环境
      // 应用信息不完整
      return this.urlHasConfig && this.appStatus !== 'reg' && this.appStatus !== 'deploy' && this.appStatus !== 'offlined';
    },
    isDisabled() {
      return !this.appPreparations.all_conditions_matched
      || (this.confirmRequiredWhenPublish && !this.isSureRisk && !this.appMarketConfig.enabled);
    },
    curAppInfo() {
      return this.$store.state.curAppInfo;
    },
    isCloudApp() {
      return this.curAppInfo.application.type === 'cloud_native';
    },
    fillInfo() {  // 未完善基本信息
      return this.appPreparations.failed_conditions.find(e => e.action_name === 'fill_product_info');
    },
    deployInfo() { // 未部署
      return this.appPreparations.failed_conditions.find(e => e.action_name === 'deploy_prod_env');
    },
    // 选择的模块对应的访问地址数据不同
    addressList() {
      if (!this.curModule) return;
      // 自定义数据
      const customData = {
        id: 1,
        name: '自定义地址',
        children: [],
      };
      // 平台内置数据
      const platformData = {
        id: 2,
        name: '平台内置地址',
        children: [],
      };
      const curAddressData = this.addressData.find(e => e.name === this.curModule) || {};
      const list = (Object.keys(curAddressData?.envs) || []).reduce((p, v) => {
        const curAddressItemData = curAddressData.envs[v];
        curAddressItemData.forEach((item) => {
          // 只需要要prod环境中运行中的地址
          if (item.env === 'prod' && item.is_running) {
            if (item.address.type === 'custom') {
              p.customData.children.push(item);
            } else {
              p.platformData.children.push(item);
            }
          }
        });
        return p;
      }, { customData, platformData });
      console.log('list', list);
      return list;
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
     * 初始化入口
     */
    async init() {
      this.initMarketConfig();
      this.checkAppPrepare();
      this.getEntryList();
      this.engineAbled = this.curAppInfo.web_config.engine_enabled;

      if (this.engineAbled) {
        await this.fetchAvaliableAddress();
      }
    },

    visitAppMarket() {
      window.open(this.marketAddress);
    },

    async fetchAvaliableAddress() {
      try {
        const res = await this.$store.dispatch('market/getAppMarketAvaliableAddress', this.appCode)
                    ;(res || []).forEach((item) => {
          if (item.type === 2 || item.type === 5) {
            this.$set(item, 'value', item.type);
          } else {
            this.$set(item, 'value', item.address);
          }
        });
        this.avaliableAddress = [...res];
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message,
        });
      }
    },

    afterAddressDialogClose() {
      this.currentAddress = {};
    },

    async sureSwitchAddress() {
      this.switchAddressDialog.loading = true;
      try {
        await this.$store.dispatch('market/updateAppMarketAvaliableAddress', {
          source_url_type: this.currentAddress.type,
          source_tp_url: '',
          custom_domain_url: this.currentAddress.type === 2 ? '' : this.currentAddress.address,
          appCode: this.appCode,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('访问地址更改成功'),
        });
        this.avaliableAddressValueBackup = this.currentAddress.value;
        this.switchAddressDialog.visiable = false;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message,
        });
      } finally {
        this.switchAddressDialog.loading = false;
      }
    },

    /**
     * 查看风险
     */
    viewRisk() {
      this.viewRiskDialog.visiable = true;
    },

    afterDialogClose() {
      this.riskChecked = false;
    },

    goOn() {
      this.isSureRisk = true;
      this.viewRiskDialog.visiable = false;
    },

    /**
     * 检查应用发布的准备条件
     */
    async checkAppPrepare() {
      try {
        const res = await this.$store.dispatch('market/getAppMarketPrepare', this.appCode);
        this.appPreparations = res;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message,
        });
      }
    },

    /**
     * 完善发布条件
     * @param {Object} condition 条件对象
     */
    handleEditCondition(condition) {
      switch (condition.action_name) {
        // 完善第三方地址
        case 'fill_thirdparty_url':
          this.$refs.urlInput.focus();
          break;

          // 未完善应用基本信息
        case 'fill_product_info':
          break;

          // 应用未在生产环境成功部署
        case 'deploy_prod_env':
          // eslint-disable-next-line no-case-declarations
          const name = this.isCloudApp ? 'cloudAppDeployForProcess' : 'appDeployForProd';
          this.$router.push({
            name,
            params: {
              id: this.appCode,
            },
          });
          break;
      }
    },

    /**
     * 获取应用市场配置
     */
    async initMarketConfig() {
      this.isDataLoading = true;
      try {
        const res = await this.$store.dispatch('market/getAppMarketConfig', this.appCode);
        this.appMarketConfig = Object.assign(this.appMarketConfig, res);
        if (this.appMarketConfig.source_url_type === 2) {
          this.avaliableAddressValue = 2;
        } else {
          this.avaliableAddressValue = this.appMarketConfig.custom_domain_url;
        }
        this.avaliableAddressValueBackup = this.avaliableAddressValue;
        this.marketAddress = this.appMarketConfig.market_address;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message,
        });
      } finally {
        this.isDataLoading = false;
        this.$emit('data-ready', true);
      }
    },

    /**
     * 提交访问数据
     */
    submitVisitInfo() {
      this.$refs.visitInfoForm.validate().then(() => {
        this.updateAppMarketConfig();
      });
    },

    /**
     * 更新应用市场配置
     */
    async updateAppMarketConfig() {
      if (this.isConfigSaving) return;

      this.isConfigSaving = true;

      try {
        await this.$store.dispatch('market/updateAppMarketConfig', {
          appCode: this.appCode,
          data: this.appMarketConfig,
        });

        this.checkAppPrepare();

        this.$paasMessage({
          theme: 'success',
          message: this.$t('保存成功！'),
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message,
        });
      } finally {
        this.isConfigSaving = false;
      }
    },

    /**
     * 处理开启或关闭市场
     */
    async handlerSwitch() {
      if (!this.appPreparations.all_conditions_matched) return;

      const status = this.appMarketConfig.enabled;
      try {
        const res = await this.$store.dispatch('market/updateAppMarketSwitch', {
          appCode: this.appCode,
          data: {
            enabled: status,
          },
        });
        this.appMarketConfig.enabled = status;
        if (res.enabled) {
          this.marketAddress = res.market_address;
        }
        bus.$emit('market_switch');
        this.$store.commit('updateCurAppMarketPublished', res.enabled);
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message,
        });
      } finally {
        if (status) {
          this.isSureRisk = false;
        }
      }
    },

    // 编辑访问地址
    handlerAddress() {
      if (this.isEditAddress) {
        this.switchAddressDialog.visiable = true;
      } else {
        this.isEditAddress = true;
      }
    },

    // 访问地址列表数据
    async getEntryList() {
      try {
        this.isTableLoading = true;
        const res = await this.$store.dispatch('entryConfig/getEntryDataList', {
          appCode: this.appCode,
        });
        this.addressData = res || [];
        this.moduleList = (res || []).map(e => e.name);
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message || e.detail || this.$t('接口异常'),
        });
      } finally {
        this.isTableLoading = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
    @import 'index.scss';

    .moudle-url .url {
        padding: 8px 21px;
        font-size: 12px;
        color: #666;
        background-color: #FAFBFD;
    }
    .bk-form-control {
        margin-top: -5px;
    }
    .icon-wrapper {
        float: left;
    }
    .module-select-cls{
      width: 100px;
      margin-right: 5px;
    }
</style>
