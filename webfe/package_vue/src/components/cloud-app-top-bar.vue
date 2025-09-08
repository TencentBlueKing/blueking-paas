<template>
  <div class="nav-wrapper">
    <div :class="['title', 'pt15', { pb15: !navList.length }, { 'fixed-height': !navList.length }]">
      <slot name="title">{{ title }}</slot>
      <div
        v-if="isMigrationProgress"
        class="migration-progress"
        @click.stop="handleShowAppMigrationDialog"
      >
        <i class="paasng-icon paasng-qianyi-mianxing" />
        <span>{{ $t('迁移进度') }}</span>
      </div>
      <!-- 模块列表 -->
      <div class="module-select-wrapper">
        <bk-select
          v-if="moduleList.length"
          :clearable="false"
          :disabled="false"
          v-model="curModelName"
          style="width: 120px"
          ext-cls="module-select-custom"
          ext-popover-cls="select-popover-custom"
          prefix-icon="paasng-icon paasng-project"
          @selected="handleChangeModule"
        >
          <bk-option
            v-for="option in moduleList"
            :key="option.name"
            :id="option.name"
            :name="option.name"
          ></bk-option>
          <div
            slot="trigger"
            class="module-wrapper"
          >
            <div
              class="name"
              :title="curModelName"
            >
              {{ curModelName }}
            </div>
            <i class="paasng-icon paasng-down-shape"></i>
          </div>
        </bk-select>
      </div>
      <div class="slot-right">
        <slot name="right"></slot>
      </div>
    </div>
    <div
      class="flex-row justify-content-between align-items-center"
      v-if="navList.length"
    >
      <bk-tab
        :active.sync="curActive"
        ext-cls="app-tab-cls"
        type="unborder-card"
        @tab-change="handleTabChange"
      >
        <bk-tab-panel
          v-for="(panel, index) in navList"
          :key="index"
          :label="panel.label"
          v-bind="panel"
        />
      </bk-tab>
      <div
        class="module-manager"
        @click="handleRightConfigClick"
        v-if="rightTitle"
      >
        <i class="paasng-icon paasng-lishijilu"></i>
        <span class="title">{{ rightTitle }}</span>
      </div>
    </div>
  </div>
</template>
<script>
import { defineComponent, ref, watch, computed, getCurrentInstance } from 'vue';
import store from '@/store';
import router from '@/router';
import { traceIds } from '@/common/trace-ids';

export default defineComponent({
  name: 'EditorStatus',
  props: {
    title: {
      type: String,
      default: '',
    },
    navList: {
      type: Array,
      default() {
        return [];
      },
    },
    active: {
      type: String,
      default: '',
    },
    rightTitle: {
      type: String,
      default: '',
    },
    appCode: {
      type: String | Number,
      default: '',
    },
    curModule: {
      type: Object,
      default() {
        return {
          name: '',
        };
      },
    },
    moduleList: {
      type: Array,
      default() {
        return [];
      },
    },
    // 迁移进度
    isMigrationProgress: {
      type: Boolean,
      default: false,
    },
    // 是否添加元素埋点
    isTrace: {
      type: Boolean,
      default: false,
    },
  },
  setup(props, { emit }) {
    const curActive = ref(props.active || props.navList[0]?.name);
    const curModelName = ref(props.curModule.name || 'default');
    const instance = getCurrentInstance();
    const route = router.currentRoute;
    const curAppInfo = computed(() => store.state.curAppInfo);
    const handleTabChange = () => {
      if (props.isTrace) {
        const category = curAppInfo.value.application?.type === 'cloud_native' ? '云原生应用' : '普通应用';
        const label = props.navList.find((item) => item.name === curActive.value).label;
        instance.proxy.sendEventTracking({ id: traceIds[label], action: 'view', category });
      }
      emit('change', curActive.value);
    };

    const handleRightConfigClick = () => {
      emit('right-config-click');
    };

    const handleChangeModule = (moduleName) => {
      const module = props.moduleList.find((item) => item.name === moduleName) || {};
      emit('change-module', module);
      store.commit('updateCurAppModule', module);
      // 根据模块刷新当前路由
      router.push({
        name: route.name,
        params: {
          id: props.appCode,
          moduleId: moduleName,
        },
        query: route.query,
      });
    };

    watch([() => props.navList, () => props.active], ([newList, newActive]) => {
      curActive.value = newActive || newList[0]?.name;
    });

    const handleShowAppMigrationDialog = () => {
      emit('migration-dialog', true);
    };

    return {
      curActive,
      curModelName,
      handleTabChange,
      handleRightConfigClick,
      handleChangeModule,
      handleShowAppMigrationDialog,
    };
  },
});
</script>
<style lang="scss" scoped>
.nav-wrapper {
  background: #fff;
  box-shadow: 0 3px 4px 0 #0000000a;
  .title {
    position: relative;
    font-size: 16px;
    color: #313238;
    padding: 0 24px;
    display: flex;
    align-items: center;
    .slot-right {
      position: absolute;
      right: 24px;
    }
    &.fixed-height {
      height: 52px;
    }
  }
  .module-select-custom {
    margin-left: 16px;
    background: #f0f1f5;
    border: none;

    &.is-focus {
      background: #fff;
      border: 1px solid #3a84ff;
      box-shadow: none;
      &:hover {
        background: #fff;
      }
    }

    &:hover {
      background: #eaebf0;
    }
  }
  .migration-progress {
    color: #3a84ff;
    font-size: 12px;
    cursor: pointer;
    i {
      margin-right: 5px;
      margin-left: 14px;
      font-size: 14px;
      transform: translateY(0);
    }
  }
}
.module-select-wrapper {
  /deep/ .is-focus {
    .paasng-down-shape {
      transform: rotate(180deg) translateY(7px);
      color: #3a84ff;
    }
  }
  /deep/ .bk-select-prefix-icon {
    color: #a3c5fd;
    font-size: 14px;
    margin-left: 3px;
  }
  .module-wrapper {
    position: relative;

    .name {
      font-size: 14px;
      margin: 0 25px;
      margin-left: 28px;
      line-height: 32px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    i {
      position: absolute;
      right: 8px;
      top: 50%;
      transform: translateY(-50%);
      transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      color: #c4c6cc;
    }
  }
}
.app-tab-cls {
  /deep/ .bk-tab-section {
    padding: 0 !important;
  }
  /deep/ .bk-tab-header {
    background-image: none !important;
  }
}
.module-manager {
  color: #3a84ff;
  cursor: pointer;
  display: flex;
  align-items: center;
  i {
    transform: translateY(0);
  }
  .title {
    font-size: 14px;
    color: #3a84ff;
    padding-left: 6px;
  }
}
</style>
