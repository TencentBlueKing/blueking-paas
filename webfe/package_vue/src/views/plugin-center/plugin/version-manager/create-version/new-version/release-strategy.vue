<template>
  <div class="release-strategy-container">
    <card
      class="mt16"
      :title="$t('发布策略')"
      :is-collapse="true"
    >
      <bk-form
        v-if="isEdit"
        :label-width="120"
        :model="releaseStrategy"
        ref="releaseStrategyForm"
      >
        <bk-form-item
          label="发布策略"
          :required="true"
          :property="'strategy'"
          :error-display-type="'normal'"
          :rules="rules.strategy"
        >
          <bk-radio-group v-model="releaseStrategy.strategy">
            <bk-radio :value="'gray'">{{ $t('先灰度后全量发布') }}</bk-radio>
            <bk-radio :value="'full'">{{ $t('直接全量发布') }}</bk-radio>
          </bk-radio-group>
        </bk-form-item>
        <bk-form-item
          v-if="!isFullRelease"
          label="灰度范围"
          :required="true"
          :property="'project'"
          :error-display-type="'normal'"
        >
          <div class="gray-range">
            <bk-form
              :model="releaseStrategy"
              ref="childForm"
              form-type="vertical"
              ext-cls="gray-range-form-cls"
            >
              <bk-form-item
                :label="$t('蓝盾项目 ID')"
                :required="true"
                :property="'bkci_project'"
                :error-display-type="'normal'"
                :rules="rules.bkci_project"
              >
                <bk-tag-input
                  v-model="releaseStrategy.bkci_project"
                  :placeholder="$t('请输入蓝盾项目 ID，多个 ID 以英文分号分隔，最多可输入 10 个 ID')"
                  :has-delete-icon="true"
                  :allow-create="true"
                  ext-cls="projec-id-tag-cls">
                </bk-tag-input>
              </bk-form-item>
              <bk-form-item
                :label="$t('组织')"
                :required="true"
                :property="'organization'"
                :error-display-type="'normal'"
                :rules="rules.organization"
              >
                <!-- <bk-input v-model="releaseStrategy.organization"></bk-input> -->
                <bk-button :theme="'default'" @click="handleSelectOrganization">{{ $t('选择组织') }}</bk-button>
                <div class="render-member-wrapper" v-if="departments.length > 0">
                  <render-member-list
                    type="department"
                    :data="departments"
                  />
                </div>
                <p
                  class="f12 from-tip"
                  style="margin-top: 2px"
                  slot="tip"
                >
                  {{ $t('最小范围可以选择中心') }}
                </p>
              </bk-form-item>
            </bk-form>
          </div>
        </bk-form-item>
      </bk-form>

      <view-mode v-else>
        <ul>
          <li class="item">
            <div class="label">{{ $t('发布策略') }}：</div>
            <div class="value">--</div>
          </li>
          <li class="item">
            <div class="label">{{ $t('灰度范围') }}：</div>
            <div class="value">--</div>
          </li>
        </ul>
      </view-mode>
    </card>


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
import userSelectorDialog from '@/components/user-selector';
import renderMemberList from '@/views/dev-center/app/market/render-member-list';
import card from '@/components/card/card.vue';
import viewMode from './view-mode.vue';

export default {
  name: 'ReleaseStrategy',
  components: {
    userSelectorDialog,
    renderMemberList,
    card,
    viewMode,
  },
  props: {
    mode: {
      type: String,
      default: 'edit',
    },
  },
  data() {
    return {
      // 发布策略
      releaseStrategy: {
        strategy: 'gray',
        bkci_project: [],
        organization: [],
      },
      isShow: false,
      apiHost: window.BK_COMPONENT_API_URL,
      departments: [],
      rules: {
        strategy: [
          {
            required: true,
            message: '必填项',
            trigger: 'blur',
          },
        ],
        bkci_project: [
          {
            required: true,
            message: '必填项',
            trigger: 'blur',
          },
        ],
        organization: [
          {
            required: true,
            message: '必填项',
            trigger: 'blur',
          },
        ],
      },
    };
  },
  computed: {
    isEdit() {
      return this.mode === 'edit';
    },
    // 全量发布
    isFullRelease() {
      return this.releaseStrategy.strategy === 'full';
    },
  },
  methods: {
    // 表单校验
    validate() {
      return Promise.all([this.$refs.releaseStrategyForm.validate(), this.$refs.childForm.validate()]);
    },
    // 向外抛出当前表单数据
    getFormData() {
      return this.releaseStrategy;
    },
    // 组织弹窗
    handleSelectOrganization() {
      this.isShow = true;
    },
    async handleSubmit(payload) {
      this.releaseStrategy.organization = payload;
      this.departments = payload;
      this.isShow = false;
    },
  },
};
</script>

<style lang="scss" scoped>
.release-strategy-container {
  .mt16 {
    margin-top: 16px;
  }
  .gray-range {
    padding: 12px 16px;
    background: #f5f7fa;
    border-radius: 2px;
    .gray-range-form-cls {
      /deep/ .bk-form-item {
        &::before,
        &::after {
          display: unset;
        }
      }
      .from-tip {
        color: #979ba5;
      }
      .projec-id-tag-cls {
        /deep/ .tag-list .key-node {
          background-color: #FAFBFD;
          border: 1px solid #DCDEE5;
          border-radius: 2px;
          .tag {
            background-color: #FAFBFD;
          }
        }
      }
    }
  }
}
</style>
