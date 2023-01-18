<template lang="html">
  <div class="right-main plugin-base-info">
    <paas-content-loader
      class="app-container middle"
      :is-loading="isLoading"
      placeholder="plugin-base-info-loading"
    >
      <paas-plugin-title />
      <section>
        <div class="basic-info-item">
          <div class="title">
            {{ $t('基本信息') }}
          </div>
          <div class="info">
            {{ $t('管理员、开发者可以修改插件名称等基本信息') }}
          </div>
          <div class="content no-border">
            <bk-form
              class="info-special-form"
              form-type="inline"
            >
              <bk-form-item style="width: 180px;">
                <label class="title-label"> {{ $t('插件标识') }} </label>
              </bk-form-item>
              <bk-form-item style="width: calc(100% - 180px);">
                <div class="item-content first-item-content">
                  {{ pluginInfo.pd_id || '--' }}
                </div>
              </bk-form-item>
            </bk-form>
            <bk-form
              class="info-special-form plugin-name-form"
              form-type="inline"
            >
              <bk-form-item style="width: 180px;">
                <label class="title-label"> {{ $t('插件名称') }} </label>
              </bk-form-item>
              <bk-form-item style="width: calc(100% - 180px);">
                <bk-input
                  v-if="isFormEdited.nameInput"
                  ref="nameInput"
                  v-model="pluginInfo.name_zh_cn"
                  :placeholder="$t('请输入插件名称')"
                  ext-cls="paas-info-app-name-cls"
                  :clearable="false"
                  :maxlength="20"
                  @blur="updatePluginBaseInfo('nameInput')"
                />
                <div
                  v-else
                  class="plugin-name-box"
                >
                  <span>{{ pluginInfo.name_zh_cn }}</span>
                  <i
                    v-bk-tooltips="$t('编辑')"
                    class="paasng-icon paasng-edit-2 plugin-name-icon"
                    @click="showEdit('nameInput')"
                  />
                </div>

                <!-- <div class="action-box">
                  <template v-if="isFormEdited.nameInput">
                    <bk-button
                      style="margin-right: 6px;"
                      theme="primary"
                      text
                      @click.stop.prevent="updatePluginBaseInfo('nameInput')"
                    >
                      {{ $t('保存') }}
                    </bk-button>
                    <bk-button
                      theme="primary"
                      text
                      @click.stop.prevent="cancelBasicInfo('nameInput', 'reset')"
                    >
                      {{ $t('取消') }}
                    </bk-button>
                  </template>
                </div> -->
              </bk-form-item>
            </bk-form>
            <!-- 属于额外字段(extra_fields) -->
            <!-- <bk-form class="info-special-form" form-type="inline">
                            <bk-form-item style="width: 180px;">
                                <label class="title-label"> {{ $t('连接器类型') }} </label>
                            </bk-form-item>
                            <bk-form-item style="width: calc(100% - 180px);">
                                <div class="item-content">{{ pluginInfo.repo_type || '--' }}</div>
                            </bk-form-item>
                        </bk-form>
                        <bk-form class="info-special-form" form-type="inline">
                            <bk-form-item style="width: 180px;">
                                <label class="title-label"> {{ $t('建议使用场景') }} </label>
                            </bk-form-item>
                            <bk-form-item style="width: calc(100% - 180px);">
                                <div class="item-content">{{ pluginInfo.test || '--' }}</div>
                            </bk-form-item>
                        </bk-form>
                        <bk-form class="info-special-form" form-type="inline">
                            <bk-form-item style="width: 180px;">
                                <label class="title-label"> {{ $t('建议日数据量') }} </label>
                            </bk-form-item>
                            <bk-form-item style="width: calc(100% - 180px);">
                                <bk-input
                                    ref="dataVolumeInput"
                                    :placeholder="$t('请输入20个字符以内的应用名称')"
                                    :readonly="!isFormEdited.dataVolumeInput"
                                    ext-cls="paas-info-app-name-cls"
                                    :clearable="false"
                                    :maxlength="20"
                                    v-model="pluginInfo.test">
                                </bk-input>

                                <div class="action-box">
                                    <template v-if="!isFormEdited.dataVolumeInput">
                                        <a class="paasng-icon paasng-edit2" v-bk-tooltips="$t('编辑')"
                                            @click="showEdit('dataVolumeInput')">
                                        </a>
                                    </template>
                                    <template v-else>
                                        <bk-button
                                            style="margin-right: 6px;"
                                            theme="primary"
                                            text
                                            @click.stop.prevent="submitBasicInfo">
                                            {{ $t('保存') }}
                                        </bk-button>
                                        <bk-button
                                            theme="primary"
                                            text
                                            @click.stop.prevent="cancelBasicInfo('dataVolumeInput')">
                                            {{ $t('取消') }}
                                        </bk-button>
                                    </template>
                                </div>
                            </bk-form-item>
                        </bk-form>
                        <bk-form class="info-special-form last-basic-form" form-type="inline">
                            <bk-form-item style="width: 180px;">
                                <label class="title-label"> {{ $t('查询模式') }} </label>
                            </bk-form-item>
                            <bk-form-item style="width: calc(100% - 180px);">
                                <div class="item-content">{{ pluginInfo.test || '--' }}</div>
                            </bk-form-item>
                        </bk-form> -->
          </div>
        </div>

        <div class="basic-info-item mt15">
          <div class="title">
            {{ $t('市场信息') }}
            <span
              class="market-edit"
              @click="toMarketInfo"
            >
              <i class="paasng-icon paasng-edit-2" />
              {{ $t('编辑') }}
            </span>
          </div>
          <div class="info">
            {{ $t('用于插件市场展示的信息') }}
          </div>
          <!-- <bk-alert type="warning" class="mt10" :show-icon="true">
                        <div slot="title">
                            {{ $t('插件市场信息从代码仓库的配置文件中获取') }}，
                            <span class="detail-doc">{{ $t('前往 tool.json 修改') }}</span>
                        </div>
                    </bk-alert> -->
          <div class="content no-border">
            <bk-form
              class="info-special-form"
              form-type="inline"
            >
              <bk-form-item style="width: 180px;">
                <label class="title-label"> {{ $t('分类') }} </label>
              </bk-form-item>
              <bk-form-item
                style="width: calc(100% - 180px);"
                :class="{ 'input-show-index': isFormEdited.classifyInput }"
              >
                <bk-input
                  ref="classifyInput"
                  :value="marketInfo.category ? marketInfo.category : marketDefault"
                  :readonly="!isFormEdited.classifyInput"
                  ext-cls="paas-info-app-name-cls"
                  :clearable="false"
                />
              </bk-form-item>
            </bk-form>
            <bk-form
              class="info-special-form"
              form-type="inline"
            >
              <bk-form-item style="width: 180px;">
                <label class="title-label"> {{ $t('简介') }} </label>
              </bk-form-item>
              <bk-form-item
                style="width: calc(100% - 180px);"
                :class="{ 'input-show-index': isFormEdited.profileInput }"
              >
                <bk-input
                  ref="profileInput"
                  :value="marketInfo.introduction ? marketInfo.introduction : marketDefault"
                  :readonly="!isFormEdited.profileInput"
                  ext-cls="paas-info-app-name-cls"
                  :clearable="false"
                />
              </bk-form-item>
            </bk-form>
            <bk-form
              :class="['info-special-form', 'user-select-wrapper', { 'user-cls': !marketInfo.contactArr.length }]"
              form-type="inline"
            >
              <bk-form-item style="width: 180px;">
                <label class="title-label"> {{ $t('联系人') }} </label>
              </bk-form-item>
              <bk-form-item
                style="width: calc(100% - 180px);"
                :class="{ 'mask-layer': !isFormEdited.contactsInput }"
              >
                <user
                  v-if="marketInfo.contactArr.length"
                  ref="contactsInput"
                  v-model="marketInfo.contactArr"
                />
                <bk-input
                  v-else
                  ref="profileInput"
                  :value="marketDefault"
                  :readonly="true"
                  ext-cls="paas-info-app-name-cls"
                  :clearable="false"
                />
                <div
                  v-if="!isFormEdited.contactsInput"
                  class="user-mask-layer"
                />
              </bk-form-item>
            </bk-form>
            <!-- 富文本 -->
            <bk-form
              class="info-special-form info-textarea"
              form-type="inline"
            >
              <bk-form-item style="width: 180px;">
                <label
                  class="title-label editor-label"
                  :style="`height: ${infoHeight}px;`"
                >
                  {{ $t('详细描述') }}
                </label>
              </bk-form-item>
              <bk-form-item
                style="width: calc(100% - 180px);"
                :class="{ 'input-show-index': isFormEdited.descriptionInput }"
              >
                <div class="content-box">
                  <div :class="['display-description', { 'description-ellipsis': editorLabelHeight }, isUnfold ? 'unfold' : 'up']">
                    <div
                      ref="editorRef"
                      v-html="marketInfo.description ? marketInfo.description : marketDefault"
                    />
                  </div>
                  <span
                    v-if="editorLabelHeight === 'down'"
                    class="unfold-btn"
                    @click="changeInfoUnfold"
                  >
                    {{ isUnfold ? '收起' : '展开' }}
                    <i :class="['paasng-icon', isUnfold ? 'paasng-angle-line-up' : 'paasng-angle-line-down']" />
                  </span>
                </div>
              </bk-form-item>
            </bk-form>
          </div>
        </div>

        <!-- 插件使用方 -->
        <div
          v-if="pluginFeatureFlags.PLUGIN_DISTRIBUTER"
          class="basic-info-item"
        >
          <div class="title">
            {{ $t('插件使用方') }}
          </div>
          <div class="info">
            {{ tipsInfo }}
          </div>
          <div class="content no-border">
            <bk-form
              class="info-special-form"
              form-type="inline"
            >
              <bk-form-item style="width: 180px;">
                <label class="title-label"> {{ $t('蓝鲸网关') }} </label>
              </bk-form-item>
              <bk-form-item style="width: calc(100% - 180px);border-top: 1px solid #dcdee5;">
                <div class="item-content border-bottm-none">
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
              <bk-form-item style="width: 180px;height: 480px;">
                <label class="title-label plugin-info">
                  <p style="height: 26px"> {{ $t('插件使用方') }} </p>
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
                  :show-overflow-tips="true"
                  :empty-content="promptContent"
                  :title="titleArr"
                  @change="transferChange"
                />
                <div class="mt20">
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
        <authentication-info v-if="pluginFeatureFlags.APP_SECRETS" />

        <div class="basic-info-item">
          <div class="title">
            {{ $t('下架插件') }}
          </div>
          <div class="info">
            {{ $t('插件下架后，插件列表、插件市场等不再展示该插件的信息') }}
          </div>
          <div class="content no-border">
            <bk-button
              theme="danger"
              @click="showRemovePlugin"
            >
              {{ $t('下架插件') }}
            </bk-button>
          </div>
        </div>
      </section>
    </paas-content-loader>

    <bk-dialog
      v-model="delPluginDialog.visiable"
      width="540"
      :title="`确认下架插件【${pluginInfo.id}】？`"
      :theme="'primary'"
      :header-position="'left'"
      :mask-close="false"
      :loading="delPluginDialog.isLoading"
      @after-leave="hookAfterClose"
    >
      <div class="ps-form">
        <div class="spacing-x1">
          {{ $t('请完整输入') }} <code>{{ pluginInfo.id }}</code> {{ $t('来确认下架插件！') }}
        </div>
        <div class="ps-form-group">
          <input
            v-model="formRemovePluginId"
            type="text"
            class="ps-form-control"
          >
          <div class="mt10 f13">
            {{ $t('注意：插件标识和名称在下架后') }} <strong> {{ $t('不会被释放') }} </strong> ，{{ $t('不能继续创建同名插件') }}
          </div>
        </div>
      </div>
      <template slot="footer">
        <bk-button
          theme="primary"
          :disabled="!formRemoveValidated"
          @click="lowerShelfPlugin"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          theme="default"
          @click="delPluginDialog.visiable = false"
        >
          {{ $t('取消') }}
        </bk-button>
      </template>
    </bk-dialog>
  </div>
