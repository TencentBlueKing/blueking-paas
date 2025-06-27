<template lang="html">
  <div
    class="bk-apps-wrapper"
    :style="{
      'min-height': `${minHeight}px`,
      'padding-top': `${isShowNotice ? GLOBAL.NOTICE_HEIGHT + 50 : 50}px`,
    }"
  >
    <paas-content-loader
      :is-loading="isFirstLoading"
      placeholder="apps-loading"
      offset-top="20"
      class="wrap"
      :height="700"
    >
      <div class="clearfix paas-application-tit">
        <div class="fright clearfix">
          <div class="app-title-left">
            <div class="create-app">
              <bk-button
                class="mr8"
                theme="primary"
                @click="createApp"
              >
                <i class="paasng-icon paasng-plus-thick" />
                {{ $t('创建应用') }}
              </bk-button>
            </div>
            <!-- 全部应用、我创建的 -->
            <section class="application-overview-module">
              <bk-radio-group
                v-model="curAppCreationType"
                @change="handlerAppOverviewChange"
              >
                <bk-radio-button value="all">
                  <span>{{ $t('全部应用') }}</span>
                  <span class="app-count">{{ appExtraData.all_app_count || 0 }}</span>
                </bk-radio-button>
                <bk-radio-button value="iCreated">
                  <span>{{ $t('我创建的') }}</span>
                  <span class="app-count">{{ appExtraData.my_app_count || 0 }}</span>
                </bk-radio-button>
              </bk-radio-group>
            </section>
          </div>

          <div class="app-title-right">
            <!-- 应用分类筛选项 -->
            <div class="paas-filter-wrapper">
              <div
                v-for="item in appTypeList"
                :key="item.key"
                :class="['filter-item', { active: item.key === curAppTypeActive }]"
                @click="switchAppType(item)"
              >
                {{ item.text }}
              </div>
            </div>
            <!-- 筛选 -->
            <section :class="['app-filter-module', { en: isEnglishEnv }]">
              <bk-popover
                theme="light navigation-message"
                :ext-cls="`app-filter-popover-cls ${isEnglishEnv ? 'en' : ''}`"
                placement="bottom"
                :arrow="false"
                offset="1, 2"
                trigger="click"
              >
                <div class="filter-view">
                  <div class="text">{{ $t(curFilterValue) }}</div>
                </div>
                <template #content>
                  <ul class="filter-navigation-list">
                    <li
                      v-for="item in filterList"
                      :key="item.value"
                      :class="['nav-item', { active: item.text === curFilterValue }]"
                      @click="handleFilterApp(item)"
                    >
                      {{ $t(item.text) }}
                    </li>
                  </ul>
                </template>
              </bk-popover>
              <div
                :class="['filter-right-icon', { active: filterActive }]"
                v-bk-tooltips="{ content: $t(filterTips) }"
                @click.stop="handleTtogleOrder"
              >
                <i :class="['paasng-icon', sortValue.indexOf('-') !== -1 ? 'paasng-shengxu' : 'paasng-jiangxu']" />
              </div>
            </section>
            <div :class="['app-list-search', { en: isEnglishEnv }]">
              <bk-input
                v-model="filterKey"
                clearable
                :placeholder="$t('输入应用名称、ID，按Enter搜索')"
                :right-icon="'bk-icon icon-search'"
                @enter="searchApp"
                @keyup="handleKeyUp"
                @right-icon-click="handleRightIconClick"
              />
            </div>

            <div
              v-if="userFeature.MGRLEGACY"
              class="migrate"
            >
              <bk-button
                theme="primary"
                text
                @click="appMigrate"
              >
                {{ $t('旧版应用迁移') }}
              </bk-button>
            </div>
          </div>
        </div>
      </div>

      <bk-table
        :data="appList"
        size="medium"
        ref="appTableCls"
        :pagination="pagination"
        :outer-border="false"
        v-bkloading="{ isLoading: isLoading, zIndex: 10 }"
        ext-cls="app-list-table-cls"
        :row-key="rowKey"
        :expand-row-keys="expandRowKeys"
        @filter-change="handleFilterChange"
        @page-change="handlePageChange"
        @page-limit-change="handlePageLimitChange"
        @row-mouse-enter="(index) => (curHoverRowIndex = index)"
        @row-mouse-leave="curHoverRowIndex = -1"
        @cell-click="handleCellClick"
      >
        <div slot="empty">
          <table-empty
            :keyword="tableEmptyConf.keyword"
            :abnormal="tableEmptyConf.isAbnormal"
            :empty-title="$t('暂无应用')"
            @reacquire="fetchAppList"
            @clear-filter="clearFilterKey"
          />
        </div>
        <bk-table-column
          label=""
          :width="50"
        >
          <template slot-scope="{ row }">
            <div
              :class="['star-wrapper', { 'off-shelf': !row.application.is_active }]"
              @click.stop="toggleAppMarked(row)"
            >
              <span
                class="star-icon"
                :title="row.marked ? $t('取消置顶') : $t('置顶')"
              >
                <i :class="['paasng-icon', { 'paasng-star-cover': row.marked }, { 'paasng-star-line': !row.marked }]" />
              </span>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column
          type="expand"
          width="0"
        >
          <template slot-scope="props">
            <bk-table
              v-if="props.row.application.config_info.engine_enabled"
              :data="props.row.application.modules"
              :outer-border="false"
              size="small"
              ext-cls="child-modules-table-cls"
              :header-cell-style="{ background: '#fff', borderRight: 'none' }"
            >
              <bk-table-column
                prop="name"
                :label="$t('模块')"
              >
                <template slot-scope="childProps">
                  <span
                    class="link"
                    @click.stop="toModule(props.row, childProps.row)"
                  >
                    {{ childProps.row.name }}
                    <span
                      v-if="childProps.row.is_default"
                      style="color: #979ba5"
                    >
                      ({{ $t('主模块') }})
                    </span>
                  </span>
                </template>
              </bk-table-column>
              <bk-table-column
                prop="language"
                :label="$t('语言')"
              >
                <template slot-scope="{ row }">
                  {{ row.language || '--' }}
                </template>
              </bk-table-column>
              <bk-table-column
                prop="created"
                :label="$t('创建时间')"
              ></bk-table-column>
              <bk-table-column :label="$t('操作')">
                <template slot-scope="{ row }">
                  <template v-if="Object.keys(props.row.application.deploy_info)?.length">
                    <a
                      href="javascript:void(0);"
                      class="blue"
                      style="margin-right: 8px"
                      @click="deploy(props.row, row)"
                    >
                      {{ $t('部署') }}
                    </a>
                    <!-- props 当前应用项，row 当前应用模块项 -->
                    <a
                      href="javascript:void(0);"
                      class="blue"
                      @click="viewLog(props.row, row)"
                    >
                      {{ $t('查看日志') }}
                    </a>
                  </template>
                  <template v-else>
                    <a
                      href="javascript:void(0);"
                      class="blue"
                      @click="applyCludeApi(props.row)"
                    >
                      {{ $t('申请 云API 权限') }}
                    </a>
                  </template>
                </template>
              </bk-table-column>
            </bk-table>
            <div class="add-module-cls">
              <bk-button
                v-if="props.row.creation_allowed"
                style="margin-left: -13px"
                theme="primary"
                icon="plus-circle-shape"
                text
                size="small"
                @click="addModule(props.row)"
              >
                {{ $t('点击创建新模块') }}
              </bk-button>
              <bk-button
                v-else
                style="margin-left: -13px"
                icon="plus-circle-shape"
                text
                size="small"
                disabled
              >
                <span
                  v-bk-tooltips="$t('非内部版应用目前无法创建其它模块')"
                  v-dashed
                >
                  {{ $t('点击创建新模块') }}
                </span>
              </bk-button>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('应用')"
          prop="name"
          :min-width="280"
        >
          <template slot-scope="{ row }">
            <div :class="['app-name', { 'off-shelf': !row.application.is_active }]">
              <img
                :src="row.application ? (row.application.logo_url ? row.application.logo_url : defaultImg) : defaultImg"
                class="app-logo"
              />
              <div class="info">
                <span
                  class="name"
                  @click.stop="toPage(row)"
                >
                  {{ row.application.name }}
                </span>
                <span class="code">{{ row.application.code }}</span>
              </div>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('模块数量')"
          :width="135"
        >
          <template slot-scope="{ row, $index }">
            <span
              v-if="row.application.config_info.engine_enabled"
              :class="['module-name', { 'off-shelf': !row.application.is_active }]"
              @click.stop="handleExpandRow(row)"
            >
              {{ $t('共') }}&nbsp; {{ row.application.modules.length }} &nbsp;{{ $t('个模块') }}
              <i
                v-if="expandRowKeys.includes(row.application.code) || $index === curHoverRowIndex"
                class="paasng-icon unfold-icon"
                :class="
                  expandRowKeys.includes(row.application.code) ? 'paasng-angle-double-up' : 'paasng-angle-double-down'
                "
              />
            </span>
            <span v-else>--</span>
          </template>
        </bk-table-column>
        <!-- ee/ce 不展示这一列 -->
        <bk-table-column
          :label="$t('版本')"
          prop="region_name"
          column-key="region_name"
          :filters="versionFilters"
          :filter-multiple="false"
          v-if="platformFeature.REGION_DISPLAY"
        >
          <template slot-scope="{ row }">
            <span :class="{ 'off-shelf': !row.application.is_active }">
              {{ $t(row.application.region_name) }}
            </span>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('应用类型')">
          <template slot-scope="{ row }">
            <!-- 外部版不展示 -->
            <div class="app-type-wrapper">
              <span :class="{ 'off-shelf': !row.application.is_active }">
                {{ $t(PAAS_APP_TYPE[row.application.type]) }}
              </span>
              <!-- 是否显示迁移应用icon, 需要后台提供字段 -->
              <template v-if="row.application.is_active">
                <div
                  v-if="
                    userFeature.CNATIVE_MGRLEGACY && !noMigrationNeededStatus.includes(row.migration_status?.status)
                  "
                  v-bk-tooltips="{
                    content:
                      row.application.type === 'cloud_native' ? $t('查看迁移进度') : $t('点击可迁移为云原生应用'),
                    allowHTML: true,
                  }"
                  class="migration-wrapper"
                  @click.stop="showAppMigrationDialog(row.application)"
                >
                  <i class="paasng-icon paasng-qianyi-mianxing" />
                </div>
              </template>
            </div>
          </template>
        </bk-table-column>
        <template v-if="isShowTenant">
          <bk-table-column
            :label="$t('租户模式')"
            prop="app_tenant_mode"
            column-key="app_tenant_mode"
            :filters="tenantFilters"
            :filter-multiple="false"
          >
            <template slot-scope="{ row }">
              {{ $t(appTenantMode[row.application.app_tenant_mode]) }}
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('租户 ID')">
            <template slot-scope="{ row }">
              {{ row.application.app_tenant_id || '--' }}
            </template>
          </bk-table-column>
        </template>
        <bk-table-column
          :label="$t('状态')"
          :render-header="statusRenderHeader"
        >
          <template slot-scope="{ row }">
            <i :class="['dot', { successful: row.application.is_active }]"></i>
            <span :class="{ 'off-shelf': !row.application.is_active }">
              {{ row.application.is_active ? $t('正常') : $t('下架') }}
            </span>
          </template>
        </bk-table-column>
        <bk-table-column
          label=""
          :width="isEnglishEnv ? 440 : 260"
        >
          <template slot-scope="{ row }">
            <div
              v-if="!Object.keys(row.application.deploy_info).length"
              class="app-operation-section"
            >
              <!-- 外链应用 -->
              <bk-button
                theme="primary"
                text
                ext-cls="link-btn-cls"
                @click="toCloudAPI(row)"
              >
                {{ $t('申请云 API 权限') }}
                <i class="paasng-icon paasng-keys cloud-icon" />
              </bk-button>
              <span
                v-bk-tooltips.top="{
                  content: $t('应用未设置访问路径'),
                  disabled: row.market_config.source_tp_url,
                  allowHTML: true,
                }"
                class="right-text link-btn-cls"
              >
                <bk-button
                  theme="primary"
                  text
                  :disabled="!row.market_config.source_tp_url"
                  @click="toAccessApps(row)"
                >
                  {{ $t('访问应用') }}
                  <i class="paasng-icon paasng-external-link" />
                </bk-button>
              </span>
            </div>
            <div
              v-else
              class="app-operation-section"
            >
              <template>
                <bk-button
                  :disabled="!row.application.deploy_info.stag.deployed"
                  text
                  ext-cls="link-btn-cls"
                  @click="visitLink(row, 'stag')"
                >
                  <template v-if="!row.application.deploy_info.stag.deployed">
                    <span
                      v-bk-tooltips="{
                        content: $t('应用未部署，不能访问'),
                        placement: 'top',
                        allowHTML: true,
                      }"
                    >
                      {{ $t('访问预发布环境') }}
                      <i class="paasng-icon paasng-external-link" />
                    </span>
                  </template>
                  <template v-else>
                    <span>
                      {{ $t('访问预发布环境') }}
                      <i class="paasng-icon paasng-external-link" />
                    </span>
                  </template>
                </bk-button>
                <bk-button
                  :disabled="!row.application.deploy_info.prod.deployed"
                  text
                  ext-cls="link-btn-cls right-text"
                  @click="visitLink(row, 'prod')"
                >
                  <template v-if="!row.application.deploy_info.prod.deployed">
                    <span
                      v-bk-tooltips="{
                        content: $t('应用未部署，不能访问'),
                        placement: 'top',
                        allowHTML: true,
                      }"
                    >
                      {{ $t('访问生产环境') }}
                      <i class="paasng-icon paasng-external-link" />
                    </span>
                  </template>
                  <template v-else>
                    <span>
                      {{ $t('访问生产环境') }}
                      <i class="paasng-icon paasng-external-link" />
                    </span>
                  </template>
                </bk-button>
              </template>
            </div>
          </template>
        </bk-table-column>
      </bk-table>
    </paas-content-loader>

    <!-- 普通应用迁移至云原生应用弹窗 -->
    <app-migration-dialog
      v-model="appMigrationDialogConfig.visible"
      :data="appMigrationDialogConfig.data"
    />
  </div>
