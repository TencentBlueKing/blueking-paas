<template>
  <div class="masked-text-viewer">
    <!-- JSON格式预览 -->
    <vue-json-pretty
      v-if="isPlaintext"
      class="paas-vue-json-pretty-cls"
      :data="jsonData"
      :deep="deep"
      :show-length="true"
      :highlight-mouseover-node="true"
    />
    <!-- 密文显示 -->
    <pre
      v-else
      class="masked-text-cls"
      >{{ maskedText }}</pre
    >
    <!-- 明文/密文切换按钮 -->
    <i
      v-bk-tooltips="isPlaintext ? $t('隐藏') : $t('显示')"
      :class="['paasng-icon toggle-icon', isPlaintext ? 'paasng-insights' : 'paasng-bukeyulan']"
      @click="toggleStatus"
    ></i>
    <!-- 复制按钮 -->
    <i
      v-bk-tooltips="$t('复制')"
      class="paasng-icon paasng-general-copy copy-icon"
      v-copy="copyText"
    ></i>
  </div>
</template>

<script>
import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';
import { convertToMaskedText } from '@/common/utils';

export default {
  name: 'MaskedTextViewer',
  components: {
    VueJsonPretty,
  },
  props: {
    // 要显示的数据（对象或字符串）
    data: {
      type: [Object, String],
      default: null,
    },
    // 默认是否显示明文
    defaultPlaintext: {
      type: Boolean,
      default: false,
    },
    // 外部控制的明文/密文状态（可选）
    plaintext: {
      type: Boolean,
      default: undefined,
    },
    // JSON 展开层级
    deep: {
      type: Number,
      default: 1,
    },
  },
  data() {
    return {
      // 内部状态管理
      internalPlaintext: this.defaultPlaintext,
    };
  },
  computed: {
    // 实际的明文/密文状态
    isPlaintext() {
      // 如果外部传入了 plaintext，优先使用外部状态
      return this.plaintext !== undefined ? this.plaintext : this.internalPlaintext;
    },
    // JSON 数据
    jsonData() {
      if (typeof this.data === 'string') {
        try {
          return JSON.parse(this.data);
        } catch (e) {
          return this.data;
        }
      }
      return this.data;
    },
    // 用于复制的文本
    copyText() {
      try {
        if (typeof this.data === 'object') {
          return JSON.stringify(this.data, null, 2);
        }
        return this.data || '';
      } catch (e) {
        return String(this.data || '');
      }
    },
    // 密文文本
    maskedText() {
      return convertToMaskedText(this.copyText);
    },
  },
  watch: {
    defaultPlaintext(val) {
      if (this.plaintext === undefined) {
        this.internalPlaintext = val;
      }
    },
  },
  methods: {
    // 切换明文/密文状态
    toggleStatus() {
      if (this.plaintext !== undefined) {
        // 如果外部控制状态，向外发送事件
        this.$emit('update:plaintext', !this.plaintext);
        this.$emit('toggle', !this.plaintext);
      } else {
        // 内部状态管理
        this.internalPlaintext = !this.internalPlaintext;
        this.$emit('toggle', this.internalPlaintext);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.masked-text-viewer {
  display: flex;
  position: relative;
  align-items: flex-start;
  min-height: 32px;

  .paas-vue-json-pretty-cls {
    flex: 1;
    min-width: 0;
    padding-right: 40px; // 图标预留空间
  }

  .masked-text-cls {
    flex: 1;
    min-width: 0;
    margin: 0;
    padding-right: 40px; // 图标预留空间
    font-family: monospace;
    font-size: 12px;
    line-height: 20px;
    color: #63656e;
    border-radius: 2px;
    overflow-x: auto;
    word-break: break-all;
  }

  i.paasng-icon {
    display: none;
    position: absolute;
    top: 50%;
    flex-shrink: 0;
    color: #3a84ff;
    cursor: pointer;
    font-size: 14px;
    transform: translateY(-50%);
    &:hover {
      color: #699df4;
    }
  }

  i.toggle-icon {
    right: 22px;
  }

  i.copy-icon {
    right: 0px;
  }
}
</style>
