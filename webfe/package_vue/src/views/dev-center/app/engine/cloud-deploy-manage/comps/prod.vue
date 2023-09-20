<template>
  <div class="stag-wrapper">
    <section class="top-operate">
      <bk-button :theme="'default'" class="mr10" @click="handleSetCloseExpand">
        <i class="paasng-icon paasng-shouqi" v-if="isExpand"></i>
        <i class="paasng-icon paasng-zhankai" v-else></i>
        {{ isExpand ? $t('全部收起') : $t('全部展开') }}
      </bk-button>
      <div class="module-select-wrapper">
        <bk-select
          :disabled="false"
          v-model="moduleValue"
          style="width: 250px;"
          ext-cls="select-custom"
          ext-popover-cls="select-popover-custom"
          searchable>
          <bk-option
            v-for="(module, index) in moduleList"
            :key="index"
            :id="module.name"
            :name="module.name">
          </bk-option>
        </bk-select>
      </div>
    </section>
    <!-- 根据模块渲染 -->
    <deploy-module-list
      :model-name="moduleValue"
      ref="moduleListRef"
      :environment="environment"
      v-bind="$attrs"
    />
  </div>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin.js';
import deployModuleList from './deploy-module-list.vue';
export default {

  components: {
    deployModuleList,
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
      moduleValue: '全部模块',
      showModuleList: [],
      isExpand: false,
    };
  },

  computed: {
    moduleList() {
      const appModuleList = [{
        id: 'all',
        name: '全部模块',
      }, ...this.curAppModuleList];
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
      if (value === '全部模块') {
        this.showModuleList = this.moduleInfoList;
      } else {
        this.showModuleList = this.moduleInfoList.filter(module => module.name === this.moduleValue);
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
  },
};
</script>

<style lang="scss" scoped>
.stag-wrapper {
  height: 100%;
  .top-operate {
    display: flex;
    margin-bottom: 16px;
    .paasng-shouqi,
    .paasng-zhankai {
      margin-right: 3px;
    }
  }
  .module-select-wrapper {
    background: #fff;
  }
}
</style>
