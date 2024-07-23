<template>
  <div class="visible-range">
    <paas-plugin-title :tips="$t('仅可见范围内的组织、用户可在研发商店查看并使用该插件')" />
    <paas-content-loader
      class="app-container middle"
      :is-loading="isContentLoading"
      placeholder="visible-range-loading"
      :is-transform="false"
    >
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
          <bk-form style="width: 800px" :label-width="150" :model="formData" ref="visibleRangeForm">
            <bk-form-item
              :label="$t('蓝盾项目')"
              :required="true"
              :property="'projectIds'"
              :error-display-type="'normal'"
              :rules="rules.projectIds">
              <bk-input v-model="formData.projectIds" :placeholder="$t('请输入蓝盾项目 Project ID，并用英文分号分隔')"></bk-input>
            </bk-form-item>
            <bk-form-item :label="$t('组织')">
              <bk-button :theme="'default'" @click="handleSelectOrganization">{{ $t('选择组织') }}</bk-button>
              <div class="render-member-wrapper" v-if="departments.length > 0">
                <render-member-list
                  type="department"
                  :data="departments"
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
          <p v-html="tips"></p>
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
      rules: {
        projectIds: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
          {
            regex: /^([a-z][a-z0-9-]{0,31})(;[a-z][a-z0-9-]{0,31})*;?$/,
            message: this.$t('请用英文分号分隔'),
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
  },
  watch: {
    formData: {
      handler(newValue) {
        this.isEditingFormData = this.initStatus === JSON.stringify(newValue);
      },
      deep: true,
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
          bkci_project: this.formData.projectIds.split(';'),
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
    .render-member-wrapper {
      margin-top: 12px;
      padding: 12px 12px 12px 36px;
      width: 320px;
      background: #f5f7fa;
      border-radius: 2px;
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
}
</style>
