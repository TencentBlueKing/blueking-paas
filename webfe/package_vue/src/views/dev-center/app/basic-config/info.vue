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
              class="edit-container"
              @click="handleEditBaseInfo"
            >
              <i class="paasng-icon paasng-edit-2 pl10" />
              {{ $t('编辑') }}
            </div>
          </div>
          <div class="info">
            {{ $t('管理员、开发者、运营者可以修改应用名称等基本信息。') }}
          </div>
          <section class="main">
            <!-- 查看态 -->
            <div
              class="view-mode"
              v-if="!appBaseInfoConfig.isEdit"
            >
              <section class="info-warpper">
                <div
                  class="item"
                  v-for="item in displayItems"
                  :key="item.label"
                >
                  <div class="label">{{ $t(item.label) }}：</div>
                  <div
                    class="value"
                    v-bk-overflow-tips
                  >
                    {{ item.value || '--' }}
                  </div>
                </div>
              </section>
              <div class="logo-wrapper">
                <img :src="localeAppInfo.logo || '/static/images/default_logo.png'" />
              </div>
            </div>
            <!-- 编辑态 -->
            <div
              class="edit-mode"
              v-else
            >
              <bk-form
                :model="localeAppInfo"
                form-type="vertical"
                ref="formNameRef"
                :rules="rules"
              >
                <bk-form-item
                  :label="$t('应用名称')"
                  :property="'name'"
                  :required="true"
                  :error-display-type="'normal'"
                >
                  <bk-input v-model="localeAppInfo.name"></bk-input>
                </bk-form-item>
                <bk-form-item
                  :label="$t('应用分类')"
                  :property="'tagId'"
                  :required="true"
                  :error-display-type="'normal'"
                >
                  <bk-select
                    v-model="localeAppInfo.tagId"
                    :clearable="true"
                    :popover-min-width="200"
                    :searchable="true"
                  >
                    <bk-option
                      v-for="(option, index) in tagList"
                      :id="option.id"
                      :key="`${option.name}-${index}`"
                      :name="option.name"
                    />
                  </bk-select>
                  <bk-button
                    v-if="testTagId && !localeAppInfo.tagId"
                    class="p0 mt5"
                    slot="tip"
                    :text="true"
                    size="small"
                    theme="primary"
                    @click="handleQuickSelectTest"
                  >
                    <div class="flex-row">
                      <img
                        class="lightening-icon"
                        src="/static/images/lightening.svg"
                        @click="handleExpand(row)"
                      />
                      {{ $t('快速标记为 “测试” 分类') }}
                    </div>
                  </bk-button>
                </bk-form-item>
                <bk-form-item
                  v-if="userFeature.APP_AVAILABILITY_LEVEL"
                  :label="$t('可用性保障登记')"
                  :required="true"
                  ext-cls="availability-item-cls"
                >
                  <bk-radio-group v-model="localeAppInfo.availabilityLevel">
                    <bk-radio
                      v-for="(val, key) in tierMap"
                      :value="key"
                      :key="key"
                      ext-cls="block"
                    >
                      {{ $t(val) }}
                      <span
                        v-if="key === 'premium'"
                        class="tip ml10 f12"
                      >
                        <i class="paasng-icon paasng-info-line"></i>
                        {{ $t('为其他 SaaS 或业务提供平台级服务，需要更高的可用性保障。') }}
                      </span>
                    </bk-radio>
                  </bk-radio-group>
                  <!-- 高级别展示风险提示 -->
                  <bk-alert
                    v-if="localeAppInfo.availabilityLevel === 'premium'"
                    class="mt10"
                    type="warning"
                    :show-icon="false"
                  >
                    <div
                      slot="title"
                      class="risk-warning"
                    >
                      <i class="paasng-icon paasng-remind f14"></i>
                      <div>
                        {{
                          $t(
                            '平台提供的 GCS-MySQL 数据库为共享实例，无法支持高级别的可用性。请参考文档申请独立的数据库实例。'
                          )
                        }}
                        <a
                          v-if="GLOBAL.DOC.GCS_MySQL_LINK"
                          :href="GLOBAL.DOC.GCS_MySQL_LINK"
                          target="_blank"
                        >
                          {{ $t('申请独立的数据库指引') }}
                        </a>
                        <div class="mt15">
                          <bk-checkbox v-model="isAwareOfRisk">
                            <span class="f12">{{ $t('我已知晓风险') }}</span>
                          </bk-checkbox>
                        </div>
                      </div>
                    </div>
                  </bk-alert>
                </bk-form-item>
                <bk-form-item
                  label="LOGO"
                  ext-cls="app-logo-cls"
                >
                  <div :class="['logoupload-wrapper', { selected: curFileData.length }]">
                    <bk-upload
                      :files="curFileData"
                      :theme="'picture'"
                      accept="image/jpeg, image/png"
                      :multiple="false"
                      ext-cls="app-logo-upload-cls"
                      :custom-request="customRequest"
                      @on-delete="curFileData = []"
                    ></bk-upload>
                    <ul class="upload-tip">
                      <li>{{ $t('支持 jpg、png 等图片格式') }}</li>
                      <li>{{ $t('图片尺寸为 72 * 72px') }}</li>
                      <li>{{ $t('不大于 2MB') }}</li>
                    </ul>
                  </div>
                </bk-form-item>
                <bk-form-item class="mt20 base-info-form-btn">
                  <span
                    style="display: inline-block"
                    v-bk-tooltips="{
                      content: $t('请点勾选 “我已知晓风险”'),
                      disabled: !isSubmitDisabled,
                      placement: 'bottom',
                    }"
                  >
                    <bk-button
                      ext-cls="mr8"
                      theme="primary"
                      :loading="appBaseInfoConfig.isLoading"
                      :disabled="isSubmitDisabled"
                      @click.stop="handleSubmitBaseInfo"
                    >
                      {{ $t('提交') }}
                    </bk-button>
                  </span>
                  <bk-button
                    theme="default"
                    @click="handlerBaseInfoCancel"
                  >
                    {{ $t('取消') }}
                  </bk-button>
                </bk-form-item>
              </bk-form>
            </div>
          </section>
        </div>

        <!-- 应用描述文件 -->
        <div
          v-if="isShowAppDescriptionFile"
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
            {{
              descAppStatus
                ? $t('已启用应用描述文件 app_desc.yaml，可在文件中定义环境变量，服务发现等。')
                : $t('未启用应用描述文件 app_desc.yaml')
            }}
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
      :title="$t(`确认删除应用【{name}】？`, { name: applicationDetail.name })"
      :theme="'primary'"
      :header-position="'left'"
      :mask-close="false"
      @after-leave="hookAfterClose"
    >
      <div class="ps-form">
        <div class="spacing-x1">
          {{ $t('请完整输入') }}
          <code>{{ applicationDetail.code }}</code>
          {{ $t('来确认删除应用！') }}
        </div>
        <div class="ps-form-group">
          <input
            v-model="formRemoveConfirmCode"
            type="text"
            class="ps-form-control"
          />
          <div class="mt10 f13">
            {{ $t('注意：因为安全等原因，应用 ID 和名称在删除后') }}
            <strong>{{ $t('不会被释放') }}</strong>
            ，{{ $t('不能继续创建同名应用') }}
          </div>
        </div>
      </div>
      <template slot="footer">
        <bk-button
          theme="danger"
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
  </div>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin';
