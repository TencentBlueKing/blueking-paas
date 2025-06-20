<template>
  <div class="tree-text-wrapper">
    <div class="tip">{{ `<${$t('代码仓库根目录')}>` }}</div>
    <pre
      class="tree-text-display"
      ref="dynamicContent"
    ></pre>
  </div>
</template>

<script>
import Vue from 'vue';

export default {
  name: 'TreeTextDisplay',
  props: {
    treeData: {
      type: Object,
      default: () => {},
    },
    // 支持传递string类型
    rootPath: {
      type: String,
      default: '',
    },
    // 根路径下追加路径
    appendPath: {
      type: String,
      default: '',
    },
    showRoot: {
      type: Boolean,
      default: true,
    },
    type: {
      type: String,
      default: 'tree',
    },
    defaultFiles: {
      type: Array,
      default: () => [],
    },
    // 是否为 Dockerfile
    isDockerfile: {
      type: Boolean,
      default: true,
    },
    tipConfig: {
      type: Object,
      default: () => {},
    },
  },
  computed: {
    displayTreeData() {
      if (this.type === 'tree') {
        return this.treeData;
      }
      return this.formatDisplayTreeData(this.rootPath, this.appendPath);
    },
    defaultTree() {
      return {
        name: '/',
        children: [
          { name: 'app_desc.yaml' },
          ...(this.isDockerfile ? [{ name: 'Dockerfile', tag: true }] : []),
          ...this.defaultFiles,
        ],
      };
    },
    formattedTree() {
      if (this.showRoot) {
        // 显示根节点的情况
        return this.formatTree(this.displayTreeData);
      } else {
        // 不显示根节点，直接从子节点开始
        return this.formatChildren(this.displayTreeData.children);
      }
    },
  },
  watch: {
    formattedTree: {
      handler() {
        this.$nextTick(() => {
          this.$refs.dynamicContent.innerHTML = '';
          this.renderDynamicContent();
        });
      },
      immediate: true,
    },
  },
  methods: {
    // 显示根节点时的格式化方法
    formatTree(node, prefix = '', isLast = true) {
      let result = '';
      const connector = isLast ? '└─ ' : '├─ ';

      // 当前节点行（根节点特殊处理）
      result += node === this.treeData ? `${node.name}\n` : `${prefix}${connector}${node.name}\n`;

      // 子节点处理
      if (node.children && node.children.length > 0) {
        const childPrefix = prefix + (isLast ? '   ' : '│  ');

        node.children.forEach((child, index) => {
          const isChildLast = index === node.children.length - 1;
          result += this.formatTree(child, childPrefix, isChildLast);
        });
      }

      return result;
    },

    renderDynamicContent() {
      const Component = Vue.extend({
        data: () => ({
          config: this.tipConfig,
        }),
        template: `<div>${this.formattedTree}</div>`,
      });
      const instance = new Component();
      instance.$mount();
      this.$refs.dynamicContent.appendChild(instance.$el);
    },

    // 不显示根节点时的格式化方法
    formatChildren(children, prefix = '', isParentLast = true) {
      if (!children || children.length === 0) return '';

      let result = '';

      children.forEach((child, index) => {
        const isLast = index === children.length - 1;
        const connector = isLast ? '└─ ' : '├─ ';

        if (child.tag) {
          const icon = `<i class="paasng-icon paasng-info-line ml10" v-bk-tooltips="config" />`;
          result += `<span class="mark">${prefix}${connector}${child.name}${icon}</span>\n`;
        } else {
          result += `${prefix}${connector}${child.name}\n`;
        }

        // 递归处理子节点
        if (child.children && child.children.length > 0) {
          const childPrefix = prefix + (isLast ? '   ' : '│  ');
          result += this.formatChildren(child.children, childPrefix, isLast);
        }
      });

      return result;
    },

    // 检查路径是否以 '/' 结尾，如果是，去掉最后一个字符
    normalizePath(path) {
      return path?.endsWith('/') ? path.slice(0, -1) : path;
    },

    arrayToNestedObject(array) {
      // 基础递归退出条件：如果数组为空，则返回空数组
      if (array.length === 0) {
        return [];
      }
      // 取第一个元素作为当前节点
      const [first, ...rest] = array;
      // 递归调用将剩余的元素转换为子节点
      const children = this.arrayToNestedObject(rest);
      return [
        {
          name: first,
          children,
        },
      ];
    },

    formatTreeData(dir) {
      const normalizedPath = this.normalizePath(dir);
      const dirList = normalizedPath.split('/');
      const rootTree = this.arrayToNestedObject(dirList)[0];
      return rootTree;
    },

    // 新增函数：将 addPath 插入到根树结构中
    insertAddPathToRoot(rootTree, addPath) {
      // 找到根树的最后一个节点
      let currentNode = rootTree;
      while (currentNode.children && currentNode.children.length > 0) {
        currentNode = currentNode.children[0];
      }

      // 如果最后一个节点没有 children 数组，则创建
      if (!currentNode.children) {
        currentNode.children = [];
      }

      // 如果 addPath 不为空，则转换为树结构并添加
      if (addPath) {
        const addPathTree = this.formatTreeData(addPath);
        addPathTree.tag = true;
        currentNode.children.push(addPathTree);
      }

      // 添加默认文件节点
      currentNode.children.push(...this.defaultFiles);

      return rootTree;
    },

    // 将字符串相对路径转为，树形结构
    formatDisplayTreeData(rootPath, appendPath) {
      if (!rootPath && !appendPath) {
        return this.defaultTree;
      }
      if (rootPath) {
        const rootTree = this.formatTreeData(rootPath?.trim());
        const addPath = this.isDockerfile ? appendPath || 'Dockerfile' : appendPath !== undefined ? appendPath : '';
        // 追加路径
        const finalTree = this.insertAddPathToRoot(rootTree, addPath);
        return {
          name: '/',
          children: [{ ...finalTree }, { name: 'app_desc.yaml' }],
        };
      } else {
        // 根路径为空 appendPath 为当前路径的根路径
        const appendTree = this.formatTreeData(appendPath?.trim());
        appendTree.tag = true;
        return {
          name: '/',
          children: [{ ...appendTree }, ...this.defaultFiles, { name: 'app_desc.yaml' }],
        };
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.tree-text-wrapper {
  font-size: 12px;
  padding: 12px;
  background-color: #fff;
  border-radius: 2px;
  .tip {
    line-height: 1;
    margin-bottom: 8px;
  }
  .tree-text-display {
    font-family: monospace;
    white-space: pre;
    margin: 0;
    color: #4d4f56;
    line-height: 1.5;
  }
}
</style>
