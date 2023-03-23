<template lang="html">
  <div class="establish">
    <div class="ps-tip-block default-info mt15">
      <i
        style="color: #3A84FF;"
        class="paasng-icon paasng-info-circle"
      />
      {{ notSmartAPP ? defaultAlertText : smartAlertText }}
    </div>
    <div class="default-app-type">
      <default-app-type
        @on-change-type="handleSwitchAppType"
      />
    </div>
    <form
      v-show="notSmartAPP"
      id="form-create-app"
      data-test-id="createDefault_form_appInfo"
      @submit.stop.prevent="submitCreateForm"
    >
      <!-- 基本信息 -->
      <div
        class="create-item"
        data-test-id="createDefault_item_baseInfo"
      >
        <div class="item-title">
          {{ $t('基本信息') }}
        </div>
        <div
          class="form-group"
          style="margin-top: 10px;"
        >
          <label class="form-label"> {{ $t('应用 ID') }} </label>
          <div class="form-group-flex">
            <p>
              <input
                type="text"
                autocomplete="off"
                name="code"
                data-parsley-required="true"
                :data-parsley-required-message="$t('该字段是必填项')"
                data-parsley-maxlength="16"
                :data-parsley-pattern="isLessCodeRule ? '[a-z]+' : '[a-z][a-z0-9-]+'"
                :data-parsley-pattern-message="isLessCodeRule ? $t('格式不正确，由小写字母组成，长度小于 16 个字符') : $t('格式不正确，只能包含：小写字母、数字、连字符(-)，首字母必须是字母，长度小于 16 个字符')"
                data-parsley-trigger="input blur"
                class="ps-form-control"
                :placeholder="isLessCodeRule ? $t('由小写字母组成，长度小于 16 个字符') : $t('由小写字母、数字、连字符(-)组成，首字母必须是字母，长度小于 16 个字符')"
              >
            </p>
            <p class="whole-item-tips">
              {{ $t('应用的唯一标识，创建后不可修改') }}
            </p>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label"> {{ $t('应用名称') }} </label>
          <p class="form-group-flex">
            <input
              type="text"
              autocomplete="off"
              name="name"
              data-parsley-required="true"
              :data-parsley-required-message="$t('该字段是必填项')"
              data-parsley-maxlength="20"
              data-parsley-pattern="[a-zA-Z\d\u4e00-\u9fa5]+"
              :data-parsley-pattern-message="$t('格式不正确，只能包含：汉字、英文字母、数字，长度小于 20 个字符')"
              data-parsley-trigger="input blur"
              class="ps-form-control"
              :placeholder="$t('由汉字、英文字母、数字组成，长度小于 20 个字符')"
            >
          </p>
        </div>
        <div
          v-if="platformFeature.REGION_DISPLAY && notBkLesscode"
          class="form-group"
          style="margin-top: 7px;"
        >
          <label class="form-label"> {{ $t('应用版本') }} </label>
          <div
            v-for="region in regionChoices"
            :key="region.key"
            class="form-group-flex-radio"
          >
            <div class="form-group-radio">
              <bk-radio-group
                v-model="regionChoose"
                style="width: 72px;"
              >
                <bk-radio
                  :key="region.key"
                  :value="region.key"
                >
                  {{ region.value }}
                </bk-radio>
              </bk-radio-group>
              <p class="whole-item-tips">
                {{ region.description }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- 应用引擎 -->
      <div
        v-if="structureType !== 'mirror'"
        :class="['create-item', { 'template-wrapper': !notBkLesscode }]"
        data-test-id="createDefault_item_appEngine"
      >
        <div class="item-title">
          {{ $t('应用模板') }}
        </div>
        <template v-if="isOpenEngine">
          <!-- 代码库 -->
          <div class="establish-tab">
            <section class="code-type">
              <label class="form-label template"> {{ $t('模板来源') }} </label>
              <div class="tab-box">
                <li
                  v-if="notBkLesscode"
                  :class="['tab-item template', { 'active': localSourceOrigin === 1 }]"
                  @click="handleCodeTypeChange(1)"
                >
                  {{ $t('蓝鲸开发框架') }}
                </li>
                <li
                  v-if="!notBkLesscode"
                  class="bk-less-code"
                >
                  {{ $t('蓝鲸可视化开发平台') }}
                </li>
                <!-- 蓝鲸插件创建入口 -->
                <!-- <li
                  v-if="curUserFeature.BK_PLUGIN_TYPED_APPLICATION && allowPluginCreation(regionChoose)"
                  :class="['tab-item', { 'active': localSourceOrigin === 3 }]"
                  @click="handleCodeTypeChange(3)"
                >
                  {{ $t('蓝鲸插件') }}
                </li> -->
                <li
                  v-if="sceneTemplateList.length && notBkLesscode"
                  :class="['tab-item template', { 'active': localSourceOrigin === 5 }]"
                  @click="handleCodeTypeChange(5)"
                >
                  {{ $t('场景模版') }}
                </li>
              </div>
            </section>
          </div>

          <div
            v-show="isBkPlugin"
            class="plugin-container"
          >
            <ul class="establish-main-list">
              <li>
                <label class="pointer">
                  <bk-radio-group v-model="isOpenSupportPlus">
                    <bk-radio
                      :value="'yes'"
                      disabled
                    > {{ $t('Python 语言') }} </bk-radio>
                  </bk-radio-group>
                </label>
                <p class="f12">
                  <a
                    target="_blank"
                    :href="GLOBAL.LINK.BK_PLUGIN"
                    style="color: #3a84ff"
                  >Python + bk-plugin-framework，{{ $t('集成插件开发框架，插件版本管理，插件运行时等模块') }}</a>
                </p>
              </li>
            </ul>
          </div>

          <div
            v-if="!isBkPlugin && sceneLocalSourceOrigin === 5 && sceneTemplateList.length"
            class="plugin-container-scene"
          >
            <div v-bkloading="{ isLoading: sceneListIsLoading, theme: 'primary', zIndex: 10 }">
              <div
                v-if="sceneTemplateList.length > 6"
                class="serch-wrapper"
              >
                <bk-input
                  v-model="sceneName"
                  :clearable="true"
                  style="margin-top: 10px;"
                  :placeholder="'场景名称'"
                  :right-icon="'bk-icon icon-search'"
                  @input="handleSearch"
                />
              </div>
              <ul
                v-if="filterSceneTemplateList.length"
                v-bkloading="{ isLoading: sceneIsLoading, theme: 'primary', zIndex: 10 }"
                :class="['scene-wrapper', !isUnfold ? 'wrapper-height' : '']"
              >
                <li
                  v-for="(item, index) in filterSceneTemplateList"
                  :key="index"
                  :class="['scene-item', item.isActive ? 'cartActive' : '']"
                  @click="cartActive(item)"
                >
                  <div class="scene-item-header">
                    <h3 :title="item.display_name">
                      {{ item.display_name }}
                    </h3>
                    <a
                      target="_blank"
                      :href="item.repo_url"
                      style="color: #3a84ff"
                    > {{ $t('查看详情') }} </a>
                  </div>
                  <div class="scene-item-body">
                    <bk-popover
                      placement="bottom-start"
                      width="300"
                    >
                      <div class="text">
                        {{ item.description }}
                      </div>
                      <div
                        slot="content"
                        style="white-space: normal;"
                      >
                        <div class="pt10 pb5 pl10 pr10">
                          {{ item.description }}
                        </div>
                      </div>
                    </bk-popover>
                  </div>
                  <div class="scene-tags-wrapper">
                    <span
                      v-for="tag in item.tags"
                      :key="tag"
                      class="tags mr5"
                    >{{ tag }}</span>
                  </div>
                </li>
              </ul>
              <div v-else>
                <div style="width: 100%; height: 128px;">
                  <chart
                    id="visitedchart"
                    style="width: 100%; height: 128px;"
                  />
                  <div
                    class="ps-no-result"
                    style="position: absolute; top: 52%; left: 50%; transform: translate(-50%, -50%);"
                  >
                    <table-empty empty />
                  </div>
                </div>
              </div>
            </div>
            <div
              v-if="filterSceneTemplateList.length > 6"
              class="icon-wrapper"
            >
              <i
                :class="['bk-icon', 'icon-angle-up', 'icon-triangle', isUnfold ? 'icon-rotate' : '']"
                @click.self="expandableListView"
              />
            </div>
          </div>

          <div
            v-show="!isBkPlugin && sourceOrigin !== GLOBAL.APP_TYPES.NORMAL_APP && !sceneLocalSourceOrigin"
            class="ps-tip-block lesscode-info mt15"
          >
            <i
              style="color: #3A84FF;"
              class="paasng-icon paasng-info-circle"
            />
            {{ $t('默认模块需要在') }} <a
              target="_blank"
              :href="GLOBAL.LINK.LESSCODE_INDEX"
              style="color: #3a84ff"
            > {{ $t('蓝鲸可视化开发平台') }} </a> {{ $t('生成源码包部署，您也可以在应用中新增普通模块。') }}
          </div>

          <div
            v-show="!isBkPlugin && sourceOrigin === GLOBAL.APP_TYPES.NORMAL_APP && sceneLocalSourceOrigin !== 5"
            class="establish-tab frame-wrapper"
          >
            <!-- 占位 -->
            <label class="frame-placeholder" />
            <div class="frame-panel">
              <section class="deploy-panel deploy-main">
                <ul
                  class="ps-tab"
                  style="position: relative; z-index: 10; padding: 0 10px"
                >
                  <li
                    v-for="(langItem, langName) in curLanguages"
                    :key="langName"
                    :class="['item', { 'active': language === langName }]"
                    @click="changeLanguage(langName)"
                  >
                    {{ $t(defaultlangName[langName]) }}
                  </li>
                </ul>
              </section>

              <div
                class="form-group establish-main card-container"
                :style="establishStyle"
              >
                <transition
                  v-if="sourceControlType"
                  :name="langTransitionName"
                >
                  <template>
                    <div
                      v-for="(langItem, langName) in curLanguages"
                      v-if="langName === language"
                      :key="langName"
                      class="options-card"
                    >
                      <ul class="establish-main-list">
                        <li
                          v-for="(item, index) in langItem"
                          :key="index"
                        >
                          <label class="pointer">
                            <input
                              v-model="sourceInitTemplate"
                              type="radio"
                              name="q"
                              :value="item.name"
                              class="ps-radio-default"
                              checked
                            >
                            {{ item.display_name }}
                          </label>
                          <p class="f12">
                            <template>
                              {{ item.description }}
                            </template>
                          </p>
                        </li>
                      </ul>
                    </div>
                  </template>
                </transition>
              </div>
            </div>
          </div>
        </template>
      </div>

      <div
        v-if="sourceOrigin === GLOBAL.APP_TYPES.NORMAL_APP && structureType !== 'mirror'"
        class="create-item"
        data-test-id="createDefault_item_appEngine"
      >
        <div class="item-title">
          {{ $t('源码管理') }}
        </div>
        <section class="code-depot">
          <label class="form-label">
            {{ $t('代码源') }}
          </label>
          <div
            v-for="(item, index) in sourceControlTypes"
            :key="index"
            :class="['code-depot-item mr10', { 'on': item.value === sourceControlType }]"
            @click="changeSourceControl(item)"
          >
            <img :src="'/static/images/' + item.imgSrc + '.png'">
            <p
              class="source-control-title"
              :title="item.name"
            >
              {{ item.name }}
            </p>
          </div>
        </section>

        <!-- Git 相关额外代码 start -->
        <template v-if="sourceOrigin === GLOBAL.APP_TYPES.NORMAL_APP">
          <div v-if="curSourceControl && curSourceControl.auth_method === 'oauth'">
            <git-extend
              :key="sourceControlType"
              :git-control-type="sourceControlType"
              :is-auth="gitExtendConfig[sourceControlType].isAuth"
              :is-loading="gitExtendConfig[sourceControlType].isLoading"
              :auth-docs="gitExtendConfig[sourceControlType].authDocs"
              :alert-text="gitExtendConfig[sourceControlType].alertText"
              :auth-address="gitExtendConfig[sourceControlType].authAddress"
              :fetch-method="gitExtendConfig[sourceControlType].fetchMethod"
              :repo-list="gitExtendConfig[sourceControlType].repoList"
              :selected-repo-url.sync="gitExtendConfig[sourceControlType].selectedRepoUrl"
            />
            <div
              v-if="deploymentIsShow"
              class="form-group-dir"
              style="margin-top: 10px;"
            >
              <label class="form-label">
                {{ $t('部署目录') }}
                <i
                  v-bk-tooltips="sourceDirTip"
                  class="paasng-icon paasng-info-circle"
                />
              </label>
              <div class="form-group-flex">
                <p>
                  <bk-input
                    v-model="sourceDirVal"
                    class="source-dir"
                    :class="sourceDirError ? 'error' : ''"
                    :placeholder="$t('请输入应用所在子目录，并确保 Procfile 文件在该目录下，不填则默认为根目录')"
                    @blur="validSourceDir"
                  />
                  <ul
                    v-if="sourceDirError"
                    class="parsley-errors-list"
                  >
                    <li class="parsley-pattern">
                      {{ $t('支持子目录、如 ab/test，允许字母、数字、点(.)、下划线(_)、和连接符(-)，但不允许以点(.)开头') }}
                    </li>
                  </ul>
                </p>
              </div>
            </div>
          </div>
          <!-- 用户自定义git、svn账号信息 start -->
          <repo-info
            v-if="curSourceControl && curSourceControl.auth_method === 'basic'"
            ref="repoInfo"
            :key="sourceControlType"
            :type="sourceControlType"
            :deployment-is-show="deploymentIsShow"
          />
          <!-- 用户自定义git、svn账号信息 end -->
        </template>
      </div>

      <div
        v-if="isShowAdvancedOptions"
        class="create-item"
        data-test-id="createDefault_item_appSelect"
      >
        <div class="item-title">
          {{ $t('高级选项') }}
        </div>
        <div
          id="choose-cluster"
          class="form-group-dir"
        >
          <label class="form-label"> {{ $t('选择集群') }} </label>
          <bk-select
            v-model="clusterName"
            style="width: 520px; margin-top: 7px;"
            searchable
            :style="errorSelectStyle"
          >
            <bk-option
              v-for="option in clusterList"
              :id="option"
              :key="option"
              :name="option"
            />
          </bk-select>
          <p
            v-if="isShowError"
            class="error-tips"
          >
            {{ $t('该字段是必填项') }}
          </p>
        </div>
      </div>

      <div
        v-if="formLoading"
        class="form-loading"
      >
        <img src="/static/images/create-app-loading.svg">
        <p> {{ $t('应用创建中，请稍候') }} </p>
      </div>
      <div
        v-else
        class="form-actions"
        data-test-id="createDefault_btn_createApp"
      >
        <bk-button
          theme="primary"
          size="large"
          class="submit-mr"
          type="submit"
        >
          {{ $t('创建应用') }}
        </bk-button>
        <bk-button
          size="large"
          class="reset-ml ml15"
          @click.prevent="back"
        >
          {{ $t('返回') }}
        </bk-button>
      </div>
    </form>
    <!-- S-mart 应用 -->
    <create-smart-app
      v-if="curCodeSource === 'smart'"
      key="smart"
    />
  </div>
</template>

<script>
    // eslint-disable-next-line
    import { Parsley, ParsleyUI } from 'parsleyjs'
    import { APP_LANGUAGES_IMAGE, DEFAULT_APP_SOURCE_CONTROL_TYPES, APP_TYPES, DEFAULR_LANG_NAME } from '@/common/constants';
    import '@/common/parsley_locale';
    import _ from 'lodash';
    import gitExtend from '@/components/ui/git-extend.vue';
    import repoInfo from '@/components/ui/repo-info.vue';
    import ECharts from 'vue-echarts/components/ECharts.vue';
    import createSmartApp from './smart';
    import defaultAppType from './default-app-type';

    export default {
        components: {
            gitExtend,
            repoInfo,
            'chart': ECharts,
            createSmartApp,
            defaultAppType
        },
        data () {
            return {
                formLoading: false,
                globalErrorMessage: '',
                language: 'Python',
                regionChoices: [],
                regionChoose: 'default',
                // sourceInitTemplate: 'dj18_with_auth',
                sourceInitTemplate: '',
                sourceControlType: this.GLOBAL.DEFAULT_SOURCE_CONTROL,
                gitExtendConfig: {
                    bk_gitlab: {
                        isAuth: true,
                        isLoading: false,
                        alertText: '',
                        authAddress: undefined,
                        fetchMethod: this.generateFetchRepoListMethod('bk_gitlab'),
                        repoList: [],
                        selectedRepoUrl: '',
                        authDocs: ''
                    },
                    tc_git: {
                        isAuth: true,
                        isLoading: false,
                        alertText: '',
                        authAddress: undefined,
                        fetchMethod: this.generateFetchRepoListMethod('tc_git'),
                        repoList: [],
                        selectedRepoUrl: '',
                        authDocs: ''
                    },
                    github: {
                        isAuth: true,
                        isLoading: false,
                        alertText: '',
                        authAddress: undefined,
                        fetchMethod: this.generateFetchRepoListMethod('github'),
                        repoList: [],
                        selectedRepoUrl: '',
                        authDocs: ''
                    },
                    gitee: {
                        isAuth: true,
                        isLoading: false,
                        alertText: '',
                        authAddress: undefined,
                        fetchMethod: this.generateFetchRepoListMethod('gitee'),
                        repoList: [],
                        selectedRepoUrl: '',
                        authDocs: ''
                    }
                },
                // For rendering template
                languages: {},
                regionDescription: '',
                language_images_map: APP_LANGUAGES_IMAGE,
                sourceControlTypes: DEFAULT_APP_SOURCE_CONTROL_TYPES,
                defaultlangName: DEFAULR_LANG_NAME,
                langTransitionName: '',
                appTypes: APP_TYPES,
                curAppType: 'web',
                allRegionsSpecs: {},

                isOpenEngine: true,
                isOpenSupportPlus: 'yes',
                supportPlusValue: true,
                isOpenCloudApi: true,
                appMarketValue: 'consistent',
                isOpenMarket: true,
                appMarketDisabled: false,
                marketDisabled: false,
                appMarketTipsParams: {
                    'consistent': 2,
                    'thirdparty': 3,
                    'no': 3
                },
                cloudApiTooltipConfig: {
                    allowHtml: true,
                    width: 240,
                    trigger: 'click',
                    theme: 'light',
                    content: '#cloud-api-tooltip',
                    placement: 'right-start',
                    onShow: () => {}
                },

                isShowTips: false,
                regionsServices: {},
                isShowAdvancedOptions: false,
                isOpenAdvancedOptions: true,
                advancedOptionsObj: {},
                // 保存与“蓝鲸插件”有关的配置，格式 {region_name: {allow_creation: false, ...}}
                bkPluginConfig: {},
                clusterName: '',
                isShowError: false,

                sourceOrigin: this.GLOBAL.APP_TYPES.NORMAL_APP,
                localSourceOrigin: this.GLOBAL.APP_TYPES.NORMAL_APP,
                curLanguages: {},
                sourceDirVal: '',
                sourceDirError: false,
                sourceDirTip: {
                    theme: 'light',
                    allowHtml: true,
                    content: this.$t('提示信息'),
                    html: `<a target="_blank" href="${this.GLOBAL.DOC.DEPLOY_DIR}" style="color: #3a84ff">${this.$t('如何设置部署目录')}</a>`,
                    placements: ['right']
                },
                isBkPlugin: false,
                structureType: 'soundCode',
                mirrorType: 'open',
                valueBkInput: '',
                mirrorData: {
                    type: 'public',
                    url: ''
                },
                isShowRadio: true,
                mirrorRules: {
                    url: [
                        {
                            required: true,
                            message: this.$t('该字段是必填项'),
                            trigger: 'blur'
                        },
                        {
                            validator: function (val) {
                                return !val.includes(':');
                            },
                            message: '镜像地址中不能包含版本(tag)信息',
                            trigger: 'blur'
                        }
                    ]
                },
                switchVal: false,
                sceneTemplateList: [],
                filterSceneTemplateList: [],
                isUnfold: false,
                sceneName: '',
                sceneInitTemplate: '',
                sceneLocalSourceOrigin: 0,
                sceneIsLoading: false,
                sceneListIsLoading: false,
                deploymentIsShow: true,
                isLessCodeRule: false,
                curCodeSource: 'default',
                defaultRegionChoose: 'default'
            };
        },
        computed: {
            isShowRegionsService () {
                return Object.keys(this.regionsServices).length > 0 && this.isOpenEngine;
            },
            clusterList () {
                return this.advancedOptionsObj[this.regionChoose] || [];
            },
            errorSelectStyle () {
                if (this.isShowError) {
                    return { borderColor: '#ff3737' };
                }
                return {};
            },
            establishStyle () {
                if (this.curLanguages && this.language && this.curLanguages[this.language]) {
                    const len = this.curLanguages[this.language].length;
                    const lanItemHeight = 50;
                    if (!len) {
                        return {
                            height: '208px'
                        };
                    }
                    return {
                        height: `${(len + 1) * lanItemHeight}px`
                    };
                }
                return {
                    height: '208px'
                };
            },
            curSourceControl () {
                const match = this.sourceControlTypes.find(item => {
                    return item.value === this.sourceControlType;
                });
                return match;
            },
            platformFeature () {
                return this.$store.state.platformFeature;
            },
            // 蓝鲸可视化平台不显示对应表单项
            notBkLesscode () {
                return this.curCodeSource !== 'bkLesscode';
            },
            notSmartAPP () {
                return this.curCodeSource !== 'smart';
            },
            defaultAlertText () {
                return this.$t('平台为该类应用提供应用引擎、增强服务、云 API 权限、应用市场等功能；适用于自主基于PaaS平台开发SaaS的场景。');
            },
            smartAlertText () {
                return this.$t('平台为该类应用提供应用引擎、增强服务等功能，并提供源码包部署和通过配置文件定义应用信息的能力；适用于熟知蓝鲸官方S-mart打包流程的SaaS开发场景。');
            }
        },
        watch: {
            globalErrorMessage (val) {
                if (val) {
                    this.$paasMessage({
                        theme: 'error',
                        message: val
                    });
                }
            },
            sourceInitTemplate (value) {
                if (value === 'dj18_hello_world' ||
                    value === 'go_gin_hello_world' ||
                    value === 'nodejs_express_hello_world' ||
                    value === 'nodejs_koa_hello_world') {
                    // this.marketDisabled = true
                    // this.appMarketDisabled = true
                    // this.appMarketValue = 'no'
                    this.isShowTips = true;
                } else {
                    // this.marketDisabled = false
                    // this.appMarketDisabled = false
                    // this.appMarketValue = 'consistent'
                    this.isShowTips = false;
                }
                if (this.isOpenEngine) {
                    this.fetchRegionsServices();
                }
                this.curAppType = this.appTypes[value];
            },
            regionChoose () {
                // 蓝鲸可视化平台推送的源码包, 无需请求场景模版
                if (this.curCodeSource === 'bkLesscode') {
                    return;
                }
                // 场景模版
                this.getSceneTemplates();
                if (this.structureType !== 'mirror') {
                    this.changeRegion();
                    this.handleCodeTypeChange(1);
                }
            },
            clusterName (value) {
                if (value) {
                    this.isShowError = false;
                }
            },
            isOpenAdvancedOptions (value) {
                if (!value) {
                    this.isShowError = false;
                    this.clusterName = '';
                }
            },
            structureType (value) {
                if (value === 'mirror') {
                    this.sourceOrigin = 4;
                } else if (value === 'soundCode') {
                    this.handleCodeTypeChange(1);
                }
            },
            sceneName (newVal, oldVal) {
                if (oldVal && !newVal) {
                    this.handleSearch();
                }
            },
            localSourceOrigin (val) {
                if (val !== 5) {
                    this.sceneInitTemplate = [];
                }
            },
            sourceOrigin (value) {
                this.isLessCodeRule = value === 2;
            }
            // localSourceOrigin () {
            //     this.sceneInitTemplate = [];
            // }
        },
        created () {
            this.fetchAdvancedOptions();
            this.fetchSpecsByRegion();
            for (const key in this.gitExtendConfig) {
                // 初始化 repo List
                const config = this.gitExtendConfig[key];
                if (key === this.sourceControlType) {
                    config.fetchMethod();
                }
            }
            this.$store.dispatch('fetchAccountAllowSourceControlType', {}).then(sourceControlTypes => {
                this.sourceControlTypes = sourceControlTypes;
                this.sourceControlTypes = this.sourceControlTypes.map(e => {
                    e.imgSrc = e.value;
                    if (e.value === 'bare_svn') {
                        e.imgSrc = 'bk_svn';
                    }
                    return e;
                });
                const sourceControlTypeValues = this.sourceControlTypes.map(item => item.value);
                sourceControlTypeValues.forEach(item => {
                    if (!Object.keys(this.gitExtendConfig).includes(item)) {
                        this.$set(this.gitExtendConfig, item, _.cloneDeep({
                            isAuth: true,
                            isLoading: false,
                            alertText: '',
                            authAddress: undefined,
                            fetchMethod: this.generateFetchRepoListMethod(item),
                            repoList: [],
                            selectedRepoUrl: ''
                        }));
                    }
                });
                for (const key in this.gitExtendConfig) {
                    // 初始化 repo List
                    const config = this.gitExtendConfig[key];
                    if (key === this.sourceControlType && ['bk_gitlab', 'tc_git', 'github', 'gitee'].includes(this.sourceControlType)) {
                        config.fetchMethod();
                    }
                }
            });
        },
        mounted () {
            this.form = $('#form-create-app').parsley();
            this.$form = this.form.$element;

            // Auto clearn ServerError message for field
            this.form.on('form:validated', (target) => {
                _.each(target.fields, (field) => {
                    field.removeError('serverError');
                });
            });
            window.Parsley.on('field:error', function () {
                // 防止出现多条错误提示
                this.$element.parsley().removeError('serverError');
            });
        },
        methods: {
            handleOpenLink () {
                window.open(this.GLOBAL.LINK.LESSCODE_INDEX);
            },

            handleCodeTypeChange (payload) {
                this.localSourceOrigin = payload;
                this.sceneLocalSourceOrigin = 0;
                this.deploymentIsShow = true;
                if (payload !== 5) {
                    this.sceneInitTemplate = '';
                }
                if (payload === this.GLOBAL.APP_TYPES.NORMAL_APP) {
                    this.sourceOrigin = payload;
                    this.curLanguages = _.cloneDeep(this.languages);
                    this.language = 'Python';
                    this.isBkPlugin = false;
                } else {
                    if (payload === 2) {
                        this.curLanguages = _.cloneDeep({
                            'NodeJS': [this.languages['NodeJS'][0]]
                        });
                        this.language = 'NodeJS';
                        this.isBkPlugin = false;
                        this.sourceOrigin = payload;
                    } else if (payload === 3) {
                        this.isBkPlugin = true;
                        this.sourceOrigin = 1;
                    } else if (payload === 5) {
                        this.isBkPlugin = false;
                        this.sourceOrigin = 1;
                        this.sceneLocalSourceOrigin = 5;
                        this.deploymentIsShow = false;
                        this.cartActive(this.sceneTemplateList[0]);
                    }
                }
                this.sourceInitTemplate = this.curLanguages[this.language][0].name;
            },
            toCloudApi () {
                window.open(this.GLOBAL.DOC.API_HELP);
            },
            engineChange (value) {
                this.supportPlusValue = value;
                if (!value) {
                    this.appMarketValue = 'thirdparty';
                    // this.marketDisabled = false
                    // this.appMarketDisabled = false
                    this.isShowTips = false;
                } else {
                    this.appMarketValue = 'consistent';
                    if (['dj18_hello_world', 'go_gin_hello_world', 'nodejs_express_hello_world', 'nodejs_koa_hello_world'].includes(this.sourceInitTemplate)) {
                        // this.marketDisabled = true
                        // this.appMarketValue = 'no'
                        // this.appMarketDisabled = true
                        this.isShowTips = true;
                    } else {
                        // this.appMarketValue = 'consistent'
                        this.isShowTips = false;
                    }
                }
            },
            back () {
                this.$router.push({
                    name: 'myApplications'
                });
            },
            async fetchAdvancedOptions () {
                let res;
                try {
                    res = await this.$store.dispatch('createApp/getOptions');
                } catch (e) {
                    // 请求接口报错时则不显示高级选项
                    this.isShowAdvancedOptions = false;
                    return;
                }

                // 初始化蓝鲸插件相关配置
                (res.bk_plugin_configs || []).forEach(c => {
                    this.bkPluginConfig[c.region] = c;
                });

                // 如果返回当前用户不支持“高级选项”，停止后续处理
                if (!res.allow_adv_options) {
                    this.isShowAdvancedOptions = false;
                    return;
                }

                // 高级选项：解析分 Region 的集群信息
                this.isShowAdvancedOptions = true;
                const advancedRegionClusters = res.adv_region_clusters || [];
                advancedRegionClusters.forEach(item => {
                    if (!this.advancedOptionsObj.hasOwnProperty(item.region)) {
                        this.$set(this.advancedOptionsObj, item.region, item.cluster_names);
                    }
                });
            },
            allowPluginCreation (region) {
                // 检查当前选择的 region 是否允许创建蓝鲸插件
                const config = this.bkPluginConfig[region];
                return !!(config && config.allow_creation);
            },
            async fetchRegionsServices () {
                // console.warn('fetchRegionsServices')
                try {
                    const res = await this.$store.dispatch('createApp/getRegionsServices', {
                        region: this.regionChoose,
                        language: this.sourceInitTemplate
                    });
                    this.regionsServices = JSON.parse(JSON.stringify(res.result));
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                }
            },
            fetchSpecsByRegion () {
                this.$http.get(BACKEND_URL + '/api/bkapps/regions/specs').then((resp) => {
                    this.allRegionsSpecs = resp;
                    _.forEachRight(this.allRegionsSpecs, (value, key) => {
                        this.regionChoices.push({
                            key: key,
                            value: value.display_name,
                            description: value.description
                        });
                    });
                    this.regionChoose = this.regionChoices[0].key;
                    this.defaultRegionChoose = this.regionChoices[0].key;
                    this.languages = this.allRegionsSpecs[this.regionChoose].languages;
                    this.curLanguages = _.cloneDeep(this.languages);
                    this.sourceInitTemplate = this.languages[this.language][0].name;
                    // console.warn(this.sourceInitTemplate)
                    this.regionDescription = this.allRegionsSpecs[this.regionChoose].description;
                });
            },
            generateFetchRepoListMethod (sourceControlType) {
                // 根据不同的 sourceControlType 生成对应的 fetchRepoList 方法
                return async () => {
                    const config = this.gitExtendConfig[sourceControlType];
                    try {
                        config.isLoading = true;
                        const resp = await this.$store.dispatch('getRepoList', { sourceControlType });
                        config.repoList = resp.results.map((repo, index) => {
                            return { name: repo.fullname, id: repo.http_url_to_repo };
                        });
                        config.isAuth = true;
                    } catch (e) {
                        const resp = e.response;
                        config.isAuth = false;
                        if (resp.status === 403 && resp.data.result) {
                            config.authAddress = resp.data.address;
                            config.authDocs = resp.data.auth_docs;
                        }
                    } finally {
                        config.isLoading = false;
                    }
                };
            },
            changeRegion () {
                // 重置选择
                this.clusterName = '';
                this.languages = this.allRegionsSpecs[this.regionChoose] && this.allRegionsSpecs[this.regionChoose].languages;
                this.regionDescription = this.allRegionsSpecs[this.regionChoose] && this.allRegionsSpecs[this.regionChoose].description;
                this.language = 'Python';
                this.langTransitionName = 'lang-card-to-right';
                this.sourceOrigin = this.GLOBAL.APP_TYPES.NORMAL_APP;
                this.curLanguages = _.cloneDeep(this.languages);
                this.sourceInitTemplate = this.curLanguages[this.language][0].name;
            },
            changeLanguage (language) {
                const fromLanguage = this.language;
                this.language = language;
                // Select the first choice of selected language
                this.sourceInitTemplate = this.languages[this.language][0].name;

                // Detect animate direction
                const languageList = _.map(this.languages, (langItem, langName) => langName);
                if (languageList.indexOf(fromLanguage) > languageList.indexOf(language)) {
                    this.langTransitionName = 'lang-card-to-right';
                } else {
                    this.langTransitionName = 'lang-card-to-left';
                }
            },
            changeSourceControl (item) {
                this.sourceDirError = false;
                this.sourceDirVal = '';
                this.sourceControlType = item.value;
                const curGitConfig = this.gitExtendConfig[this.sourceControlType];
                if (curGitConfig && curGitConfig.repoList.length < 1 && ['bk_gitlab', 'tc_git', 'github', 'gitee'].includes(this.sourceControlType)) {
                    curGitConfig.fetchMethod();
                }
            },
            changeScenarioTemplate () {
                const item = this.filterSceneTemplateList.filter(v => v.isActive);
                if (item.length) {
                    this.sceneInitTemplate = item[0].name;
                }
            },
            validSourceDir () {
                const val = this.sourceDirVal || '';
                if (!val) {
                    this.sourceDirError = false;
                    return;
                }
                this.sourceDirError = !/^((?!\.)[a-zA-Z0-9_./-]+|\s*)$/.test(val);
            },

            // 创建应用提交封装
            async submitCreateFormFun () {
                let sourceRepoUrl = null;
                if (this.sourceOrigin === this.GLOBAL.APP_TYPES.NORMAL_APP && ['bare_git', 'bare_svn'].includes(this.sourceControlType)) {
                    if (this.$refs.repoInfo) {
                        const validRet = await this.$refs.repoInfo.valid();
                        if (!validRet) {
                            window.scrollTo(0, 0);
                            return;
                        }
                    }
                }

                this.formLoading = true;
                // Remove all serverError error messages
                this.globalErrorMessage = '';
                this.form.reset();
                if (this.isOpenEngine && this.sourceOrigin === this.GLOBAL.APP_TYPES.NORMAL_APP) {
                    switch (this.sourceControlType) {
                        case 'bk_gitlab':
                        case 'github':
                        case 'gitee':
                        case 'tc_git':
                            const config = this.gitExtendConfig[this.sourceControlType];
                            sourceRepoUrl = config.selectedRepoUrl;
                            if (!sourceRepoUrl) {
                                this.formLoading = false;
                                this.$paasMessage({
                                    theme: 'error',
                                    message: config.isAuth ? this.$t('请选择关联的远程仓库') : this.$t('请关联 git 账号')
                                });
                                window.scrollTo(0, 0);
                                return;
                            }
                            break;
                        case 'bk_svn':
                        default:
                            sourceRepoUrl = undefined;
                            break;
                    }
                }
                const formData = this.$form.serializeObject();

                const params = {
                    type: this.isBkPlugin ? 'bk_plugin' : 'default',
                    region: this.regionChoose || formData.region,
                    code: formData.code,
                    name: formData.name,
                    engine_enabled: this.isOpenEngine,
                    engine_params: {
                        source_init_template: this.sourceInitTemplate,
                        source_control_type: this.sourceControlType,
                        source_repo_url: sourceRepoUrl,
                        source_origin: this.sourceOrigin,
                        source_dir: this.sourceDirVal || ''
                    },
                    market_params: {
                        // TODO: 移除魔数
                        source_url_type: this.appMarketTipsParams[this.appMarketValue],
                        source_tp_url: formData.source_tp_url,
                        enabled: this.isOpenMarket
                    },
                    advanced_options: {
                        cluster_name: this.clusterName
                    }
                };

                if (this.sceneInitTemplate.length && this.sceneLocalSourceOrigin === 5) {
                    params.engine_params.source_init_template = this.sceneInitTemplate;
                    params.engine_params.source_origin = 5;
                }

                if (this.isBkPlugin) {
                    delete params.engine_params.source_init_template;
                }

                if (this.sourceOrigin !== this.GLOBAL.APP_TYPES.NORMAL_APP && !this.sceneInitTemplate.length) {
                    delete params.engine_params.source_repo_url;
                }

                if (!this.isOpenAdvancedOptions || !this.clusterName) {
                    delete params.advanced_options;
                }

                if (this.sourceOrigin === this.GLOBAL.APP_TYPES.NORMAL_APP && ['bare_git', 'bare_svn'].includes(this.sourceControlType)) {
                    if (this.$refs.repoInfo) {
                        const repoData = this.$refs.repoInfo.getData();
                        params.engine_params.source_repo_url = repoData.url;
                        params.engine_params.source_repo_auth_info = {
                            username: repoData.account,
                            password: repoData.password
                        };
                        params.engine_params.source_dir = repoData.sourceDir;
                    }
                }

                if (!params.engine_enabled) {
                    delete params.engine_params;
                }

                if (this.sourceOrigin === this.GLOBAL.APP_TYPES.IMAGE) {
                    params.type = 'default';
                    params.engine_params.source_control_type = 'tc_docker';
                    params.engine_params.source_repo_url = this.GLOBAL.APP_VERSION === 'te' ? `mirrors.tencent.com/${this.mirrorData.url}` : `${this.mirrorData.url}`;
                    params.engine_params.source_repo_auth_info = {
                        username: '',
                        password: ''
                    };
                }

                this.$http.post(BACKEND_URL + '/api/bkapps/applications/v2/', params).then(
                    (resp) => {
                        const objectKey = `SourceInitResult${Math.random().toString(36)}`;
                        if (resp.source_init_result) {
                            localStorage.setItem(objectKey, JSON.stringify(resp.source_init_result.extra_info));
                        }
                        const path = this.isOpenEngine ? `/developer-center/apps/${resp.application.code}/create/${this.sourceControlType}/success` : `/developer-center/apps/${resp.application.code}/create/success`;
                        this.$router.push({
                            path: path,
                            query: { objectKey: objectKey }
                        });
                    },
                    (resp) => {
                        const body = resp;
                        let fieldFocused = false;
                        // Error message for individual fields
                        if (body.fields_detail !== undefined) {
                            _.forEach(body.fields_detail || [], (detail, key) => {
                                if (key === 'non_field_errors') {
                                    this.globalErrorMessage = detail[0];
                                    window.scrollTo(0, 0);
                                } else {
                                    const field = this.$form.find(`input[name="${key}"]`).parsley();
                                    if (field) {
                                        field.addError('serverError', { message: detail[0] });
                                        if (!fieldFocused) {
                                            field.$element.focus();
                                            fieldFocused = true;
                                        }
                                        setTimeout(() => {
                                            field.removeError('serverError', { updateClass: true });
                                        }, 3000);
                                    } else {
                                        this.globalErrorMessage = detail[0];
                                        window.scrollTo(0, 0);
                                    }
                                }
                            });
                        } else {
                            this.globalErrorMessage = body.detail;
                            window.scrollTo(0, 0);
                        }
                    }).then(
                    () => {
                        this.formLoading = false;
                    }
                );
            },

            // 创建应用提交
            async submitCreateForm () {
                if (!this.form.isValid()) {
                    return;
                }

                if (this.sourceDirError) {
                    return;
                }

                // 镜像地址填写允许创建
                if (this.$refs.validate2) {
                    this.$refs.validate2.validate().then(validator => {
                        this.submitCreateFormFun();
                    }, err => {
                        return err;
                    });
                } else {
                    this.submitCreateFormFun();
                }
            },
            handleToggleType (type) {
                console.log(typeof type);
                if (typeof type === 'string') {
                    this.isBkPlugin = true;
                } else {
                    this.sourceOrigin = type;
                }
            },

            getSceneTemplates () {
                this.sceneListIsLoading = true;
                this.filterSceneTemplateList = [];
                this.$http.get(BACKEND_URL + `/api/bkapps/scene/tmpls/?region=${this.regionChoose}`).then((resp) => {
                    resp.forEach(v => {
                        v.isActive = false;
                    });
                    this.sceneTemplateList = resp;
                    this.filterSceneTemplateList = resp;
                    this.sceneListIsLoading = false;
                    this.cartActive(this.sceneTemplateList[0]);
                });
            },

            expandableListView () {
                this.isUnfold = !this.isUnfold;
            },

            handleSearch () {
                if (!this.sceneTemplateList.length) {
                    return;
                }
                this.sceneIsLoading = true;
                this.sceneSearch();
            },

            sceneSearch: _.debounce(function () {
                this.filterSceneTemplateList = this.sceneTemplateList.filter(v => {
                    if (v.display_name.toLowerCase().indexOf(this.sceneName.toLowerCase()) === -1) {
                        this.sceneIsLoading = false;
                        return false;
                    }
                    this.sceneIsLoading = false;
                    return true;
                });
            }, 350),

            cartActive (data) {
                this.filterSceneTemplateList.forEach(v => {
                    v.isActive = false;
                    if (data.name === v.name) {
                        v.isActive = true;
                    }
                });
                this.changeScenarioTemplate();
            },

            // 切换应用类型
            handleSwitchAppType (codeSource) {
                this.curCodeSource = codeSource;
                this.$nextTick(() => {
                    // 蓝鲸可视化平台推送的源码包
                    if (codeSource === 'bkLesscode') {
                        this.regionChoose = this.GLOBAL.APP_VERSION === 'te' ? 'ieod' : 'default';
                        this.structureType = 'soundCode';
                        this.handleCodeTypeChange(2);
                    } else if (codeSource === 'default') {
                        // 普通应用
                        this.regionChoose = this.defaultRegionChoose;
                    }
                });
            }
        }
    };
</script>

<style lang="scss" scoped>
    @import './default.scss';
</style>
<style lang="scss">
@import '~@/assets/css/mixins/border-active-logo.scss';
#choose-cluster {
    .bk-select {
        width: 520px;
        height: 42px;
        .bk-select-name {
            height: 40px;
        }

        .bk-select-angle {
            top: 10px;
        }

        .bk-select-loading {
            top: 10px;
        }

        &.is-unselected:before {
            line-height: 40px;
        }

        .bk-select-name {
            line-height: 40px;
        }
    }
}
.form-group-flex-radio {
    width: 100%;
}
.construction-manner {
    display: flex;
    width: 100%;
}
.bk-form-control .group-box .group-text {
    line-height: 38px;
}
.item-cls {
    .bk-form-content{
        .form-error-tip{
            margin: 5px 0 0 260px;
        }
    }
}

