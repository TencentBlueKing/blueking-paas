<template lang="html">
  <div class="right-main">
    <div class="ps-top-bar">
      <h2> {{ $t('基本信息') }} </h2>
    </div>
    <paas-content-loader
      class="app-container middle"
      :is-loading="isLoading"
      placeholder="base-info-loading"
    >
      <section>
        <div class="basic-info-item mt15">
          <div class="title">
            {{ $t('基本信息') }}
          </div>
          <div
            v-if="isSmartApp"
            class="info"
          >
            {{ $t('应用名称等基本信息请在“app.yaml”文件中配置') }}
          </div>
          <div
            v-else
            class="info"
          >
            {{ $t('管理员、开发者和运营者可以修改应用名称等基本信息') }}
          </div>
          <div class="content no-border">
            <bk-form
              class="info-special-form"
              form-type="inline"
            >
              <bk-form-item style="width: 180px;">
                <label class="title-label logo"> {{ $t('应用logo') }} </label>
              </bk-form-item>
              <bk-form-item style="width: calc(100% - 180px);">
                <div class="logo-uploader item-logn-content">
                  <div class="preview">
                    <img :src="localeAppInfo.logo || '/static/images/default_logo.png'">
                  </div>
                  <div
                    v-if="canEditAppBasicInfo"
                    class="preview-btn pl20"
                  >
                    <template>
                      <div>
                        <bk-button
                          :theme="'default'"
                          class="upload-btn mt5"
                        >
                          {{ $t('更换图片') }}
                          <input
                            type="file"
                            accept="image/jpeg, image/png"
                            value=""
                            name="logo"
                            @change="handlerUploadFile"
                          >
                        </bk-button>
                        <p
                          class="tip"
                          style="line-height: 1;"
                        >
                          {{ $t('支持jpg、png等图片格式，图片尺寸为72*72px，不大于2MB。') }}
                        </p>
                      </div>
                    </template>
                  </div>
                </div>
              </bk-form-item>
            </bk-form>
            <bk-form
              class="info-special-form"
              form-type="inline"
            >
              <bk-form-item style="width: 180px;">
                <label class="title-label"> {{ $t('应用名称') }} </label>
              </bk-form-item>
              <bk-form-item style="width: calc(100% - 180px);">
                <bk-input
                  ref="nameInput"
                  v-model="localeAppInfo.name"
                  :placeholder="$t('请输入20个字符以内的应用名称')"
                  :readonly="!isEdited"
                  ext-cls="paas-info-app-name-cls"
                  :clearable="false"
                  :maxlength="20"
                />

                <div
                  v-if="!isSmartApp && canEditAppBasicInfo"
                  class="action-box"
                >
                  <template v-if="!isEdited">
                    <a
                      v-bk-tooltips="$t('编辑')"
                      class="paasng-icon paasng-edit2"
                      @click="showEdit"
                    />
                  </template>
                  <template v-else>
                    <bk-button
                      style="margin-right: 6px;"
                      theme="primary"
                      :disabled="localeAppInfo.name === ''"
                      text
                      @click.stop.prevent="submitBasicInfo"
                    >
                      {{ $t('保存') }}
                    </bk-button>
                    <bk-button
                      theme="primary"
                      text
                      @click.stop.prevent="cancelBasicInfo"
                    >
                      {{ $t('取消') }}
                    </bk-button>
                  </template>
                </div>
              </bk-form-item>
            </bk-form>
            <bk-form
              v-if="platformFeature.REGION_DISPLAY"
              class="info-special-form"
              form-type="inline"
            >
              <bk-form-item style="width: 180px;">
                <label class="title-label"> {{ $t('应用版本') }} </label>
              </bk-form-item>
              <bk-form-item style="width: calc(100% - 180px);">
                <div class="item-content">
                  {{ curAppInfo.application.region_name || '--' }}
                </div>
              </bk-form-item>
            </bk-form>
            <bk-form
              class="info-special-form"
              form-type="inline"
            >
              <bk-form-item style="width: 180px;">
                <label class="title-label"> {{ $t('创建时间') }} </label>
              </bk-form-item>
              <bk-form-item style="width: calc(100% - 180px);">
                <div class="item-content">
                  {{ curAppInfo.application.created || '--' }}
                </div>
              </bk-form-item>
            </bk-form>
          </div>
        </div>
        <div
          v-if="curAppInfo.application.type !== 'cloud_native'"
          class="basic-info-item mt15"
        >
          <div class="desc-flex">
            <div class="title">
              {{ $t('应用描述文件') }}
            </div>
            <div
              class="ps-switcher-wrapper"
              @click="toggleDescSwitch"
            >
              <bk-switcher
                v-model="descAppStatus"
                :disabled="descAppDisabled"
              />
            </div>
          </div>
          <div class="info">
            {{ descAppStatus ? $t('已启用应用描述文件 app_desc.yaml，可在文件中定义环境变量，服务发现等。') : $t('未启用应用描述文件 app_desc.yaml') }}
            <a
              :href="GLOBAL.DOC.APP_DESC_DOC"
              target="_blank"
            > {{ $t('文档：什么是应用描述文件') }} </a>
          </div>
        </div>
        <div
          v-if="curAppInfo.application.type === 'bk_plugin'"
          class="basic-info-item plugin-type-scope"
        >
          <div class="title">
            {{ $t('插件信息') }}
          </div>
          <div class="info">
            {{ $t('管理插件相关信息') }}
          </div>
          <div class="content no-border">
            <bk-form
              class="info-special-form"
              form-type="inline"
            >
              <bk-form-item style="width: 180px;">
                <label class="title-label"> {{ $t('插件简介') }} </label>
              </bk-form-item>
              <bk-form-item style="width: calc(100% - 180px);">
                <bk-input
                  ref="pluginInput"
                  v-model="localeAppInfo.introduction"
                  :placeholder="pluginPlaceholder"
                  :readonly="!pluginIntroDuction"
                  ext-cls="paas-info-app-name-cls"
                  :clearable="false"
                />

                <div class="action-box">
                  <template v-if="!pluginIntroDuction">
                    <a
                      v-bk-tooltips="$t('编辑')"
                      class="paasng-icon paasng-edit2"
                      @click="showPluginEdit"
                    />
                  </template>
                  <template v-else>
                    <bk-button
                      style="margin-right: 6px;"
                      theme="primary"
                      :disabled="localeAppInfo.name === ''"
                      text
                      @click.stop.prevent="submitPluginBasicInfo('')"
                    >
                      {{ $t('保存') }}
                    </bk-button>
                    <bk-button
                      theme="primary"
                      text
                      @click.stop.prevent="cancelPluginBasicInfo"
                    >
                      {{ $t('取消') }}
                    </bk-button>
                  </template>
                </div>
              </bk-form-item>
            </bk-form>
            <bk-form
              class="info-special-form"
              form-type="inline"
            >
              <bk-form-item style="width: 180px;">
                <label class="title-label"> {{ $t('联系人员') }} </label>
              </bk-form-item>
              <bk-form-item style="width: calc(100% - 180px);">
                <!-- <bk-member-selector
                  v-if="GLOBAL.APP_VERSION === 'te'"
                  ref="member_selector"
                  v-model="localeAppInfo.contact"
                  ext-cls="member-cls"
                  :disabled="isDisabled"
                  @change="updateContact"
                />
                <blueking-user-selector
                  v-else
                  ref="member_selector"
                  v-model="localeAppInfo.contact"
                  ext-cls="member-cls"
                  display-list-tips
                  :disabled="isDisabled"
                  @change="updateContact"
                /> -->
                <user
                  ref="member_selector"
                  v-model="localeAppInfo.contact"
                  :disabled="isDisabled"
                  class="info-member-cls"
                  @change="updateContact"
                />
                <div class="action-box">
                  <template v-if="isDisabled">
                    <a
                      v-bk-tooltips="$t('编辑')"
                      class="paasng-icon paasng-edit2"
                      @click="showPluginContactEdit"
                    />
                  </template>
                  <template v-else>
                    <bk-button
                      style="margin-right: 6px;"
                      theme="primary"
                      :disabled="localeAppInfo.name === ''"
                      text
                      @click.stop.prevent="submitPluginBasicInfo({ contact: curVal })"
                    >
                      {{ $t('保存') }}
                    </bk-button>
                    <bk-button
                      theme="primary"
                      text
                      @click.stop.prevent="cancelPluginContactBasicInfo"
                    >
                      {{ $t('取消') }}
                    </bk-button>
                  </template>
                </div>
              </bk-form-item>
            </bk-form>
            <bk-form
              class="info-special-form"
              form-type="inline"
            >
              <bk-form-item style="width: 180px;">
                <label class="title-label"> {{ $t('蓝鲸网关') }} </label>
              </bk-form-item>
              <bk-form-item style="width: calc(100% - 180px);">
                <div class="item-content">
                  <span
                    v-if="apiGwName"
                    style="color: #3A84FF;"
                  >{{ $t('已绑定到') + apiGwName }}</span>
                  <span
                    v-else
                    style="color: #979ba5;"
                  > {{ $t('暂未找到已同步网关') }} </span>
                  <i
                    v-bk-tooltips="$t('网关维护者默认为应用管理员')"
                    class="paasng-icon paasng-info-circle tooltip-icon"
                  />
                </div>
              </bk-form-item>
            </bk-form>
            <bk-form
              class="info-special-form"
              form-type="inline"
            >
              <bk-form-item style="width: 180px;">
                <label class="title-label"> {{ $t('插件分类') }} </label>
              </bk-form-item>
              <bk-form-item style="width: calc(100% - 180px);">
                <div
                  ref="refPluginType"
                  :class="['item-content', 'plugin-type', { 'custom-active': !isPluginTypeSelect && isFocus }]"
                >
                  <bk-select
                    v-model="pluginTypeValue"
                    :disabled="isPluginTypeSelect"
                    clearable
                    ext-cls="select-custom"
                    searchable
                  >
                    <bk-option
                      v-for="option in pluginTypeList"
                      :id="option.id"
                      :key="option.id"
                      :name="option.name"
                    />
                  </bk-select>
                </div>
                <div class="action-box">
                  <template v-if="isPluginTypeSelect">
                    <a
                      v-bk-tooltips="$t('编辑')"
                      class="paasng-icon paasng-edit2"
                      @click="showPluginSelected"
                    />
                  </template>
                  <template v-else>
                    <bk-button
                      style="margin-right: 6px;"
                      theme="primary"
                      :disabled="localeAppInfo.name === ''"
                      text
                      @click.stop.prevent="submitPluginBasicInfo({ 'tag': pluginTypeValue })"
                    >
                      {{ $t('保存') }}
                    </bk-button>
                    <bk-button
                      theme="primary"
                      text
                      @click.stop.prevent="cancelPluginType"
                    >
                      {{ $t('取消') }}
                    </bk-button>
                  </template>
                </div>
              </bk-form-item>
            </bk-form>
            <bk-form
              class="info-special-form"
              form-type="inline"
            >
              <bk-form-item style="width: 180px;height: 480px;">
                <label class="title-label plugin-info">
                  <p style="height: 26px"> {{ $t('插件使用方') }} </p>
                  <span
                    v-bk-tooltips.bottom="tipsInfo"
                    class="bottom-middle"
                  >
                    <!-- <a href="#"> {{ $t('功能说明') }} </a> 待确定路径-->
                    <span
                      v-dashed
                      style="color: #3a84ff;height: 30px;"
                    > {{ $t('功能说明') }} </span>
                  </span>
                </label>
              </bk-form-item>
              <bk-form-item
                class="pluginEmploy"
                style="width: calc(100% - 180px);"
              >
                <bk-transfer
                  :target-list="targetPluginList"
                  :source-list="pluginList"
                  :display-key="'name'"
                  :setting-key="'code_name'"
                  :show-overflow-tips="false"
                  :empty-content="promptContent"
                  :title="titleArr"
                  @change="transferChange"
                />
                <div class="button-wrap">
                  <bk-button
                    :theme="'primary'"
                    type="submit"
                    :title="$t('保存')"
                    class="mr10"
                    @click="updateAuthorizationUse"
                  >
                    {{ $t('保存') }}
                  </bk-button>
                  <bk-button
                    :theme="'default'"
                    :title="$t('还原')"
                    class="mr10"
                    @click="revivification"
                  >
                    {{ $t('还原') }}
                  </bk-button>
                </div>
                <div class="explain">
                  <p> {{ $t('说明: 只有授权给了某个使用方，后者才能拉取到本地插件的相关信息，并在产品中通过访问插件注册到蓝鲸网关的API来使用插件功能。') }} </p>
                  <p>{{ $t('除了创建时注明的“插件使用方”之外，插件默认不授权给任何其他使用方。') }}</p>
                </div>
              </bk-form-item>
            </bk-form>
          </div>
        </div>
        <!-- 鉴权信息 -->
        <authentication-info />
        <!-- <div
          v-if="canViewSecret"
          class="basic-info-item"
        >
          <div class="title">
            {{ $t('鉴权信息') }}
          </div>
          <div class="info">
            {{ $t('在调用蓝鲸云 API 时需要提供应用鉴权信息。使用方法请参考：') }} <a
              :href="GLOBAL.DOC.APIGW_USER_API"
              target="_blank"
            > {{ $t('API调用指引') }} </a>
          </div>
          <div class="content">
            <div class="content-item">
              <label v-if="platformFeature.APP_ID_ALIAS">
                <p class="title-p">app id</p>
                <p class="title-p tip"> {{ $t('别名') }}：bk_app_code </p>
              </label>
              <label v-else>
                <p class="title-p mt15">bk_app_code</p>
              </label>
              <div class="item-practical-content">
                {{ curAppInfo.application.code }}
              </div>
            </div>
            <div class="content-item">
              <label v-if="platformFeature.APP_ID_ALIAS">
                <p class="title-p">app secret</p>
                <p class="title-p tip"> {{ $t('别名') }}：bk_app_secret </p>
              </label>
              <label v-else>
                <p class="title-p mt15">bk_app_secret</p>
              </label>
              <div class="item-practical-content">
                <span>{{ appSecretText }}</span>
                <span
                  v-if="!appSecret"
                  v-bk-tooltips="platformFeature.VERIFICATION_CODE ? $t('验证查看') : $t('点击查看')"
                  class="paasng-icon paasng-eye"
                  style="cursor: pointer;"
                  @click="onSecretToggle"
                />
                <div
                  v-if="isAcceptSMSCode"
                  class="accept-vcode"
                >
                  <p> {{ $t('验证码已发送至您的企业微信，请注意查收！') }} </p>
                  <p style="display: flex;align-items: center;">
                    <b> {{ $t('验证码：') }} </b>
                    <bk-input
                      v-model="appSecretVerificationCode"
                      type="text"
                      :placeholder="$t('请输入验证码')"
                      style="width: 200px; margin-right: 10px;"
                    />
                    <bk-button
                      v-if="appSecretTimer !== 0"
                      theme="default"
                      :disabled="true"
                    >
                      {{ appSecretTimer }}s&nbsp;{{ $t('后重新获取') }}
                    </bk-button>
                    <bk-button
                      v-else
                      theme="default"
                      @click="sendMsg"
                    >
                      {{ $t('重新获取') }}
                    </bk-button>
                  </p>
                  <p style="display: flex;">
                    <b style="visibility: hidden;"> {{ $t('验证码：') }} </b>
                    <bk-button
                      theme="primary"
                      style="margin-right: 10px;"
                      @click="getAppSecret"
                    >
                      {{ $t('提交') }}
                    </bk-button>
                    <bk-button
                      theme="default"
                      @click="isAcceptSMSCode = false"
                    >
                      {{ $t('取消') }}
                    </bk-button>
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div> -->
        <div
          v-if="canDeleteApp"
          class="basic-info-item"
        >
          <div class="title">
            {{ $t('删除应用') }}
          </div>
          <div class="info">
            {{ $t('只有管理员才能删除应用，请在删除前与应用其他成员沟通') }}
          </div>
          <div class="content no-border">
            <bk-button
              theme="danger"
              @click="showRemovePrompt"
            >
              {{ $t('删除应用') }}
            </bk-button>
            <div class="ps-text-warn spacing-x1">
              {{ $t('该操作无法撤回') }}
            </div>
          </div>
        </div>
      </section>
    </paas-content-loader>

    <bk-dialog
      v-model="delAppDialog.visiable"
      width="540"
      :title="`确认删除应用【${curAppInfo.application.name}】？`"
      :theme="'primary'"
      :header-position="'left'"
      :mask-close="false"
      :loading="delAppDialog.isLoading"
      @after-leave="hookAfterClose"
    >
      <div class="ps-form">
        <div class="spacing-x1">
          {{ $t('请完整输入') }} <code>{{ curAppInfo.application.code }}</code> {{ $t('来确认删除应用！') }}
        </div>
        <div class="ps-form-group">
          <input
            v-model="formRemoveConfirmCode"
            type="text"
            class="ps-form-control"
          >
          <div class="mt10 f13">
            {{ $t('注意：因为安全等原因，应用 ID 和名称在删除后') }} <strong> {{ $t('不会被释放') }} </strong> ，{{ $t('不能继续创建同名应用') }}
          </div>
        </div>
      </div>
      <template slot="footer">
        <bk-button
          theme="primary"
          :disabled="!formRemoveValidated"
          @click="submitRemoveApp"
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

