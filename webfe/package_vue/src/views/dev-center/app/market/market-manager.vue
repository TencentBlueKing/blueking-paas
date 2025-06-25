<template>
  <paas-content-loader
    :is-loading="isDataLoading"
    placeholder="market-visit-loading"
  >
    <section class="market-manager">
      <div class="market-info mb25 shadow-card-style">
        <div class="flex-row justify-content-between align-items-center">
          <div class="market-info-title-wrapper">
            <strong class="market-info-title">{{ $t('市场信息') }}</strong>
          </div>
          <bk-button
            v-if="isSaveMarketInfo"
            theme="primary"
            outline
            class="mr10 market-info-btn"
            :title="$t('编辑')"
            @click="isSaveMarketInfo = false"
          >
            {{ $t('编辑') }}
          </bk-button>
        </div>
        <div v-if="!isSaveMarketInfo">
          <bk-form
            class="market-info-container"
            ref="baseInfoForm"
            style="width: 890px"
            :label-width="120"
            :model="baseInfo"
          >
            <bk-form-item
              :label="$t('应用简介：')"
              :required="true"
              :property="'introduction'"
              :rules="baseInfoRules.introduction"
            >
              <bk-input
                v-model="baseInfo.introduction"
                type="text"
                :show-word-limit="true"
                :maxlength="100"
              />
            </bk-form-item>
            <bk-form-item
              v-if="GLOBAL.CONFIG.MARKET_INFO"
              :label="$t('应用联系人：')"
              :required="true"
              :property="'contactArr'"
              :rules="baseInfoRules.contact"
            >
              <user v-model="baseInfo.contactArr" />
            </bk-form-item>

            <bk-form-item
              v-if="GLOBAL.CONFIG.MARKET_INFO"
              :label="$t('所属业务：')"
            >
              <bk-tag-input
                v-model="baseInfo.related_corp_products"
                :placeholder="$t('请输入关键字，按Enter结束')"
                :save-key="'id'"
                :search-key="'display_name'"
                :setting-key="'id'"
                :display-key="'display_name'"
                :list="businessList"
              />
            </bk-form-item>

            <bk-form-item
              :label="$t('详细描述：')"
              :property="'name'"
            >
              <bk-input
                v-model="baseInfo.description"
                type="textarea"
                :maxlength="100"
              />
            </bk-form-item>

            <bk-form-item
              v-if="marketVisibility && isNewlyCreated"
              :label="$t('可见范围：')"
              :property="'name'"
            >
              <bk-org-selector
                v-if="platformFeature.MULTI_TENANT_MODE"
                v-model="orgMemberSelector"
                :api-base-url="tenantApiBaseUrl"
                :tenant-id="tenantId"
                :has-user="true"
                @change="handleBkOrgSelector"
              ></bk-org-selector>
              <template v-else>
                <section>
                  <bk-button @click="handleOpenMemberDialog">
                    {{ $t('选择组织/人员') }}
                  </bk-button>
                  <span
                    v-if="!users.length && !departments.length"
                    style="font-size: 12px; color: #c4c6cc; margin-left: 5px"
                  >
                    <i class="paasng-icon paasng-info-circle" />
                    {{ $t('默认为全局可见') }}
                  </span>
                </section>
                <p
                  v-if="GLOBAL.CONFIG.MARKET_TIPS"
                  class="tip"
                >
                  {{ $t('仅影响') }}
                  <a
                    :href="platFormConfig.LINK.APP_MARKET"
                    target="_blank"
                  >
                    {{ GLOBAL.CONFIG.MARKET_TIPS }}
                  </a>
                  {{ $t('上应用的可见范围，可见范围外的用户仍可以通过应用访问地址打开应用。') }}
                </p>
                <render-member-item
                  v-if="users.length > 0"
                  :data="users"
                  @on-delete="handleDeleteUser"
                />
                <render-member-item
                  v-if="departments.length > 0"
                  :data="departments"
                  type="department"
                  @on-delete="handleDeleteDepartment"
                />
              </template>
            </bk-form-item>
          </bk-form>

          <bk-form
            ref="baseWinForm"
            class="market-info-container"
            :label-width="120"
            style="width: 890px"
            :model="baseInfo"
          >
            <bk-form-item
              :label="$t('打开方式：')"
              :required="true"
            >
              <div class="bk-button-group bk-button-group-cls">
                <bk-button
                  :class="baseInfo.open_mode === 'desktop' ? 'is-selected' : ''"
                  @click="changeDesktop"
                >
                  {{ $t('桌面') }}
                </bk-button>
                <bk-button
                  :class="baseInfo.open_mode === 'new_tab' ? 'is-selected' : ''"
                  @click="changeNewtab"
                >
                  {{ $t('新标签页') }}
                </bk-button>
              </div>
            </bk-form-item>

            <bk-form-item
              v-if="baseInfo.open_mode === 'desktop'"
              :label="$t('窗口大小：')"
              :required="true"
            >
              <bk-input
                v-model="baseInfo.width"
                type="number"
                style="width: 200px; line-height: 1"
                class="fl mr10"
                :placeholder="$t('输入')"
                :min="0"
                :show-controls="false"
              >
                <template slot="prepend">
                  <div class="group-text">
                    {{ $t('宽') }}
                  </div>
                </template>
                <template slot="append">
                  <div class="group-text">px</div>
                </template>
              </bk-input>

              <bk-input
                v-model="baseInfo.height"
                type="number"
                style="width: 200px; line-height: 1"
                :placeholder="$t('输入')"
                :min="0"
                :show-controls="false"
              >
                <template slot="prepend">
                  <div class="group-text">
                    {{ $t('高') }}
                  </div>
                </template>
                <template slot="append">
                  <div class="group-text">px</div>
                </template>
              </bk-input>
              <p class="tip mt5">
                {{ $t('应用在蓝鲸桌面打开时的窗口大小，建议选择1200px*600px') }}
              </p>
            </bk-form-item>

            <bk-form-item
              v-if="baseInfo.open_mode === 'desktop'"
              :label="$t('拉伸窗口：')"
              :required="true"
            >
              <bk-select
                v-model="baseInfo.resizableKey"
                style="width: 411px"
                :clearable="false"
              >
                <bk-option
                  v-for="option in winResizeList"
                  :id="option.id"
                  :key="option.id"
                  :name="option.name"
                />
              </bk-select>
            </bk-form-item>
          </bk-form>

          <bk-form
            :label-width="130"
            style="width: 860px"
            class="mt20"
          >
            <bk-form-item class="mb20">
              <bk-button
                theme="primary"
                class="mr10 market-info-btn"
                :title="$t('保存')"
                :loading="isInfoSaving"
                @click.stop.prevent="submitMarketInfo"
              >
                {{ $t('保存') }}
              </bk-button>

              <bk-button
                theme="primary"
                outline
                class="ml10 market-info-btn"
                :title="$t('取消')"
                @click="handleCancel"
              >
                {{ $t('取消') }}
              </bk-button>
            </bk-form-item>
          </bk-form>
        </div>
        <div
          v-else
          class="flex-row justify-content-between"
        >
          <bk-form
            class="market-detail-container"
            ref="baseInfoForm"
            style="width: 890px"
            :label-width="120"
            :model="baseInfo"
            form-type="inline"
          >
            <bk-form-item
              :label="$t('应用简介：')"
              :rules="baseInfoRules.appArrange"
              :icon-offset="380"
            >
              <p
                class="form-text text-ellipsis"
                v-bk-overflow-tips
              >
                {{ baseInfo.introduction || '--' }}
              </p>
            </bk-form-item>
            <bk-form-item
              :label="$t('应用联系人：')"
              v-if="GLOBAL.CONFIG.MARKET_INFO"
              :rules="baseInfoRules.appArrange"
              :icon-offset="380"
            >
              <!-- 多租户展示 -->
              <template v-if="platformFeature.MULTI_TENANT_MODE && baseInfo.contactArr.length">
                <div class="form-text">
                  <span
                    v-for="(user, index) in baseInfo.contactArr"
                    :key="user"
                  >
                    <bk-user-display-name :user-id="user"></bk-user-display-name>
                    <span v-if="baseInfo.contactArr.length > index + 1">;&nbsp;</span>
                  </span>
                </div>
              </template>
              <p
                v-else
                class="form-text"
              >
                {{ baseInfo.contactArr.join('; ') || '--' }}
              </p>
            </bk-form-item>
            <bk-form-item
              v-if="GLOBAL.CONFIG.MARKET_INFO && baseInfo.related_corp_products.length"
              :label="$t('所属业务：')"
            >
              <p class="form-text">{{ businessDetailName || '--' }}</p>
            </bk-form-item>
            <bk-form-item :label="$t('详细描述：')">
              <p
                class="form-text text-ellipsis"
                v-bk-overflow-tips
              >
                {{ baseInfo.description || '--' }}
              </p>
            </bk-form-item>
            <bk-form-item :label="$t('打开方式：')">
              <p class="form-text">{{ baseInfo.open_mode === 'desktop' ? $t('桌面') : $t('新标签页') }}</p>
            </bk-form-item>
            <bk-form-item
              v-if="baseInfo.open_mode === 'desktop'"
              :label="$t('窗口大小：')"
            >
              <p class="form-text">{{ $t('宽') }}{{ baseInfo.width }}， {{ $t('高') }}{{ baseInfo.height }}</p>
            </bk-form-item>
            <bk-form-item
              v-if="baseInfo.open_mode === 'desktop'"
              :label="$t('拉伸窗口：')"
            >
              <p class="form-text">{{ baseInfo.resizableKey === 'able' ? $t('允许') : $t('不允许') }}</p>
            </bk-form-item>
          </bk-form>
        </div>
      </div>

      <user-selector-dialog
        v-if="marketVisibility && isNewlyCreated"
        :show.sync="isShow"
        :users="users"
        :departments="departments"
        :api-host="apiHost"
        @sumbit="handleSubmit"
      />
    </section>

    <!-- 可见范围 -->
    <visible-range
      v-if="marketVisibility && !isNewlyCreated"
      :data="baseInfo"
      @get-app-info="handleGetAppInfo"
    />
  </paas-content-loader>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin.js';