</template>

<script>
import auth from '@/auth';
import i18n from '@/language/i18n';
import tebleHeaderFilters from '@/components/teble-header-filters';
import appMigrationDialog from '@/components/app-migration-dialog';
import { PAAS_APP_TYPE, APP_TENANT_MODE } from '@/common/constants';
import { mapGetters } from 'vuex';

const APP_TYPE_MAP = [
  {
    text: i18n.t('全部'),
    key: 'all',
    type: 'all',
  },
  {
    text: i18n.t('普通应用'),
    key: 'default_app_count',
    type: 'default',
  },
  {
    text: i18n.t('云原生应用'),
    key: 'cloud_native_app_count',
    type: 'cloud_native',
  },
  {
    text: i18n.t('外链应用'),
    key: 'engineless_app_count',
    type: 'engineless_app',
  },
];

const FILTER_TIP = {
  code: 'A - Z',
  '-code': 'Z - A',
  created: '最早',
  '-created': '最新',
  latest_operated_at: '最早',
  '-latest_operated_at': '最新',
};

export default {
  components: {
    appMigrationDialog,
  },
  // Get userHasApp before render
  beforeRouteEnter(to, from, next) {
    const promise = auth.requestHasApp();
    promise.then((userHasApp) => {
      next(async (vm) => {
        if (!userHasApp) {
          vm.isFirstLoading = true;
          await auth
            .requestOffApp()
            .then((flag) => {
              vm.userHasApp = flag;
            })
            .finally(() => {
              vm.isFirstLoading = false;
            });
        } else {
          vm.userHasApp = userHasApp;
        }
      });
    });
  },
  beforeRouteUpdate(to, from, next) {
    const promise = auth.requestHasApp();
    promise.then((userHasApp) => {
      next(async () => {
        if (!userHasApp) {
          this.isFirstLoading = true;
          await auth
            .requestOffApp()
            .then((flag) => {
              this.userHasApp = flag;
            })
            .finally(() => {
              this.isFirstLoading = false;
            });
        } else {
          this.userHasApp = userHasApp;
        }
      });
    });
  },
  data() {
    return {
      isLoading: true,
      isFirstLoading: true,
      userHasApp: true,
      minHeight: 550,
      appList: [],
      defaultImg: '/static/images/default_logo.png',
      // 搜索条件筛选
      appFilter: {
        // 显示已下架应用
        isActive: null,
        // 显示我创建的
        excludeCollaborated: false,
        // 版本选择
        regionList: ['ieod', 'tencent', 'clouds'],
        // 语言选择
        languageList: ['Python', 'PHP', 'Go', 'NodeJS'],
        type: false,
      },
      // 搜索词
      filterKey: '',
      sortValue: 'code',
      // fetchParams
      fetchParams: {
        // 等于 filterKey
        search_term: '',
        // (curPage -1 ) * limit
        offset: 0,
        // 是否排除拥有协作者权限的应用，默认不排除。如果为 true，意为只返回我创建的
        exclude_collaborated: false,
        // 应用状态过滤
        is_active: null,
        // limit
        limit: 0,
        order_by: 'code',
      },
      availableLanguages: ['Python', 'PHP', 'Go', 'NodeJS'],
      availableRegions: ['ieod', 'tencent', 'clouds'],
      RegionTranslate: {
        ieod: this.$t('内部版'),
        tencent: this.$t('外部版'),
        clouds: this.$t('混合云版'),
        default: this.$t('默认'),
      },
      type: 'default',
      curAppType: '',
      curAppTypeActive: 'all',
      tableEmptyConf: {
        keyword: '',
        isAbnormal: false,
      },
      curFilterValue: '应用ID',
      filterList: [
        { text: '应用ID', value: 'code' },
        { text: '创建时间', value: '-created' },
        { text: '操作时间', value: '-latest_operated_at' },
      ],
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
        limitList: [5, 10, 20, 50],
      },
      PAAS_APP_TYPE,
      curAppCreationType: 'all',
      versionFilters: [
        { text: '内部版', value: '内部版' },
        { text: '外部版', value: '外部版' },
      ],
      expandRowKeys: [],
      curHoverRowIndex: -1,
      appExtraData: {},
      tableHeaderFilterValue: 'all',
      appMigrationDialogConfig: {
        visible: false,
        data: {},
      },
      noMigrationNeededStatus: ['no_need_migration', 'confirmed'],
      appTypeList: APP_TYPE_MAP,
      appTenantMode: APP_TENANT_MODE,
      tenantFilters: [
        { text: this.$t('单租户'), value: 'single' },
        { text: this.$t('全租户'), value: 'global' },
      ],
      tableFilters: {},
    };
  },
  computed: {
    userFeature() {
      return this.$store.state.userFeature;
    },
    platformFeature() {
      return this.$store.state.platformFeature;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    isEnglishEnv() {
      return this.localLanguage === 'en';
    },
    isShowNotice() {
      return this.$store.state.isShowNotice;
    },
    filterTips() {
      return FILTER_TIP[this.sortValue];
    },
    filterActive() {
      return this.sortValue.includes('code')
        ? this.sortValue.indexOf('-') !== -1
        : !(this.sortValue.indexOf('-') !== -1);
    },
    ...mapGetters(['isShowTenant']),
  },
  watch: {
    filterKey(newVal, oldVal) {
      if (newVal === '' && oldVal !== '') {
        this.fetchAppList();
      }
    },
  },
  created() {
    this.handleFilterApp({ text: '操作时间', value: '-latest_operated_at' }, false);
    if (this.$route.query.is_active) {
      this.appFilter.isActive = true;
    }
    this.fetchAppList();
  },
  mounted() {
    this.handlePageHeight();
  },
  methods: {
    handlePageHeight() {
      const HEADER_HEIGHT = 50;
      const FOOTER_HEIGHT = 70;
      const winHeight = window.innerHeight;
      const contentHeight = winHeight - HEADER_HEIGHT - FOOTER_HEIGHT;
      if (contentHeight > this.minHeight) {
        this.minHeight = contentHeight;
      }
    },

    deploy(item, subModule) {
      this.$router.push({
        name: item.application.type === 'cloud_native' ? 'cloudAppDeployManageStag' : 'appDeploy',
        params: {
          id: item.application.code,
          moduleId: subModule.name,
        },
      });
    },

    toPage(appItem) {
      this.toAppSummary(appItem);
    },

    handlePageChange(page) {
      this.pagination.current = page;
      this.fetchAppList(page);
    },

    handlePageLimitChange(limit) {
      this.pagination.limit = limit;
      this.fetchAppList();
    },

    toCloudAPI(item) {
      this.$router.push({
        name: 'appCloudAPI',
        params: {
          id: item.application.code,
        },
      });
    },

    createApp() {
      this.$router.push({
        name: 'createApp',
      });
    },

    viewLog(item, subModule) {
      this.$router.push({
        name: 'appLog',
        params: {
          id: item.application.code,
          moduleId: subModule.name,
        },
        query: {
          tab: 'structured',
        },
      });
    },

    addModule(appItem) {
      this.$router.push({
        name: appItem.application.type === 'cloud_native' ? 'appCreateCloudModule' : 'appCreateModule',
        params: {
          id: appItem.application.code,
        },
      });
    },

    applyCludeApi(item) {
      this.$router.push({
        name: 'appCloudAPI',
        params: {
          id: item.application.code,
        },
      });
    },

    toModule(appItem, subModule) {
      this.$router.push({
        name: 'appSummary',
        params: {
          id: appItem.application.code,
          moduleId: subModule.name,
        },
      });
    },

    toAppSummary(appItem) {
      const routeName = appItem.application?.type === 'cloud_native' ? 'cloudAppSummary' : 'appSummary';

      this.$router.push({
        name: routeName,
        params: {
          id: appItem.application.code,
          moduleId: appItem.application.modules.find((item) => item.is_default).name,
        },
      });
    },

    appMigrate() {
      this.$router.push({
        name: 'appLegacyMigration',
      });
    },

    searchApp() {
      if (this.filterKey === '') {
        return;
      }
      this.fetchAppList();
    },

    // 获取 app list
    async fetchAppList(page = 1) {
      let url = `${BACKEND_URL}/api/bkapps/applications/lists/detailed?format=json`;
      // 筛选,搜索等操作时，强制切到 page 的页码
      // APP 编程语言， vue-resource 不支持替換 array 的編碼方式（會編碼成 language[], drf 默认配置不能识别 )
      url = this.concatenateFilters(url);
      this.fetchParams.order_by = this.sortValue;
      const params = Object.assign(this.fetchParams, {
        search_term: this.filterKey,
        offset: (page - 1) * this.pagination.limit,
        limit: this.pagination.limit,
        // 是否排除拥有协作者权限的应用，默认不排除。如果为 true，意为只返回我创建的
        exclude_collaborated: this.appFilter.excludeCollaborated,
        // 是否是活跃应用
        is_active: undefined,
        // 对应类型
        type: this.curAppType,
      });

      // 全部: 不传参数 / 正常: true / 下架: false
      if (this.tableHeaderFilterValue === 'all') {
        delete params.is_active;
      } else if (this.tableHeaderFilterValue === 'normal') {
        params.is_active = true;
      } else if (this.tableHeaderFilterValue === 'archive') {
        params.is_active = false;
      } 

      this.isLoading = true;
      for (const key in params) {
        url += `&${key}=${params[key]}`;
      }
      try {
        const res = await this.$store.dispatch('getAppList', { url });
        (res.results || []).forEach((item) => {
          this.$set(item, 'creation_allowed', true);
        });
        this.appList = res.results || [];
        this.pagination.count = res.count;
        this.pagination.current = page;
        this.appExtraData = res.extra_data;
        this.updateTableEmptyConfig();
        this.tableEmptyConf.isAbnormal = false;
      } catch (e) {
        this.tableEmptyConf.isAbnormal = true;
        this.$paasMessage({
          theme: 'error',
          message: e.detail || this.$t('接口异常'),
        });
      } finally {
        this.isFirstLoading = false;
        this.isLoading = false;
      }
    },

    visitLink(data, env) {
      window.open(data.application.deploy_info[env].url);
    },

    // 标记应用，标记后的应用会被放在列表最前端
    async toggleAppMarked(appItem) {
      const appCode = appItem.application.code;
      const msg = appItem.marked ? this.$t('取消收藏成功') : this.$t('应用收藏成功');
      try {
        await this.$store.dispatch('toggleAppMarked', { appCode, isMarked: appItem.marked });
        appItem.marked = !appItem.marked;
        this.$paasMessage({
          theme: 'success',
          message: msg,
        });
      } catch (error) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('无法标记应用，请稍后再试'),
        });
      }
    },

    reset() {
      this.appFilter = {
        // 默认显示所有应用
        isActive: null,
        // 我创建的
        excludeCollaborated: false,
        languageList: ['Python', 'PHP', 'Go', 'NodeJS'],
        regionList: ['ieod', 'tencent', 'clouds'],
        type: false,
      };
      this.filterKey = '';
      this.fetchAppList();
    },

    toAccessApps(appItem) {
      if (appItem.market_config && appItem.market_config.source_tp_url) {
        window.open(appItem.market_config.source_tp_url);
      }
    },

    switchAppType(item) {
      if (item.key === this.curAppTypeActive) return;
      this.curAppType = item.type !== 'all' ? item.type : '';
      this.curAppTypeActive = item.key;
      this.fetchAppList();
    },

    // 清空搜索筛选条件
    clearFilterKey() {
      this.$refs.appTableCls?.clearFilter();
      this.tableHeaderFilterValue = 'all';
      this.filterKey = '';
      this.reset();
    },

    concatenateFilters(url) {
      const { region, tenant } = this.tableFilters;
      if (region) {
        const region = region === '内部版' ? 'ieod' : 'tencent';
        url += `&region=${region}`;
      }
      if (tenant) {
        url += `&app_tenant_mode=${tenant}`;
      }
      return url;
    },

    // 是否存在筛选条件
    updateTableEmptyConfig() {
      if (this.filterKey || this.tableFilters.region || this.tableFilters.tenant) {
        this.tableEmptyConf.keyword = 'placeholder';
        return;
      }
      this.tableEmptyConf.keyword = '';
    },
    handleFilterApp(item, isRequest = true) {
      this.curFilterValue = item.text;
      this.sortValue = item.value;
      isRequest && this.fetchAppList();
    },
    // 切换排序规则
    handleTtogleOrder() {
      if (this.sortValue.indexOf('-') !== -1) {
        this.sortValue = this.sortValue.replace('-', '');
      } else {
        this.sortValue = `-${this.sortValue}`;
      }
      this.fetchAppList();
    },
    handlerAppOverviewChange(value) {
      this.appFilter.excludeCollaborated = value === 'iCreated';
      this.fetchAppList(1);
    },
    // 行key
    rowKey(row) {
      return row.application.code;
    },
    // 模块详情展开处理
    handleExpandRow(row) {
      if (this.expandRowKeys.includes(row.application.code)) {
        this.expandRowKeys = this.expandRowKeys.filter((item) => item !== row.application.code);
        return;
      }
      this.expandRowKeys.push(row.application.code);
    },
    // 表格筛选
    handleFilterChange(filds) {
      if (filds.region_name) {
        this.tableFilters['region'] = filds.region_name.length ? filds.region_name[0] : '';
      }
      if (filds.app_tenant_mode) {
        this.tableFilters['tenant'] = filds.app_tenant_mode.length ? filds.app_tenant_mode[0] : '';
      }
      this.fetchAppList();
    },

    statusRenderHeader(h) {
      return h(tebleHeaderFilters, {
        props: {
          active: this.tableHeaderFilterValue,
          label: this.$t('状态'),
          iconClass: 'bk-icon icon-funnel',
          filterList: [
            { text: this.$t('全部'), value: 'all' },
            { text: this.$t('正常'), value: 'normal' },
            { text: this.$t('下架'), value: 'archive' },
          ],
        },
        on: {
          'filter-change': (data) => {
            this.tableHeaderFilterValue = data.value;
            this.fetchAppList();
          },
        },
      });
    },

    // 右侧icon搜索
    handleRightIconClick() {
      this.fetchAppList();
    },

    // 单元格点击处理
    handleCellClick(row, column) {
      if (column.property === 'name') {
        this.toPage(row);
      }
    },

    handleKeyUp(value, event) {
      // 支持 delete 删除
      if (event.key === 'Delete' && this.filterKey !== '') {
        this.filterKey = '';
      }
    },

    showAppMigrationDialog(data) {
      this.appMigrationDialogConfig.visible = true;
      this.appMigrationDialogConfig.data = data;
    },
  },
};
</script>

