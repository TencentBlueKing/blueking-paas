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
        ext-cls="release-strategy-form-cls"
      >
        <bk-form-item
          :label="$t('发布策略')"
          :required="true"
          :property="'strategy'"
          :error-display-type="'normal'"
          :rules="rules.strategy"
        >
          <bk-radio-group v-model="releaseStrategy.strategy" @change="handleChange">
            <bk-radio
              v-for="item in releaseStrategyMap"
              :value="item.value"
              :key="item.value"
            >
              {{ item.name }}
            </bk-radio>
          </bk-radio-group>
        </bk-form-item>
        <bk-form-item
          v-if="!isFullRelease"
          :label="$t('灰度范围')"
          :required="true"
          ref="grayscaleRangeForm"
          :error-display-type="'normal'"
          :rules="rules.grayscaleRange"
        >
          <div class="gray-range">
            <bk-form
              :model="releaseStrategy"
              form-type="vertical"
              ext-cls="gray-range-form-cls"
            >
              <bk-form-item :label="$t('蓝盾项目 ID')">
                <bk-tag-input
                  ref="tagInputRef"
                  v-model="releaseStrategy.bkci_project"
                  :placeholder="$t('请输入蓝盾项目 ID，多个 ID 以英文分号分隔，最多可输入 10 个 ID')"
                  :has-delete-icon="true"
                  :allow-create="true"
                  :paste-fn="customCopyRules"
                  :clearable="!isDetailStep"
                  :tag-tpl="renderMemberTag"
                  ext-cls="projec-id-tag-cls"
                  @focus="handleFocus"
                  @blur="handleBlur"
                  @keydown.capture.native="handleKeyDown"
                ></bk-tag-input>
              </bk-form-item>
              <bk-form-item :label="$t('组织')">
                <bk-button
                  :theme="'default'"
                  @click="handleSelectOrganization"
                >
                  {{ $t('选择组织') }}
                </bk-button>
                <div
                  class="render-member-wrapper"
                  v-if="departments.length > 0"
                >
                  <render-member-list
                    type="department"
                    :data="organizationLevel"
                  />
                </div>
                <p
                  class="f12 from-tip"
                  style="margin-top: 2px"
                  slot="tip"
                >
                  {{ $t('最小范围可以选择中心。') }}
                  <span v-dompurify-html="organizationTips" class="t2"></span>
                </p>
              </bk-form-item>
            </bk-form>
          </div>
        </bk-form-item>
      </bk-form>

      <view-mode v-else>
        <ul
          class="release-strategy-cls"
          v-if="data?.latest_release_strategy"
        >
          <li class="item">
            <div class="label">{{ $t('发布策略') }}：</div>
            <div class="value">
              {{ releaseStrategyMap.find((v) => v.value === data.latest_release_strategy.strategy)?.name }}
            </div>
          </li>
          <li
            class="item"
            v-if="data.latest_release_strategy.strategy === 'gray'"
          >
            <div class="label">{{ $t('灰度范围') }}：</div>
            <div class="value range">
              <div class="c-item">
                <p class="c-title">{{ $t('蓝盾项目') }}：</p>
                <p class="c-value">
                  {{
                    data.latest_release_strategy.bkci_project?.length
                      ? data.latest_release_strategy.bkci_project.join()
                      : '--'
                  }}
                </p>
              </div>
              <div class="c-item">
                <p class="c-title">{{ $t('组织') }}：</p>
                <ul
                  class="c-value"
                  v-if="data.latest_release_strategy.organization?.length"
                >
                  <li
                    v-for="item in organizationLevel"
                    :key="item.id"
                  >
                    {{ item.name }}
                  </li>
                </ul>
                <p
                  v-else
                  class="c-value"
                >
                  --
                </p>
              </div>
            </div>
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
      :departments-fn="handleDepartments"
      :clearable="isDetailStep"
      :organize-disable-icon-fn="handleDisableIconFn"
      departments-type="tc"
      @sumbit="handleSubmit"
    />
  </div>
</template>

