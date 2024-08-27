<template>
  <div class="process-card-container" @click="handleClick">
    <div :class="wrapperClasses">
      <div class="logo mr10">
        <img
          class="image-icon"
          src="/static/images/deploy-4.svg"
        />
      </div>
      <div class="title">
        <span>{{ $t(label) }}</span>：
        <span>{{ name }}</span>
      </div>
      <!-- 编辑 -->
      <i
        v-if="isEdit"
        class="paasng-icon paasng-edit-2 edit-cls"
        @click.stop="$emit('edit', name)"
      />
      <!-- 删除、主模块不能删除 -->
      <i
        v-if="!main && isEdit"
        v-bk-tooltips="{ content: $t('一个模块下，必须有一个进程'), disabled: !delIconDisabled }"
        class="paasng-icon paasng-plus-circle-shape delete-cls"
        :class="{ 'disabled': delIconDisabled }"
        @click.stop="$emit('delete', name)"
      />
      <!-- 主入口标识 -->
      <div
        class="main-sign"
        v-if="main"
      >
        {{ $t('访问入口') }}
      </div>
      <!-- 开启进程服务，开启展示 -->
      <div
        v-if="startService"
        class="start-service-sign"
        v-bk-tooltips="$t('已开启服务')"
      >
        <img
          class="servie-icon"
          src="/static/images/svc.svg"
        />
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ProcessCard',
  props: {
    mode: {
      type: String,
      default: 'view',
    },
    active: {
      type: Boolean,
      default: false,
    },
    main: {
      type: Boolean,
      default: false,
    },
    startService: {
      type: Boolean,
      default: false,
    },
    label: {
      type: String,
      default: '进程',
    },
    name: {
      type: String,
      default: '',
    },
    delIconDisabled: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {};
  },
  computed: {
    wrapperClasses() {
      return {
        wrapper: true,
        main: this.main,
        active: this.active,
        edit: this.isEdit,
      };
    },
    isEdit() {
      return this.mode === 'edit';
    },
  },
  methods: {
    handleClick() {
      this.$emit('change', this.name);
    },
  },
};
</script>

<style lang="scss" scoped>
.process-card-container {
  display: inline-block;
  position: relative;
  cursor: pointer;
  .wrapper {
    position: relative;
    min-width: 160px;
    display: flex;
    align-items: center;
    height: 52px;
    padding: 0 12px 0 14px;
    font-size: 14px;
    color: #313238;
    background: #f5f7fa;
    border-radius: 2px;
    &.active {
      background: #e1ecff !important;
      border: 1px solid #3a84ff;
    }
    &:hover {
      background: #eaebf0;
      .edit-cls,
      .delete-cls {
        display: block;
      }
    }
    &.edit {
      background: #ffffff;
      box-shadow: 0 2px 4px 0 #1919290d;
      &:hover {
        box-shadow: 0 2px 4px 0 #0000001a, 0 2px 4px 0 #1919290d;
      }
    }
    .edit-cls {
      margin-left: 5px;
      display: none;
      transform: translateY(0);
      color: #979ba5;
      &:hover {
        color: #3a84ff;
      }
    }
    .delete-cls {
      display: none;
      position: absolute;
      top: -3px;
      right: -3px;
      color: #EA3636;
      transform: rotate(45deg);
      &.disabled {
        color: #c4c6cc;
        cursor: not-allowed;
      }
    }
    .main-sign {
      position: absolute;
      top: 0;
      right: 0;
      height: 16px;
      font-size: 10px;
      padding-left: 6px;
      color: #FFFFFF;
      background: #3a84ff;
      border-radius: 0 2px 0 100px;
    }
    .start-service-sign {
      position: absolute;
      display: flex;
      align-items: center;
      justify-content: center;
      top: -5px;
      left: -5px;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: #ffffff;
      border: 1px solid #dcdee5;
      .servie-icon {
        width: 18px;
        height: 18px;
      }
    }
    .logo {
      flex-shrink: 0;
      width: 26px;
      height: 26px;
      .image-icon {
        width: 100%;
        height: 100%;
      }
    }
    .title {
      flex: 1;
      user-select: none;
    }
  }
}
</style>
