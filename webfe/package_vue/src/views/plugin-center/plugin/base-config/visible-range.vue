<template>
  <div class="visible-range">
    <paas-plugin-title :tips="$t('仅可见范围内的组织、用户可在研发商店查看并使用该插件')" />
    <paas-content-loader
      class="app-container"
      :is-loading="isContentLoading"
      placeholder="visible-range-loading"
      :is-transform="false"
    >
      <bk-alert
        v-if="visibleRangeData.is_in_approval"
        class="warning-alert-cls mb16"
        type="warning"
        :show-icon="false"
      >
        <div slot="title">
          <i class="paasng-icon paasng-remind"></i>
          {{ $t('修改的可见范围已提交审批，尚未生效') }}
          <bk-button
            size="small"
            text
            class="ml10"
            @click="viewApprovalDetails"
          >
            {{ $t('查看审批详情') }}
          </bk-button>
          <i class="paasng-icon paasng-refresh-line refresh" @click="getVisibleRange" />
        </div>
      </bk-alert>
      <!-- 无数据状态 -->
      <section class="exception-wrapper" v-if="!isEdit">
        <bk-exception class="exception-wrap-item exception-part" type="empty" scene="part">
          <p class="text-btn">{{ $t('暂未设置可见范围') }}</p>
          <bk-button
            :text="true"
            title="primary"
            size="small"
            @click="() => isEdit = true"
          >
            {{ $t('去设置') }}
          </bk-button>
        </bk-exception>
      </section>
      <!-- 编辑态 -->
      <template v-else>
        <section class="visible-range-form card-style">
          <bk-form
            style="width: 800px"
            :label-width="150"
            :model="formData"
            ext-cls="visible-range-form-cls"
            ref="visibleRangeForm">
            <bk-form-item
              :label="$t('蓝盾项目')"
              :property="'projectIds'"
              :error-display-type="'normal'"
              :rules="rules.projectIds"
            >
              <bk-input v-model="formData.projectIds" :placeholder="$t('请输入蓝盾项目 ID，并用英文分号分隔')"></bk-input>
            </bk-form-item>
            <bk-form-item
              :label="$t('组织')"
              :required="true"
              :error-display-type="'normal'"
              :rules="rules.organization"
            >
              <bk-button :theme="'default'" @click="handleSelectOrganization">{{ $t('选择组织') }}</bk-button>
              <div class="render-member-wrapper" v-if="departments.length > 0">
                <render-member-list
                  type="department"
                  :data="organizationLevel"
                />
              </div>
            </bk-form-item>
          </bk-form>
        </section>
        <div class="footer-btn">
          <!-- 当前数据未更改禁用、 审批中禁用 -->
          <span v-bk-tooltips="{ content: submitBtnTips, disabled: !submitDisabled }">
            <bk-button
              :theme="'primary'"
              :disabled="submitDisabled"
              @click="submitReview">
              {{ $t('提交审核') }}
            </bk-button>
          </span>
          <p v-dompurify-html="tips"></p>
        </div>
      </template>
    </paas-content-loader>

    <user-selector-dialog
      ref="userSelectorDialogRef"
      title="选择组织"
      placeholder="组织"
      :show.sync="isShow"
      :departments="departments"
      :api-host="apiHost"
      :custom-close="true"
      :range="'departments'"
      :departments-fn="handleDepartments"
      departments-type="tc"
      @sumbit="handleSubmit"
    />
  </div>
</template>
<script>
import paasPluginTitle from '@/components/pass-plugin-title';
import userSelectorDialog from '@/components/user-selector';
import renderMemberList from '@/views/dev-center/app/market/render-member-list';