<script>
import userSelectorDialog from '@/components/user-selector';
import renderMemberList from '@/views/dev-center/app/market/render-member-list';
import card from '@/components/card/card.vue';
import viewMode from './view-mode.vue';
import { cloneDeep } from 'lodash';

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
    data: {
      type: Object,
      default: () => {},
    },
    step: {
      type: String,
      default: 'create',
    },
    versionData: {
      type: Object,
      default: () => {},
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
      initDepartments: [],
      releaseStrategyMap: [
        { value: 'gray', name: this.$t('先灰度后全量发布') },
        { value: 'full', name: this.$t('直接全量发布') },
      ],
      organizationLevel: [],
      disableDeletionMapping: {},
      focusLastTag: '',
      rules: {
        strategy: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
        grayscaleRange: [
          {
            validator: () => this.releaseStrategy.bkci_project?.length || this.departments.length,
            message: this.$t('蓝盾项目 ID 和 组织至少填写一个'),
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
    versionId() {
      return this.$route.query.versionId;
    },
    cachePool() {
      return this.$store.getters['plugin/getCachePool'];
    },
    isDetailStep() {
      return this.step === 'release';
    },
    organizationTips() {
      return this.$t('若选择了按照组织灰度，还需要由<em>工具发布者的直属Leader</em>进行审批。');
    },
  },
  watch: {
    data: {
      handler(newValue) {
        if (this.isDetailStep) {
          this.releaseStrategy = cloneDeep(newValue?.latest_release_strategy || {});
          this.departments = newValue.latest_release_strategy?.organization || [];
          this.initDepartments = cloneDeep(this.departments);
          if (this.departments.length) {
            this.requestAllOrganization(this.departments);
          }
          if (this.releaseStrategy?.bkci_project?.length) {
            this.releaseStrategy.bkci_project.forEach((v) => {
              this.disableDeletionMapping[v] = true;
            });
          }
        }
        if (this.versionId) {
          this.setVersionDefaultValue();
        }
      },
      immediate: true,
      deep: true,
    },
    'releaseStrategy.bkci_project.length'() {
      this.triggerValidate();
    },
    'departments.length'() {
      this.triggerValidate();
    },
  },
  methods: {
    // 重新申请设置默认值
    setVersionDefaultValue() {
      if (!this.versionData) return;
      const {
        latest_release_strategy: { strategy, bkci_project, organization },
      } = this.versionData;
      this.releaseStrategy = {
        strategy,
        bkci_project,
        organization,
      };
      this.departments = organization || [];
      if (this.departments.length) {
        this.requestAllOrganization(this.departments);
      }
    },
    // 表单校验
    validate() {
      const validateForm = [this.$refs.releaseStrategyForm.validate()];
      if (!this.isFullRelease) {
        validateForm.push(this.$refs.grayscaleRangeForm.validate());
      }
      return Promise.all(validateForm);
    },
    // 手动触发校验
    triggerValidate() {
      this.$refs.grayscaleRangeForm?.validate();
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
      await this.requestAllOrganization(payload);
      this.releaseStrategy.organization = payload;
      this.departments = payload;
      this.isShow = false;
    },
    // 请求组织的层级结构
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
    // 自定义粘贴规则
    customCopyRules(val) {
      const value = String(val).trim();
      if (!value) {
        this.$bkMessage({ theme: 'error', message: this.$t('粘贴内容不能为空'), delay: 2000, dismissable: false });
        return [];
      }
      const commandArr = value.split(',');
      commandArr.forEach((item) => {
        if (!this.releaseStrategy.bkci_project.includes(item)) {
          this.releaseStrategy.bkci_project.push(item);
        }
      });
      return this.releaseStrategy.bkci_project;
    },
    renderMemberTag(node) {
      const h = this.$createElement;

      return h('div', { class: ['tag', { 'hide-delete-icon': this.disableDeletionMapping[node.id] }] }, [
        h('span', { class: ['text'], attrs: { tabIndex: 0 } }, node.id),
      ]);
    },
    handleKeyDown(event) {
      // 已经灰度的项目id不能通过 backspace 键删除
      if (event.key === 'Backspace' && this.disableDeletionMapping[this.focusLastTag]) {
        this.$refs.tagInputRef.isCanRemoveTag = false;
      }
    },
    handleFocus(values) {
      if (values.length) {
        this.focusLastTag = values[values.length - 1];
      }
    },
    handleBlur(input) {
      if (input !== '') {
        this.releaseStrategy.bkci_project.push(input);
      }
    },
    // 是否允许删除已勾选的组织
    handleDisableIconFn(id) {
      if (!this.isDetailStep) return false;
      return this.initDepartments.findIndex(v => v.id === id) !== -1;
    },
    handleChange(value) {
      this.$emit('strategy-change', value);
    },
  },
};
</script>

<style lang="scss" scoped>
.release-strategy-container {
  .mt16 {
    margin-top: 16px;
  }
  .release-strategy-form-cls {
    /deep/ .bk-form-item.is-error {
      .gray-range .bk-button {
        border-color: #ea3636;
        color: #ea3636;
      }
    }
  }
  .release-strategy-cls {
    .range {
      min-width: 323px;
      padding: 12px 16px;
      background: #f5f7fa;
      border-radius: 2px;
      font-size: 12px;
      color: #979ba5;

      .c-item {
        margin-bottom: 16px;
        &:last-child {
          margin-bottom: 0;
        }
        .c-title,
        .c-value {
          line-height: 20px;
        }
        .c-value {
          margin-top: 4px;
          color: #313238;
        }
      }
    }
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
        .bk-label::after {
          display: none;
        }
      }
      .from-tip {
        color: #979ba5;
        .t2 {
          color: #ea3636;
          /deep/ em {
            font-weight: 700;
          }
        }
      }
      .projec-id-tag-cls {
        /deep/ .tag-list .key-node {
          background-color: #fafbfd;
          border: 1px solid #dcdee5;
          border-radius: 2px;
          .tag {
            background-color: #fafbfd;
          }
          .hide-delete-icon + .icon-close {
            display: none;
          }
        }
      }
    }
  }
  .render-member-wrapper .render-member-list-wrapper {
    padding: 0 12px 12px 12px;
  }
}
</style>
