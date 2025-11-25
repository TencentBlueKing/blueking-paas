<template>
  <div class="example-directory-wrapper">
    <p class="mb-8">{{ $t('示例目录') }}</p>
    <div>
      <div class="tree-text-wrapper">
        <div class="single-module flex-1 flex-column">
          <span class="f12 mb-8">{{ $t('单模块应用') }}：</span>
          <pre
            class="directory-tree"
            ref="singleModuleTree"
          >
                  <i 
                    class="paasng-icon paasng-general-copy"
                    @click="copyDirectoryTree('singleModuleTree')"
                  ></i>
├── app_desc.yml
├── urls.py
└── requirements.txt
                </pre>
        </div>
        <div class="multi-module flex-1 flex-column">
          <span class="f12 mb-8">{{ $t('多模块应用') }}：</span>
          <pre
            class="directory-tree"
            ref="multiModuleTree"
          >
                  <i 
                    class="paasng-icon paasng-general-copy"
                    @click="copyDirectoryTree('multiModuleTree')"
                  ></i>
├── app_desc.yml
└── src
    ├── backend
    │   └── requirements.txt
    └── frontend
        └── package.json
                </pre>
        </div>
      </div>
      <p class="f12 mt-12 mb-8">{{ $t('可在根目录下执行如下命令生成源码包') }}：</p>
      <pre>tar czvf xxx.tgz .</pre>
    </div>
  </div>
</template>

<script>
import { copy } from '@/common/tools';

export default {
  name: 'ExampleDirectory',
  methods: {
    // 复制目录树内容
    copyDirectoryTree(refName) {
      const treeElement = this.$refs[refName];
      if (treeElement) {
        // 获取文本内容，去掉复制图标等非文本元素
        const textContent = treeElement.textContent || treeElement.innerText || '';
        const cleanContent = textContent.trim();
        copy(cleanContent, this);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.example-directory-wrapper {
  margin: 22px 0 0 100px;
  padding: 12px 16px;
  border-radius: 2px;
  background: #f0f1f5;
  .tree-text-wrapper {
    display: flex;
    gap: 16px;
  }
  pre {
    font-size: 12px;
    white-space: pre;
    color: #4d4f56;
    line-height: 1.5;
    font-family: monospace, 'Monaco';
  }
  .directory-tree {
    position: relative;
    height: 100%;
    margin: 0;
    padding: 8px 12px;
    background-color: #fff;
    i.paasng-general-copy {
      position: absolute;
      top: 8px;
      right: 8px;
      font-size: 14px;
      color: #979ba5;
      cursor: pointer;
      &:hover {
        color: #3a84ff;
      }
    }
  }
}
</style>