export default {
  components: {
    paasPluginTitle,
    userSelectorDialog,
    renderMemberList,
  },
  data() {
    return {
      formData: {
        projectIds: '',
        organization: [],
      },
      apiHost: window.BK_COMPONENT_API_URL,
      isShow: false,
      departments: [],
      isEdit: false,
      isContentLoading: true,
      initStatus: '',
      visibleRangeData: {},
      isEditingFormData: true,
      submitBtnTips: '',
      organizationLevel: [],
      rules: {
        projectIds: [
          {
            regex: /^([a-z][a-zA-Z0-9-]+)(;[a-z][a-zA-Z0-9-]+)*;?$|^$/,
            message: this.$t('Project ID是字符+数字组成，并以小写字母开头，Project ID之间用英文分号分隔'),
            trigger: 'blur',
          },
        ],
        organization: [
          {
            validator: () => this.departments.length,
            message: '必填项',
            trigger: 'blur',
          },
        ],
      },
    };
  },
  computed: {
    pdId() {
      return this.$route.params.pluginTypeId;
    },
    pluginId() {
      return this.$route.params.id;
    },
    tips() {
      return this.$t('修改可见范围需由<i class="bold">平台管理员</i>进行审批');
    },
    submitDisabled() {
      if (this.visibleRangeData.is_in_approval) {
        this.submitBtnTips = this.$t('正在审批中');
        return true;
      }
      if (this.isEditingFormData) {
        this.submitBtnTips = this.$t('未修改');
        return true;
      }
      return false;
    },
    cachePool() {
      return this.$store.getters['plugin/getCachePool'];
    },
  },
  watch: {
    formData: {
      handler(newValue) {
        this.isEditingFormData = this.initStatus === JSON.stringify(newValue);
      },
      deep: true,
    },
    initStatus(newValue) {
      this.isEditingFormData = newValue === JSON.stringify(this.formData);
    },
    'departments.length'() {
      this.triggerValidate();
    },
  },
  created() {
    this.getVisibleRange();
  },
  methods: {
    // 提交审核
    submitReview() {
      this.$refs.visibleRangeForm.validate().then(() => {
        const params = {
          bkci_project: this.formData.projectIds.length ? this.formData.projectIds.split(';') : [],
          organization: this.formData.organization,
        };
        this.updateVisibleRange(params);
      }, (validator) => {
        console.warn(validator);
      });
    },
    // 组织弹窗
    handleSelectOrganization() {
      this.isShow = true;
    },
    collectDependencies() {
      // 初始状态
      this.initStatus = JSON.stringify(this.formData);
    },
    async handleSubmit(payload) {
      this.formData.organization = payload;
      this.departments = payload;
      await this.requestAllOrganization(payload);
      this.isShow = false;
    },
    // 获取可见范围数据
    async getVisibleRange() {
      try {
        const res = await this.$store.dispatch('plugin/getVisibleRange', {
          pdId: this.pdId,
          pluginId: this.pluginId,
        });
        // is_in_approval 审批中
        this.visibleRangeData = res;
        this.formData.projectIds = res.bkci_project.join(';');
        this.formData.organization = res.organization || [];
        this.departments = this.formData.organization;
        this.isEdit = true;
        await this.requestAllOrganization(res.organization);
      } catch (e) {
        // 404 就说明没有数据
        if (e.status === 404) {
          this.isEdit = false;
          return;
        }
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isContentLoading = false;
        this.collectDependencies();
      }
    },
    async updateVisibleRange(params) {
      try {
        await this.$store.dispatch('plugin/updateVisibleRange', {
          pdId: this.pdId,
          pluginId: this.pluginId,
          data: params,
        });
        this.getVisibleRange();
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
    async requestAllOrganization(data) {
      if (!data.length) return;
      const organizationLevel = await this.$store.dispatch('plugin/requestAllOrganization', data);
      this.organizationLevel = organizationLevel;
    },
    // 过滤出指定部门
    handleDepartments(data, type) {
      const TCID = 2874;
      const prefix = '腾讯公司/';

      if (type === 'search') {
        // 搜索过滤出指定部门数据
        return [data.filter(v => v.full_name.startsWith(prefix))];
      }
      const tc = data.find(v => v.id === TCID);
      return tc ? [tc] : [];
    },
    // 查看申请详情
    viewApprovalDetails() {
      const url = this.visibleRangeData.itsm_detail?.ticket_url;
      window.open(url, '_blank');
    },
    // 手动触发校验
    triggerValidate() {
      this.$refs.visibleRangeForm?.validate().then(() => {}, (validator) => {
        console.warn(validator);
      });;
    },
  },
};
</script>
<style lang="scss" scoped>
.visible-range {
  .exception-wrapper {
    height: 350px;
  }
  .visible-range-form {
    padding: 24px 0;
    .visible-range-form-cls {
      /deep/ .bk-form-item.is-error .bk-button {
        border-color: #ea3636;
        color: #ea3636;
      }
    }
  }
  .footer-btn {
    margin-top: 24px;
    display: flex;
    align-items: center;
    p {
      color: #979BA5;
      font-size: 12px;
      margin-left: 8px;
    }
  }
  /deep/ .bold {
    font-style: normal;
    font-weight: bold;
  }
  .text-btn {
    margin-bottom: 8px;
  }
  .mb16  {
    margin-bottom: 16px;
  }
  .warning-alert-cls {
    position: relative;
    i {
      font-size: 14px;
      color: #ff9c01;
      transform: translateY(0px);
    }
    /deep/ .bk-alert-wraper {
      height: 32px;
      align-items: center;
      font-size: 12px;
      color: #63656e;
    }
    /deep/ .bk-button-text.bk-button-small {
      padding: 0;
    }
    .refresh {
      cursor: pointer;
      position: absolute;
      top: 50%;
      right: 10px;
      transform: translateY(-50%);
      color: #3a84ff;
    }
  }
}
</style>
