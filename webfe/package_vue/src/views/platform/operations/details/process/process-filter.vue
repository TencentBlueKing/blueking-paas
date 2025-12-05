<template>
  <div class="card-style top-box flex-row align-items-center">
    <div class="filter-section">
      <div class="label">
        <i class="paasng-icon paasng-project"></i>
        {{ $t('模块') }}
      </div>
      <bk-select
        v-model="currentModule"
        style="width: 180px"
        :clearable="false"
        searchable
        ext-cls="module-select-cls"
        @change="handleModuleChange"
      >
        <bk-option
          v-for="option in moduleList"
          :key="option.name"
          :id="option.name"
          :name="option.name"
        ></bk-option>
      </bk-select>
    </div>
    <template v-if="processList.length">
      <div class="line"></div>
      <div
        class="process-section flex-row align-items-center"
        v-bkloading="{ isLoading: loading, zIndex: 10 }"
      >
        <div class="process-label">
          <img
            class="image-icon"
            src="/static/images/deploy-4.svg"
          />
          <span>{{ $t('进程') }}</span>
        </div>
        <div class="process-tabs">
          <div
            v-for="process in processList"
            :key="process.name"
            class="process-tab"
            :class="{ active: currentProcess === process.name }"
            @click="handleProcessClick(process.name)"
          >
            <span class="process-name">{{ process.name }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
export default {
  name: 'ProcessFilter',
  props: {
    loading: {
      type: Boolean,
      default: false,
    },
    moduleList: {
      type: Array,
      default: () => [],
    },
    processList: {
      type: Array,
      default: () => [],
    },
    curModule: {
      type: String,
      default: '',
    },
    curProcess: {
      type: String,
      default: '',
    },
  },
  computed: {
    currentModule: {
      get() {
        return this.curModule;
      },
      set(value) {
        this.$emit('update:curModule', value);
      },
    },
    currentProcess: {
      get() {
        return this.curProcess;
      },
      set(value) {
        this.$emit('update:curProcess', value);
      },
    },
  },
  methods: {
    handleModuleChange(value) {
      this.$emit('module-change', value);
    },
    handleProcessClick(processId) {
      this.$emit('process-change', processId);
    },
  },
};
</script>

<style lang="scss" scoped>
.top-box {
  padding: 10px 24px 10px 0;
  background: #fff;
  margin-bottom: 16px;
}

.filter-section {
  display: flex;
  align-items: center;

  .label {
    width: 104px;
    padding-right: 24px;
    font-size: 14px;
    color: #63656e;
    text-align: right;
    i {
      color: #a3c5fd;
    }
  }
  .module-select-cls {
    background-color: #f0f1f5;
    border: none;
  }
}

.line {
  width: 1px;
  height: 32px;
  background: #eaebf0;
  margin: 0 24px;
}

.process-section {
  .process-label {
    display: flex;
    align-items: center;
    font-size: 14px;
    color: #63656e;
    margin-right: 24px;

    .image-icon {
      width: 18px;
      height: 18px;
      margin-right: 4px;
    }
  }

  .process-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;

    .process-tab {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 32px;
      padding: 0 24px;
      background: #f5f7fa;
      border-radius: 2px;
      cursor: pointer;
      transition: all 0.3s;

      .process-name {
        font-size: 14px;
        color: #63656e;
      }

      &:hover {
        background: #e1ecff;
      }

      &.active {
        background: #e1ecff;
        border: 1px solid #3a84ff;

        .process-name {
          color: #3a84ff;
          font-weight: 500;
        }
      }
    }
  }
}
</style>