<style lang="scss" scoped>
$customize-disabled-color: #c4c6cc;

.app-list-search {
  width: 320px;
}

@media (max-width: 1350px) {
  .app-list-search {
    width: 300px;
  }
  .app-list-search.en {
    width: 260px;
  }
}

@media (max-width: 1300px) {
  .app-list-search.en {
    width: 220px;
  }
}

.bk-apps-wrapper {
  width: calc(100% - 48px);
}

.app-operation-section {
  position: relative;
  button {
    i {
      position: relative;
      top: 2px;
      font-size: 20px;
      opacity: 0;
    }
    i.cloud-icon {
      left: -3px;
    }
  }
  .right-text {
    margin-left: 14px;
  }
}

.app-type-wrapper {
  display: flex;
  align-items: center;

  .migration-wrapper {
    margin-left: 1px;
    width: 24px;
    height: 24px;
    line-height: 24px;
    text-align: center;
    transform: translateY(2px);
    border-radius: 2px;

    i {
      font-size: 14px;
      color: #3a84ff;
    }
    &:hover {
      background-color: #e1ecff;
    }
  }
}

.shaixuan,
.shaixuan input {
  cursor: pointer;
}

div.choose-panel {
  input {
    appearance: none;
  }
}

label {
  display: inline;
  cursor: pointer;
}

