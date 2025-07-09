<template>
  <div class="establish">
    <bk-alert
      type="info"
      class="external-tip"
      :title="$t('平台为该类应用提供云 API 权限申请、应用市场等功能')"
    ></bk-alert>
    <div class="info-cards card-style">
      <div class="item-title">{{ $t('基本信息') }}</div>
      <div class="content">
        <bk-form
          :label-width="100"
          :model="formData"
          :rules="rules"
          ref="baseInfoForm"
        >
          <bk-form-item
            :label="$t('应用 ID')"
            :required="true"
            :property="'code'"
            :error-display-type="'normal'"
          >
            <bk-input
              v-model="formData.code"
              :placeholder="$t('请输入 3-16 字符的小写字母、数字、连字符(-)，以小写字母开头')"
            ></bk-input>
            <p
              class="item-tips mb0"
              slot="tip"
            >
              {{ $t('应用的唯一标识，创建后不可修改') }}
            </p>
          </bk-form-item>
          <bk-form-item
            :label="$t('应用名称')"
            :required="true"
            :property="'name'"
            error-display-type="'normal'"
          >
            <bk-input
              v-model="formData.name"
              :placeholder="$t('由汉字、英文字母、数字、连字符（-）组成，长度小于 20 个字符')"
            ></bk-input>
          </bk-form-item>
          <!-- 多租户 -->
          <template v-if="isShowTenant">
            <bk-form-item
              :required="true"
              :property="'tenant'"
              error-display-type="normal"
              ext-cls="form-item-cls"
              :label="$t('租户模式')"
            >
              <bk-radio-group v-model="formData.tenantMode">
                <bk-radio-button value="single">{{ $t('单租户') }}</bk-radio-button>
                <bk-radio-button value="global">{{ $t('全租户') }}</bk-radio-button>
              </bk-radio-group>
            </bk-form-item>
            <bk-form-item
              v-if="formData.tenantMode === 'single'"
              :required="true"
              ext-cls="form-item-cls"
              :label="$t('租户 ID')"
            >
              <bk-input
                class="form-input-width"
                :value="curUserInfo.tenantId"
                :disabled="true"
              ></bk-input>
            </bk-form-item>
          </template>
        </bk-form>
      </div>
    </div>
    <div class="info-cards card-style">
      <div class="item-title">{{ $t('应用市场') }}</div>
      <div class="content">
        <bk-form
          :label-width="100"
          :model="appMarketData"
          :rules="rules"
          ref="appMarketForm"
        >
          <bk-form-item
            :label="$t('访问地址')"
            :property="'sourceTpUrl'"
            :error-display-type="'normal'"
          >
            <bk-input
              v-model="appMarketData.sourceTpUrl"
              :placeholder="$t('请输入正确的地址')"
            ></bk-input>
            <p
              class="item-tips mb0"
              slot="tip"
            >
              {{ $t('应用上线到蓝鲸应用市场的访问地址，你也可以在创建后修改选项') }}
            </p>
          </bk-form-item>
        </bk-form>
      </div>
    </div>
    <div
      v-if="createLoading"
      class="form-loading"
    >
      <img src="/static/images/create-app-loading.svg" />
      <p>{{ $t('应用创建中，请稍候') }}</p>
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
        @click="handleCreateApp"
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
  </div>
