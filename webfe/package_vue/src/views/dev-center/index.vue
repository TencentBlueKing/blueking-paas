<template lang="html">
  <div
    class="bk-apps-wrapper mt30"
    :style="{ 'min-height': `${minHeight}px` }"
    @click="resetAction()"
  >
    <div
      v-if="!userHasApp"
      class="wrap"
    >
      <div class="application-blank">
        <h2> {{ $t('蓝鲸应用是蓝鲸应用引擎提供的服务单位') }} </h2>
        <p> {{ $t('您可以创建自己的蓝鲸应用，使用您熟悉的编程语言（Python、Golang等）进行开发。开发完成后，您可以一键部署，使应用运行在蓝鲸 PaaS 平台上。') }} </p>
        <p>
          {{ $t('您可将应用发布到') }} <a
            class="blue"
            :href="GLOBAL.LINK.APP_MARKET"
            target="_blank"
          > {{ $t('蓝鲸应用市场') }} </a> {{ $t('后，其他蓝鲸平台的用户便可以通过应用市场搜索和访问您的应用') }}
        </p>
        <p>
          <router-link
            :to="{ name: 'createApp' }"
            class="paas-operation-icon"
          >
            <i class="paasng-icon paasng-plus" /> {{ $t('创建应用') }}
          </router-link>
          <router-link
            v-if="userFeature.MGRLEGACY"
            :to="{ name: 'appLegacyMigration' }"
            class="btn-link spacing-h-x2"
          >
            {{ $t('迁移旧版应用') }}
          </router-link>
        </p>
      </div>

      <ul class="application-list">
        <li>
          <h2>
            <a
              href=""
              target="_blank"
            > {{ $t('快速开始应用开发') }} </a>
          </h2>
          <div class="application-list-text">
            <p> {{ $t('新手福利，这里有详细的Step by Step入门指南') }} </p>
            <p>
              <a
                href="javascript:"
                target="_blank"
              >[{{ $t('新手入门') }}]</a>
              <a
                href="javascript:"
                target="_blank"
              >[{{ $t('开发指南') }}]</a>
            </p>
          </div>
          <a
            href="javascript:"
            target="_blank"
          ><img src="/static/images/application-list-1.png"></a>
        </li>
        <li>
          <h2>
            <a
              href="javascript:"
              target="_blank"
            > {{ $t('使用预发布环境') }} </a>
          </h2>
          <div class="application-list-text">
            <p> {{ $t('蓝鲸PaaS平台为所有应用提供预发布环境，使您的应用在上线到生产环境前经过充分的测试') }} </p>
          </div>
          <a
            href="javascript:"
            target="_blank"
          ><img src="/static/images/application-list-2.png"></a>
        </li>
        <li>
          <h2>
            <a
              href="javascript:"
              target="_blank"
            > {{ $t('发布到应用市场') }} </a>
          </h2>
          <div class="application-list-text">
            <p> {{ $t('将应用部署到生产环境后，您就可以将其发布到蓝鲸应用市场了') }} </p>
          </div>
          <a
            href="javascript:"
            target="_blank"
          ><img src="/static/images/application-list-3.png"></a>
        </li>
      </ul>
    </div>
    <paas-content-loader
      v-else
      :is-loading="isFirstLoading"
      :placeholder="loaderPlaceholder"
      offset-top="20"
      class="wrap"
      :height="575"
    >
      <h2 class="application-title">
        {{ $t('我的应用') }}
        <span> ({{ pageConf.count }}) </span>
      </h2>
      <div class="paas-application-tit clearfix">
        <div class="fright clearfix">
          <div class="app-title-left">
            <div class="create-app">
              <bk-button
                class="mr8"
                theme="primary"
                @click="createApp"
              >
                {{ $t('创建应用') }}
              </bk-button>
            </div>
            <div
              v-if="userFeature.MGRLEGACY"
              class="migrate"
            >
              <bk-button
                :theme="'default'"
                @click="appMigrate"
              >
                {{ $t('迁移旧版应用') }}
              </bk-button>
            </div>
          </div>

          <div class="app-title-right">
            <!-- 应用分类筛选项 -->
            <div class="paas-filter-wrapper mr8">
              <div
                v-for="item in appTypeList"
                :key="item.key"
                :class="['filter-item', { 'active': item.key === curAppTypeActive }]"
                @click="switchAppType(item)"
              >
                {{ item.text }}
              </div>
            </div>
            <div class="paas-search mr8">
              <bk-input
                v-model="filterKey"
                :placeholder="$t('输入应用名称、ID，按Enter搜索')"
                :clearable="true"
                :right-icon="'paasng-icon paasng-search'"
                @enter="searchApp"
              />
            </div>

            <div
              class="advanced-filter"
              @click.stop="toggleChoose(true)"
            >
              <p>
                {{ $t('高级筛选') }}
                <i
                  class="paasng-icon"
                  :class="ifopen ? 'paasng-angle-double-up' : 'paasng-angle-double-down'"
                />
              </p>
            </div>
          </div>
          <div
            v-if="ifopen"
            class="choose-panel"
            @click.stop="showChoose"
          >
            <div class="overflow shaixuan">
              <label class="button-holder">
                <input
                  v-model="appFilter.includeInactive"
                  type="checkbox"
                  class="ps-checkbox-default"
                  value="true"
                >
                <span> {{ $t('显示已下架应用') }} </span>
              </label>
            </div>
            <div class="overflow shaixuan">
              <label class="button-holder">
                <input
                  v-model="appFilter.excludeCollaborated"
                  type="checkbox"
                  class="ps-checkbox-default"
                  value="true"
                >
                <span> {{ $t('只显示我创建的') }} </span>
              </label>
            </div>
            <div class="overflow shaixuan">
              <div style="margin-top: -5px; width: 78px; float: left">
                {{ $t('排序方式') }}
              </div>
              <div style="width: 110px; float: right">
                <bk-radio-group v-model="sortValue">
                  <bk-radio
                    value="name"
                    style="display: block; margin: 4px 0 0 0;"
                  >
                    {{ $t('应用名称') }}
                  </bk-radio>
                  <bk-radio
                    value="-created"
                    style="display: block; margin: 4px 0 0 0;"
                  >
                    {{ $t('最新创建') }}
                  </bk-radio>
                  <bk-radio
                    value="created"
                    style="display: block; margin: 4px 0 0 0;"
                  >
                    {{ $t('最早创建') }}
                  </bk-radio>
                  <bk-radio
                    value="-latest_operated_at"
                    style="display: block; margin: 4px 0 0 0;"
                  >
                    {{ $t('最近操作') }}
                  </bk-radio>
                </bk-radio-group>
              </div>
            </div>
            <div
              v-if="isShowLanguagesSearch"
              class="overflow"
            >
              <div style="width: 78px; float: left; margin-top: -4px;">
                {{ $t('使用语言') }}
              </div>
              <div style="width: 110px; float: right">
                <label
                  v-if="isShowAllWithLanguages"
                  class="button-holder"
                >
                  <input
                    v-model="IncludeAllLanguages"
                    type="checkbox"
                    class="ps-checkbox-default"
                  >
                  <span> {{ $t('全部') }} ({{ appNumInfo.All }})</span>
                </label>
                <label
                  v-for="(language, languageIndex) in availableLanguages"
                  v-if="appNumInfo[language]"
                  :key="languageIndex"
                  class="button-holder"
                >
                  <input
                    v-model="appFilter.languageList"
                    type="checkbox"
                    class="ps-checkbox-default"
                    :value="language"
                  >
                  <span>{{ language }} ({{ appNumInfo[language] }})</span>
                </label>
              </div>
            </div>
            <div
              v-if="isShowRegionsSearch && platformFeature.REGION_DISPLAY"
              class="overflow"
            >
              <div style="width: 78px; float: left">
                {{ $t('应用版本') }}
              </div>
              <div style="width: 110px; float: right">
                <label
                  v-if="isShowAllWithRegions"
                  class="button-holder"
                >
                  <input
                    v-model="IncludeAllRegions"
                    type="checkbox"
                    class="ps-checkbox-default"
                  >
                  <span> {{ $t('全部') }} ({{ appNumInfo.All }})</span>
                </label>
                <label
                  v-for="(region, regionIndex) in availableRegions"
                  v-if="appNumInfo[region]"
                  :key="regionIndex"
                  class="button-holder"
                >
                  <input
                    v-model="appFilter.regionList"
                    type="checkbox"
                    class="ps-checkbox-default"
                    :value="region"
                  >
                  <span>{{ RegionTranslate[region] }} ({{ appNumInfo[region] }})</span>
                </label>
              </div>
            </div>
            <div class="application-choose-btn">
              <bk-button
                theme="primary"
                @click.stop.prevent="fetchAppList(1)"
              >
                {{ $t('筛选') }}
              </bk-button>
              <bk-button
                theme="default"
                @click.stop.prevent="reset"
              >
                {{ $t('重置') }}
              </bk-button>
            </div>
          </div>
        </div>
      </div>

      <div
        v-bkloading="{ isLoading: isLoading, opacity: .7 }"
        :class="['apps-table-wrapper', { 'min-h': isLoading }, { 'reset-min-h': !isLoading && !appList.length }]"
      >
        <template v-if="appList.length">
          <div
            v-for="(appItem, appIndex) in appList"
            :key="appIndex"
            class="table-item"
            :class="{ 'mt': appIndex !== appList.length - 1 }"
          >
            <div class="item-header">
              <div
                class="star-wrapper"
                @click="toggleAppMarked(appItem)"
              >
                <span
                  class="star-icon"
                  :title="appItem.marked ? $t('取消置顶') : $t('置顶')"
                >
                  <i :class="['paasng-icon', { 'paasng-star-cover': appItem.marked }, { 'paasng-star-line': !appItem.marked }]" />
                </span>
              </div>
              <div
                class="basic-info"
                @click="toPage(appItem)"
              >
                <img
                  :src="appItem.application ? (appItem.application.logo_url ? appItem.application.logo_url : defaultImg) : defaultImg"
                  class="app-logo"
                >
                <span class="app-name">
                  {{ appItem.application.name }}
                </span>
              </div>
              <div
                v-if="platformFeature.REGION_DISPLAY"
                class="region-info"
              >
                <span
                  :class="['reg-tag', { 'inner': appItem.application.region_name === $t('内部版') }, { 'clouds': appItem.application.region_name === $t('混合云版') }]"
                >
                  {{ appItem.application.region_name }}
                </span>
              </div>
              <div
                class="module-info"
                @click="expandedPanel(appItem)"
              >
                <template v-if="appItem.application.config_info.engine_enabled && appItem.application.type !== 'cloud_native'">
                  <span
                    class="module-name"
                    :class="appItem.expanded ? 'expanded' : ''"
                  > {{ $t('共') }}&nbsp; {{ appItem.application.modules.length }} &nbsp;{{ $t('个模块') }} <i
                    class="paasng-icon unfold-icon"
                    :class="appItem.expanded ? 'paasng-angle-double-up' : 'paasng-angle-double-down'"
                  />
                  </span>
                </template>
              </div>
              <div class="visit-operate">
                <div
                  v-if="!Object.keys(appItem.application.deploy_info).length"
                  class="app-operation-section"
                >
                  <!-- 外链应用 -->
                  <bk-button
                    theme="primary"
                    text
                    ext-cls="link-btn-cls"
                    @click="toCloudAPI(appItem)"
                  >
                    {{ $t('申请云API权限') }}
                    <i class="paasng-icon paasng-keys cloud-icon" />
                  </bk-button>
                  <span
                    v-bk-tooltips.top="{ content: $t('应用未设置访问路径'), disabled: appItem.market_config.source_tp_url }"
                    class="link-btn-cls right-text"
                  >
                    <bk-button
                      theme="primary"
                      text
                      :disabled="!appItem.market_config.source_tp_url"
                      @click="toAccessApps(appItem)"
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
                      :disabled="!appItem.application.deploy_info.stag.deployed"
                      text
                      ext-cls="link-btn-cls"
                      @click="visitLink(appItem, 'stag')"
                    >
                      <template v-if="!appItem.application.deploy_info.stag.deployed">
                        <span v-bk-tooltips="$t('应用未部署，不能访问')"> {{ $t('预发布环境') }} <i class="paasng-icon paasng-external-link" />
                        </span>
                      </template>
                      <template v-else>
                        <span>
                          {{ $t('预发布环境') }}
                          <i class="paasng-icon paasng-external-link" />
                        </span>
                      </template>
                    </bk-button>
                    <bk-button
                      :disabled="!appItem.application.deploy_info.prod.deployed"
                      text
                      ext-cls="link-btn-cls right-text"
                      @click="visitLink(appItem, 'prod')"
                    >
                      <template v-if="!appItem.application.deploy_info.prod.deployed">
                        <span v-bk-tooltips="$t('应用未部署，不能访问')"> {{ $t('生产环境') }} <i class="paasng-icon paasng-external-link" />
                        </span>
                      </template>
                      <template v-else>
                        <span>
                          {{ $t('生产环境') }}
                          <i class="paasng-icon paasng-external-link" />
                        </span>
                      </template>
                    </bk-button>
                  </template>
                </div>
              </div>
            </div>
            <div
              v-show="appItem.expanded"
              class="item-content"
            >
              <div class="apps-table-wrapper">
                <table class="ps-table ps-table-default ps-instances-table ps-table-special">
                  <thead>
                    <th> {{ $t('模块') }} </th>
                    <th> {{ $t('语言') }} </th>
                    <th> {{ $t('创建时间') }} </th>
                    <th style="width: 150px;">
                      {{ $t('操作') }}
                    </th>
                  </thead>
                  <tbody>
                    <template v-if="appItem.application.modules.length">
                      <tr
                        v-for="subModule in appItem.application.modules"
                        :key="subModule.id"
                      >
                        <td
                          class="module-name"
                          @click.stop="toModule(appItem, subModule)"
                        >
                          <p>
                            {{ subModule.name }}
                            <span
                              v-if="subModule.is_default"
                              style="color: #979ba5;"
                            > {{ $t('(主模块)') }} </span>
                          </p>
                        </td>
                        <td class="run-state">
                          <p>{{ subModule.language }}</p>
                        </td>
                        <td class="time">
                          <p>{{ subModule.created || '--' }}</p>
                        </td>
                        <td class="operate">
                          <template v-if="Object.keys(appItem.application.deploy_info).length">
                            <a
                              href="javascript:void(0);"
                              class="blue"
                              style="margin-right: 6px;"
                              @click="deploy(appItem, subModule)"
                            > {{ $t('部署') }} </a>
                            <a
                              href="javascript:void(0);"
                              class="blue"
                              @click="viewLog(appItem, subModule)"
                            > {{ $t('查看日志') }} </a>
                          </template>
                          <template v-else>
                            <a
                              href="javascript:void(0);"
                              class="blue"
                              @click="applyCludeApi(appItem)"
                            > {{ $t('申请云API权限') }} </a>
                          </template>
                        </td>
                      </tr>
                    </template>
                    <template v-else>
                      <tr class="module-tr-empty">
                        <td colspan="4">
                          <div class="ps-no-result">
                            <table-empty
                              :empty-title="$t('暂无模块')"
                              empty
                            />
                          </div>
                        </td>
                      </tr>
                    </template>
                    <tr v-if="appItem.application.type !== 'cloud_native'">
                      <td
                        colspan="4"
                        style="text-align: left;"
                      >
                        <bk-button
                          v-if="appItem.creation_allowed"
                          style="margin-left: -13px;"
                          theme="primary"
                          icon="plus-circle-shape"
                          text
                          size="small"
                          @click="addModule(appItem)"
                        >
                          {{ $t('点击创建新模块') }}
                        </bk-button>
                        <bk-button
                          v-else
                          style="margin-left: -13px;"
                          icon="plus-circle-shape"
                          text
                          size="small"
                          disabled
                        >
                          <span v-bk-tooltips="$t('非内部版应用目前无法创建其它模块')"> {{ $t('点击创建新模块') }} </span>
                        </bk-button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </template>
        <template v-if="!isLoading && !appList.length">
          <div class="ps-no-result">
            <table-empty
              :keyword="tableEmptyConf.keyword"
              :abnormal="tableEmptyConf.isAbnormal"
              :empty-title="$t('暂无应用')"
              @reacquire="fetchAppList"
              @clear-filter="clearFilterKey"
            />
          </div>
        </template>
      </div>

      <div
        v-if="pageConf.count"
        style="margin: 20px 0;"
      >
        <bk-pagination
          size="small"
          align="right"
          :current.sync="pageConf.curPage"
          :count="pageConf.count"
          :limit="pageConf.limit"
          :limit-list="pageConf.limitList"
          @change="pageChange"
          @limit-change="handlePageSizeChange"
        />
      </div>
    </paas-content-loader>
  </div>