</template>

<script>
    // import moment from 'moment';
    import pluginBaseMixin from '@/mixins/plugin-base-mixin';
    import paasPluginTitle from '@/components/pass-plugin-title';
    import user from '@/components/user';
    import authenticationInfo from '@/components/authentication-info.vue';
    import xss from 'xss';
    import 'BKSelectMinCss';

    const xssOptions = {
        whiteList: {
            'bk-highlight-mark': []
        }
    };
    const logXss = new xss.FilterXSS(xssOptions);
    export default {
        // components: {
        //     'bk-member-selector': () => {
        //         return import('@/components/user/member-selector/member-selector.vue');
        //     }
        // },
        components: {
            authenticationInfo,
            user,
            paasPluginTitle
        },
        mixins: [pluginBaseMixin],
        data () {
            return {
                // 插件开发
                isLoading: true,
                isFormEdited: {
                    nameInput: false,
                    dataVolumeInput: false,
                    classifyInput: false,
                    profileInput: false,
                    descriptionInput: false,
                    contactsInput: false
                },
                // 当前显示数据
                pluginInfo: {},
                // 服务器返回数据
                resPluginInfo: {
                    pd_name: ''
                },
                marketInfo: {
                    contactArr: []
                },
                marketDefault: '--',
                resMarketInfo: {},
                // 市场信息只读
                isMarketInfo: true,
                formRemovePluginId: '',
                localeAppInfo: {
                    name: '',
                    logo: '',
                    introduction: '',
                    contact: []
                },
                isUnfold: false,
                delPluginDialog: {
                    visiable: false,
                    isLoading: false
                },
                titleArr: [this.$t('可选的插件使用方'), this.$t('已授权给以下使用方')],
                promptContent: [this.$t('无数据'), this.$t('未选择已授权使用方')],
                editorConfig: {
                    visible: false,
                    position: {
                        top: 100
                    }
                },
                editorValue: '',
                editorLabelHeight: '',
                editorHeight: '',
                apiGwName: '',
                TargetDataFirst: true,
                PluginDataAllFirst: true,
                targetPluginList: [],
                AuthorizedUseList: [],
                restoringPluginList: [],
                restoringTargetData: [],
                pluginList: [],
                tipsInfo: this.$t('如果你将插件授权给某个使用方，对方便能读取到你的插件的基本信息、（通过 API 网关）调用插件的 API、并将插件能力集成到自己的系统中。')
            };
        },
        computed: {
            formRemoveValidated () {
                return this.pluginInfo.id === this.formRemovePluginId;
            },
            localLanguage () {
                return this.$store.state.localLanguage;
            },
            infoHeight () {
                return this.isUnfold ? Number(this.editorHeight) + 32 : 232;
            }
        },
        created () {
            this.init();
        },
        methods: {
            init () {
                this.getPluginBaseInfo();
                this.getMarketInfo();
                if (this.pluginFeatureFlags.PLUGIN_DISTRIBUTER) {
                    this.getPluginAll();
                    this.getAuthorizedUse();
                    this.getProfile();
                }
                if (this.pluginFeatureFlags.APP_SECRETS) {
                    this.store.dispatch('plugin/getPluginAppInfo', { pluginId: this.pluginId, pdId: this.pdId });
                }
            },

            formattParams () {
                const data = {
                    pdId: this.pdId,
                    pluginId: this.pluginId
                };
                return data;
            },

            // 基本信息
            async getPluginBaseInfo () {
                const data = this.formattParams();
                try {
                    const res = await this.$store.dispatch('plugin/getPluginBaseInfo', data);
                    this.pluginInfo = res;
                    // 取消的还原数据
                    this.resPluginInfo.name_zh_cn = res.name_zh_cn;
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    setTimeout(() => {
                        this.isLoading = false;
                    }, 200);
                }
            },

            // 市场信息
            async getMarketInfo () {
                const data = this.formattParams();
                try {
                    const res = await this.$store.dispatch('plugin/getMarketInfo', data);
                    this.marketInfo = res;
                    const contactformat = !res.contact ? [] : res.contact.split(',');
                    this.$set(this.marketInfo, 'contactArr', contactformat);
                    res.contactArr = contactformat;
                    this.resMarketInfo = JSON.stringify(res);
                    this.$nextTick(() => {
                        this.editorLabelHeight = this.$refs.editorRef && this.$refs.editorRef.offsetHeight > 200 ? 'down' : '';
                        this.editorHeight = this.$refs.editorRef && this.$refs.editorRef.offsetHeight || 232;
                    });
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    setTimeout(() => {
                        this.isLoading = false;
                    }, 200);
                }
            },

            // 保存基本信息
            async updatePluginBaseInfo (ref) {
                if (this.resPluginInfo.name_zh_cn === this.pluginInfo.name_zh_cn) {
                    this.cancelBasicInfo(ref, 'reset');
                    return;
                }
                // this.pluginInfo
                const data = {
                    name: this.pluginInfo.name_zh_cn,
                    extra_fields: {}
                };
                const query = this.formattParams();
                try {
                    await this.$store.dispatch('plugin/updatePluginBaseInfo', { ...query, data });
                    this.getPluginBaseInfo();
                    this.cancelBasicInfo(ref);
                    this.$bkMessage({
                        theme: 'success',
                        message: this.$t('基本信息修改成功！')
                    });
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                    this.cancelBasicInfo(ref, 'reset');
                }
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
                    this.$emit('current-plugin-info-updated');
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

            // 插件开发
            showEdit (key) {
                this.isFormEdited[key] = true;
                this.localeAppInfoNameTemp = this.localeAppInfo.name;
                if (key === 'contactsInput') {
                    this.$nextTick(() => {
                        this.$refs.contactsInput.$refs.member_selector.handleClick();
                    });
                    return;
                }
                this.$nextTick(() => {
                    this.$refs[key].focus();
                });
            },

            dialogAfterLeave () {
                this.isFormEdited['descriptionInput'] = false;
            },

            // ref inputRef(可修改), key当前更改的值
            cancelBasicInfo (ref, isReset) {
                // 重置数据
                if (isReset) {
                    this.resetData(ref);
                }
                this.isFormEdited[ref] = false;
                this.localeAppInfo.name = this.localeAppInfoNameTemp;
            },

            resetData (ref) {
                // 基本信息
                if (ref === 'nameInput') {
                    this.pluginInfo.name_zh_cn = this.resPluginInfo.name_zh_cn;
                }
                const marketData = JSON.parse(this.resMarketInfo);
                // 市场信息
                if (ref === 'classifyInput') {
                    this.marketInfo.category = marketData.category;
                }
                if (ref === 'profileInput') {
                    this.marketInfo.introduction = marketData.introduction;
                }
                if (ref === 'descriptionInput') {
                    this.marketInfo.description = logXss.process(marketData.description);
                }
                if (ref === 'contactsInput') {
                    this.marketInfo.contactArr = marketData.contactArr;
                }
            },

            showRemovePlugin () {
                this.delPluginDialog.visiable = true;
            },

            hookAfterClose () {
                this.delPluginDialog.visiable = false;
                this.formRemovePluginId = '';
            },

            async lowerShelfPlugin () {
                try {
                    await this.$store.dispatch('plugin/lowerShelfPlugin', {
                        pdId: this.pdId,
                        pluginId: this.pluginId,
                        data: {}
                    });
                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('插件下架成功！')
                    });
                    this.hookAfterClose();
                    this.$router.push({
                        name: 'plugin'
                    });
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                }
            },

            toMarketInfo () {
                this.$router.push({
                    name: 'marketInfoEdit'
                });
            },

            changeInfoUnfold () {
                this.isUnfold = !this.isUnfold;
            },

            // 获取可选插件适用方
            async getPluginAll () {
                try {
                    const res = await this.$store.dispatch('plugin/getPluginDistributors');
                    this.pluginList = res;
                    if (this.PluginDataAllFirst) {
                        this.restoringPluginList = this.pluginList;
                        this.PluginDataAllFirst = false;
                    }
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message || e.detail || this.$t('接口异常')
                    });
                }
            },

            arrayEqual (arr1, arr2) {
                if (arr1 === arr2) return true;
                if (arr1.length !== arr2.length) return false;
                for (let i = 0; i < arr1.length; ++i) {
                    if (arr1[i] !== arr2[i]) return false;
                }
                return true;
            },

            async getProfile () {
                try {
                    const res = await this.$store.dispatch('plugin/getProfileData', { pluginId: this.pluginId });
                    this.localeAppInfo.introduction = res.introduction;
                    this.localeAppInfo.contact = res.contact ? res.contact.split(';') : [];
                    this.apiGwName = res.api_gw_name;
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message || e.detail || this.$t('接口异常')
                    });
                }
            },

            async updateAuthorizationUse () {
                const data = this.AuthorizedUseList;
                const flag = this.arrayEqual(this.targetPluginList, data);
                if (!flag) {
                    try {
                        await this.$store.dispatch('plugin/updatePluginUser', {
                            pluginId: this.pluginId,
                            data: { distributors: data }
                        });
                        this.getPluginAll();
                        this.getAuthorizedUse();
                        this.$paasMessage({
                            theme: 'success',
                            message: this.$t('授权成功！')
                        });
                    } catch (e) {
                        this.$paasMessage({
                            theme: 'error',
                            message: e.detail
                        });
                    }
                } else {
                    this.$paasMessage({
                        theme: 'warning',
                        message: this.$t('未选择授权使用方')
                    });
                }
            },

            async getAuthorizedUse () {
                try {
                    const res = await this.$store.dispatch('plugin/getAuthorizedUse', { pluginId: this.pluginId });
                    this.targetPluginList = res.map(item => item.code_name);
                    if (this.TargetDataFirst) {
                        this.restoringTargetData = this.targetPluginList;
                        this.TargetDataFirst = false;
                    }
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message || e.detail || this.$t('接口异常')
                    });
                }
            },

            transferChange (sourceList, targetList, targetValueList) {
                this.AuthorizedUseList = targetValueList;
            },

            revivification () {
                this.pluginList.splice(0, this.pluginList.length, ...this.restoringPluginList);
                this.targetPluginList.splice(0, this.targetPluginList.length, ...this.restoringTargetData);
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
                top: -5px;
            }
            .info-special-form:nth-child(3) {
                position: relative;
                top: -11px;
            }
            .info-special-form:nth-child(4) {
                position: relative;
                top: -16px;
                z-index: 99;
            }
            .info-special-form:nth-child(5) {
                position: relative;
                top: -16px;
            }
            .info-special-form:nth-child(6) {
                position: relative;
                top: -20px;
            }
            .input-show-index {
                z-index: 10;
            }
            .item-content {
                font-size: 12px;
                padding: 0 10px 0 25px;
                height: 42px;
                line-height: 42px;
                border-right: 1px solid #dcdee5;
                border-bottom: 1px solid #dcdee5;
            }

            .first-item-content {
                border-top: 1px solid #dcdee5;
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
                font-size: 12px;
                display: inline-block;
                width: 180px;
                height: 42px;
                line-height: 42px;
                text-align: center;
                border: 1px solid #dcdee5;
                background: #FAFBFD;;
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
    .plugin-type {
        display: flex;
        align-items: center;
    }
    .action-box {
        width: 88px !important;
        z-index: 11 !important;
    }
    .description-edit {
        top: 10px;
    }
    .detail-doc {
        color: #3a84ff;
        cursor: pointer;
    }
    .edit-wrapper {
        height: 280px;
        .editor{
            height: 240px;
        }
    }
    .display-description {
        position: relative;
        // overflow: hidden;
        // text-overflow: ellipsis;
        // -webkit-line-clamp: 2;
    }
    .content-box {
        font-size: 12px;
        border: 1px solid #dcdee5;
        background: #fff;
        padding: 0 5px 30px 25px;
        border-radius: 0 2px 2px 0;
        .unfold {
            overflow: auto;
            min-height: 200px;
        }
        .up {
            height: 200px;
            overflow: hidden;
        }
        .is-down {
            transform-origin: 50% 50%;
            // transform: rotate(-180deg);
        }
    }
    .unfold-btn {
        position: absolute;
        bottom: 0;
        right: 10px;
        cursor: pointer;
        color: #3a84ff;
        i {
            transform-origin: 50% 50%;
            transform: translateX(-2px);
        }
    }
    .description-ellipsis {
        display: -webkit-box;
    }
    .user-select-wrapper {
        .user-mask-layer {
            position: absolute;
            top: 0;
            z-index: 99;
            background: transparent;
            height: 41px;
            line-height: 41px;
            width: 100%;
            border: 1px solid #dcdee5;
        }
    }
    .user-select-wrapper.user-cls .user-mask-layer {
        border-bottom: none;
    }
    .plugin-top-title {
        margin-top: 6px;
    }
    .market-edit,
    .plugin-name-icon-cls {
        cursor: pointer;
        font-size: 14px;
        font-weight: 400;
        margin-left: 5px;
        color: #3a84ff;

        i {
            font-size: 16px;
            transform: translateX(2px);
        }
    }
    .plugin-name-icon-cls {
        i {
            transform: translateX(9px);
        }
    }
    // .edit-cls {
    //     display: inline-block;
    //     width: 100%;
    //     height: 100%;
    // }
    .edit-box-cls {
        cursor: pointer;
        color: #979ba5;
        i {
            transform: translateX(8px);
        }
        .text {
            font-size: 12px;
        }
        &:hover {
            color: #3a84ff;
        }
    }
    .plugin-name-form {
        top: -4px !important;
    }
    .plugin-name-box {
        font-size: 12px;
        padding: 0 10px 0 25px;
        height: 42px;
        line-height: 42px;
        border-right: 1px solid #dcdee5;
        border-bottom: 1px solid #dcdee5;
        .plugin-name-icon {
            margin-left: 5px;
            cursor: pointer;
            color: #3a84ff;
            font-size: 16px;
        }
    }
    .border-bottm-none {
        border-bottom: none !important;
    }
    .pluginEmploy {
        height: 460px;padding: 20px 24px 0;
        border: 1px solid #dcdee5;
    }
    .explain {
        margin-top: 20px;
        p {
            line-height: 1.5em;
            color: #979ba5;
        }
    }
</style>
<style lang="scss">
    .plugin-base-info section .content .content-item label {
        background: #FAFBFD;
    }
    .plugin-base-info section .content .content-item label.first-label {
        border-bottom: 1px solid #dcdee5;
    }
    .content .paas-info-app-name-cls .bk-form-input {
        font-size: 12px !important;
    }
    .plugin-type-scope .info-special-form.bk-form.bk-inline-form .bk-select .bk-select-name {
        height: 32px;
        line-height: 32px;
        font-size: 12px;
    }
    .plugin-type-scope .info-special-form.bk-form.bk-inline-form .bk-select .bk-select-angle {
        top: 4px;
    }
    .member-cls{
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
    }
    .right-main {
        section {
            margin-top: 20px;
        }
        .cls-bk-input {
            input {
                padding-right: 85px !important;
                white-space: nowrap;
                text-overflow: ellipsis;
                overflow: hidden;
            }
        }
        .basic-info-item .content .editor-label {
            height: 232px;
            line-height: 232px;
            border-right-color: transparent;
        }
        .user-select-wrapper .bk-form-content .bk-tag-input {
            position: relative;
            z-index: 9;
            height: 41px;
            padding-right: 85px;
            padding-left: 20px;
            border-radius: 0 2px 2px 0;
            .placeholder {
                line-height: 41px;
                padding-left: 16px;
            }
        }
        .user-select-wrapper .mask-layer .bk-form-content .bk-tag-input i {
            display: none;
        }
    }

</style>