</template>
<script>
/* eslint-disable max-len */
import sidebarDiffMixin from '@/mixins/sidebar-diff-mixin';
import { mapGetters } from 'vuex';
export default {
  mixins: [sidebarDiffMixin],
  data() {
    return {
      createLoading: false,
      // 基本信息
      formData: {
        code: '',
        name: '',
        tenantMode: 'single',
        region: 'default',
      },
      // 应用市场
      appMarketData: {
        sourceTpUrl: '',
      },
      rules: {
        code: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
          {
            regex: /^[a-z][a-z0-9-]{2,15}$/,
            message: this.$t('请输入 3-16 字符的小写字母、数字、连字符(-)，以小写字母开头'),
            trigger: 'blur',
          },
        ],
        name: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
          {
            regex: /^[a-zA-Z\d\u4e00-\u9fa5-]{1,19}$/,
            message: this.$t('格式不正确，只能包含：汉字、英文字母、数字、连字符(-)，长度小于 20 个字符'),
            trigger: 'blur',
          },
        ],
        // 访问地址
        sourceTpUrl: [
          {
            validator(val) {
              if (val === '') return true;
              // const reg =
              //   /^(https?|ftp|rtsp|mms):\/\/[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})+(\/[A-Za-z0-9.+&@#/%=~_|-]*)*$/;
              // return reg.test(val);

              // 使用更安全的 URL 验证，避免 ReDOS 风险
              try {
                const url = new URL(val);
                return ['http:', 'https:', 'ftp:', 'rtsp:', 'mms:'].includes(url.protocol);
              } catch {
                return false;
              }
            },
            message: this.$t('地址格式不正确'),
            trigger: 'blur',
          },
        ],
      },
    };
  },
  computed: {
    ...mapGetters(['isShowTenant']),
    curUserInfo() {
      return this.$store.state.curUserInfo;
    },
  },
  created() {
    this.fetchSpecs();
  },
  methods: {
    // 格式化参数
    formatParams() {
      const { tenantMode, ...result } = this.formData;
      const params = {
        ...result,
        ...(this.isShowTenant && { app_tenant_mode: tenantMode }),
        market_params: {
          source_tp_url: this.appMarketData.sourceTpUrl,
        },
      };
      return params;
    },

    // 处理创建应用
    handleCreateApp() {
      // 表单校验
      Promise.all([this.$refs.baseInfoForm.validate(), this.$refs.appMarketForm.validate()]).then(
        () => {
          const params = this.formatParams();
          this.createLoading = true;
          this.submitCreateForm(params);
        },
        (validator) => {
          console.error(validator);
        },
      );
    },
    // 提交表单
    async submitCreateForm(params) {
      try {
        const res = await this.$store.dispatch('createApp/createExternalLinkApp', {
          appCode: this.appCode,
          data: params,
        });
        const objectKey = `SourceInitResult${Math.random().toString(36)}`;
        if (res.source_init_result) {
          localStorage.setItem(objectKey, JSON.stringify(res.source_init_result.extra_info));
        }
        const path = `/developer-center/apps/${res.application.code}/create/success`;
        this.$router.push({
          path,
          query: { objectKey },
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.createLoading = false;
      }
    },
    // 获取应用版本
    async fetchSpecs() {
      try {
        const res = await this.$store.dispatch('module/getLanguageInfo');
        this.formData.region = Object.keys(res)[0] || 'default';
        // 收集初始依赖
        this.$nextTick(() => {
          const data = this.formatParams();
          this.initSidebarFormData(data);
        });
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    async back() {
      // 内容变更输入弹窗提示
      const isSwitching = await this.handleBeforeFunction();
      if (!isSwitching) {
        return;
      }
      this.$router.push({
        name: 'myApplications',
      });
    },
    async handleBeforeFunction() {
      const data = this.formatParams();
      return this.$isSidebarClosed(JSON.stringify(data));
    },
  },
};
</script>
<style lang="scss" scoped>
@import './default.scss';
.establish {
  .external-tip {
    margin: 16px 0;
  }
  .info-cards {
    padding: 16px 24px;
    margin-bottom: 16px;
    &:last-child {
      margin-bottom: 0;
    }
    .content {
      width: 750px;
    }
    .item-title {
      font-weight: 700;
      font-size: 14px;
      color: #313238;
      margin-bottom: 16px;
    }
    .item-tips {
      color: #979ba5;
      font-size: 12px;
    }
  }
  .form-group-flex-radio {
    .form-group-radio {
      display: flex;
      align-items: center;
    }
  }
}
</style>