.button-holder {
  display: block;
  line-height: 30px;
}

.paas-application-tit {
  padding: 24px 0 16px;
  color: #666;
  line-height: 36px;
  position: relative;
  .mr8 {
    margin-right: 8px;
  }
}

.paas-application-tit .fright {
  width: 100%;
  .app-title-left {
    float: left;
    display: flex;
  }
  .app-title-right {
    float: right;
    display: flex;
    .paas-filter-wrapper {
      display: flex;
      align-items: center;
      height: 32px;
      margin-top: 3px;
      padding: 4px;
      background: #eaebf0;
      color: #63656e;
      border-radius: 2px;
      .filter-item {
        position: relative;
        font-size: 12px;
        line-height: 24px;
        padding: 0 10px;
        &:hover {
          cursor: pointer;
        }
        &.active {
          background: #fff;
          color: #3a84ff;
          border-radius: 2px;
          z-index: 9;
          &::before {
            background: transparent;
          }
          & + .filter-item::before {
            background: transparent;
          }
        }
        &::before {
          content: '';
          position: absolute;
          width: 1px;
          height: 12px;
          background: #dddfe6;
          left: 0;
          top: 50%;
          transform: translateY(-50%);
        }
        &:first-child::before {
          background: transparent;
        }
      }
    }
  }
}