<script>
    import moment from 'moment';
    import appBaseMixin from '@/mixins/app-base-mixin';
    import User from '@/components/user';
    // import BluekingUserSelector from '@blueking/user-selector';
    import authenticationInfo from '@/components/authentication-info.vue';
    // import 'BKSelectMinCss';

    export default {
        components: {
          authenticationInfo,
          User
          // BluekingUserSelector,
          //   'bk-member-selector': () => {
          //       return import('@/components/user/member-selector/member-selector.vue');
          //   }
        },
        mixins: [appBaseMixin],
        data () {
            return {
                isLoading: false,
                formRemoveConfirmCode: '',
                curEnv: '',
                appSecret: null,
                showingSecret: false,
                appSecretVerificationCode: '',
                appSecretTimeInterval: undefined,
                appSecretTimer: 0,
                resolveLocker: undefined,
                isAcceptSMSCode: false,
                phoneNumerLoading: true,

                localeAppInfo: {
                    name: '',
                    logo: '',
                    introduction: '',
                    contact: []
                },
                localeAppInfoNameTemp: '',
                localeAppInfoPluginTemp: '',
                rules: {
                    appName: [
                        {
                            required: true,
                            message: this.$t('请输入20个字符以内的应用名称'),
                            trigger: 'blur'
                        },
                        {
                            max: 20,
                            message: this.$t('应用名称不可超过20个字符'),
                            trigger: 'blur'
                        },
                        {
                            required: /[a-zA-Z\d\u4e00-\u9fa5]+/,
                            message: this.$t('格式不正确，只能包含：汉字、英文字母、数字'),
                            trigger: 'blur'
                        }
                    ]
                },
                delAppDialog: {
                    visiable: false,
                    isLoading: false
                },
                isEdited: false,
                pluginIntroDuction: false,
                pluginPlaceholder: this.$t('无'),
                isDisabled: true,
                curVal: '',
                contactCopy: [],
                descAppStatus: false,
                descAppDisabled: false,
                pluginList: [],
                targetPluginList: [],
                restoringPluginList: [],
                restoringTargetData: [],
                PluginDataAllFirst: true,
                TargetDataFirst: true,
                titleArr: [this.$t('可选的插件使用方'), this.$t('已授权给以下使用方')],
                promptContent: [this.$t('无数据'), this.$t('未选择已授权使用方')],
                apiGwName: '',
                AuthorizedUseList: [],
                tipsInfo: this.$t('如果你将插件授权给某个使用方，对方便能读取到你的插件的基本信息、（通过 API 网关）调用插件的 API、并将插件能力集成到自己的系统中。'),
                pluginTypeList: [],
                pluginTypeValue: '',
                isPluginTypeSelect: true,
                isFocus: true
            };
        },
        computed: {
            canDeleteApp () {
                return this.curAppInfo.role.name === 'administrator';
            },
            canViewSecret () {
                return this.curAppInfo.role.name !== 'operator';
            },
            canEditAppBasicInfo () {
                return ['administrator', 'operator'].indexOf(this.curAppInfo.role.name) !== -1;
            },
            formRemoveValidated () {
                return this.curAppInfo.application.code === this.formRemoveConfirmCode;
            },
            appSecretText () {
                if (this.appSecret && this.showingSecret) {
                    return this.appSecret;
                } else {
                    return '************';
                }
            },
            platformFeature () {
                console.warn(this.$store.state.platformFeature);
                return this.$store.state.platformFeature;
            },
            userFeature () {
                return this.$store.state.userFeature;
            },
            localLanguage () {
                return this.$store.state.localLanguage;
            },
            isPluginTypeActive () {
                return this.$route.params.pluginTypeActive;
            }
        },
        watch: {
            curAppInfo (value) {
                this.isLoading = true;
                this.localeAppInfo.name = value.application.name;
                this.localeAppInfo.logo = value.application.logo_url;
                if (value.application.type === 'bk_plugin') {
                    this.getProfile();
                }
                setTimeout(() => {
                    this.isLoading = false;
                }, 300);
            },
            'localeAppInfo.name' () {
                this.appSecret = '';
                this.appSecretTimer = 0;
            }
        },
        created () {
            moment.locale(this.localLanguage);
        },
        mounted () {
            this.descAppStatus = this.curAppInfo.feature.APPLICATION_DESCRIPTION;
            this.isLoading = true;
            this.getDescAppStatus();
            this.getPluginAll();
            this.getAuthorizedUse();
            this.init();
            if (this.curAppInfo.application.type === 'bk_plugin') {
                this.getProfile();
            }
            if (this.curAppInfo.application.name) {
                this.localeAppInfo.name = this.curAppInfo.application.name;
            }
            setTimeout(() => {
                this.isLoading = false;
            }, 300);
            this.$nextTick(() => {
                // 是否active插件分类
                if (this.isPluginTypeActive) {
                    this.showPluginSelected();
                }
            });
        },
        beforeDestroy () {
            window.removeEventListener('click', this.isCustomActive);
        },
        methods: {
            async getDescAppStatus () {
                try {
                    const res = await this.$store.dispatch('market/getDescAppStatus', this.appCode);
                    this.descAppDisabled = res.DISABLE_APP_DESC.activated;
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message || e.detail || this.$t('接口异常')
                    });
                }
            },
            async init () {
                this.initAppMarketInfo();
                this.getPluginTypeList();
                this.formRemoveConfirmCode = '';
                this.appSecret = null;
                this.showingSecret = false;
            },

            cancelBasicInfo () {
                this.isEdited = false;
                this.localeAppInfo.name = this.localeAppInfoNameTemp;
            },

            showEdit () {
                this.isEdited = true;
                this.localeAppInfoNameTemp = this.localeAppInfo.name;
                this.$refs.nameInput.focus();
            },

            cancelPluginBasicInfo () {
                this.pluginIntroDuction = false;
                this.localeAppInfo.introduction = this.localeAppInfoPluginTemp;
                this.pluginPlaceholder = this.$t('无');
            },

            cancelPluginContactBasicInfo () {
                this.isDisabled = true;
                this.localeAppInfo.contact = this.contactCopy;
            },

            showPluginEdit () {
                this.pluginIntroDuction = true;
                this.localeAppInfoPluginTemp = this.localeAppInfo.introduction;
                this.pluginPlaceholder = this.$t('请输入插件简介');
                this.$refs.pluginInput.focus();
            },

            showPluginContactEdit () {
                this.isDisabled = false;
                this.$nextTick(() => {
                    this.$refs.member_selector.focus();
                });
            },

            updateContact (curVal) {
                this.curVal = curVal.length > 0 ? curVal.join(';') : '';
            },

            async submitPluginBasicInfo (data = '') {
                let params;
                if (!data) {
                    params = {
                        introduction: this.localeAppInfo.introduction
                    };
                } else {
                    params = { ...data };
                }
                const url = `${BACKEND_URL}//api/bk_plugins/${this.curAppInfo.application.code}/profile/`;
                this.$http.patch(url, params).then(
                    res => {
                        this.$paasMessage({
                            theme: 'success',
                            message: this.$t('插件信息修改成功！')
                        });
                        if (data) {
                            this.contactCopy = res.contact ? res.contact.split(';') : [];
                        }
                    },
                    e => {
                        if (!data) this.localeAppInfo.introduction = this.localeAppInfoPluginTemp;
                        this.$paasMessage({
                            theme: 'error',
                            message: e.message || e.detail || this.$t('接口异常')
                        });
                    }
                ).finally(() => {
                    if (data) {
                        this.isDisabled = true;
                    } else {
                        this.pluginIntroDuction = false;
                        this.pluginPlaceholder = this.$t('无');
                    }
                    this.isPluginTypeSelect = true;
                });
            },

            transferChange (sourceList, targetList, targetValueList) {
                this.AuthorizedUseList = targetValueList;
            },

            arrayEqual (arr1, arr2) {
                if (arr1 === arr2) return true;
                if (arr1.length !== arr2.length) return false;
                for (let i = 0; i < arr1.length; ++i) {
                    if (arr1[i] !== arr2[i]) return false;
                }
                return true;
            },

            updateAuthorizationUse () {
                const url = `${BACKEND_URL}/api/bk_plugins/${this.appCode}/distributors/`;
                const data = this.AuthorizedUseList;
                const flag = this.arrayEqual(this.targetPluginList, data);
                if (!flag) {
                    this.$http.put(url, {
                        distributors: data
                    }).then(
                        res => {
                            this.getPluginAll();
                            this.getAuthorizedUse();
                            this.$paasMessage({
                                theme: 'success',
                                message: this.$t('授权成功！')
                            });
                        },
                        res => {
                            this.$paasMessage({
                                theme: 'error',
                                message: res.detail
                            });
                        }
                    );
                } else {
                    this.$paasMessage({
                        theme: 'warning',
                        message: this.$t('未选择授权使用方')
                    });
                }
            },

            getPluginAll () {
                const url = `${BACKEND_URL}/api/bk_plugin_distributors/`;
                this.$http.get(url).then((res) => {
                    this.pluginList = res;
                    if (this.PluginDataAllFirst) {
                        this.restoringPluginList = this.pluginList;
                        this.PluginDataAllFirst = false;
                    }
                }, (e) => {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message || e.detail || this.$t('接口异常')
                    });
                });
            },

            getAuthorizedUse () {
                const url = `${BACKEND_URL}/api/bk_plugins/${this.appCode}/distributors/`;
                this.$http.get(url).then((res) => {
                    this.targetPluginList = res.map(item => item.code_name);
                    if (this.TargetDataFirst) {
                        this.restoringTargetData = this.targetPluginList;
                        this.TargetDataFirst = false;
                    }
                }, (e) => {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message || e.detail || this.$t('接口异常')
                    });
                });
            },

            revivification () {
                this.pluginList.splice(0, this.pluginList.length, ...this.restoringPluginList);
                this.targetPluginList.splice(0, this.targetPluginList.length, ...this.restoringTargetData);
            },

            async submitBasicInfo () {
                const url = `${BACKEND_URL}/api/bkapps/applications/${this.curAppInfo.application.code}/`;
                this.$http.put(url, {
                    name: this.localeAppInfo.name
                }).then(
                    res => {
                        this.$store.commit('updateCurAppName', this.localeAppInfo.name);
                        this.$paasMessage({
                            theme: 'success',
                            message: this.$t('信息修改成功！')
                        });
                    },
                    res => {
                        this.localeAppInfo.name = this.localeAppInfoNameTemp;
                        this.$paasMessage({
                            theme: 'error',
                            message: res.detail
                        });
                    }
                ).finally(() => {
                    this.isEdited = false;
                });
            },

            showRemovePrompt () {
                this.delAppDialog.visiable = true;
            },

            hookAfterClose () {
                this.formRemoveConfirmCode = '';
            },

            submitRemoveApp () {
                const url = `${BACKEND_URL}/api/bkapps/applications/${this.curAppInfo.application.code}/`;

                this.$http.delete(url).then(
                    res => {
                        this.delAppDialog.visiable = false;
                        this.$paasMessage({
                            theme: 'success',
                            message: this.$t('应用删除成功')
                        });
                        this.$router.push({
                            name: 'myApplications'
                        });
                    },
                    res => {
                        this.$paasMessage({
                            theme: 'error',
                            message: res.detail
                        });
                        this.delAppDialog.visiable = false;
                    }
                );
            },
            onSecretToggle () {
                if (!this.userFeature.VERIFICATION_CODE) {
                    const url = `${BACKEND_URL}/api/bkapps/applications/${this.curAppInfo.application.code}/secret_verifications/`;
                    this.$http.post(url, { verification_code: '' }).then(
                        res => {
                            this.isAcceptSMSCode = false;
                            this.appSecret = res.app_secret;
                            this.showingSecret = true;
                        },
                        res => {
                            this.$paasMessage({
                                theme: 'error',
                                message: this.$t('验证码错误！')
                            });
                        }
                    );
                    return;
                }
                if (this.appSecret) {
                    this.showingSecret = !this.showingSecret;
                    return;
                }
                this.phoneNumerLoading = true;
                this.sendMsg().then(() => {
                    this.phoneNumerLoading = false;
                    this.isAcceptSMSCode = true;
                }).catch(_ => {
                    this.isAcceptSMSCode = false;
                    this.appSecretTimer = 0;
                    this.$paasMessage({
                        theme: 'error',
                        message: this.$t('请求失败，请稍候重试')
                    });
                });
            },

            getAppSecret () {
                if (this.appSecretVerificationCode === '') {
                    this.$paasMessage({
                        limit: 1,
                        theme: 'error',
                        message: this.$t('请输入验证码！')
                    });
                    return;
                }
                const form = {
                    verification_code: this.appSecretVerificationCode
                };
                const url = `${BACKEND_URL}/api/bkapps/applications/${this.curAppInfo.application.code}/secret_verifications/`;
                this.$http.post(url, form).then(
                    res => {
                        this.isAcceptSMSCode = false;
                        this.appSecret = res.app_secret;
                        this.showingSecret = true;
                    },
                    res => {
                        this.$paasMessage({
                            theme: 'error',
                            message: this.$t('验证码错误！')
                        });
                    }
                ).then(() => {
                    this.appSecretVerificationCode = '';
                });
            },

            sendMsg () {
                // 硬编码，需前后端统一
                return new Promise((resolve, reject) => {
                    this.resolveLocker = resolve;
                    if (this.appSecretTimer > 0) {
                        this.resolveLocker();
                        return;
                    }
                    const url = `${BACKEND_URL}/api/accounts/verification/generation/`;

                    this.appSecretTimer = 60;
                    this.$http.post(url, { func: 'GET_APP_SECRET' }).then(
                        res => {
                            this.appSecretVerificationCode = '';
                            this.resolveLocker();
                            if (!this.appSecretTimeInterval) {
                                this.appSecretTimeInterval = setInterval(() => {
                                    if (this.appSecretTimer > 0) {
                                        this.appSecretTimer--;
                                    } else {
                                        clearInterval(this.appSecretTimeInterval);
                                        this.appSecretTimeInterval = undefined;
                                    }
                                }, 1000);
                            }
                        },
                        res => {
                            this.appSecretVerificationCode = '';
                            reject(new Error(this.$t('请求失败，请稍候重试！')));
                        }
                    );
                });
            },

            /**
             * 选择文件后回调处理
             * @param {Object} e 事件
             */
            async handlerUploadFile (e) {
                e.preventDefault();
                const files = e.target.files;
                const data = new FormData();
                const fileInfo = files[0];
                const maxSize = 2 * 1024;
                // 支持jpg、png等图片格式，图片尺寸为72*72px，不大于2MB。验证
                const imgSize = fileInfo.size / 1024;

                if (imgSize > maxSize) {
                    this.$paasMessage({
                        theme: 'error',
                        message: this.$t('文件大小应<2M！')
                    });
                    return;
                }

                data.append('logo', files[0]);
                const params = {
                    appCode: this.appCode,
                    data: data
                };

                try {
                    const res = await this.$store.dispatch('market/uploadAppLogo', params);
                    this.localeAppInfo.logo = res.logo_url;
                    this.$emit('current-app-info-updated');
                    this.$store.commit('updateCurAppProductLogo', this.localeAppInfo.logo);

                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('logo上传成功！')
                    });
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message
                    });
                }
            },
            async initAppMarketInfo () {
                try {
                    const res = await this.$store.dispatch('market/getAppBaseInfo', this.appCode);
                    this.localeAppInfo.logo = res.application.logo_url;
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message || e.detail || this.$t('接口异常')
                    });
                }
            },
            async getProfile () {
                const url = `${BACKEND_URL}/api/bk_plugins/${this.curAppInfo.application.code}/profile/`;
                this.$http.get(url).then((res) => {
                    this.localeAppInfo.introduction = res.introduction;
                    this.localeAppInfo.contact = res.contact ? res.contact.split(';') : [];
                    this.contactCopy = res.contact ? res.contact.split(';') : [];
                    this.curVal = res.contact;
                    this.apiGwName = res.api_gw_name;
                    this.pluginTypeValue = res.tag || '';
                }, (e) => {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message || e.detail || this.$t('接口异常')
                    });
                }).finally(() => {
                    this.exportLoading = false;
                });
            },
            async toggleDescSwitch () {
                if (this.descAppDisabled) return;
                console.log(this.descAppStatus);
                let title = this.$t('确认启用应用描述文件');
                let subTitle = this.$t('启用后，可在 app_desc.yaml 文件中定义环境变量，服务发现等');
                if (this.descAppStatus) {
                    title = this.$t('确认禁用应用描述文件');
                    subTitle = this.$t('禁用后，将不再读取 app_desc.yaml 文件中定义的内容');
                }
                this.$bkInfo({
                    width: 500,
                    title: title,
                    subTitle: subTitle,
                    maskClose: true,
                    confirmFn: () => {
                        this.changeDescAppStatus();
                    }
                });
            },

            async changeDescAppStatus () {
                try {
                    const res = await this.$store.dispatch('market/changeDescAppStatus', this.appCode);
                    this.descAppStatus = res.APPLICATION_DESCRIPTION;
                    this.$store.commit('updateCurDescAppStatus', this.descAppStatus);
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message || e.detail || this.$t('接口异常')
                    });
                }
            },

            async getPluginTypeList () {
                try {
                    const data = await this.$store.dispatch('market/getPluginTypeList');
                    this.pluginTypeList = data || [];
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message || e.detail || this.$t('接口异常')
                    });
                }
            },

            showPluginSelected () {
                window.addEventListener('click', this.isCustomActive);
            },

            cancelPluginType () {
                this.isPluginTypeSelect = true;
                window.removeEventListener('click', this.isCustomActive);
            },
            isCustomActive (ev) {
                if (!this.isPluginTypeSelect) {
                    this.isFocus = this.isParent(ev.target, document.querySelector('.plugin-type'));
                }
                this.isPluginTypeSelect = false;
            },
            isParent (obj, parentObj) {
                while (obj !== undefined && obj !== null && obj.tagName.toUpperCase() !== 'BODY') {
                    if (obj === parentObj) {
                        return true;
                    }
                    obj = obj.parentNode;
                }
                return false;
            }
        }
    };
