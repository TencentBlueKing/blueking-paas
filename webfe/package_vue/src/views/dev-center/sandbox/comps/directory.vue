<template>
  <div class="change-directory">
    <!-- 根目录 name 为空字符串，无需展示 -->
    <div
      v-if="node.name && (node.files?.length || node.dirs?.length)"
      class="path"
      :style="{ marginLeft: `${indentLevel}px` }"
    >
      <i
        v-if="node.dirs?.length || node.files?.length"
        class="paasng-icon paasng-angle-line-down"
        :class="{ expand: isExpand }"
        @click="toggleCollapse"
      ></i>
      {{ node.name }}
    </div>
    <ul v-if="isExpand">
      <li
        v-for="dir in filteredDirs || node.dirs"
        :key="dir.name"
        class="dir"
      >
        <Directory
          :node="dir"
          :path="fullPath"
          :indentLevel="indentLevel + 18"
        />
      </li>
      <li
        v-for="file in filteredFiles || node.files"
        :key="file.path"
        class="file-name"
        :style="{ paddingLeft: `${indentLevel + 18}px` }"
        :class="{ 'error-background': isInvalidFileName(file.path) }"
        v-bk-tooltips="{
          content: $t('修改的文件路径中不能包含中文，空格，以及除连接符（-），下划线（一），句号（.）外的特殊字符'),
          width: 220,
          disabled: !isInvalidFileName(file.path),
          allowHTML: true,
        }"
      >
        <!-- 根目录文件图标 -->
        <i
          class="paasng-icon paasng-process-file mr5"
          style="color: #c4c6cb"
        ></i>
        <span :class="file.action">{{ file.path }}</span>
      </li>
    </ul>
  </div>
</template>

<script>
import { bus } from '@/common/bus';

export default {
  name: 'Directory',
  props: {
    node: Object,
    path: String,
    indentLevel: {
      type: Number,
      default: 0,
    },
  },
  data() {
    return {
      isExpand: true,
    };
  },
  computed: {
    fullPath() {
      return this.path ? (this.path === '/' ? `/${this.node.name}` : `${this.path}/${this.node.name}`) : this.node.name;
    },
    filteredDirs() {
      return this.node.name === '' ? this.node.dirs : null;
    },
    filteredFiles() {
      return this.node.name === '' ? this.node.files : null;
    },
    isRootDirectory() {
      return this.node.name === '';
    },
  },
  methods: {
    toggleCollapse() {
      this.isExpand = !this.isExpand;
    },
    // 判断文件名是否符合要求
    isInvalidFileName(fileName) {
      if (!/^[a-zA-Z0-9._-]+$/.test(fileName)) {
        bus.$emit('name-validation-failed', fileName);
        return true;
      }
      return false;
    },
  },
};
</script>

<style lang="scss" scoped>
.change-directory {
  .added {
    color: #299e56;
  }
  .modified {
    color: #e38b02;
  }
  .deleted {
    position: relative;
    color: #c4c6cc;
    &:before {
      content: '';
      border-bottom: 1px solid #c4c6cc;
      width: 100%;
      position: absolute;
      right: 0;
      top: 50%;
    }
  }
  .dir,
  .file-name {
    line-height: 26px;
  }
  .file-name {
    position: relative;
    overflow: hidden;
    &.error-background {
      background-color: #f8d7da;
    }
  }
  .path {
    line-height: 26px;
    color: #4d4f56;
    i {
      margin-right: 2px;
      color: #979ba5;
      cursor: pointer;
      transition: 0.2s all;
      transform: rotate(-90deg);
      &.expand {
        transform: rotate(0deg);
      }
    }
  }
}
</style>
