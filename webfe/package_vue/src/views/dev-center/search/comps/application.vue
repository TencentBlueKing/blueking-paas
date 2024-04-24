<template>
  <div class="paas-app-wrapper apps-table-wrapper">
    <div
      v-for="(appItem, appIndex) in data"
      :key="appIndex"
      class="table-item"
      :class="{ 'mt': appIndex !== data.length - 1 }"
    >
      <div class="item-header">
        <div
          class="basic-info"
          @click="toPage(appItem)"
        >
          <img
            :src="appItem.logo_url ? appItem.logo_url : defaultImg"
            class="app-logo"
          >
          <span class="app-name">
            {{ appItem.name }}
          </span>
        </div>
        <div class="region-info">
          <span
            :class="['reg-tag', { 'inner': appItem.region_name === $t('内部版') }, { 'clouds': appItem.region_name === $t('混合云版') }]"
          >
            {{ appItem.region_name }}
          </span>
        </div>
        <div class="module-info">
          <template v-if="appItem.config_info.engine_enabled">
            <span
              class="module-name"
              :class="appItem.expanded ? 'expanded' : ''"
            >
              {{ $t('共') }}&nbsp; {{ appItem.modules.length }} &nbsp;{{ $t('个模块') }}
            </span>
          </template>
        </div>
        <div class="visit-operate">
          <div
            v-if="!Object.keys(appItem.deploy_info).length"
            class="app-operation-section"
          >
            <bk-button
              theme="primary"
              text
              style="margin-left: 80px;"
              @click="toCloudAPI(appItem)"
            >
              {{ $t('申请云 API 权限') }}
              <i class="paasng-icon paasng-keys" />
            </bk-button>
          </div>

          <div
            v-else
            class="app-operation-section"
          >
            <bk-button
              :disabled="!appItem.deploy_info.stag.deployed"
              text
              @click="visitLink(appItem, 'stag')"
            >
              <template v-if="!appItem.deploy_info.stag.deployed">
                <span v-bk-tooltips="$t('应用未部署，不能访问')">
                  {{ $t('预发布环境') }}
                  <i class="paasng-icon paasng-external-link" />
                </span>
              </template>
              <template v-else>
                <span>
                  {{ $t('预发布环境') }}
                  <i class="paasng-icon paasng-external-link" />
                </span>
              </template>
            </bk-button>
            <bk-button
              :disabled="!appItem.deploy_info.prod.deployed"
              text
              style="margin-left: 18px;"
              @click="visitLink(appItem, 'prod')"
            >
              <template v-if="!appItem.deploy_info.prod.deployed">
                <span v-bk-tooltips="$t('应用未部署，不能访问')">
                  {{ $t('生产环境') }}
                  <i class="paasng-icon paasng-external-link" />
                </span>
              </template>
              <template v-else>
                <span>
                  {{ $t('生产环境') }}
                  <i class="paasng-icon paasng-external-link" />
                </span>
              </template>
            </bk-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
export default {
  props: {
    data: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      defaultImg: '/static/images/default_logo.png',
    };
  },
  methods: {
    toPage(appItem) {
      if (appItem.config_info.engine_enabled) {
        this.toAppSummary(appItem);
        return;
      }
      this.toAppBaseInfo(appItem);
    },

    toAppSummary(appItem) {
      this.$router.push({
        name: 'appSummary',
        params: {
          id: appItem.code,
          moduleId: appItem.modules.find(item => item.is_default).name,
        },
      });
    },

    toAppBaseInfo(appItem) {
      this.$router.push({
        name: 'appBaseInfo',
        params: {
          id: appItem.code,
        },
      });
    },

    visitLink(data, env) {
      window.open(data.deploy_info[env].url);
    },

    toCloudAPI(item) {
      this.$router.push({
        name: 'appCloudAPI',
        params: {
          id: item.code,
        },
      });
    },
  },
};
</script>
<style lang="scss" scoped>
    .apps-table-wrapper {
        position: relative;
        margin-top: 20px;
        width: 100%;
        min-height: 100px;
        &.min-h {
            min-height: 255px;
        }
        &.reset-min-h {
            min-height: 400px;
        }
        .table-item {
            width: calc(100% - 2px);
            background: #fff;
            border-radius: 2px;
            border: 1px solid #dcdee5;
            &.mt {
                margin-bottom: 10px;
            }
            &:hover {
                box-shadow: 0px 3px 6px 0px rgba(99, 101, 110, .1);
            }
        }
        .ps-no-result {
            position: absolute;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
        }
        .item-header {
            width: 100%;
            height: 64px;
            line-height: 64px;
            .basic-info {
                display: inline-block;
                position: relative;
                width: 30%;
                height: 100%;
                cursor: pointer;
                &:hover {
                    .app-name {
                        color: #3a84ff;
                    }
                }
                .app-name {
                    display: inline-block;
                    position: relative;
                    top: -2px;
                    height: 100%;
                    padding-left: 6px;
                    max-width: 250px;
                    text-overflow: ellipsis;
                    overflow: hidden;
                    white-space: nowrap;
                    color: #63656e;
                    font-size: 14px;
                    font-weight: bold;
                    vertical-align: middle;
                    &:hover {
                        color: #3a84ff;
                    }
                }
                .app-logo {
                    position: relative;
                    top: 10px;
                    margin: 0 5px 0 12px;
                    width: 32px;
                    height: 32px;
                    border-radius: 4px;
                    &:hover {
                        color: #3a84ff;
                    }
                    &.reset-ml {
                        margin-left: 48px;
                    }
                }
            }
            .region-info {
                display: inline-block;
                width: 10%;
                .reg-tag {
                    display: inline-block;
                    padding: 2px 6px;
                    margin-left: 2px;
                    line-height: 16px;
                    background: #e7fcfa;
                    color: #2dcbae;
                    font-size: 12px;
                    border-radius: 2px;
                    &.inner {
                        background: #fdefd8;
                        color: #ff9c01;
                    }
                    &.clouds {
                        background: #ede8ff;
                        color: #7d01ff;
                    }
                }
            }
            .module-info {
                display: inline-block;
                width: 40%;
                .module-name {
                    display: inline-block;
                    margin: 0 4px;
                    width: 100px;
                    color: #63656e;
                    &.expanded {
                        color: #3a84ff;
                        .unfold-icon {
                            display: inline-block;
                        }
                    }
                    .unfold-icon {
                        display: none;
                        position: relative;
                        top: 1px;
                        font-size: 14px;
                        color: #3a8fff;
                    }
                }
            }
            .visit-operate {
                display: inline-block;
            }
        }
    }
</style>