</script>

<style lang="scss" scoped>
    .desc-flex{
        display: flex;
        justify-content: flex-start;
        align-items: center;
        padding-bottom: 5px;
        .title{
            color: #313238;
            font-size: 14px;
            font-weight: bold;
            line-height: 1;
            margin-bottom: 0px !important;
        }
    }
    .basic-info-item {
        margin-bottom: 35px;
        .title {
            color: #313238;
            font-size: 14px;
            font-weight: bold;
            line-height: 1;
            margin-bottom: 5px;
        }
        .info {
            color: #979ba5;
            font-size: 12px;
        }
        .content {
            margin-top: 20px;
            border: 1px solid #dcdee5;
            border-radius: 2px;
            &.no-border {
                border: none;
            }
            .info-special-form:nth-child(2) {
                position: relative;
                top: -4px;
            }
            .info-special-form:nth-child(3) {
                position: relative;
                top: -8px;
            }
            .info-special-form:nth-child(4) {
                position: relative;
                top: -12px;
            }
            .info-special-form:nth-child(5) {
                position: relative;
                top: -16px;
            }
            .item-content {
                padding: 0 10px 0 25px;
                height: 42px;
                line-height: 42px;
                border-right: 1px solid #dcdee5;
                border-bottom: 1px solid #dcdee5;
            }

            .item-logn-content{
                padding: 20px 10px 0 25px;
                height: 105px;
                border-right: 1px solid #dcdee5;
                border-top: 1px solid #dcdee5;
                .tip {
                    font-size: 12px;
                    color: #979BA5;
                }
            }
            .title-label {
                display: inline-block;
                width: 180px;
                height: 42px;
                line-height: 42px;
                text-align: center;
                border: 1px solid #dcdee5;
            }

            .logo{
                height: 105px;
                line-height: 105px;
            }

            .plugin-info {
                height: 460px;
                padding-top: 20px;
            }

            .content-item {
                position: relative;
                height: 60px;
                line-height: 60px;
                border-bottom: 1px solid #dcdee5;
                label {
                    display: inline-block;
                    position: relative;
                    top: -1px;
                    width: 180px;
                    height: 60px;
                    border-right: 1px solid #dcdee5;
                    color: #313238;
                    vertical-align: middle;
                    .basic-p {
                        padding-left: 30px;
                    }
                    .title-p {
                        line-height: 30px;
                        text-align: center;
                        &.tip {
                            font-size: 12px;
                            color: #979ba5;
                        }
                    }
                }
                .item-practical-content {
                    display: inline-block;
                    padding-left: 20px;
                    max-width: calc(100% - 180px);
                    text-overflow: ellipsis;
                    overflow: hidden;
                    white-space: nowrap;
                    vertical-align: top;

                    .edit-input {
                        display: inline-block;
                        position: relative;
                        top: -1px;
                    }

                    .edit-button {
                        display: inline-block;
                        position: absolute;
                        right: 10px;
                    }

                    .edit {
                        position: relative;
                        color: #63656e;
                        font-weight: bold;
                        cursor: pointer;
                        &:hover {
                            color: #3a84ff;
                        }
                    }
                }
            }
            .content-item:last-child {
                border-bottom: none;
            }
            .pre-release-wrapper,
            .production-wrapper {
                display: inline-block;
                position: relative;
                width: 430px;
                border: 1px solid #dcdee5;
                border-radius: 2px;
                vertical-align: top;
                &.has-left {
                    left: 12px;
                }
                .header {
                    height: 41px;
                    line-height: 41px;
                    border-bottom: 1px solid #dcdee5;
                    background: #fafbfd;
                    .header-title {
                        margin-left: 20px;
                        color: #63656e;
                        font-weight: bold;
                        float: left;
                    }
                    .switcher-wrapper {
                        margin-right: 20px;
                        float: right;
                        .date-tip {
                            margin-right: 5px;
                            line-height: 1;
                            color: #979ba5;
                            font-size: 12px;
                        }
                    }
                }
                .ip-content {
                    padding: 14px 24px 14px 14px;
                    height: 138px;
                    overflow-x: hidden;
                    overflow-y: auto;
                    .ip-item {
                        display: inline-block;
                        margin-left: 10px;
                        vertical-align: middle;
                    }
                    .no-ip {
                        position: absolute;
                        top: 50%;
                        left: 50%;
                        transform: translate(-50%, -50%);
                        text-align: center;
                        font-size: 12px;
                        color: #63656e;
                        p:nth-child(2) {
                            margin-top: 2px;
                        }
                    }
                }
            }
            .ip-tips {
                margin-top: 7px;
                color: #63656e;
                font-size: 12px;
                i {
                    color: #ff9c01;
                }
            }
        }
    }

    .app-main-container {
        padding: 0 30px 0 30px;
    }

    .accept-vcode {
        position: relative;
        top: -6px;
        margin-top: 15px;
        padding: 20px;
        background: #fff;
        box-shadow: 0 2px 4px #eee;
        border: 1px solid #eaeeee;
        color: #666;
        z-index: 1600;

        .bk-loading2 {
            display: inline-block;
        }

        b {
            color: #333;
        }

        p {
            line-height: 30px;
            padding-bottom: 10px;
        }

        .password-text {
            padding: 0 10px;
            margin-right: 10px;
            width: 204px;
            height: 34px;
            line-height: 34px;
            border-radius: 2px 0 0 2px;
            border: solid 1px #e1e6e7;
            font-size: 14px;
            transition: all .5s;
        }

        .password-text:focus {
            outline: none;
            border-color: #e1e6e7;
            box-shadow: 0 2px 4px #eee;
        }

        .password-wait {
            background: #ccc;
            color: #fff;
            display: inline-block;
        }

        .password-submit,
        .password-reset {
            margin: 10px 10px 0 0;
            width: 90px;
            height: 34px;
            line-height: 34px;
            border: solid 1px #3A84FF;
            font-size: 14px;
            font-weight: normal;
        }

        .password-reset {
            color: #ccc;
            background: #fff;
            border: solid 1px #ccc;
        }

        .password-reset:hover {
            background: #ccc;
            color: #fff;
        }

        .get-password:after {
            content: "";
            position: absolute;
            top: -10px;
            left: 147px;
            width: 16px;
            height: 10px;
            background: url(/static/images/user-icon2.png) no-repeat;
        }

        .immediately {
            margin-left: 10px;
            width: 90px;
            height: 36px;
            line-height: 36px;
            color: #fff;
            text-align: center;
            background: #3A84FF;
            font-weight: bold;
            border-radius: 2px;
            transition: all .5s;
        }

        .immediately:hover {
            background: #4e93d9
        }

        .immediately img {
            position: relative;
            top: 10px;
            margin-right: 5px;
            vertical-align: top;
        }
    }

    .button-wrap {
        margin-top: 20px;
    }

    .explain {
        margin-top: 20px;
    }

    .explain p {
        line-height: 1.5em;
        color: #979ba5;
    }

    .pluginEmploy {
        height: 460px;padding: 20px 24px 0;
        border: 1px solid #dcdee5;
    }

    .logo-uploader {
        // margin-bottom: 15px;
        display: flex;
        overflow: hidden;

        .preview {
            img {
                width: 64px;
                height: 64px;
                border-radius: 2px;
            }
        }

        .upload-btn {
            width: 100px;
            overflow: hidden;
            margin-bottom: 10px;
            input {
                position: absolute;
                left: 0;
                top: 0;
                z-index: 10;
                height: 100%;
                min-height: 40px;
                width: 100%;
                opacity: 0;
                cursor: pointer;
            }
        }
    }
    .select-custom {
        width: 500px;
        height: 32px !important;
    }
    .custom-active {
        transition: all .2s;
        position: relative;
        border-radius: 0 2px 2px 0;
        border-color:#3a84ff !important;
        border-top: 1px solid #3a84ff;
        border-left: 1px solid #3a84ff;
        z-index: 9;
    }
    .plugin-type {
        display: flex;
        align-items: center;
    }
    .action-box {
        z-index: 11 !important;
    }
</style>
<style lang="scss">
    .plugin-type-scope .info-special-form.bk-form.bk-inline-form .bk-select .bk-select-name {
        height: 32px;
        line-height: 32px;
        font-size: 12px;
    }
    .plugin-type-scope .info-special-form.bk-form.bk-inline-form .bk-select .bk-select-angle {
        top: 4px;
    }
    .info-member-cls{
        height: 41px;
        .bk-tag-selector{
            min-height: 41px;
            .bk-tag-input{
                height: 41px !important;
                padding-left: 20px;
                border-top: 0;
                border-color: #dcdee5;
                margin-top: 1px;
                .placeholder{
                    top: 5px;
                    left: 25px;
                }
                .clear-icon{
                    margin-right: 19px !important;
                    display: none;
                }
            }

            .active{
                border-color:#3a84ff !important;
                border-top: 1px solid #3a84ff;
                border-radius: 0 2px 2px 0;
            }
        }
        .user-selector-layout{
            height: 42px !important;
            .user-selector-container{
              height: 41px !important;
              .user-selector-selected{
                margin-top: 10px;
              }
              .user-selector-input{
                margin-top: 10px;
              }
            }
          }
    }
</style>
