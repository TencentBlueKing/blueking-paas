<template lang="html">
  <div class="right-main">
    <paas-content-loader
      class="app-container middle base-info-container"
      :is-loading="isLoading"
      placeholder="base-info-loading"
    >
      <section>
        <!-- 基本信息 -->
        <div class="basic-info-item info-card-style">
          <div class="title">
            {{ $t('基本信息-title') }}
            <div
              v-if="!appBaseInfoConfig.isEdit"
              :class="['edit-container', { 'disabled': !isBasicInfoEditable }]"
              @click="handleEditBaseInfo">
              <i class="paasng-icon paasng-edit-2 pl10" />
              {{ $t('编辑') }}
            </div>
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
          <section class="main">
            <!-- 查看态 -->
            <div class="view-mode" v-if="!appBaseInfoConfig.isEdit">
              <section class="info-warpper">
                <div class="row">
                  <div class="item">
                    <div class="label">{{ $t('应用名称') }}：</div>
                    <div class="value" v-bk-overflow-tips>{{ localeAppInfo.name || '--' }}</div>
                  </div>
                  <div class="item" v-if="platformFeature.REGION_DISPLAY">
                    <div class="label">{{ $t('应用版本') }}：</div>
                    <div class="value">{{ curAppInfo.application.region_name || '--' }}</div>
                  </div>
                </div>
                <div class="item">
                  <div class="label">{{ $t('创建时间') }}：</div>
                  <div class="value">{{ curAppInfo.application.created || '--' }}</div>
                </div>
              </section>
              <div class="logo-wrapper">
                <img :src="localeAppInfo.logo || '/static/images/default_logo.png'">
              </div>
            </div>
            <!-- 编辑态 -->
            <div class="edit-mode" v-else>
              <bk-form
                :label-width="200"
                :model="localeAppInfo"
                form-type="vertical"
                ref="formNameRef">
                <bk-form-item
                  :label="$t('应用名称')"
                  :property="'name'"
                  :rules="rules.name"
                  :required="true"
                  :error-display-type="'normal'">
                  <bk-input v-model="localeAppInfo.name"></bk-input>
                </bk-form-item>
                <bk-form-item :label="$t('应用版本')" v-if="platformFeature.REGION_DISPLAY">
                  <bk-input disabled v-model="curAppInfo.application.region_name"></bk-input>
                </bk-form-item>
                <bk-form-item label="LOGO">
                  <div class="logoupload-wrapper">
                    <div
                      :class="['logoupload-cls', { 'preview': appBaseInfoConfig.isPreviewImageShow }]"
                      @mouseenter="isMaskLayerShown = true"
                      @mouseleave="isMaskLayerShown = false"
                    >
                      <!-- 默认 -->
                      <div class="logoupload-content">
                        <i class="bk-icon icon-plus-line"></i>
                        <p>{{ $t('点击上传') }}</p>
                      </div>
                      <!-- 预览图 -->
                      <div class="preview-image-cls">
                        <img id="preview-image" />
                      </div>
                      <!-- 遮罩层 -->
                      <div class="logo-mask-layer-cls" v-if="appBaseInfoConfig.isPreviewImageShow && isMaskLayerShown">
                        <i class="paasng-icon paasng-close" @click="handleClose"></i>
                        <i class="paasng-icon paasng-upload-2" @click="handleInputClick"></i>
                      </div>
                      <input
                        ref="logoInputRef"
                        type="file"
                        accept="image/jpeg, image/png"
                        name="logo"
                        @change="beforeFileUploadProcessing"
                      >
                    </div>
                    <p class="tip">
                      {{ $t('支持jpg、png等图片格式，图片尺寸为72*72px，不大于2MB。') }}
                    </p>
                  </div>
                </bk-form-item>
                <bk-form-item class="mt20 base-info-form-btn">
                  <bk-button
                    ext-cls="mr8"
                    theme="primary"
                    :loading="appBaseInfoConfig.isLoading"
                    @click.stop="handleSubmitBaseInfo">
                    {{ $t('提交') }}
                  </bk-button>
                  <bk-button
                    ext-cls="mr8"
                    theme="default"
                    :disabled="appBaseInfoConfig.logoData === null"
                    @click="handlePreview">{{ $t('预览') }}</bk-button>
                  <bk-button
                    theme="default"
                    @click="handlerBaseInfoCancel">
                    {{ $t('取消') }}
                  </bk-button>
                </bk-form-item>
              </bk-form>
            </div>
          </section>
        </div>

        <!-- 应用描述文件 -->
        <div
          v-if="curAppInfo.application.type !== 'cloud_native'"
          class="basic-info-item mt16 info-card-style"
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
                theme="primary"
                size="small"
                :disabled="descAppDisabled"
              />
            </div>
          </div>
          <div class="info">
            {{ descAppStatus ? $t('已启用应用描述文件 app_desc.yaml，可在文件中定义环境变量，服务发现等。') : $t('未启用应用描述文件 app_desc.yaml') }}
            <a
              :href="GLOBAL.DOC.APP_DESC_DOC"
              target="_blank"
            >
              <i class="paasng-icon paasng-process-file"></i>
              {{ $t('文档：什么是应用描述文件') }}
            </a>
          </div>
        </div>

        <!-- 插件信息 -->
        <plugin-info v-if="curAppInfo.application.is_plugin_app" />

        <!-- 鉴权信息 -->
        <authentication-info
          v-if="canViewSecret"
          ref="authenticationRef"
        />

        <div
          v-if="canDeleteApp"
          class="delete-app-wrapper mt16"
        >
          <bk-button
            theme="danger"
            @click="showRemovePrompt"
          >
            {{ $t('删除应用') }}
          </bk-button>
          <p>
            <i class="paasng-icon paasng-paas-remind-fill mr5"></i>
            {{ $t('只有管理员才能删除应用，请在删除前与应用其他成员沟通') }}
          </p>
        </div>
      </section>
    </paas-content-loader>

    <bk-dialog
      v-model="delAppDialog.visiable"
      width="540"
      :title="$t(`确认删除应用【{name}】？`, { name: curAppInfo.application.name })"
      :theme="'primary'"
      :header-position="'left'"
      :mask-close="false"
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
          :loading="delAppDialog.isLoading"
          @click="submitRemoveApp"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          class="ml10"
          theme="default"
          @click="delAppDialog.visiable = false"
        >
          {{ $t('取消') }}
        </bk-button>
      </template>
    </bk-dialog>

    <!-- 预览效果 -->
    <bk-dialog
      v-model="previewDialogConfig.visible"
      ext-cls="base-info-preview-dialog-cls"
      theme="primary">
      <div class="content">
        <img id="dislog-preview-image" />
        <h3 class="title">{{ localeAppInfo.name }}</h3>
      </div>
    </bk-dialog>
  </div>
