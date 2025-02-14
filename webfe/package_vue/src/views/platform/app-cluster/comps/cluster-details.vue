<template>
  <div class="cluster-details-container">
    <bk-resize-layout
      :immediate="true"
      :min="280"
      style="width: 100%"
    >
      <div
        class="list"
        slot="aside"
      >
        <!-- 收起详情 -->
        <div
          class="hide-icon"
          @click="$emit('toggle', false)"
        >
          <i class="paasng-icon paasng-angle-line-up"></i>
        </div>
        <div class="top-tool">
          <div class="left flex-row">
            <bk-button :theme="'primary'">
              <i class="paasng-icon paasng-plus"></i>
            </bk-button>
            <SwitchDisplay
              class="ml8 switch-cls"
              :list="buttonList"
              :has-icon="true"
              :active="buttonActive"
              @change="handlerChange"
            >
              <div slot-scope="{ item }">
                <i :class="`btn-icon paasng-icon paasng-${item.icon}`"></i>
              </div>
            </SwitchDisplay>
          </div>
          <bk-input
            class="search-input"
            v-model="searchValue"
            :placeholder="$t('搜索集群名称、集群ID、所属租户、特性')"
            :right-icon="'bk-icon icon-search'"
          ></bk-input>
        </div>
        <ul class="mt15 cluster-list">
          <li class="header-item item">{{ $t('集群名称') }}</li>
          <li
            v-for="item in ['cluster01', 'cluster02', 'cluster03']"
            :key="item"
            :class="['item', { active: curClusterdetail === item }]"
            @click="handleChange(item)"
          >
            {{ item }}
          </li>
        </ul>
      </div>
      <div
        class="details-wrapper"
        slot="main"
      >
        <div
          class="close"
          @click="$emit('toggle', false)"
        >
          <bk-icon type="close" />
        </div>
        <bk-tab
          :active.sync="tabActive"
          type="card"
        >
          <bk-tab-panel
            v-for="(panel, index) in panels"
            v-bind="panel"
            :key="index"
          ></bk-tab-panel>
          <p>1111</p>
          <p>1111</p>
          <p>1111</p>
        </bk-tab>
      </div>
    </bk-resize-layout>
  </div>
</template>

<script>
import SwitchDisplay from './switch-display.vue';
export default {
  name: 'ClusterDetails',
  components: {
    SwitchDisplay,
  },
  data() {
    return {
      tabActive: 'info',
      buttonActive: 'cluster',
      curClusterdetail: 'cluster01',
      buttonList: [
        { name: 'cluster', icon: 'organization' },
        { name: 'tenant', icon: 'user2' },
      ],
      panels: [
        { name: 'info', label: this.$t('集群信息') },
        { name: 'components', label: this.$t('集群组件') },
        { name: 'feature', label: this.$t('集群特性') },
      ],
      searchValue: '',
    };
  },
  methods: {
    handlerChange(data) {
      this.buttonActive = data.name;
    },
    handleChange(row) {
      this.curClusterdetail = row;
    },
  },
};
</script>

<style lang="scss" scoped>
.cluster-details-container {
  height: 100%;
  display: flex;
  margin-top: 16px;
  /deep/ .bk-resize-layout {
    gap: 16px;
    border: none;
    .bk-resize-layout-aside,
    .bk-resize-layout-main {
      border: none;
      background: #fff;
      box-shadow: 0 2px 4px 0 #1919290d;
      border-radius: 2px;
    }
    .bk-resize-layout-aside {
      min-width: 280px;
    }
  }
  .list {
    padding: 16px;
    .cluster-list {
      .item {
        position: relative;
        height: 42px;
        line-height: 42px;
        font-size: 12px;
        padding: 0 16px;
        margin-top: -1px;
        color: #3a84ff;
        background: #ffffff;
        border: 1px solid transparent;
        border-top-color: #dcdee5;
        &:last-child {
          border-bottom-color: #dcdee5;
        }
        &:not(.header-item) {
          cursor: pointer;
        }
        &.active {
          height: 42px;
          border: 1px solid #3a84ff;
          background: #f0f5ff;
          border-radius: 2px;
          z-index: 2;
          &::after {
            content: '';
            position: absolute;
            width: 0;
            height: 0;
            right: -8px;
            top: 50%;
            border: 4px solid transparent;
            border-left: 4px solid #3a84ff;
            transform: translateY(-50%);
          }
        }
      }
      .header-item {
        border-top-color: transparent;
        background: #fafbfd;
        color: #313238;
      }
    }
    .hide-icon {
      position: absolute;
      display: flex;
      align-items: center;
      right: -16px;
      top: 35%;
      width: 16px;
      height: 64px;
      color: #ffffff;
      background: #dcdee5;
      cursor: pointer;
      border-radius: 0 4px 4px 0;
      i {
        transform: rotate(90deg);
      }
    }
    .top-tool {
      display: flex;
      align-items: center;
      gap: 8px;
      .switch-cls /deep/ .group-item {
        padding: 0 4px;
      }
      .bk-button {
        min-width: 0;
        padding: 0 10px;
      }
      .paasng-plus {
        font-size: 12px;
        font-weight: 700;
      }
      .search-input {
        flex: 1;
      }
    }
  }
  .details-wrapper {
    position: relative;
    flex: 1;
    .close {
      position: absolute;
      right: 7px;
      top: 6px;
      font-size: 28px;
      color: #979ba5;
      z-index: 9;
      i {
        cursor: pointer;
      }
    }
    /deep/ .bk-tab-header {
      height: 42px !important;
      background-image: none !important;
      background-color: #f0f1f5;
      .bk-tab-label-list {
        border: none !important;
        .bk-tab-label-item {
          line-height: 42px !important;
          position: relative;
          border: none;
          &::before,
          &:last-child::after {
            content: '';
            position: absolute;
            top: 50%;
            width: 1px;
            height: 16px;
            background: #c4c6cc;
            transform: translateY(-50%);
          }
          &::before {
            left: 0;
          }
          &:last-child::after {
            right: 0;
          }
          &.active {
            border-radius: 4px 4px 0 0;
          }
          &.active::before,
          &.active::after {
            background: transparent;
          }
          &.active + .bk-tab-label-item::before {
            background: transparent;
          }
          &.is-first::before {
            background: transparent !important;
          }
        }
      }
    }
    /deep/ .bk-tab-section {
      border: none;
    }
  }
}
</style>
