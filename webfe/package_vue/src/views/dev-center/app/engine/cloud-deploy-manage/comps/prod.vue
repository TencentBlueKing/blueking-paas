<template>
  <div class="stag-wrapper flex-column">
    <section class="top-operate">
      <div class="left">
        <bk-button
          :theme="'default'"
          class="mr10"
          @click="handleSetCloseExpand"
        >
          <i
            class="paasng-icon paasng-shouqi"
            v-if="isExpand"
          ></i>
          <i
            class="paasng-icon paasng-zhankai"
            v-else
          ></i>
          {{ isExpand ? $t('收起实例详情') : $t('展开实例详情') }}
        </bk-button>
        <div class="module-select-wrapper">
          <bk-select
            :disabled="false"
            v-model="moduleValue"
            style="width: 250px"
            ext-cls="select-custom"
            ext-popover-cls="select-popover-custom"
            prefix-icon="paasng-icon paasng-project"
            searchable
          >
            <bk-option
              v-for="(module, index) in moduleList"
              :key="index"
              :id="module.name"
              :name="module.name"
            ></bk-option>
          </bk-select>
        </div>
      </div>
      <!-- 后续兼容 -->
      <!-- <bk-button
        class="sandbox-btn"
        :loading="isSandboxLoading"
        @click="handleSandboxDev"
      >
        {{ $t('沙箱开发') }}
      </bk-button> -->
    </section>
    <!-- 根据模块渲染 -->
    <deploy-module-list
      :model-name="moduleValue"
      ref="prodModuleListRef"
      :environment="environment"
      v-bind="$attrs"
      @module-deployment-info="updateModuleDeploymentData"
      @expand="($event) => (isExpand = !$event)"
    />
    <!-- 后续兼容 -->
    <!-- <sandbox-sideslider
      env="prod"
      :show.sync="isShowSandboxSideslider"
      :module-deploy-list="moduleDeploymentData"
    /> -->
  </div>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin.js';
import deployModuleList from './deploy-module-list.vue';
import SandboxSideslider from './sandbox-sideslider.vue';
export default {
  components: {
    deployModuleList,
    SandboxSideslider,
  },
  mixins: [appBaseMixin],
  props: {
    environment: {
      type: String,
      default: () => 'stag',
    },
  },

  data() {
    return {
      moduleValue: this.$t('全部模块'),
      showModuleList: [],
      isExpand: false,
      isShowSandboxSideslider: false,
      isSandboxLoading: true,
      moduleDeploymentData: [],
    };
  },

  computed: {
    moduleList() {
      const appModuleList = [
        {
          id: 'all',
          name: this.$t('全部模块'),
        },
        ...this.curAppModuleList,
      ];
      return appModuleList;
    },
    // 包含当前面板所需状态
    moduleInfoList() {
      return this.curAppModuleList.map((module) => {
        module.isExpand = true;
        // 默认展开已部署第一项
        // if (module.repo) {
        //   module.isExpand = true;
        // }
        return module;
      });
    },
  },

  watch: {
    moduleValue(value) {
      if (value === this.$t('全部模块') || value === '') {
        this.showModuleList = this.moduleInfoList;
      } else {
        this.showModuleList = this.moduleInfoList.filter((module) => module.name === this.moduleValue);
      }
    },
  },

  created() {
    this.showModuleList = this.moduleInfoList;
  },

  methods: {
    // 将模块的进程实例全部收起
    handleSetCloseExpand() {
      if (this.isExpand) {
        this.$refs.prodModuleListRef && this.$refs.prodModuleListRef.handleSetCloseExpand();
      } else {
        this.$refs.prodModuleListRef && this.$refs.prodModuleListRef.handleSetOpenExpand();
      }
      this.isExpand = !this.isExpand;
    },
    // 沙箱开发
    handleSandboxDev() {
      this.isShowSandboxSideslider = true;
    },
    updateModuleDeploymentData(data) {
      this.moduleDeploymentData = data;
      this.isSandboxLoading = false;
    },
  },
};
</script>

<style lang="scss" scoped>
.stag-wrapper {
  height: 100%;
  .top-operate {
    display: flex;
    justify-content: space-between;
    margin-bottom: 16px;
    .left {
      display: flex;
    }
    .paasng-shouqi,
    .paasng-zhankai {
      margin-right: 3px;
    }
    .sandbox-btn {
      border-color: #3a84ff;
      color: #3a84ff;
      &:hover {
        border-color: #1768ef;
        background: #e1ecff;
        color: #1768ef;
      }
    }
  }
  .module-select-wrapper {
    background: #fff;
  }
}
.select-custom {
  /deep/ i.paasng-project {
    color: #a3c5fd;
  }
}
</style>
