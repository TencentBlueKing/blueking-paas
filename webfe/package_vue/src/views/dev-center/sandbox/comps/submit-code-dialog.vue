<template>
  <bk-dialog
    v-model="dialogVisible"
    :width="640"
    :theme="'primary'"
    :header-position="'left'"
    :mask-close="false"
    :auto-close="false"
    render-directive="if"
    :title="$t('提交代码')"
    @value-change="handleChange"
  >
    <div slot="footer">
      <span
        style="display: inline-block"
        v-bk-tooltips="{ content: disableTip, disabled: !isConfirmBtnDisable }"
      >
        <bk-button
          theme="primary"
          :disabled="isConfirmBtnDisable"
          :loading="isConfirmLoading"
          @click="handleConfirm"
        >
          {{ $t('确定') }}
        </bk-button>
      </span>
      <bk-button
        :theme="'default'"
        type="submit"
        class="ml8"
        @click="dialogVisible = false"
      >
        {{ $t('取消') }}
      </bk-button>
    </div>
    <div
      class="dialog-content"
      :style="{ height: twoThirdsHeight + 'px' }"
      v-bkloading="{ isLoading: config.loading, zIndex: 10 }"
    >
      <div class="file-change-box item">
        <div class="top flex-row align-items-center justify-content-between">
          <div class="title">
            {{ $t('变更文件') }}
            <span class="file-count">（{{ config.fileTotal }}）</span>
          </div>
          <div class="right flex-row align-items-center">
            <div
              v-for="item in changeStatus"
              :key="item.status"
              :style="{ color: item.color }"
              class="status-item"
            >
              <i
                :class="['icon', item.status]"
                :style="{ background: item.color }"
              ></i>
              <span class="text">{{ item.text }}</span>
            </div>
          </div>
        </div>
        <div :class="['file-change', { empty: config.fileTotal === 0 }]">
          <bk-exception
            v-if="config.fileTotal === 0"
            type="empty"
            scene="part"
          >
            <span class="empty-text">{{ $t('没有变更的文件') }}</span>
          </bk-exception>
          <Directory
            v-else
            :node="fileTree"
            :path="''"
            :indent-level="12"
          />
        </div>
      </div>
      <div class="commit item">
        <div class="top">
          <div class="title">Commit Message</div>
        </div>
        <bk-form
          :label-width="0"
          :model="formData"
          :rules="rules"
          ref="messageRef"
        >
          <bk-form-item
            label=""
            :required="true"
            :property="'commitMessage'"
            :error-display-type="'normal'"
          >
            <bk-input
              v-model="formData.commitMessage"
              :clearable="true"
            ></bk-input>
          </bk-form-item>
        </bk-form>
      </div>
    </div>
  </bk-dialog>
</template>

<script>
import Directory from './directory.vue';
import { bus } from '@/common/bus';
import { throttle } from 'lodash';
const defaultDialogHeight = 480;

export default {
  name: 'SubmitCodeDialog',
  components: { Directory },
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    config: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      changeStatus: [
        { status: 'add', color: '#299E56', text: this.$t('新增') },
        { status: 'change', color: '#E38B02', text: this.$t('修改') },
        { status: 'del', color: '#C4C6CC', text: this.$t('删除') },
      ],
      isConfirmLoading: false,
      isConfirmBtnDisable: false,
      formData: {
        commitMessage: '',
      },
      errorFileNames: [],
      twoThirdsHeight: defaultDialogHeight,
      rules: {
        commitMessage: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
      },
    };
  },
  computed: {
    dialogVisible: {
      get: function () {
        return this.show;
      },
      set: function (val) {
        this.$emit('update:show', val);
      },
    },
    fileTree() {
      return this.config?.tree ?? {};
    },
    disableTip() {
      if (this.config.fileTotal === 0) {
        return this.$t('没有变更的文件');
      }
      if (!this.errorFileNames.length) {
        return this.$t('文件名不符合规范');
      } else if (this.errorFileNames.length < 3) {
        return this.$t('文件 {x} 名称不符合规范', { x: this.errorFileNames.join('，') });
      } else {
        return this.$t('文件 {x} 等 {n} 个文件名称不符合规范', {
          x: this.errorFileNames.slice(0, 2).join('，'),
          n: this.errorFileNames.length,
        });
      }
    },
  },
  watch: {
    config: {
      handler(newValue) {
        this.isConfirmBtnDisable = newValue.isConfirm;
      },
      deep: true,
    },
  },
  created() {
    this.updateHeight();
    bus.$on('name-validation-failed', (fileName) => {
      // 不符合规则的文件名称列表
      if (!this.errorFileNames.includes(fileName)) {
        this.errorFileNames.push(fileName);
      }
      this.isConfirmBtnDisable = true;
    });
    window.addEventListener('resize', throttle(this.updateHeight, 50));
  },
  beforeDestroy() {
    bus.$off('name-validation-failed');
    window.removeEventListener('resize', this.updateHeight);
  },
  methods: {
    reset() {
      this.isConfirmBtnDisable = false;
      this.formData.commitMessage = '';
    },
    closeLoading() {
      this.isConfirmLoading = false;
    },
    handleConfirm() {
      this.$refs.messageRef.validate().then(
        () => {
          this.isConfirmLoading = true;
          this.$emit('submit', this.formData.commitMessage);
        },
        (e) => {
          console.error(e);
        }
      );
    },
    handleChange(flag) {
      if (!flag) {
        this.$emit('reset');
        this.reset();
      }
    },
    updateHeight() {
      const calculatedHeight = Math.floor((2 / 3) * window.innerHeight) - 138;
      this.twoThirdsHeight = calculatedHeight;
    },
  },
};
</script>

<style lang="scss" scoped>
.dialog-content {
  display: flex;
  flex-direction: column;
  font-size: 12px;
  .file-change-box {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .added {
    color: #299e56;
  }
  .modified {
    color: #e38b02;
  }
  .deleted {
    color: #c4c6cc;
  }
  .item {
    &.commit {
      margin-top: 24px;
    }
    .title {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 14px;
      color: #4d4f56;
      line-height: 22px;
      margin-bottom: 6px;
    }
    .file-count {
      font-size: 12px;
      color: #979ba5;
    }
    .right {
      .icon {
        display: inline-block;
        width: 8px;
        height: 8px;
        margin-right: 4px;
      }
      .text {
        font-size: 12px;
        line-height: 20px;
      }
      .status-item {
        margin-left: 16px;
      }
    }
    .file-change {
      flex: 1;
      padding: 8px 0;
      overflow: auto;
      font-size: 14px;
      border-radius: 2px;
      background: #ffffff;
      border: 1px solid #dcdee5;
      &.empty {
        display: flex;
        align-items: center;
      }
      .empty-text {
        font-size: 12px;
      }
    }
  }
}
</style>
