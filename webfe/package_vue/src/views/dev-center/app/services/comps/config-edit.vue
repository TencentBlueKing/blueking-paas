<template lang="html">
  <section v-if="isShowPage">
    <h3 class="title">
      {{ $t('配置信息') }}
      <bk-button
        text
        size="small"
        theme="primary"
        style="font-weight: normal;"
        @click="handleOpenGuide"
      >
        {{ $t('使用指南') }}
      </bk-button>
    </h3>
    <section class="content">
      <section
        v-for="(item, index) in listDisplay"
        :key="index"
        class="item"
        :class="index !== listDisplay.length - 1 ? 'mb' : ''"
      >
        <div
          class="config-label"
          :title="$t(item.display_name)"
        >
          <span>{{ $t(item.display_name) }}</span>
        </div>
        <div class="bk-button-group">
          <bk-button
            v-for="subItem in item.children"
            :key="subItem"
            :class="item.active === subItem ? 'is-selected' : ''"
            :disabled="computedDisabled(item, index, subItem)"
            @click="handleSelected(item, index, subItem)"
          >
            {{ $t(subItem) }}
          </bk-button>
        </div>
        <p
          v-if="item.showError"
          class="error"
        >
          {{ $t('请选择') + $t(item.display_name) }}
        </p>
      </section>
      <p
        v-if="mode === ''"
        class="info"
      >
        {{ $t('模块部署前可在“增强服务/管理实例”页面修改配置信息，部署后则不能再修改配置信息') }}
      </p>
    </section>
    <section class="action">
      <template v-if="mode === ''">
        <bk-button
          :loading="enableLoadingUse"
          @click="handleEnabled"
        >
          {{ $t('启用服务') }}
        </bk-button>
      </template>
      <template v-else>
        <section>
          <bk-button
            :loading="saveLoadingUse"
            theme="primary"
            @click="handleSave"
          >
            {{ $t('保存') }}
          </bk-button>
          <bk-button
            style="margin-left: 4px;"
            @click="handleCancel"
          >
            {{ $t('取消') }}
          </bk-button>
        </section>
      </template>
    </section>

    <bk-sideslider
      :is-show.sync="isShow"
      :title="$t('使用指南')"
      :width="640"
      :quick-close="true"
    >
      <div slot="content">
        <div id="markdown">
          <div
            class="markdown-body"
            v-html="compiledMarkdown"
          />
        </div>
      </div>
    </bk-sideslider>
  </section>
</template>

<script>
import { marked } from 'marked';

export default {
  name: '',
  props: {
    list: {
      type: Array,
      default: () => [],
    },
    value: {
      type: Array,
      default: () => [],
    },
    enableLoading: {
      type: Boolean,
      default: false,
    },
    saveLoading: {
      type: Boolean,
      default: false,
    },
    // '' 表示正常启用态，'edit'表示编辑态
    mode: {
      type: String,
      default: '',
      validator(value) {
        if (['', 'edit'].indexOf(value) < 0) {
          console.error(`mode is not valid: '${value}'`);
          return false;
        }
        return true;
      },
    },
    guide: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      listDisplay: this.list,
      valuesMap: [],
      enableLoadingUse: this.enableLoading,
      saveLoadingUse: this.saveLoading,
      isShow: false,
    };
  },
  computed: {
    isShowPage() {
      return this.listDisplay.length > 0;
    },
    compiledMarkdown() {
      // eslint-disable-next-line vue/no-async-in-computed-properties
      this.$nextTick(() => {
        $('#markdown').find('a')
          .each(function () {
            $(this).attr('target', '_blank');
          });
      });
      console.log('marked', marked, this.guide);
      return marked(this.guide, { sanitize: true });
    },
  },
  watch: {
    list(value) {
      this.listDisplay = [...value];
      this.handleSetData();
    },
    enableLoading(value) {
      this.enableLoadingUse = !!value;
    },
    saveLoading(value) {
      this.saveLoadingUse = !!value;
    },
  },
  mounted() {
    this.handleSetData();
  },
  methods: {
    handleOpenGuide() {
      this.isShow = true;
    },
    handleEnabled() {
      let flag = false;
      const params = {};
      this.listDisplay.forEach((item) => {
        params[item.name] = item.active;
        if (item.active === '') {
          item.showError = true;
          flag = true;
        }
      });
      if (flag) {
        return;
      }
      this.$emit('on-change', 'enabled', params);
    },
    handleSave() {
      let flag = false;
      const params = {};
      this.listDisplay.forEach((item) => {
        params[item.name] = item.active;
        if (item.active === '') {
          item.showError = true;
          flag = true;
        }
      });
      if (flag) {
        return;
      }
      this.$emit('on-change', 'save', params);
    },
    handleCancel() {
      this.$emit('on-change', 'cancel', {});
    },
    handleSetData() {
      if (this.listDisplay.length === 1) {
        this.valuesMap = [];
        return;
      }
      const checkedArr = this.listDisplay.map(item => item.active).filter(Boolean);
      const tempArr = [];
      checkedArr.forEach((arrItem) => {
        tempArr.push(...this.value.filter(valItem => valItem.includes(arrItem)));
      });
      if (!tempArr.length) {
        const valueArr = [];
        this.listDisplay.forEach((item) => {
          valueArr.push(item.children);
        });
        this.valuesMap = [...valueArr];
        return;
      }
      let currentVal = [];
      const subLen = tempArr[0].length;
      const len = tempArr.length;
      for (let i = 0; i < len; i++) {
        for (let j = 0; j < subLen; j++) {
          if (currentVal[j]) {
            currentVal[j].push(tempArr[i][j]);
          } else {
            currentVal.push([tempArr[i][j]]);
          }
        }
      }
      // 此时有未选择的项
      if (checkedArr.length < this.listDisplay.length) {
        const valueIndexs = [];
        checkedArr.forEach((item) => {
          valueIndexs.push(this.listDisplay.findIndex(val => val.active === item));
        });
        valueIndexs.forEach((val) => {
          if (currentVal[val]) {
            currentVal[val].push(...this.listDisplay[val].children);
          }
        });
      }
      currentVal = currentVal.map(item => [...new Set(item)]);
      this.valuesMap = [...currentVal];
    },
    handleSelected(item, index, subItem) {
      item.showError = false;
      if (item.active === subItem) {
        if (item.active) {
          item.active = '';
        } else {
          item.active = subItem;
        }
      } else {
        item.active = subItem;
      }
      this.handleSetData();
    },
    computedDisabled(item, index, subItem) {
      if (!this.valuesMap.length) {
        return false;
      }
      return !this.valuesMap[index].includes(subItem);
    },
  },
};