import authenticationInfo from '@/components/authentication-info.vue';
import pluginInfo from './plugin-info.vue';
import { APP_TENANT_MODE } from '@/common/constants';
import { mapState, mapGetters } from 'vuex';

export default {
  components: {
    authenticationInfo,
    pluginInfo,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      isLoading: true,
      formRemoveConfirmCode: '',
      localeAppInfo: {
        name: '',
        logo: '',
        tagId: '',
        availabilityLevel: 'standard',
      },
      rules: {
        name: [
          {
            required: true,
            message: this.$t('必填项'),
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
        tagId: [
          {
            required: true,
            message: this.$t('必填项'),
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
        logoData: null,
        isLoading: false,
      },
      curFileData: [],
      appTenantMode: APP_TENANT_MODE,
      // 当前应用详情
      curAppData: {},
      // 应用分类下拉列表
      tagList: [],
      // 是否知晓风险
      isAwareOfRisk: false,
      tierMap: {
        standard: '基础',
        premium: '高级别',
      },
      testTagId: '',
    };
  },
  computed: {
    ...mapState(['platformFeature', 'userFeature', 'localLanguage']),
    ...mapGetters(['isShowTenant']),
    canDeleteApp() {
      return this.curAppInfo.role.name === 'administrator';
    },
    canViewSecret() {
      return this.curAppInfo.role.name !== 'operator';
    },
    // 管理员 & 运营者允许编辑
    isBasicInfoEditable() {
      return ['administrator', 'operator'].indexOf(this.curAppInfo.role.name) !== -1;
    },
    formRemoveValidated() {
      return this.applicationDetail.code === this.formRemoveConfirmCode;
    },
    applicationDetail() {
      return this.curAppData.application || {};
    },
    // 是否展示应用描述文件
    isShowAppDescriptionFile() {
      return !['engineless_app', 'cloud_native'].includes(this.applicationDetail.type);
    },
    // 高级别提交禁用
    isSubmitDisabled() {
      return this.userFeature.APP_AVAILABILITY_LEVEL
        ? this.localeAppInfo.availabilityLevel === 'premium' && !this.isAwareOfRisk
        : false;
    },
    displayItems() {
      const { extra_info } = this.applicationDetail;
      return [
        {
          key: 'name',
          label: '应用名称',
          value: this.applicationDetail.name,
          visible: true,
        },
        ...(this.isShowTenant
          ? [
              {
                key: 'tenant-mode',
                label: '租户模式',
                value: this.$t(this.appTenantMode[this.applicationDetail.app_tenant_mode]),
                visible: true,
              },
              {
                key: 'tenant-id',
                label: '租户 ID',
                value: this.applicationDetail.app_tenant_id,
                visible: true,
              },
            ]
          : []),
        {
          key: 'category',
          label: '应用分类',
          value: extra_info?.tag?.name,
          visible: true,
        },
        {
          key: 'availability',
          label: '可用性保障登记',
          value: this.tierMap[extra_info?.availability_level],
          visible: !!this.userFeature.APP_AVAILABILITY_LEVEL,
        },
        {
          key: 'created',
          label: '创建时间',
          value: this.applicationDetail.created,
          visible: true,
        },
      ].filter((item) => item.visible);
    },
  },
  mounted() {
    this.descAppStatus = this.curAppInfo.feature.APPLICATION_DESCRIPTION;
    this.init();
  },
  methods: {
    async init() {
      Promise.all([this.getAppInfo(), this.getDescAppStatus()]).finally(() => {
        this.isLoading = false;
        this.handleAutoEditMode();
      });
      this.formRemoveConfirmCode = '';
    },
    // 页面进入后，判断是否开启编辑模式
    handleAutoEditMode() {
      if (this.$route.query.editMode) {
        this.handleEditBaseInfo(); // 进入编辑模式
        this.$nextTick(() => {
          this.$refs.formNameRef?.validate().catch((e) => {
            console.error(e);
          });
        });
      }
    },
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
    // 准备接口数据
    prepareFormData() {
      const formData = new FormData();
      const { name, tagId, availabilityLevel } = this.localeAppInfo;
      const { logoData } = this.appBaseInfoConfig;

      // 添加必填字段
      Object.entries({ name, tag_id: tagId, availability_level: availabilityLevel }).forEach(
        ([key, value]) => value !== undefined && formData.append(key, value)
      );

      if (logoData) {
        formData.append('logo', logoData);
      }

      return formData;
    },
    // 更新基本信息
    async updateAppBasicInfo() {
      try {
        this.appBaseInfoConfig.isLoading = true;
        const data = this.prepareFormData();
        const res = await this.$store.dispatch('baseInfo/updateAppBasicInfo', {
          appCode: this.appCode,
          data,
        });
        this.getAppInfo();
        this.$paasMessage({
          theme: 'success',
          message: this.$t('信息修改成功！'),
        });
        this.resetAppBaseInfoConfig();
        this.$store.commit('updateCurAppBaseInfo', res);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.appBaseInfoConfig.isLoading = false;
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
    // 初始化表单数据
    initFromData(data) {
      const { name, logo_url, extra_info } = data || {};
      this.localeAppInfo = {
        name,
        logo: logo_url,
        tagId: extra_info?.tag?.id || '',
        availabilityLevel: extra_info?.availability_level || 'standard',
      };
    },
    // 获取应用所有信息
    async getAppInfo() {
      try {
        const ret = await this.$store.dispatch('market/getAppBaseInfo', this.appCode);
        this.initFromData(ret.application);
        this.curAppData = ret || {};
        this.$refs.authenticationRef?.resetAppSecret();
      } catch (e) {
        this.catchErrorHandler(e);
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
        this.catchErrorHandler(e);
      }
    },

    // 基本信息编辑
    handleEditBaseInfo() {
      // 获取应用分类列表
      if (!this.tagList.length) {
        this.getTagList();
      }
      this.curFileData = this.localeAppInfo.logo ? [{ url: this.localeAppInfo.logo }] : [];
      this.appBaseInfoConfig.isEdit = true;
    },

    // 基本信息取消
    handlerBaseInfoCancel() {
      this.initFromData(this.applicationDetail);
      this.resetAppBaseInfoConfig();
    },

    // 数据重置
    resetAppBaseInfoConfig() {
      this.appBaseInfoConfig = {
        isEdit: false,
        logoData: null,
        isLoading: false,
      };
    },

    // 基本信息提交
    handleSubmitBaseInfo() {
      // 检查 logo 是否上传
      if (!this.curFileData.length) {
        this.catchErrorHandler({ detail: this.$t('必须上传 logo') });
        return;
      }
      this.$refs.formNameRef?.validate().then(
        async () => {
          this.updateAppBasicInfo();
        },
        (e) => {
          console.error(e);
        }
      );
    },

    // 自定义上传处理
    customRequest(file) {
      const fileData = file.fileObj.origin;

      // 支持jpg、png等图片格式，图片尺寸为72*72px，不大于2MB。验证
      const imgSize = fileData.size / 1024;
      const maxSize = 2 * 1024;
      if (imgSize > maxSize) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('文件大小应<2M！'),
        });
        return;
      }
      this.appBaseInfoConfig.logoData = fileData;
      const previewImageUrl = URL.createObjectURL(fileData);
      this.curFileData = [
        {
          name: fileData.name,
          url: previewImageUrl,
        },
      ];
    },

    // 获取应用分类下拉数据
    async getTagList() {
      try {
        const res = await this.$store.dispatch('market/getTags');
        this.tagList = res;
        this.testTagId = res.find((v) => v.name === '测试')?.id || '';
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },

    // 快速选择为测试分类
    handleQuickSelectTest() {
      this.localeAppInfo.tagId = this.testTagId;
    },
  },
};
</script>

<style lang="scss" scoped>
.mt16 {
  margin-top: 16px;
}
.desc-flex {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  padding-bottom: 5px;
  .title {
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
      color: #3a84ff;
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
  .risk-warning {
    display: flex;
    line-height: 20px;
    .paasng-remind {
      margin: 3px 9px 0 0;
      color: #f59500;
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
    transition: all 0.5s;
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
    border: solid 1px #3a84ff;
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
    content: '';
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
    background: #3a84ff;
    font-weight: bold;
    border-radius: 2px;
    transition: all 0.5s;
  }

  .immediately:hover {
    background: #4e93d9;
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
      color: #63656e;
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
      width: 104px;
      height: 104px;
      img {
        width: 100%;
        height: 100%;
      }
    }
  }

  .edit-mode {
    position: relative;
    font-size: 12px;
    width: 480px;
    margin-top: 16px;
    .lightening-icon {
      width: 14px;
      margin-right: 5px;
    }
    .app-logo-cls {
      position: absolute;
      width: 300px;
      top: -8px;
      left: 510px;
      .upload-tip {
        margin-left: 12px;
        font-size: 12px;
        color: #979ba5;
        line-height: 20px;
      }
    }
    .logoupload-wrapper {
      display: flex;
      &.selected {
        .app-logo-upload-cls /deep/ .file-wrapper .picture-btn {
          background: #fff;
        }
      }
      .app-logo-upload-cls {
        /deep/ .file-wrapper {
          width: 104px;
          height: 104px;
          padding-top: 0px;
          .picture-btn {
            background: #fafbfd;
            .pic-item,
            .mask {
              width: 104px;
              height: 104px;
            }
          }
          .upload-btn {
            width: 104px;
            height: 104px;
            display: flex;
            align-items: center;
            flex-direction: column;
            justify-content: center;
          }
        }
      }
    }
    .tip {
      color: #979ba5;
    }
    .availability-item-cls {
      /deep/ .bk-form-control {
        display: flex;
        flex-direction: column;
        gap: 14px;
        .bk-form-radio {
          margin-left: 0;
        }
      }
    }
  }
}
.base-info-form-btn button {
  width: 88px;
}
.logoupload-cls .preview-image-cls #preview-image {
  position: absolute;
  width: 100%;
  height: 100%;
  left: 0;
  top: 0;
  z-index: 5;
}
.delete-app-wrapper {
  p {
    color: #63656e;
    font-size: 12px;
    margin-left: 13px;
    i {
      font-size: 14px;
      color: #ffb848;
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
</style>