</template>

<script>
    import auth from '@/auth';
    import i18n from '@/language/i18n';

    const APP_TYPE_MAP = [
        {
           text: i18n.t('全部'),
           key: 'all',
           type: 'all'
        },
        {
           text: i18n.t('普通应用'),
           key: 'default_app_count',
           type: 'default'
        },
        {
           text: i18n.t('云原生应用'),
           key: 'cloud_native_app_count',
           type: 'cloud_native'
        },
        {
           text: i18n.t('外链应用'),
           key: 'engineless_app_count',
           type: 'engineless_app'
        }
    ];

    export default {
        // Get userHasApp before render
        beforeRouteEnter (to, from, next) {
            const promise = auth.requestHasApp();
            promise.then((userHasApp) => {
                next(async vm => {
                    if (!userHasApp) {
                        vm.isFirstLoading = true;
                        await auth.requestOffApp()
                            .then(flag => {
                                vm.userHasApp = flag;
                            }).finally(() => {
                                vm.isFirstLoading = false;
                            });
                    } else {
                        vm.userHasApp = userHasApp;
                    }
                });
            });
        },
        beforeRouteUpdate (to, from, next) {
            const promise = auth.requestHasApp();
            promise.then((userHasApp) => {
                next(async () => {
                    if (!userHasApp) {
                        this.isFirstLoading = true;
                        await auth.requestOffApp()
                            .then(flag => {
                                this.userHasApp = flag;
                            }).finally(() => {
                                this.isFirstLoading = false;
                            });
                    } else {
                        this.userHasApp = userHasApp;
                    }
                });
            });
        },
        data () {
            return {
                isInitLoading: true,
                isLoading: true,
                isFirstLoading: true,
                searcLoading: false,
                userHasApp: true,
                ifopen: false,
                minHeight: 550,
                ifvisited: -1,
                appList: [],
                loaderPlaceholder: 'apps-loading',
                // 过滤后的 app 数量
                appNum: '',
                focusInput: 0,
                defaultImg: '/static/images/default_logo.png',
                // 搜索条件筛选
                appFilter: {
                    // 显示已下架应用
                    includeInactive: false,
                    // 显示我创建的
                    excludeCollaborated: false,
                    // 版本选择
                    regionList: ['ieod', 'tencent', 'clouds'],
                    // 语言选择
                    languageList: ['Python', 'PHP', 'Go', 'NodeJS'],
                    type: false
                },
                // 搜索词
                filterKey: '',
                pageConf: {
                    count: 0,
                    curPage: 0,
                    totalPage: 0,
                    limit: 10,
                    limitList: [5, 10, 20, 50]
                },
                sortValue: 'name',
                // fetchParams
                fetchParams: {
                    // 等于 filterKey
                    search_term: '',
                    // (curPage -1 ) * limit
                    offset: 0,
                    // 是否排除拥有协作者权限的应用，默认不排除。如果为 true，意为只返回我创建的
                    exclude_collaborated: false,
                    // 是否包含已下架应用，默认不包含
                    include_inactive: false,
                    // limit
                    limit: 0,
                    order_by: 'name'
                },
                // app数量, 不考虑筛选情况
                appNumInfo: {
                    All: 0,
                    PHP: 0,
                    Go: 0,
                    NodeJS: 0,
                    Python: 0,
                    ieod: 0,
                    tencent: 0,
                    clouds: 0,
                    default: 0
                },
                availableLanguages: ['Python', 'PHP', 'Go', 'NodeJS'],
                availableRegions: ['ieod', 'tencent', 'clouds'],
                RegionTranslate: {
                    ieod: this.$t('内部版'),
                    tencent: this.$t('外部版'),
                    clouds: this.$t('混合云版'),
                    default: this.$t('默认')
                },
                isFilter: false,
                type: 'default',
                appTypeList: APP_TYPE_MAP,
                curAppType: '',
                curAppTypeActive: 'all',
                tableEmptyConf: {
                    keyword: '',
                    isAbnormal: false
                }
            };
        },
        computed: {
            userFeature () {
                return this.$store.state.userFeature;
            },
            platformFeature () {
                return this.$store.state.platformFeature;
            },
            // 显示全部语言
            IncludeAllLanguages: {
                get: function () {
                    // 由于当全不选时，按照drf的逻辑是不使用该filter字段，导致行为也是全选
                    return this.appFilter.languageList.length === this.availableLanguages.length;
                },
                set: function (value) {
                    this.appFilter.languageList = (value) ? this.availableLanguages : [];
                }
            },
            // 显示所有版本
            IncludeAllRegions: {
                get: function () {
                    // 由于当全不选时，按照drf的逻辑是不使用该filter字段，导致行为也是全选
                    return this.appFilter.regionList.length === this.availableRegions.length;
                },
                set: function (value) {
                    this.appFilter.regionList = (value) ? this.availableRegions : [];
                }
            },
            isOrderByDesc: function () {
                // 是否倒序
                return this.fetchParams.order_by.indexOf('-') === 0;
            },
            isShowLanguagesSearch () {
                return this.availableLanguages.filter(item => this.appNumInfo[item]).length > 0;
            },
            isShowRegionsSearch () {
                return this.availableRegions.length > 0;
            },
            isShowAllWithLanguages () {
                return this.availableLanguages.filter(item => this.appNumInfo[item]).length > 1;
            },
            isShowAllWithRegions () {
                return this.availableRegions.length > 1;
            }
        },
        watch: {
            filterKey (newVal, oldVal) {
                if (newVal === '' && oldVal !== '') {
                    if (this.isFilter) {
                        this.fetchAppList();
                        this.isFilter = false;
                    }
                }
            },
            ifopen (value) {
                if (!value) {
                    this.sortValue = this.fetchParams.order_by;
                }
            }
        },
        created () {
            this.getAppCategory(false);
            if (this.$route.query.include_inactive) {
                this.appFilter.includeInactive = true;
            }
            this.fetchAppList();
        },
        mounted () {
            const HEADER_HEIGHT = 50;
            const FOOTER_HEIGHT = 70;
            const winHeight = window.innerHeight;
            const contentHeight = winHeight - HEADER_HEIGHT - FOOTER_HEIGHT;
            if (contentHeight > this.minHeight) {
                this.minHeight = contentHeight;
            }
        },
        methods: {
            deploy (item, subModule) {
                if (item.application.type === 'cloud_native') {
                    this.toDeploy(item.application);
                } else {
                    this.$router.push({
                        name: 'appDeploy',
                        params: {
                            id: item.application.code,
                            moduleId: subModule.name
                        }
                    });
                }
            },

            async toDeploy (recordItem) {
                const url = `${BACKEND_URL}/api/bkapps/applications/${recordItem.code}/`;
                try {
                    const res = await this.$http.get(url);
                    this.type = res.application.type;
                    this.$router.push({
                        name: this.type === 'cloud_native' ? 'cloudAppDeploy' : 'appDeploy',
                        params: {
                            id: recordItem.code
                        }
                    });
                } catch (e) {
                    this.$paasMessage({
                        limit: 1,
                        theme: 'error',
                        message: e.message
                    });
                }
            },

            toPage (appItem) {
                this.toAppSummary(appItem);
            },

            pageChange (page) {
                this.fetchAppList(page);
            },

            toCloudAPI (item) {
                this.$router.push({
                    name: 'appCloudAPI',
                    params: {
                        id: item.application.code
                    }
                });
            },

            createApp () {
                this.$router.push({
                    name: 'createApp'
                });
            },

            viewLog (item, subModule) {
                this.$router.push({
                    name: 'appLog',
                    params: {
                        id: item.application.code,
                        moduleId: subModule.name
                    },
                    query: {
                        tab: 'structured'
                    }
                });
            },

            addModule (appItem) {
                this.$router.push({
                    name: 'appCreateModule',
                    params: {
                        id: appItem.application.code
                    }
                });
            },

            applyCludeApi (item) {
                this.$router.push({
                    name: 'appCloudAPI',
                    params: {
                        id: item.application.code
                    }
                });
            },

            expandedPanel (item) {
                if (!item.application.config_info.engine_enabled) {
                    return;
                }
                this.fetchRegionInfo(item.application.region, item);
                item.expanded = !item.expanded;
            },

            async fetchRegionInfo (region, item) {
                try {
                    const res = await this.$store.dispatch('fetchRegionInfo', region);
                    this.$set(item, 'creation_allowed', res.mul_modules_config.creation_allowed);
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.detail || this.$t('接口异常')
                    });
                }
            },

            toAppBaseInfo (appItem) {
                this.$router.push({
                    name: 'appBaseInfo',
                    params: {
                        id: appItem.application.code
                    }
                });
            },

            toModule (appItem, subModule) {
                this.$router.push({
                    name: 'appSummary',
                    params: {
                        id: appItem.application.code,
                        moduleId: subModule.name
                    }
                });
            },

            toAppSummary (appItem) {
                this.$router.push({
                    name: 'appSummary',
                    params: {
                        id: appItem.application.code,
                        moduleId: appItem.application.modules.find(item => item.is_default).name
                    }
                });
            },

            appMigrate () {
                this.$router.push({
                    name: 'appLegacyMigration'
                });
            },

            searchApp () {
                if (this.filterKey === '') {
                    return;
                }
                this.isFilter = true;
                this.fetchAppList();
            },

            clearFilter () {
                this.filterKey = '';
            },

            // 列表排序
            toggleSortTab () {
                if (this.fetchParams.order_by.indexOf('-') === 0) {
                    this.fetchParams.order_by = this.fetchParams.order_by.substr(1);
                } else {
                    this.fetchParams.order_by = '-' + this.fetchParams.order_by;
                }
                this.fetchAppList();
            },

            setFocus (n) {
                this.focusInput = n;
            },

            // 初始化
            resetAction () {
                this.ifopen = false;
                this.ifvisited = -1;
            },

            showChoose () {
                this.ifopen = true;
            },

            toggleChoose () {
                this.ifopen = !this.ifopen;
            },

            handlePageSizeChange (pageSize) {
                this.pageConf.limit = pageSize;
                this.fetchAppList();
            },

            // 获取 app list
            async fetchAppList (page = 1) {
                let url = BACKEND_URL + `/api/bkapps/applications/lists/detailed?format=json`;
                // 筛选,搜索等操作时，强制切到 page 的页码
                // APP 编程语言， vue-resource 不支持替換 array 的編碼方式（會編碼成 language[], drf 默认配置不能识别 )
                // 如果能切到 axios 就可以去掉这部分代码了
                url = this.getParams(url);
                this.fetchParams.order_by = this.sortValue;
                this.fetchParams = Object.assign(this.fetchParams, {
                    search_term: this.filterKey,
                    offset: (page - 1) * this.pageConf.limit,
                    limit: this.pageConf.limit,
                    // 是否排除拥有协作者权限的应用，默认不排除。如果为 true，意为只返回我创建的
                    exclude_collaborated: this.appFilter.excludeCollaborated,
                    // 是否包含已下架应用，默认不包含
                    include_inactive: this.appFilter.includeInactive,
                    // 对应类型
                    type: this.curAppType
                });
                this.isLoading = true;
                for (const key in this.fetchParams) {
                    url += `&${key}=` + this.fetchParams[key];
                }
                try {
                    const res = await this.$store.dispatch('getAppList', { url });
                    this.pageConf.curPage = page;
                    this.pageConf.count = res.count;
                    this.pageConf.totalPage = Math.ceil(this.pageConf.count / this.pageConf.limit);
                    (res.results || []).forEach(item => {
                        this.$set(item, 'expanded', false);
                        this.$set(item, 'creation_allowed', true);
                    });
                    this.appList.splice(0, this.appList.length, ...(res.results || []));
                    this.updateTableEmptyConfig();
                    this.tableEmptyConf.isAbnormal = false;
                } catch (e) {
                    this.tableEmptyConf.isAbnormal = true;
                    this.$paasMessage({
                        theme: 'error',
                        message: e.detail || this.$t('接口异常')
                    });
                } finally {
                    this.isFirstLoading = false;
                    this.isLoading = false;
                }
            },

            visitLink (data, env) {
                window.open(data.application.deploy_info[env].url);
            },

            // 标记应用，标记后的应用会被放在列表最前端
            async toggleAppMarked (appItem) {
                const appCode = appItem.application.code;
                const msg = appItem.marked ? this.$t('取消收藏成功') : this.$t('应用收藏成功');
                try {
                    await this.$store.dispatch('toggleAppMarked', { appCode, isMarked: appItem.marked });
                    appItem.marked = !appItem.marked;
                    this.$paasMessage({
                        theme: 'success',
                        message: msg
                    });
                } catch (error) {
                    this.$paasMessage({
                        theme: 'error',
                        message: this.$t('无法标记应用，请稍后再试')
                    });
                }
            },

            reset () {
                this.appFilter = {
                    // 已下架
                    includeInactive: false,
                    // 我创建的
                    excludeCollaborated: false,
                    IncludeAllLanguages: true,
                    IncludeAllRegions: true,
                    languageList: ['Python', 'PHP', 'Go', 'NodeJS'],
                    regionList: ['ieod', 'tencent', 'clouds'],
                    type: false
                };
                this.sortValue = 'name';
                this.filterKey = '';
                this.fetchAppList();
            },

            // 获取App类型列表及数量
            getAppCategory (includeInactive) {
                const url = `${BACKEND_URL}/api/bkapps/applications/summary/group_by_field/?field=language&include_inactive=${includeInactive}`;
                const regionUrl = `${BACKEND_URL}/api/bkapps/applications/summary/group_by_field/?field=region&include_inactive=${includeInactive}`;
                this.$http.get(url).then((res) => {
                    const langGroup = res.groups;
                    // 这里的总数是拥有的App总数，而不是筛选后得到的总数
                    this.appNumInfo.All = res.total;
                    langGroup.forEach((item) => {
                        this.appNumInfo[item.language] = item.count;
                    });
                });
                this.$http.get(regionUrl).then((res) => {
                    const regionGroup = res.groups;
                    regionGroup.forEach((item) => {
                        this.appNumInfo[item.region] = item.count;
                    });
                });
            },

            toAccessApps (appItem) {
                if (appItem.market_config && appItem.market_config.source_tp_url) {
                    window.open(appItem.market_config.source_tp_url);
                }
            },

            switchAppType (item) {
                this.curAppType = item.type !== 'all' ? item.type : '';
                this.curAppTypeActive = item.key;
                this.fetchAppList();
            },

            clearFilterKey () {
                this.filterKey = '';
                this.reset();
            },

            getParams (url) {
                if (!this.IncludeAllLanguages) {
                    this.appFilter.languageList.forEach((item) => {
                        url += '&language=' + item;
                    });
                }
                // 应用版本
                if (!this.IncludeAllRegions) {
                    this.appFilter.regionList.forEach((item) => {
                        url += '&region=' + item;
                    });
                }
                return url;
            },

            updateTableEmptyConfig (arr) {
                let url = '';
                let isParams = false;
                url = this.getParams(url);
                for (const value in this.appFilter) {
                    if (typeof this.appFilter[value] === 'boolean' && this.appFilter[value]) {
                        isParams = true;
                        break;
                    }
                };
                if (this.filterKey || isParams || url) {
                    this.tableEmptyConf.keyword = 'placeholder';
                    return;
                }
                this.tableEmptyConf.keyword = '';
            }
        }
    };