</script>

<style lang="scss" scoped>
    .title {
        color: #1b1f23;
        font-weight: 600;
    }
    .content {
        padding: 25px 10px 10px 10px;
        border-bottom: 1px solid #dcdee5;
        .item {
            &.mb {
                margin-bottom: 20px;
            }
            .config-label {
                display: inline-block;
                padding-right: 10px;
                width: 85px;
                color: #313238;
                white-space: nowrap;
                text-overflow: ellipsis;
                overflow: hidden;
                vertical-align: middle;
            }
            .bk-button-group {
                button {
                    min-width: 100px;
                    &:hover {
                        color: #3a84ff;
                    }
                    &.is-disabled:hover {
                        color: #c4c6cc;
                    }
                }
            }
            .error {
                padding-left: 98px;
                margin-top: 5px;
                font-size: 12px;
                color: #ea3636;
            }
        }
        .info {
            margin-top: 10px;
            padding-left: 98px;
            font-size: 12px;
            color: #63656e;
        }
    }
    .action {
        margin-top: 10px;
    }
    .markdown-body {
        box-sizing: border-box;
        min-width: 200px;
        margin: 0 auto;
        padding: 5px 20px;

        h2 {
            color: var(--color-fg-default);
        }
    }
</style>
<style lang="scss">
    #markdown h2 {
        padding-bottom: 0.3em;
        font-size: 1.5em;
        border-bottom: 1px solid #eaecef;
        padding: 0;
        padding-bottom: 10px;
        margin-top: 24px;
        margin-bottom: 16px;
        font-weight: 600;
        line-height: 1.25;
    }

    #markdown h3 {
        color: var(--color-fg-default);
        line-height: 52px;
        font-size: 14px;
        position: relative;
    }

    #markdown h2 .octicon-link {
        color: #1b1f23;
        vertical-align: middle;
        visibility: hidden;
    }

    #markdown h2:hover .anchor {
        text-decoration: none;
    }

    #markdown h2:hover .anchor .octicon-link {
        visibility: visible;
    }

    #markdown code,
    #markdown kbd,
    #markdown pre {
        font-size: 1em;
    }

    #markdown code {
        font-size: 12px;
    }

    #markdown pre {
        margin-top: 0;
        margin-bottom: 16px;
        font-size: 12px;
    }

    #markdown pre {
        word-wrap: normal;
    }

    #markdown code {
        padding: 0.2em 0.4em;
        margin: 0;
        font-size: 85%;
        background-color: rgba(27, 31, 35, 0.05);
        border-radius: 3px;
        color: inherit;
    }

    #markdown pre>code {
        padding: 0;
        margin: 0;
        font-size: 100%;
        word-break: normal;
        white-space: pre;
        background: transparent;
        border: 0;
    }

    #markdown .highlight {
        margin-bottom: 16px;
    }

    #markdown .highlight pre {
        margin-bottom: 0;
        word-break: normal;
    }

    #markdown .highlight pre,
    #markdown pre {
        padding: 16px;
        overflow: auto;
        font-size: 85%;
        line-height: 1.45;
        background-color: var(--color-canvas-subtle);
        border-radius: 3px;
    }

    #markdown pre code {
        display: inline;
        max-width: auto;
        padding: 0;
        margin: 0;
        overflow: visible;
        line-height: inherit;
        word-wrap: normal;
        background-color: transparent;
        border: 0;
    }

    #markdown p {
        margin-top: 0;
        margin-bottom: 10px;
    }

    #markdown a {
        background-color: transparent;
    }

    #markdown a:active,
    #markdown a:hover {
        outline-width: 0;
    }

    #markdown a {
        color: #0366d6;
        text-decoration: none;
    }

    #markdown a:hover {
        text-decoration: underline;
    }

    #markdown a:not([href]) {
        color: inherit;
        text-decoration: none;
    }

    #markdown ul,
    #markdown ol {
        padding-left: 0;
        margin-top: 0;
        margin-bottom: 0;
        list-style: unset !important;
    }

    #markdown ol ol,
    #markdown ul ol {
        list-style-type: lower-roman;
    }

    #markdown ul ul ol,
    #markdown ul ol ol,
    #markdown ol ul ol,
    #markdown ol ol ol {
        list-style-type: lower-alpha;
    }

    #markdown ul,
    #markdown ol {
        padding-left: 2em;
    }

    #markdown ul ul,
    #markdown ul ol,
    #markdown ol ol,
    #markdown ol ul {
        margin-top: 0;
        margin-bottom: 0;
    }
</style>