.clearfix::after {
  content: '';
  display: block;
  height: 0;
  clear: both;
  visibility: hidden;
}
.clearfix {
  *zoom: 1;
}

h2.application-title {
  font-size: 16px;
  margin-top: 8px;
  font-weight: normal;
  color: #313238;
}

.disabledBox .section-button {
  color: #d7eadf;
  cursor: not-allowed;
}

.disabledBox .section-button:hover {
  color: #d7eadf;
}

.disabledBox .section-button img {
  opacity: 0.3;
}

.paas-legacy-app {
  position: absolute;
  right: 482px;
}

.choose-box {
  position: absolute;
  right: -2px;
  margin-top: 3px;
  width: 92px;
  overflow: hidden;
  height: 30px;
  border: solid 1px #afbec5;
  padding: 0;
  line-height: 30px;
}

.choose {
  color: #666;
  font-size: 14px;
  height: 30px;
  line-height: 30px;
  width: 52px;
  padding-left: 14px;
}
.application-choose img {
  position: relative;
  top: 2px;
  padding-right: 8px;
}

.choose-panel {
  position: absolute;
  right: 0;
  top: 60px;
  width: 228px;
  border-top: solid 1px #e9edee;
  box-shadow: 0 2px 5px #e5e5e5;
  background: #fff;
  height: auto;
  overflow: hidden;
  padding: 5px 0 0 0;
  z-index: 99;
  transition: all 0.5s;
}