</template>

<script>import moment from 'moment';
import appBaseMixin from '@/mixins/app-base-mixin';
// import BluekingUserSelector from '@blueking/user-selector';
import authenticationInfo from '@/components/authentication-info.vue';
// import 'BKSelectMinCss';
import pluginInfo from './plugin-info.vue';

export default {
  components: {
    authenticationInfo,
    pluginInfo,
    // BluekingUserSelector,
    //   'bk-member-selector': () => {
    //       return import('@/components/user/member-selector/member-selector.vue');
    //   }
  },
  mixins: [appBaseMixin],
  data() {
    return {
      isLoading: false,
      formRemoveConfirmCode: '',
      localeAppInfo: {
        name: '',
        logo: '',
        introduction: '',
        contact: [],
      },
      rules: {
        name: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
          {
            max: 20,
            message: this.$t('请输入 1-20 字符的字母、数字、汉字'),
            trigger: 'blur',
          },
          {
            validator(val) {
              const reg = /^[a-zA-Z\d\u4e00-\u9fa5-]*$/;
              return reg.test(val);
            },
            message: this.$t('格式不正确，只能包含：汉字、英文字母、数字、连字符(-)，长度小于 20 个字符'),
            trigger: 'blur',
          },
        ],
      },
      delAppDialog: {
        visiable: false,
        isLoading: false,
      },
      descAppStatus: false,
      descAppDisabled: false,
      appBaseInfoConfig: {
        isEdit: false,
        isPreviewImageShow: false,
        logoData: null,
        isLoading: false,
      },
      previewDialogConfig: {
        visible: false,
      },
      isMaskLayerShown: false,
    };
  },
  computed: {
    canDeleteApp() {
      return this.curAppInfo.role.name === 'administrator';
    },
    canViewSecret() {
      return this.curAppInfo.role.name !== 'operator';
    },
    isBasicInfoEditable() {
      return ['administrator', 'operator'].indexOf(this.curAppInfo.role.name) !== -1;
    },
    formRemoveValidated() {
      return this.curAppInfo.application.code === this.formRemoveConfirmCode;
    },
    platformFeature() {
      console.warn(this.$store.state.platformFeature);
      return this.$store.state.platformFeature;
    },
    userFeature() {
      return this.$store.state.userFeature;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    curAppName() {
      return this.curAppInfo.application?.name;
    },
  },
  watch: {
    curAppInfo(value) {
      this.isLoading = true;
      this.localeAppInfo.name = value.application.name;
      this.localeAppInfo.logo = value.application.logo_url;
      this.$refs.authenticationRef?.resetAppSecret();
      setTimeout(() => {
        this.isLoading = false;
      }, 500);
    },
  },
  created() {
    moment.locale(this.localLanguage);
  },
  mounted() {
    this.descAppStatus = this.curAppInfo.feature.APPLICATION_DESCRIPTION;
    this.isLoading = true;
    this.getDescAppStatus();
    this.init();
    if (this.curAppName) {
      this.localeAppInfo.name = this.curAppName;
    }
    setTimeout(() => {
      this.isLoading = false;
    }, 300);
  },
  methods: {
    async getDescAppStatus() {
      try {
        const res = await this.$store.dispatch('market/getDescAppStatus', this.appCode);
        this.descAppDisabled = res.DISABLE_APP_DESC.activated;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
    async init() {
      this.initAppMarketInfo();
      this.formRemoveConfirmCode = '';
    },


    // 应用名称校验
    handleSaveCheck() {
      // 应用名称保存
      this.$refs.appNmaeRef.validate().then(() => {
        this.updateAppBasicInfo();
      }, (e) => {
        console.error(e.content || e);
      });
    },

    // 更新基本信息
    async updateAppBasicInfo() {
      try {
        const data = new FormData();
        data.append('name', this.localeAppInfo.name);
        if (this.appBaseInfoConfig.logoData) {
          data.append('logo', this.appBaseInfoConfig.logoData);
        }
        const res = await this.$store.dispatch('baseInfo/updateAppBasicInfo', {
          appCode: this.appCode,
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('信息修改成功！'),
        });
        this.resetAppBaseInfoConfig();
        this.localeAppInfo.logo = res.logo_url;
        this.$emit('current-app-info-updated');
        this.$store.commit('updateCurAppProductLogo', this.localeAppInfo.logo);
      } catch (e) {
        this.localeAppInfo.name = this.curAppName;
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.$refs.appNmaeRef?.clearError();
      }
    },

    showRemovePrompt() {
      this.delAppDialog.visiable = true;
    },

    hookAfterClose() {
      this.formRemoveConfirmCode = '';
    },

    // 删除应用
    async submitRemoveApp() {
      this.delAppDialog.isLoading = true;
      try {
        await this.$store.dispatch('baseInfo/deleteApp', {
          appCode: this.appCode,
        });
        this.delAppDialog.visiable = false;
        this.$paasMessage({
          theme: 'success',
          message: this.$t('应用删除成功'),
        });
        this.$router.push({
          name: 'myApplications',
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail,
        });
        this.delAppDialog.visiable = false;
      } finally {
        this.delAppDialog.isLoading = false;
      }
    },

    async initAppMarketInfo() {
      try {
        const res = await this.$store.dispatch('market/getAppBaseInfo', this.appCode);
        this.localeAppInfo.logo = res.application.logo_url;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
    async toggleDescSwitch() {
      if (this.descAppDisabled) return;
      let title = this.$t('确认启用应用描述文件');
      let subTitle = this.$t('启用后，可在 app_desc.yaml 文件中定义环境变量，服务发现等');
      if (this.descAppStatus) {
        title = this.$t('确认禁用应用描述文件');
        subTitle = this.$t('禁用后，将不再读取 app_desc.yaml 文件中定义的内容');
      }
      this.$bkInfo({
        width: 500,
        title,
        subTitle,
        maskClose: true,
        confirmFn: () => {
          this.changeDescAppStatus();
        },
      });
    },

    async changeDescAppStatus() {
      try {
        const res = await this.$store.dispatch('market/changeDescAppStatus', this.appCode);
        this.descAppStatus = res.APPLICATION_DESCRIPTION;
        this.$store.commit('updateCurDescAppStatus', this.descAppStatus);
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 基本信息编辑
    handleEditBaseInfo() {
      if (!this.isBasicInfoEditable) return;
      this.appBaseInfoConfig.isEdit = true;
    },

    // 处理文件选择，显示选择后的预览图
    beforeFileUploadProcessing(e) {
      e.preventDefault();
      const file = e.target.files[0];
      if (!file) return;
      const maxSize = 2 * 1024;

      // 支持jpg、png等图片格式，图片尺寸为72*72px，不大于2MB。验证
      const imgSize = file.size / 1024;
      if (imgSize > maxSize) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('文件大小应<2M！'),
        });
        return;
      }

      // 显示预览图
      const imgEl = document.querySelector('#preview-image');
      const previewImageUrl = URL.createObjectURL(file);
      imgEl.style.display = 'block';
      imgEl.src = previewImageUrl;
      this.appBaseInfoConfig.isPreviewImageShow = true;
      this.appBaseInfoConfig.logoData = file;
    },

    // 设置预览图
    setPreviewImage(imgEl, file) {
      const previewImageUrl = URL.createObjectURL(file);
      imgEl.style.display = 'block';
      imgEl.src = previewImageUrl;
    },

    // 预览
    handlePreview() {
      this.previewDialogConfig.visible = true;
      // 显示预览图
      const imgEl = document.querySelector('#dislog-preview-image');
      this.setPreviewImage(imgEl, this.appBaseInfoConfig.logoData);
    },

    // 基本信息取消
    handlerBaseInfoCancel() {
      this.localeAppInfo.name = this.curAppName;
      this.resetAppBaseInfoConfig();
    },

    // 数据重置
    resetAppBaseInfoConfig() {
      this.appBaseInfoConfig.isEdit = false;
      this.appBaseInfoConfig.isPreviewImageShow = false;
      this.appBaseInfoConfig.logoData = null;
      this.appBaseInfoConfig.isLoading = false;
    },

    // 基本信息提交
    handleSubmitBaseInfo() {
      this.$refs.formNameRef?.validate().then(async () => {
        this.appBaseInfoConfig.isLoading = true;
        this.updateAppBasicInfo();
      }, (e) => {
        console.error(e);
      });
    },

    handleClose() {
      const imgEl = document.querySelector('#preview-image');
      imgEl.src = '';
      imgEl.style.display = 'none';
      this.$refs.logoInputRef.value = '';
      this.appBaseInfoConfig.logoData = null;
      this.appBaseInfoConfig.isPreviewImageShow = false;
    },

    handleInputClick() {
      this.$refs.logoInputRef?.click();
    },
  },
};
</script>

<style lang="scss" scoped>
    .mt16 {
      margin-top: 16px;
    }
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
        &:first-child {
          margin-top: 8px;
        }
        .title {
            display: flex;
            align-items: flex-end;
            color: #313238;
            font-size: 14px;
            font-weight: bold;
            line-height: 1;
            margin-bottom: 4px;
            .edit-container {
              font-size: 12px;
              color: #3A84FF;
              cursor: pointer;

              &.disabled {
                color: #c4c6cc;
                cursor: not-allowed;
              }
            }
        }
        .info {
            color: #979ba5;
            font-size: 12px;
        }
        .content {
            margin-top: 20px;
            border: 1px solid #dcdee5;
            border-radius: 2px;
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

    .action-box {
        z-index: 11 !important;
    }

    h2.basic-information {
      box-shadow: 0 3px 4px 0 #0000000a;
    }

    .info-card-style {
      .title {
        font-weight: 700;
        font-size: 14px;
        color: #313238;
      }
    }
    .main {
      .view-mode {
        display: flex;
        justify-content: space-between;
        .info-warpper {
          margin-top: 16px;
          flex: 1;
          .row {
            display: flex;
            .value {
              width: 150px;
            }
          }
        }
        .item {
          display: flex;
          align-items: center;
          height: 40px;
          line-height: 40px;
          font-size: 14px;
          color: #63656E;
          .label {
            width: 130px;
            text-align: right;
          }
          .value {
            color: #313238;
            text-wrap: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }
        }
        .logo-wrapper {
          flex-shrink: 0;
          margin-right: 78px;
          width: 96px;
          height: 96px;
          img {
            width: 100%;
            height: 100%;
          }
        }
      }

      .edit-mode {
        font-size: 12px;
        width: 630px;
        margin-top: 16px;
        .logoupload-wrapper {
          display: flex;
          align-items: center;
          .tip {
            margin-left: 12px;
            color: #979BA5;
          }
        }
        .logoupload-cls {
          flex-shrink: 0;
          position: relative;
          display: flex;
          flex-direction: column;
          justify-content: center;
          width: 96px;
          height: 96px;
          color: #63656E;
          background: #FAFBFD;
          border: 1px dashed #C4C6CC;
          border-radius: 2px;
          cursor: pointer;

          &.preview {
            background: #FFFFFF;
            border: 1px solid #C4C6CC !important;
          }

          &:hover {
            color: #3A84FF;
            border-color: #3A84FF;
            .icon-plus-line {
              color: #3A84FF;
            }
          }

          .logoupload-content {
            display: flex;
            flex-direction: column;
            justify-content: center;
          }

          .preview-image-cls {
            position: absolute;
            left: 3px;
            top: 3px;
            width: calc(100% - 6px);
            height: calc(100% - 6px);
          }

          .logo-mask-layer-cls {
            position: absolute;
            top: 3px;
            left: 3px;
            width: calc(100% - 6px);
            height: calc(100% - 6px);
            background: #00000099;
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: default;

            i {
              cursor: pointer;
              color: #FAFBFD;
              font-size: 20px;
            }

            i:hover {
              color: #3A84FF;
            }

            .paasng-close {
              position: absolute;
              right: 3px;
              top: 3px;
            }
          }

          i {
            font-size: 22px;
            color: #979BA5;
          }
          p {
            text-align: center;
          }
          input {
            width: 100%;
            height: 100%;
            position: absolute;
            left: 0;
            top: 0;
            z-index: 10;
            cursor: pointer;
            opacity: 0;
          }
        }
      }
    }
    .base-info-form-btn button {
      width: 88px;
    }
    .logoupload-cls .preview-image-cls #preview-image {
      display: none;
      position: absolute;
      width: 100%;
      height: 100%;
      left: 0;
      top: 0;
      z-index: 5;
    }
    .delete-app-wrapper {
      p {
        color: #63656E;
        font-size: 12px;
        margin-left: 13px;
        i {
          font-size: 14px;
          color: #FFB848;
        }
      }
      display: flex;
      align-items: center;
    }
</style>
<style lang="scss">
    @import '~@/assets/css/mixins/ellipsis.scss';
    .plugin-type-scope .info-special-form.bk-form.bk-inline-form .bk-select .bk-select-name {
        height: 32px;
        line-height: 32px;
        font-size: 12px;
    }
    .plugin-type-scope .info-special-form.bk-form.bk-inline-form .bk-select .bk-select-angle {
        top: 4px;
    }
    .paas-info-app-name-cls.plugin-name .bk-form-input {
        padding-right: 130px !important;
        @include ellipsis;
    }
    .base-info-preview-dialog-cls {
      .bk-dialog-footer {
        display: none;
      }
      .bk-dialog-body {
        padding: 0;
      }
      .content {
        display: flex;
        align-items: center;
        background: #182132;
        margin: 0 24px 24px;
        padding-left: 12px;
        height: 45px;
        #dislog-preview-image {
          height: 32px;
          width: 32px;
        }
        .title {
          font-family: MicrosoftYaHei;
          margin-left: 8px;
          font-size: 14px;
          font-weight: 400;
          color: #EAEBF0;
        }
      }
    }
</style>
