<template>
  <div class="env-var-info-container">
    <div class="title">{{ title }}</div>
    <div class="content">
      <div
        v-for="item in data"
        :key="item.label"
        class="item">
        <div class="key" v-bk-overflow-tips>
          {{ type === 'bk' ? `${item.label}=${item.value.value}` : item.label }}
          <i
            v-copy="type === 'bk' ? `${item.label}=${item.value.value}` : item.label"
            class="paasng-icon paasng-general-copy copy-icon"
          />
        </div>
        <div class="description" v-bk-overflow-tips>
          {{ type === 'bk' ? item.value.description : item.value }}
        </div>
      </div>
    </div>
    <div v-if="shadow" class="bottom-shadow"></div>
  </div>
</template>

<script>

export default {
  name: 'EnvVarInfo',
  props: {
    title: {
      type: String,
      default: '',
    },
    type: {
      type: String,
      default: '',
    },
    data: {
      type: Array,
      default: () => [],
    },
    shadow: {
      type: Boolean,
      default: false,
    },
  },
};
</script>

<style lang="scss" scoped>
.env-var-info-container {
  .mb16 {
    margin-bottom: 16px;
  }
  .title {
    height: 24px;
    line-height: 24px;
    padding-left: 16px;
    font-size: 12px;
    color: #313238;
    background: #F0F1F5;
  }
  .content {
    .item {
      display: flex;
      align-items: center;
      height: 42px;
      background: #FFFFFF;
      border-bottom: 1px solid #DCDEE5;
      font-size: 12px;
      color: #63656E;
      &:hover {
        background: #F5F7FA;
        .key .copy-icon {
          display: block;
        }
      }
      .key,
      .description {
        padding-left: 16px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .key {
        position: relative;
        padding-right: 32px;
        width: 338px;
        .copy-icon {
          position: absolute;
          right: 10px;
          top: 50%;
          transform: translateY(-50%);
          color: #3A84FF;
          cursor: pointer;
          display: none;
        }
      }
      .description {
        flex: 1;
      }
      &:last-of-type {
        border-bottom: none;
      }
    }
  }
  .bottom-shadow {
    height: 16px;
    background-image: linear-gradient(180deg, #00000000 0%, #00000014 100%);
  }
}
</style>