</script>

<style lang="scss" scoped>
    .bk-apps-wrapper {
        width: 100%;
        padding: 28px 0 44px;
    }

    .apps-table-wrapper {
        position: relative;
        width: 100%;
        min-height: 100px;
        &.min-h {
            min-height: 255px;
        }
        &.reset-min-h {
            min-height: 400px;
        }
        .table-item {
            width: calc(100% - 2px);
            background: #fff;
            border-radius: 2px;
            border: 1px solid #dcdee5;
            &.mt {
                margin-bottom: 10px;
            }
            &:hover {
                box-shadow: 0px 3px 6px 0px rgba(99, 101, 110, .1);
                .visit-operate .app-operation-section button i {
                    opacity: 1;
                }
            }
        }
        .ps-no-result {
            position: absolute;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
        }
        .item-header {
            width: 100%;
            height: 64px;
            line-height: 64px;
            .star-wrapper {
                display: inline-block;
                position: relative;
                width: 38px;
                height: 61px;
                cursor: pointer;
                &:hover {
                    .star-icon {
                        .paasng-star-line {
                            color: #979ba5;
                        }
                    }
                }
                .star-icon {
                    display: inline-block;
                    position: relative;
                    left: 18px;
                    top: 12px;
                    margin-right: 10px;
                    height: 31px;
                    width: 27px;
                    z-index: 1;
                    .paasng-icon {
                        position: relative;
                        top: -13px;
                        font-size: 20px;
                    }
                    .paasng-star-cover {
                        color: #ff9c01;
                    }
                    .paasng-star-line {
                        color: #dcdee5;
                    }
                }
            }
            .basic-info {
                display: inline-block;
                position: relative;
                width: 30%;
                height: 100%;
                cursor: pointer;
                &:hover {
                    .app-name {
                        color: #3a84ff;
                    }
                }
                .app-name {
                    display: inline-block;
                    position: relative;
                    top: -2px;
                    height: 100%;
                    padding-left: 6px;
                    max-width: 250px;
                    text-overflow: ellipsis;
                    overflow: hidden;
                    white-space: nowrap;
                    color: #63656e;
                    font-size: 14px;
                    font-weight: bold;
                    vertical-align: middle;
                    &:hover {
                        color: #3a84ff;
                    }
                }
                .app-logo {
                    position: relative;
                    top: 10px;
                    margin: 0 5px 0 12px;
                    width: 32px;
                    height: 32px;
                    border-radius: 4px;
                    // cursor: pointer;
                    &:hover {
                        color: #3a84ff;
                    }
                    &.reset-ml {
                        margin-left: 48px;
                    }
                }
            }
            .region-info {
                display: inline-block;
                width: 10%;
                .reg-tag {
                    display: inline-block;
                    padding: 2px 6px;
                    margin-left: 2px;
                    line-height: 16px;
                    background: #e7fcfa;
                    color: #2dcbae;
                    font-size: 12px;
                    border-radius: 2px;
                    &.inner {
                        background: #fdefd8;
                        color: #ff9c01;
                    }
                    &.clouds {
                        background: #ede8ff;
                        color: #7d01ff;
                    }
                }
            }
            .module-info {
                display: inline-block;
                width: 34%;
                cursor: pointer;
                &:hover {
                    .module-name {
                        color: #3a84ff;
                        .unfold-icon {
                            display: inline-block;
                        }
                    }
                }
                .module-name {
                    display: inline-block;
                    margin: 0 4px;
                    width: 200px;
                    height: 65px;
                    overflow: hidden;
                    vertical-align: middle;
                    color: #63656e;
                    &.expanded {
                        color: #3a84ff;
                        .unfold-icon {
                            display: inline-block;
                        }
                    }
                    // 图标默认为隐藏
                    .unfold-icon {
                        display: none;
                        position: relative;
                        top: 1px;
                        font-size: 14px;
                        color: #3a8fff;
                    }
                }
            }
            .visit-operate {
                display: inline-block;
                width: 21%;
            }
        }
        .item-content {
            .header-shadow {
                width: 100%;
                height: 5px;
                background: linear-gradient(180deg,rgba(99,101,110,1) 0%,rgba(99,101,110,0) 100%);
                opacity: .05;
            }
            .apps-table-wrapper {
                padding: 0 35px 0 54px !important;
            }
            .ps-instances-table {
                width: 100%;

                &.ps-table th,
                &.ps-table td {
                    position: relative;
                    padding: 8px 24px;
                    line-height: 24px;
                    background: #fff;
                }
            }
            .ps-table-special {
                thead {
                    th {
                        border-top: none !important;
                        border-right: none !important;
                        color: #63656e;
                        font-size: 12px;
                        font-weight: bold;
                        background: #f5f6fa !important;
                    }
                }
            }
            .module-name {
                color: #3a84ff;
                cursor: pointer;
                &:hover {
                    color: #699df4;
                }
            }
            .operate {
                margin-left: -6px;
                a:hover {
                    color: #699df4;
                }
            }
            .ps-no-result {
                height: auto;

                .text {
                    height: 90px;
                }
            }
        }
    }

    .advanced-filter {
        float: left;
        width: 98px;
        height: 32px;
        line-height: 32px;
        margin-top: 3px;
        border: 1px solid #c4c6cc;
        border-radius: 2px;
        background: #fff;
        cursor: pointer;
        z-index: 1;
        color: #63656E;
        font-size: 12px;
        &:hover {
            color: #3a84ff;
            p .paasng-icon {
                color: #3a84ff !important;
            }
        }
        p {
            text-align: center;
            .paasng-icon {
                font-size: 12px;
                color: #979BA5;
            }
        }
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

    .shaixuan,
    .shaixuan input {
        cursor: pointer;
    }

    .paas-operation-icon {
        color: #fff;
        font-size: 14px;
        height: 36px;
        line-height: 36px;
        border-radius: 18px;
        width: 120px;
        text-align: center;
        margin-left: 19px;
        background: #3A84FF;
        transition: all .5s;

        &:hover {
            background: #4b9cf2;
        }

        .paasng-icon {
            margin-right: 5px;
        }
    }

    .ps-table-app {
        color: #666;

        &:hover {
            color: #3a84ff;
        }
    }

    .ps-table-operate {
        color: #3a84ff;
        padding: 0 9px;

        &:hover {
            color: #699df4;
        }
    }

    .ps-table th.pl30,
    .ps-table td.pl30 {
        padding-left: 30px;
    }

    .ps-table tr:hover {
        .ps-table-app {
            color: #3a84ff;
        }
    }

    div.choose-panel {
        input {
            appearance: none;
        }
    }

    .table-applications {

        th,
        td {
            font-size: 14px;
        }
    }

    .table-applications {
        width: 100%;
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
        padding: 16px 0;
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
                background: #F0F1F5;
                color: #63656E;
                border-radius: 2px;
                .filter-item {
                    font-size: 12px;
                    line-height: 24px;
                    padding: 0 10px;
                    &:hover {
                        cursor: pointer;
                    }
                    &.active {
                        background: #fff;
                        color: #3A84FF;
                        border-radius: 2px;
                    }
                }
            }
        }
    }

    .clearfix::after {
        content: "";
        display: block;
        height: 0;
        clear:both;
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
        opacity: .3;
    }

    .paas-legacy-app {
        position: absolute;
        right: 482px;
    }

    .paas-search {
        width: 320px;
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

    .application-choose-btn {
        border-top: solid 1px #e9edee;
        text-align: center;
        padding: 6px 0;
    }

    .application-choose-btn a {
        width: 68px;
        height: 30px;
        line-height: 30px;
        border: solid 1px #e9edee;
        margin: 8px 5px;
        border-radius: 2px;
        color: #666;
        transition: all .5s;
    }

    .application-choose-btn a:hover {
        background: #e9edee;
    }

    .application-choose-btn a.active {
        background: #3A84FF;
        border: solid 1px #3A84FF;
        color: #fff;
    }

    .application-choose-btn a.active:hover {
        background: #3a84ff;
    }

    .application-choose img {
        position: relative;
        top: 2px;
        padding-right: 8px;
    }

    .application-list {
        overflow: hidden;
        margin: 57px -25px 31px -25px;
    }

    .application-list li {
        float: left;
        width: 360px;
        padding: 0 25px;
        text-align: center;
        color: #333;
        padding-bottom: 5px;
    }

    .application-list li h2 {
        width: 100%;
        height: 64px;
        overflow: hidden;
        font-weight: normal;
    }

    .application-list li h2 a {
        color: #333;
        font-size: 18px;
        line-height: 64px;
    }

    .application-list-text {
        height: 48px;
        overflow: hidden;
    }

    .application-list-text a {
        color: #3A84FF;
        padding: 0 4px;
    }

    .application-list li img {
        width: 360px;
        height: 180px;
        float: left;
        margin-top: 24px;
        box-shadow: 0 3px 5px #e5e5e5;
        transition: all .5s;
    }

    .application-list li:hover img {
        transform: translateY(-4px);
    }

    .application-blank {
        background: #fff;
        padding: 50px 30px;
        text-align: center;
        color: #666;
        box-shadow: 0 2px 5px #e5e5e5;
        margin-top: 2px;
    }

    .application-blank h2 {
        font-size: 18px;
        color: #333;
        line-height: 42px;
        padding: 14px 0;
        font-weight: normal;
    }

    .application-blank .paas-operation-icon {
        width: 140px;
        margin: 34px auto 30px;
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
        transition: all .5s;
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
        opacity: 0.4
    }

    .save.on:hover {
        opacity: .65;
    }

    .overflow {
        overflow: hidden;
        padding: 0 20px;
    }

    .paasng-angle-up,
    .paasng-angle-down {
        padding-left: 3px;
        transition: all .5s;
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
        width: 1180px;
    }
    .module-tr-empty {
        height: 280px;
    }
    .link-btn-cls {
        display: inline-block;
        height: 100%;
    }
</style>
