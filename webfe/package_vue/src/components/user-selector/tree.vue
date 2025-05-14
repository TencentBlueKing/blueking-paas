<template>
  <div
    :class="['paasng-infinite-tree', { 'bk-has-border-tree': isBorder }]"
    @scroll="rootScroll">
    <div class="ghost-wrapper" :style="ghostStyle"></div>
    <div class="render-wrapper" ref="content">
      <div
        v-for="item in renderData" :key="item.$id"
        :style="getNodeStyle(item)"
        :class="['node-item', { 'is-disabled': item.disabled && item.type === 'user' }]"
        @click.stop="nodeClick(item)">
        <template v-if="item.async">
          <img class="arrow-icon mr5" src="./images/angle-up-fill.svg" alt="" v-if="item.expanded" @click.stop="expandNode(item)">
          <img class="arrow-icon mr5" src="./images/right-shape.svg" alt="" v-else @click.stop="expandNode(item)">
        </template>
        <template v-if="item.type === 'department'">
          <img class="node-icon" src="./images/file-close.svg" alt="">
        </template>
        <img v-else class="node-svg" src="./images/personal-user.svg" alt="">
        <span
          :style="nameStyle(item)"
          :class="['node-title', { 'is-disabled': item.disabled && item.type === 'user' }]"
          :title="item.type === 'department' ? item.full_name : item.username !== '' ? `${item.display_name}(${item.username})` : item.display_name">
          {{ item.type === 'user' ? item.display_name : item.name }}
          <template v-if="item.type === 'user' && item.username !== ''">
            ({{ item.username }})
          </template>
        </span>
        <div class="bk-spin-loading bk-spin-loading-mini bk-spin-loading-primary loading ml5" v-if="item.loading">
          <div class="rotate rotate1"></div>
          <div class="rotate rotate2"></div>
          <div class="rotate rotate3"></div>
          <div class="rotate rotate4"></div>
          <div class="rotate rotate5"></div>
          <div class="rotate rotate6"></div>
          <div class="rotate rotate7"></div>
          <div class="rotate rotate8"></div>
        </div>
        <div class="node-radio" v-if="item.showRadio">
          <span
            class="node-checkbox"
            :class="{
              'is-disabled': item.disabled,
              'is-checked': item.is_selected,
              'is-indeterminate': item.indeterminate
            }"
            @click.stop="handleNodeClick(item)">
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
export default {
  name: '',
  props: {
    // 所有数据
    allData: {
      type: Array,
      default: () => [],
    },
    // 每个节点的高度
    itemHeight: {
      type: Number,
      default: 32,
    },
    // 子节点左侧偏移的基础值
    leftBaseIndent: {
      type: Number,
      default: 18,
    },
    // 点击事件 $emit 事件 类型
    // all: 既触发click 也触发 radio 事件
    // only-click: 只触发click 不触发 radio 事件
    // only-radio: 不触发click 只触发 radio 事件
    clickTriggerType: {
      type: String,
      default: 'all',
      validator(val) {
        return ['all', 'only-click', 'only-radio'].includes(val);
      },
    },
    isBorder: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      startIndex: 0,
      endIndex: 0,
      clickTriggerTypeBat: this.clickTriggerType,
    };
  },
  computed: {
    ghostStyle() {
      return {
        height: `${this.visiableData.length * this.itemHeight}px`,
      };
    },
    // allData 中 visiable 为 true 的数据，visiable 属性辅助设置展开收起的
    // 当父节点收起时，子节点的 visiable 为 false
    visiableData() {
      return this.allData.filter(item => item.visiable);
    },
    // 页面渲染的数据
    renderData() {
      // 渲染 visiable 为 true 并且在可视区的，这里要注意，必须要先 filter visiable 然后 slice，不能反过来
      return this.visiableData.slice(this.startIndex, this.endIndex);
    },
    nameStyle() {
      return (payload) => {
        if (payload.type === 'user') {
          return {
            maxWidth: 'calc(100% - 50px)',
          };
        }
        let otherOffset = 14 + 18 + 22 + 18 + 10;
        // loading 时需计算loading的宽度
        if (payload.loading) {
          otherOffset += 20;
        }
        if (payload.async) {
          otherOffset += 14;
        }
        return {
          maxWidth: `calc(100% - ${otherOffset}px)`,
        };
      };
    },
  },
  watch: {
    clickTriggerType(val) {
      if (!val) {
        this.clickTriggerTypeBat = 'all';
      }
      this.clickTriggerTypeBat = val;
    },
  },
  mounted() {
    const height = this.$el.clientHeight === 0
      ? parseInt(window.getComputedStyle(this.$el).height, 10)
      : this.$el.clientHeight;

    this.endIndex = Math.ceil(height / this.itemHeight);
  },
  methods: {
    /**
     * 获取节点的样式
     *
     * @param {Object} node 当前节点对象
     */
    getNodeStyle(node) {
      // node.async 表示含有子节点的节点，含有子节点的节点即节点左侧有箭头
      return {
        paddingLeft: `${(node.async ? node.level : node.level + 1) * this.leftBaseIndent}px`,
      };
    },

    /**
     * 滚动回调函数
     */
    rootScroll() {
      this.updateRenderData(this.$el.scrollTop);
    },

    /**
     * 更新可视区渲染的数据列表
     *
     * @param {Number} scrollTop 滚动条高度
     */
    updateRenderData(scrollTop = 0) {
      // 可视区显示的条数
      const count = Math.ceil(this.$el.clientHeight / this.itemHeight);
      // 滚动后可视区新的 startIndex
      const newStartIndex = Math.floor(scrollTop / this.itemHeight);
      // 滚动后可视区新的 endIndex
      const newEndIndex = newStartIndex + count;
      this.startIndex = newStartIndex;
      this.endIndex = newEndIndex;
      this.$refs.content.style.transform = `translate3d(0, ${newStartIndex * this.itemHeight}px, 0)`;
    },

    /**
     * 点击节点
     *
     * @param {Object} node 当前节点
     */
    nodeClick(node) {
      if (node.async && node.disabled) {
        this.expandNode(node);
        return;
      }
      if (!node.disabled) {
        if (['all', 'only-radio'].includes(this.clickTriggerTypeBat)) {
          node.is_selected = !node.is_selected;
          // type为user时需校验不同组织下的相同用户让其禁选
          if (node.type === 'user') {
            this.handleBanUser(node, node.is_selected);
          }
          this.$emit('on-select', node.is_selected, node);
        }
      }
      if (['all', 'only-click'].includes(this.clickTriggerTypeBat)) {
        this.$emit('on-click', node);
      }
    },

    handleBanUser(node, flag) {
      this.allData.forEach((item) => {
        if (item.username === node.username && item.id !== node.id) {
          item.disabled = flag;
          item.is_selected = flag;
        }
      });
    },

    /**
     * 节点展开/收起
     *
     * @param {Object} node 当前节点
     * @param {Boolean} isExpand 是否展开
     */
    expandNode(node, isExpand) {
      if (node.loading) {
        return;
      }
      if (isExpand) {
        node.expanded = isExpand;
      } else {
        node.expanded = !node.expanded;
      }

      if (node.children && node.children.length) {
        const children = this.allData.filter(item => item.parent === node.id);
        children.forEach((child) => {
          child.visiable = node.expanded;
          if (child.async && !node.expanded) {
            this.collapseNode(child);
          }
        });
      } else {
        if (node.async) {
          this.$emit('async-load-nodes', node);
        }
      }
      this.$emit('expand-node', node);
    },

    /**
     * 收起节点，收起节点的时候需要把节点里面的所有节点都收起，节点里面的父节点收起同时节点里面的父节点下的子节点都要隐藏
     *
     * @param {Object} node 当前要收起的节点，这个节点指的是含有子节点的节点
     */
    collapseNode(node) {
      node.expanded = false
      ;(node.children || []).forEach((child) => {
        child.visiable = false;
        if (child.async && !node.expanded) {
          this.collapseNode(child);
        }
      });
    },

    /**
     * 设置父级节点 radio 是否显示
     */
    showAllRadio(flag) {
      this.allData.forEach((item) => {
        // 父节点
        if (item.async) {
          item.showRadio = flag;
        }
      });
    },

    handleNodeClick(node) {
      if (node.disabled) {
        return;
      }
      node.is_selected = !node.is_selected;
      if (node.type === 'user') {
        this.handleBanUser(node, node.is_selected);
      }
      this.$emit('on-select', node.is_selected, node);
    },

    /**
     * radio 选择回调
     */
    nodeChange(newVal, oldVal, localVal, node) {
      this.$emit('on-select', newVal, node);
    },

    /**
     * 清除节点 is_selected 状态(不含禁选节点)
     */
    clearAllIsSelectedStatus() {
      this.allData.forEach((item) => {
        if (!item.disabled) {
          item.is_selected = false;
        }
      });
    },

    /**
     * 设置单个节点 is_selected 状态
     *
     * @param {String} nodeKey 当前节点唯一key值
     * @param {Boolean} isSelected 多选框是否选中
     */
    setSingleSelectedStatus(nodeKey, isSelected) {
      for (let i = 0; i < this.allData.length; i++) {
        const item = this.allData[i];
        if (nodeKey === item.id) {
          item.is_selected = isSelected;
          break;
        }
      }
    },
  },
};
</script>
<style lang="scss">
    .paasng-infinite-tree {
        height: 862px;
        font-size: 14px;
        overflow: auto;
        position: relative;
        will-change: transform;

        &::-webkit-scrollbar {
            width: 4px;
            background-color: lighten(transparent, 80%);
        }
        &::-webkit-scrollbar-thumb {
            height: 5px;
            border-radius: 2px;
            background-color: #e6e9ea;
        }

        .ghost-wrapper {
            position: absolute;
            left: 0;
            top: 0;
            right: 0;
            z-index: -1;
        }

        .render-wrapper {
            left: 0;
            right: 0;
            top: 0;
            position: absolute;
        }

        .node-item {
            position: relative;
            margin: 0;
            text-align: left;
            line-height: 32px;
            cursor: pointer;
            &.is-disabled {
                color: #c4c6cc;
                cursor: not-allowed;
            }
            &:hover {
                color: #3a84ff;
                background: #eef4ff;
            }
            &.is-disabled:hover {
                color: #c4c6cc;
                background: #eee;
            }
            &.is-selected {
                background: #eef4ff;
            }
        }

        .node-svg {
            width: 18px;
            border-radius: 50%;
            vertical-align: text-top;
        }

        .node-icon {
            position: relative;
            top: 3px;
            width: 18px;
        }

        .arrow-icon {
            position: relative;
            top: 1px;
            width: 14px;
            cursor: pointer;
        }

        .node-title {
            position: relative;
            display: inline-block;
            min-width: 14px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            vertical-align: top;
            user-select: none;
            &.is-disabled {
                color: #c4c6cc;
                cursor: not-allowed;
            }
        }

        .node-radio {
            margin-right: 5px;
            float: right;
            .node-checkbox {
                display: inline-block;
                position: relative;
                top: 3px;
                width: 16px;
                height: 16px;
                margin: 0 6px 0 0;
                border: 1px solid #979ba5;
                border-radius: 50%;
                &.is-checked {
                    border-color: #3a84ff;
                    background-color: #3a84ff;
                    background-clip: border-box;
                    &:after {
                        content: "";
                        position: absolute;
                        top: 2px;
                        left: 5px;
                        width: 4px;
                        height: 8px;
                        border: 2px solid #fff;
                        border-left: 0;
                        border-top: 0;
                        transform-origin: center;
                        transform: rotate(45deg) scaleY(1);
                    }
                    &.is-disabled {
                        background-color: #dcdee5;
                    }
                }
                &.is-disabled {
                    border-color: #dcdee5;
                    cursor: not-allowed;
                }
                &.is-indeterminate {
                    border-width: 7px 4px;
                    border-color: #3a84ff;
                    background-color: #fff;
                    background-clip: content-box;
                    &:after {
                        visibility: hidden;
                    }
                }
            }
        }

        .loading {
            display: inline-block;
            position: relative;
            top: -1px;
            width: 14px;
            height: 14px;
        }
    }
</style>