.save {
  width: 20px;
  height: 24px;
  vertical-align: middle;
  background: url(/static/images/save-icon.png) center center no-repeat;
}

.save.on,
.save:hover {
  background: url(/static/images/save-icon2.png) center center no-repeat;
}

.save:hover {
  opacity: 0.4;
}

.save.on:hover {
  opacity: 0.65;
}

.overflow {
  overflow: hidden;
  padding: 0 20px;
}

.paasng-angle-up,
.paasng-angle-down {
  padding-left: 3px;
  transition: all 0.5s;
  font-size: 12px;
  font-weight: bold;
  color: #5bd18b;
}

.open .section-button .paasng-angle-down {
  position: absolute;
  top: 8px;
  right: 12px;
}

.ps-btn-visit-disabled .paasng-angle-down,
.ps-btn-visit:disabled .paasng-angle-down,
.ps-btn-visit[disabled] .paasng-angle-down {
  color: #d7eadf !important;
}
.wrap {
  width: 100%;
  margin: 0 24px 24px;
}

.link-btn-cls {
  display: inline-block;
  height: 100%;
}
.migrate {
  margin-left: 16px;
}

.app-list-table-cls {
  .app-name {
    display: flex;
    img {
      width: 32px;
      height: 32px;
    }
    .info {
      display: flex;
      flex-flow: column;
      justify-content: center;
      margin-left: 8px;
      font-size: 12px;
      color: #63656e;
      .name {
        font-weight: 700;
        font-size: 12px;
        color: #3a84ff;
        cursor: pointer;
      }
    }
  }

  .module-name {
    display: inline-block;
    padding: 5px 5px 5px 0px;
    user-select: none;
    color: #3a84ff;
    cursor: pointer;
  }

  .star-wrapper {
    i {
      color: #979ba5;
      font-size: 16px;
      cursor: pointer;

      &.paasng-star-cover {
        color: #ffb848 !important;
      }

      &:hover {
        color: #63656e;
      }
    }
  }
  i.dot {
    display: inline-block;
    margin-right: 8px;
    width: 8px;
    height: 8px;
    background: #f0f1f5;
    border: 1px solid $customize-disabled-color;
    border-radius: 50%;

    &.successful {
      background: #e5f6ea;
      border: 1px solid #3fc06d;
    }
  }

  .off-shelf {
    color: $customize-disabled-color;
    &.app-name .info {
      .name,
      .code {
        color: $customize-disabled-color;
      }
    }
    &.module-name {
      color: $customize-disabled-color;
    }
  }

  :deep(.add-module-cls) {
    border-top: 1px solid #dfe0e5;
    background-color: #fff;
    padding: 8px 16px;
    button i.bk-icon.left-icon {
      top: -1px;
    }
  }
}
.application-overview-module {
  .bk-radio-button-input.is-checked + .bk-radio-button-text .app-count {
    background: #ffffff;
  }
  .app-count {
    display: inline-block;
    font-size: 12px;
    height: 16px;
    line-height: 16px;
    padding: 0 8px;
    background: #f0f1f5;
    border-radius: 18px;
    margin-left: 3px;
    transform: translateY(-1px);
  }
}
</style>

