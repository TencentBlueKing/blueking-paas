<template lang="html">
  <div class="right-main">
    <div
      v-if="showTitle"
      class="ps-top-bar"
    >
      <h2>{{ data.name }}</h2>
    </div>
    <div class="ps-container middle bnone">
      <div class="service-top card-style">
        <div class="flex-row">
          <img
            :src="data.image"
            class="service-img"
            alt=""
          />
          <div class="info">
            <p class="sub-title">
              {{ data.apititle }}
            </p>
            <p class="tips">
              {{ data.apiexplain }}
            </p>
          </div>
        </div>
        <bk-button
          v-if="data.hasLink"
          theme="primary"
          :outline="true"
          ext-cls="try-now-cls"
          @click="goPage(data)"
        >
          {{ $t('立即体验') }}
          <i class="paasng-icon paasng-angle-double-right" />
        </bk-button>
      </div>
      <div class="service-content card-style">
        <div
          v-for="(item, index) in data.apiList"
          :key="index"
          class="service-p"
        >
          <h3>{{ item.title }}</h3>
          <div>
            <template v-if="item.hasOwnProperty('explainIsLink') && item.explainIsLink">
              <a
                :href="item.url"
                target="_blank"
                class="blue"
              >
                {{ item.explain }}
              </a>
            </template>
            <template v-else>
              {{ item.explain }}
              <a
                v-if="item.hasOwnProperty('url') && item.url !== ''"
                :href="item.url"
                target="_blank"
                class="blue code-a"
              >
                {{ item.isDoc ? $t('查看文档') : $t('立即体验') }}
                <i class="paasng-icon paasng-angle-double-right" />
              </a>
            </template>
            <span
              v-if="item.action_links"
              class="action-links"
            >
              <a
                v-for="(link, linkIndex) in item.action_links"
                :key="linkIndex"
                :href="link.target_url"
                target="_blank"
              >
                {{ link.text }}
              </a>
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ServiceGeneral',
  props: {
    data: {
      type: Object,
    },
    showTitle: {
      type: Boolean,
      default: true,
    },
  },
  methods: {
    goPage(data) {
      window.open(data.link);
    },
  },
};
</script>
<style lang="scss" scoped>
.service-top {
  padding: 14px 16px;
  min-height: 64px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  .service-img {
    flex-shrink: 0;
    width: 64px;
    height: 64px;
    border-radius: 6px;
    border: solid 1px #eaeeee;
    overflow: hidden;
  }
  .try-now-cls {
    flex-shrink: 0;
  }
  .info {
    margin-left: 12px;
    .sub-title {
      line-height: 24px;
      font-size: 18px;
      color: #313238;
    }
    .tips {
      color: #979ba5;
      line-height: 16px;
      margin-top: 5px;
      font-size: 12px;
    }
  }
}
.service-content {
  margin-top: 16px;
  padding: 16px;
}
.action-links a {
  margin-left: 4px;
  margin-right: 8px;
}
// 开发框架样式优化
.frame-wrapper {
  .service-p {
    color: #979ba5;
    font-size: 12px;
    line-height: 16px;
    &:last-child {
      .action-links {
        padding-left: 0;
        a {
          margin: 0 30px 0 0;
        }
      }
    }
    h3 {
      margin: 25px 0 5px 0;
      line-height: 19px;
      color: #63656e;
      font-weight: bold;
    }
    .action-links {
      padding-left: 26px;
      a {
        margin: 0 14px 0 0;
        &:last-child {
          margin: 0;
        }
      }
    }
  }
}
</style>