.plugin-container-scene {
    background: #fafafa;
    padding: 8px 20px;
    .serch-wrapper {
        position: relative;
        z-index: 99;
        width: 210px;
        margin-left: auto;
        margin-bottom: 14px;
    }
    .cartActive {
        position: relative;
        border: 2px solid #3a84ff;
        border-radius: 2px;
        @include border-active-logo;
    }
    .icon-wrapper {
        text-align: center;
        .icon-triangle {
            padding: 0 10px;
            font-size: 26px;
            font-weight: 700;
            margin-top: 12px;
            display: inline-block;
            transform: rotate(180deg);
            transition: all .3s;
        }
        .icon-rotate {
            transform: rotate(360deg);
        }
    }
    .scene-wrapper {
        display: grid;
        justify-content: space-between;
        grid-template-columns: repeat(auto-fill, 285px);
        grid-gap: 20px;
        padding: 10px 0;
        overflow: hidden;
    }
    .wrapper-height {
        max-height: 270px;
    }
    .scene-item {
        width: 280px;
        height: 120px;
        padding: 12px;
        background: #FFF;
        border-radius: 2px;
        box-sizing: border-box;
        &:hover {
            cursor: pointer;
        }
    }
    .scene-item-header {
        display: flex;
        justify-content: space-between;
        h3 {
            font-size: 14px;
            font-weight: 500;
            color: #222222;
            line-height: 20px;
            flex: 1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        a {
            width: 64px;
            font-size: 12px;
            line-height: 20px;
            text-align: right;
        }
    }
    .scene-item-body {
        height: 55px;
        margin-top: 5px;

        .text {
            font-size: 10px;
            line-height: 16px;
            color: #979ba5;
            word-break: break-all;
            overflow: hidden;
            text-overflow: ellipsis;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            overflow:hidden;
            /*! autoprefixer: off */
            -webkit-box-orient: vertical;
        }
    }
    .scene-tags-wrapper {
        .tags {
            display: inline-block;
            padding: 2px 5px;
            background: #eaedf2;
            border-radius: 1px;
            font-size: 10px;
            font-size: 10px;
            font-weight: 400;
            color: #63656e;
            border-radius: 1px;
            &:last-child {
                margin-right: 0 !important;
            }
        }
    }
}

.template-wrapper {
  .form-label {
      line-height: 32px !important;
  }
  .bk-less-code {
      font-size: 14px;
      color: #313238;
      line-height: 32px;
  }
}

</style>