<style lang="scss">
section.app-filter-module {
  display: flex;
  margin: 3px 16px 0;
  width: 117px;
  height: 32px;
  background: #eaebf0;
  border-radius: 2px;
  &.en {
    width: 135px;
  }
  .bk-tooltip {
    flex: 1;
    white-space: nowrap;
    display: block;
    .tippy-active {
      background: #ffffff;
      border: 1px solid #3a84ff;
      border-radius: 2px 0 0 2px;
    }
  }

  .text {
    position: relative;
    padding: 0 8px;
    font-size: 12px;
    color: #63656e;
    flex: 1;
    line-height: 32px;
    cursor: pointer;
    text-overflow: ellipsis;
    white-space: nowrap;
    overflow: hidden;
    &:hover {
      background: #dcdee5;
      border-radius: 2px 0 0 2px;
    }
  }
  .filter-right-icon {
    position: relative;
    cursor: pointer;
    width: 30px;
    display: flex;
    align-items: center;
    justify-content: center;

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 50%;
      transform: translateY(-50%);
      height: 14px;
      width: 1px;
      background-color: #dcdee5;
    }

    i {
      color: #979ba5;
    }

    &:hover {
      background: #dcdee5;
      border-radius: 0 2px 2px 0;
    }
    &.active {
      i {
        color: #3a84ff;
      }
    }
  }
}
.bk-apps-wrapper .wrap .app-filter-module .bk-tooltip-ref {
  display: block;
}
.app-filter-popover-cls {
  width: 87px;
  background: #ffffff;
  border: 1px solid #dcdee5;
  box-shadow: 0 2px 6px 0 #0000001a;
  border-radius: 2px;
  height: 104px;
  padding: 4px 0;
  &.en {
    width: 105px;
  }
  .tippy-content {
    padding: 0 !important;
  }
  .tippy-tooltip.light-theme {
    height: 100%;
    transform: translateY(0px) !important;
    padding: 0px;
    box-shadow: none;
  }
  .filter-navigation-list {
    .nav-item {
      display: flex;
      align-items: center;
      height: 32px;
      padding: 12px;
      background: #ffffff;
      font-size: 12px;
      color: #63656e;
      cursor: pointer;
      &:hover {
        background: #f5f7fa;
      }
      &.active {
        color: #3a84ff;
        background: #e1ecff;
      }
    }
  }
}
.app-list-table-cls {
  .bk-table-row.expanded .bk-table-column-expand .bk-table-expand-icon i {
    color: #63656e;
  }
  // height
  & > .bk-table-body-wrapper > table tbody > tr {
    height: 56px;

    &.hover-row {
      td:nth-child(3) {
        cursor: pointer;
      }
    }
  }

  .is-expanded-row td.bk-table-expanded-cell {
    padding: 0 52px !important;
    background-color: #fafbfd;
  }
  .bk-table-pagination-wrapper {
    background-color: #ffffff;
  }

  .child-modules-table-cls {
    .bk-table-header-wrapper thead tr th {
      background: #f5f7fa !important;
    }
    .bk-table-body-wrapper table tbody > tr {
      height: 42px !important;
      cursor: default;
      td {
        height: 42px;
      }
    }
    .link {
      cursor: pointer;
      color: #3a84ff;
    }
  }
}
</style>