import user from '@/components/user';
import userSelectorDialog from '@/components/user-selector';
import RenderMemberItem from './render-member-display';
import BkOrgSelector from '@blueking/bk-org-selector/vue2';
import visibleRange from './visible-range';
import { PLATFORM_CONFIG } from '../../../../../static/json/paas_static';
import { cloneDeep } from 'lodash';
import { mapGetters, mapState } from 'vuex';
import { normalizeOrgSelectionData } from '@/common/tools';

export default {
  components: {
    user,
    userSelectorDialog,
    RenderMemberItem,
    visibleRange,
    BkOrgSelector,
  },
  mixins: [appBaseMixin],
  data() {
    let userRules = [];
    if (this.GLOBAL.CONFIG.MARKET_INFO) {
      userRules = [
        {
          validator(val) {
            return val.length > 0;
          },
          message: this.$t('请选择应用联系人'),
          trigger: 'blur',
        },
        {
          validator(val) {
            return val.length <= 4;
          },
          message: this.$t('应用联系人不能超过4人'),
          trigger: 'blur',
        },
      ];
    }
    return {
      isDataLoading: true,
      isInfoSaving: false,
      baseInfo: {
        name: '',
        introduction: '',
        logo: '',
        description: '',
        is_win_maximize: 0,
        type: 1,
        resizable: true,
        resizableKey: 'able',
        win_bars: true,
        contact: '',
        contactArr: [],
        related_corp_products: [],
        business: '',
        width: 1280,
        height: 600,
        open_mode: 'desktop',
        visiable_labels: [],
      },
      appStatus: '',
      businessList: [],
      winResizeList: [
        {
          id: 'able',
          name: this.$t('允许'),
        },
        {
          id: 'disable',
          name: this.$t('不允许'),
        },
      ],
      baseInfoRules: {
        name: [
          {
            required: true,
            message: this.$t('请输入应用名称'),
            trigger: 'blur',
          },
          {
            regex: /^[a-zA-Z\d\u4e00-\u9fa5]+$/,
            message: this.$t('格式不正确，只能包含：汉字、英文字母、数字'),
            trigger: 'blur',
          },
        ],
        introduction: [
          {
            required: true,
            message: this.$t('请输入应用简介'),
            trigger: 'blur',
          },
        ],
        appArrange: [
          {
            required: true,
            message: this.$t('请先选择分类信息'),
            trigger: 'blur',
          },
        ],
        contact: userRules,
      },
      isShow: false,
      platFormConfig: PLATFORM_CONFIG,
      apiHost: window.BK_COMPONENT_API_URL,
      isSaveMarketInfo: false,
      baseInfoBackup: Object.freeze({}),
      orgMemberSelector: [],
    };
  },
  computed: {
    ...mapState(['platformFeature']),
    ...mapGetters(['tenantId', 'tenantApiBaseUrl']),
    users() {
      return (this.baseInfo.visiable_labels || []).filter((item) => item.type === 'user');
    },
    departments() {
      return (this.baseInfo.visiable_labels || []).filter((item) => item.type === 'department');
    },
    businessDetailName() {
      return this.businessList.find((e) => this.baseInfo.related_corp_products.includes(e.id))?.display_name;
    },
    marketVisibility() {
      return this.curAppInfo.feature.MARKET_VISIBILITY;
    },
    isNewlyCreated() {
      return this.curAppInfo.product === null;
    },
  },
  watch: {
    $route() {
      this.init();
    },
    'baseInfo.contactArr'() {
      this.baseInfo.contact = this.baseInfo.contactArr.join('; ');
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
      this.initAppMarketInfo();
      this.getBusinessList();
    },

    handleSubmit(payload) {
      this.baseInfo.visiable_labels = payload;
    },

    handleOpenMemberDialog() {
      this.isShow = true;
    },

    handleDeleteUser(payload) {
      const index = this.baseInfo.visiable_labels.findIndex((item) => item.id === payload);
      this.baseInfo.visiable_labels.splice(index, 1);
    },

    handleDeleteDepartment(payload) {
      const index = this.baseInfo.visiable_labels.findIndex((item) => item.id === payload);
      this.baseInfo.visiable_labels.splice(index, 1);
    },

    /**
     * 获取业务列表
     */
    async getBusinessList() {
      try {
        const res = await this.$store.dispatch('market/getBusinessList');
        this.businessList = res;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    /**
     * 获取应用的市场基础信息
     *
     * appStatus:
     * offlined: 已经下架
     * deploy: 没有部署到生产环境
     * reg: 还没注册
     */
    async initAppMarketInfo(loading = true) {
      this.isDataLoading = loading;
      try {
        const res = await this.$store.dispatch('market/getAppBaseInfo', this.appCode);
        const { product, application } = res;

        // 如果没注册过，应用市场name为空，初始化与应用名称一样
        this.baseInfo.name = application.name;
        this.baseInfo.updated = application.updated;
        this.baseInfo.region_name = application.region_name;
        this.isSaveMarketInfo = res.product;
        // 通过product判断应用是否已经保存过
        if (res.product) {
          // 已注册用户判断是否在生产环境发布部署
          try {
            const prodEnvInfo = await this.$store.dispatch('market/getAppEnvInfo', {
              appCode: this.appCode,
              env: 'prod',
            });

            if (prodEnvInfo.offline) {
              this.appStatus = 'offlined'; // 已下架
            } else {
              this.appStatus = 'edit'; // 有正式部署
            }
          } catch (e) {
            // 最近无部署记录
            this.appStatus = 'deploy';
          }

          // 获取应用市场详细信息
          const marketInfo = await this.$store.dispatch('market/getAppMarketInfo', this.appCode);
          if (!marketInfo.contact) {
            marketInfo.contact = '';
          }
          marketInfo.logo = application.logo_url;
          this.baseInfo = Object.assign(this.baseInfo, marketInfo);
          this.formatMarketInfo();
        } else {
          this.appStatus = 'reg';
          this.baseInfo = Object.assign(this.baseInfo, {
            introduction: '',
            logo: '/static/images/default_logo.png',
            description: '',
            is_win_maximize: 0,
            type: 1,
            resizable: true,
            resizableKey: 'able',
            win_bars: true,
            contact: '',
            contactArr: [],
            related_corp_products: [],
            business: '',
            width: 1280,
            height: 600,
          });
          if (application.logo_url) {
            this.baseInfo.logo = application.logo_url;
          }
        }
        if (!product) {
          this.changeNewtab();
        }
        this.backfillOrgSelection(this.baseInfo.visiable_labels);
        this.baseInfoBackup = cloneDeep(this.baseInfo);
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isDataLoading = false;
        this.$emit('data-ready', true);
      }
    },

    /**
     * 针对接口数据处理，以适应前端需要
     */
    formatMarketInfo() {
      this.baseInfo.contactArr = this.baseInfo.contact.split('; ');
      this.baseInfo.resizableKey = this.baseInfo.resizable ? 'able' : 'disable';
    },

    /**
     * 提交基础信息数据
     */
    submitMarketInfo() {
      this.$refs.baseInfoForm
        .validate()
        .then(() => {
          this.saveMarketInfo();
        })
        .catch((e) => {
          console.error(e);
        });
    },

    /**
     * 保存应用市场信息
     */
    async saveMarketInfo() {
      if (this.isInfoSaving) return;

      this.isInfoSaving = true;
      this.baseInfo.resizable = this.baseInfo.resizableKey === 'able';

      let params = JSON.parse(JSON.stringify(this.baseInfo));
      delete params.logo;

      // 暂未注册 --开始注册信息
      if (this.appStatus === 'reg') {
        try {
          params.application = this.appCode;
          const res = await this.$store.dispatch('market/registerMarketInfo', params);

          this.appStatus = 'deploy';
          this.$emit('current-app-info-updated');

          this.$paasMessage({
            theme: 'success',
            message: this.$t('信息保存成功！'),
          });
          this.$store.commit('updateCurAppProduct', res);
          this.isSaveMarketInfo = false;
          this.initAppMarketInfo(); // 请求市场信息
        } catch (e) {
          this.$paasMessage({
            theme: 'error',
            message: e.detail || e.message || this.$t('接口异常'),
          });
        } finally {
          this.isInfoSaving = false;
        }
      } else {
        try {
          const res = await this.$store.dispatch('market/updateMarketInfo', {
            appCode: this.appCode,
            data: params,
          });

          this.$emit('current-app-info-updated');
          this.$paasMessage({
            theme: 'success',
            message: this.$t('信息修改成功！'),
          });
          this.$store.commit('updateCurAppProduct', res);
          this.isSaveMarketInfo = false;
          this.initAppMarketInfo(); // 请求市场信息
        } catch (e) {
          this.$paasMessage({
            theme: 'error',
            message: e.detail || e.message || this.$t('接口异常'),
          });
        } finally {
          this.isInfoSaving = false;
        }
      }
    },

    /**
     * 切换保打开方式
     */
    changeDesktop() {
      this.baseInfo.open_mode = 'desktop';
    },

    changeNewtab() {
      this.baseInfo.open_mode = 'new_tab';
    },

    handleGetAppInfo() {
      this.initAppMarketInfo(false);
    },

    // 取消处理
    handleCancel() {
      this.isSaveMarketInfo = true;
      this.baseInfo = cloneDeep(this.baseInfoBackup);
    },
    backfillOrgSelection(data) {
      this.orgMemberSelector = normalizeOrgSelectionData(data || [], { nonUserType: 'org' });
    },
    // 多租户组织架构选择
    handleBkOrgSelector(data) {
      const visiableLabels = normalizeOrgSelectionData(data);
      this.baseInfo.visiable_labels = visiableLabels;
    },
  },
};
</script>

<style lang="scss" scoped>
@import 'index.scss';
</style>
