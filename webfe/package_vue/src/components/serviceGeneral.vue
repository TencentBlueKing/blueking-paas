<template lang="html">
  <div class="right-main">
    <div
      v-if="showTitle"
      class="ps-top-bar"
    >
      <h2>{{ data.name }}</h2>
    </div>
    <div class="ps-container middle bnone">
      <div class="service-ex">
        <img
          :src="data.image"
          class="service-ex-img ex"
          alt=""
        >
        <h2 class="magicbox-h2">
          {{ data.apititle }}
        </h2>
        <p class="magicbox-p">
          {{ data.apiexplain }}
        </p>
        <a
          v-if="data.hasLink"
          :href="data.link"
          target="_blank"
          class="ps-btn ps-btn-l ps-btn-primary-ghost ps-btn-service-try-now"
          style="right: 0;"
        >
          {{ $t('立即体验') }} <i class="paasng-icon paasng-angle-double-right" />
        </a>
      </div>
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
            >{{ item.explain }}</a>
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
</template>

<script>
    export default {
        name: 'ServiceGeneral',
        props: {
            data: {
                type: Object
            },
            showTitle: {
                type: Boolean,
                default: true
            }
        },
        methods: {
            goPage (data) {
                window.open(data.link);
            }
        }
    };
</script>
<style lang="scss" scoped>
.action-links a {
    margin-left: 4px;
    margin-right: 8px;
}
.service-ex {
    padding-left: 84px;
    padding-bottom: 6px;
    height: 64px;
    box-sizing: content-box;
    .magicbox-h2 {
        top: 0;
        line-height: 24px;
        color: #313238;
    }
    .magicbox-p {
        color: #979BA5;
        line-height: 16px;
        margin-top: 4px;
    }
}
// 开发框架样式优化
.frame-wrapper {
    .service-p {
        color: #979BA5;
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
            color: #63656E;
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
