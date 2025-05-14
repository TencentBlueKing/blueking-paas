<template>
  <div class="package-info">
    <!-- 包code/name是否冲突，如果冲突后台会改变code的值 -->
    <div
      class="conflict"
      v-if="(isCodeConflicted || isNameConflicted) && !isModifiedDataDisplayed"
    >
      <!-- 上传包code或name冲突了 -->
      <div>
        <span v-if="originalCode !== packageAppCode">{{ $t('应用 ID') }}：{{ originalCode }}</span>
        &nbsp;
        <span v-if="originalName !== packageAppName">{{ $t('应用名称') }}：{{ originalName }}</span>
        <span>{{ $t('应用已经存在！') }}</span>
        <bk-button
          class="edit-btn ml5"
          :text="true"
          title="primary"
          size="small"
          @click="showEditDialog(true)"
        >
          {{ $t('修改应用 ID') }}
        </bk-button>
      </div>
    </div>
    <div
      class="smart-info"
      v-else
    >
      <div class="left">
        <div class="row-item">
          <div class="label">{{ $t('应用 ID') }}：</div>
          <div :class="['value', { 'has-change': isAppCodeChanged }]">
            <!-- 如果修改了应用信息采用修改后的应用信息 -->
            <span v-if="isModifiedDataDisplayed">{{ modifiedAppData?.code }}</span>
            <span v-else>{{ packageAppCode }}</span>
            <i
              v-if="isAppCodeChanged"
              class="paasng-icon paasng-info-line ml5"
              v-bk-tooltips="$t('Smart 包中声明的应用 ID 为：{n}', { n: originalCode })"
            ></i>
          </div>
        </div>
        <div class="row-item">
          <div class="label">{{ $t('应用名称') }}：</div>
          <div :class="['value', { 'has-change': isAppNameChanged }]">
            <span v-if="isModifiedDataDisplayed">{{ modifiedAppData?.name }}</span>
            <span v-else>{{ packageAppName }}</span>
            <i
              v-if="isAppNameChanged"
              class="paasng-icon paasng-info-line ml5"
              v-bk-tooltips="$t('Smart 包中声明的应用名称为：{n}', { n: originalName })"
            ></i>
          </div>
        </div>
      </div>
      <bk-button
        :text="true"
        title="primary"
        size="small"
        @click="showEditDialog(false)"
      >
        {{ $t('修改应用 ID') }}
      </bk-button>
    </div>
    <ModifyIdDialog
      :show.sync="isEditDialog"
      :data="dialogData"
      :verify-code="verifyCode"
      @confirm="handleConfirm"
    />
  </div>
</template>

<script>
import ModifyIdDialog from './modify-id-dialog.vue';
export default {
  props: {
    data: {
      type: Object,
      default: () => ({}),
    },
  },
  components: {
    ModifyIdDialog,
  },
  data() {
    return {
      isEditDialog: false,
      modifiedAppData: null,
      dialogData: {},
      verifyCode: '',
    };
  },
  computed: {
    packageAppCode() {
      return this.data.app_description?.code;
    },
    packageAppName() {
      return this.data.app_description?.name;
    },
    originalCode() {
      return this.data.original_app_description?.code;
    },
    originalName() {
      return this.data.original_app_description?.name;
    },
    // code是否冲突 (如果code一致，后台回在code加上两位随机数)
    isCodeConflicted() {
      return this.originalCode !== this.packageAppCode;
    },
    // name是否冲突
    isNameConflicted() {
      return this.originalName !== this.packageAppName;
    },
    // code 是否与包一致
    isAppCodeChanged() {
      if (this.isModifiedDataDisplayed) {
        return this.modifiedAppData?.code !== this.originalCode;
      }
      return this.isCodeConflicted;
    },
    // name 是否与包一致
    isAppNameChanged() {
      if (this.isModifiedDataDisplayed) {
        return this.modifiedAppData?.name !== this.originalName;
      }
      return this.isNameConflicted;
    },
    isModifiedDataDisplayed() {
      return this.modifiedAppData !== null;
    },
  },
  methods: {
    // 修改信息弹窗
    showEditDialog(isConflict = false) {
      if (isConflict || !this.isModifiedDataDisplayed) {
        this.dialogData = {
          code: this.packageAppCode,
          name: this.packageAppName,
        };
      } else {
        this.dialogData = { ...this.modifiedAppData };
      }
      this.verifyCode = this.isCodeConflicted ? this.originalCode : '';
      this.isEditDialog = true;
    },
    handleConfirm(data) {
      this.modifiedAppData = { ...data };
      this.$emit('change-app', data);
    },
  },
};
</script>

<style lang="scss" scoped>
.package-info {
  .conflict {
    font-size: 12px;
    color: #e71818;
  }
  .edit-btn {
    line-height: 0;
    height: auto;
    padding: 0;
  }
}
.smart-info,
.row-item {
  display: flex;
  align-items: center;
}
.smart-info {
  justify-content: space-between;
  margin-top: 8px;
  background: #f5f7fa;
  border-radius: 2px;
  padding: 10px 12px;
  .row-item {
    .label {
      min-width: 90px;
      text-align: right;
    }
    .value {
      flex: 1;
      color: #313238;
      &.has-change {
        color: #e38b02;
      }
      i {
        color: #979ba5;
        &:hover {
          color: #4d4f56;
        }
      }
    }
  }
}
</style>
