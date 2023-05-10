<template>
  <div class="app-top-bar">
    <section class="bar-container">
      <strong
        v-if="title && !hideTitle"
        class="title"
      >{{ title }}</strong>
      <template v-for="(path, index) of paths">
        <span
          v-if="index !== (paths.length - 1)"
          :key="index"
          class="expert"
        >
          <template v-if="path.routeName">
            <router-link :to="{ name: path.routeName, params: { id: appCode, moduleId: moduleId } }">{{ path.title }}</router-link>
          </template>
          <template v-else>
            <span>{{ path.title }}</span>
          </template>
        </span>
        <span
          v-else
          :key="index"
        >{{ path.title }}</span>
      </template>

      <template v-if="disabled">
        <span class="span" />
        <span class="module-title"> {{ $t('模块') }}： </span>
        <a
          v-bk-tooltips.right="$t('权限管理功能目前只支持主模块')"
          href="javascript: void(0);"
          class="module-name disbled"
        >
          {{ curModule.name }}
          <span v-if="curModule.is_default">{{ $t('(主)') }}</span>
          <i class="paasng-icon paasng-down-shape" />
        </a>
      </template>
      <template v-if="isDataReady && moduleList.length && !disabled">
        <span
          v-if="!hideTitle"
          class="span"
        />
        <span class="module-title"> {{ $t('模块') }}： </span>
        <dropdown
          ref="dropdown"
          style="display: inline-block; vertical-align: middle;"
          :options="{
            openOn: 'click',
            position: 'bottom left'
          }"
        >
          <div slot="trigger">
            <a
              href="javascript: void(0);"
              class="module-name"
            >
              {{ curModule.name }}
              <span v-if="curModule.is_default">{{ $t('(主)') }}</span>
              <i class="paasng-icon paasng-down-shape" />
            </a>
          </div>
          <div
            slot="content"
            style="width: 185px;"
          >
            <div class="bk-dropdown-content left-align">
              <ul class="bk-dropdown-list">
                <li
                  v-for="(module, moduleIndex) of moduleList"
                  :key="moduleIndex"
                  @click="handleModuleSelect(module)"
                >
                  <a
                    href="javascript: void(0);"
                    :class="{ active: curModule.name === module.name }"
                  >
                    {{ module.name }}
                    <span v-if="module.is_default">{{ $t('(主)') }}</span>
                  </a>
                </li>
              </ul>
              <div class="bk-select-extension">
                <span
                  v-if="canCreate"
                  style="cursor: pointer;"
                  @click="createAppModule"
                >
                  <i class="paasng-icon paasng-plus-circle" /> {{ $t('新增模块') }} </span>
                <span
                  v-else
                  v-bk-tooltips="{ content: isSmartApp ? `S-mart ${$t('应用目前不允许创建其它模块')}` : $t('当前应用不允许新增模块'), zIndex: 11000 }"
                  style="color: #c4c6cc; cursor: not-allowed;"
                >
                  <i class="paasng-icon paasng-plus-circle" /> {{ $t('新增模块') }}
                </span>
                <span
                  class="help-docu"
                  @click="toHelpDocu"
                > {{ $t('帮助') }} </span>
              </div>
            </div>
          </div>
        </dropdown>
      </template>

      <!-- 概览页时间选择 -->
      <template v-if="isOverview">
        <span class="span" />
        <dropdown
          ref="dropdown"
          style="display: inline-block; vertical-align: middle;"
          :options="{
            openOn: 'click',
            position: 'bottom left'
          }"
        >
          <div slot="trigger">
            <a
              href="javascript: void(0);"
              class="module-name time-text"
            >
              <i class="paasng-icon paasng-time icon-time-cls" />
              {{ curTime.text }}
              <i class="paasng-icon paasng-angle-line-down icon-down-cls" />
            </a>
          </div>
          <div
            slot="content"
            style="width: 185px;"
          >
            <div class="bk-dropdown-content left-align">
              <ul class="bk-dropdown-list">
                <li
                  v-for="(date, index) in shortcuts"
                  :key="index"
                  @click="handleChangeTime(date, date.id)"
                >
                  <a
                    href="javascript: void(0);"
                    :class="{ active: curTime.id === date.id }"
                  >
                    {{ date.text }}
                  </a>
                </li>
              </ul>
            </div>
          </div>
        </dropdown>
      </template>

      <div
        v-if="$slots['right']"
        class="right-slot"
      >
        <slot name="right" />
      </div>
    </section>
  </div>
</template>

<script>
    import dropdown from '@/components/ui/Dropdown';
    import { formatDate } from '@/common/tools';

    export default {
        components: {
            dropdown
        },
        props: {
            title: {
                type: String,
                default: ''
            },
            paths: {
                type: Array,
                default () {
                    return [];
                }
            },
            curModule: {
                type: Object,
                default () {
                    return {
                        name: ''
                    };
                }
            },
            canCreate: {
                type: Boolean,
                default: true
            },
            moduleList: {
                type: Array,
                default () {
                    return [];
                }
            },
            disabled: {
                type: Boolean,
                default: false
            },
            hideTitle: {
                type: Boolean,
                default: false
            },
            isOverview: {
                type: Boolean,
                default: false
            },
            shortcuts: {
                type: Array,
                default: () => []
            },
            curTime: {
                type: Object
            }
        },
        data () {
            return {};
        },
        computed: {
            isDataReady () {
                return this.title || this.paths.length;
            },
            appCode () {
                return this.$route.params.id;
            },
            moduleId () {
                return this.$route.params.moduleId;
            },
            routeName () {
                return this.$route.name;
            },
            curAppModule () {
                return this.$store.state.curAppModule;
            },
            isSmartApp () {
                return this.curAppModule.source_origin === this.GLOBAL.APP_TYPES.SMART_APP;
            }
        },
        methods: {
            handleModuleSelect (module) {
                this.$refs.dropdown.close();
                this.$emit('change-module', module);
                this.$store.commit('updateCurAppModule', module);

                const routeName = this.$route.name;
                let query = this.$route.query;
                if (routeName === 'appLog') {
                    query = {
                        tab: this.$route.query.tab || ''
                    };
                }

                this.$router.push({
                    name: routeName,
                    params: {
                        id: this.appCode,
                        moduleId: module.name
                    },
                    query: query
                });
            },
            setCurModule (payload) {
                this.$emit('change-module', payload);
                this.$store.commit('updateCurAppModule', payload);
            },
            createAppModule () {
                this.$router.push({
                    name: 'appCreateModule',
                    params: {
                        id: this.appCode
                    }
                });
            },
            toHelpDocu () {
                window.open(this.GLOBAL.DOC.MODULE_INTRO);
            },
            handleChangeTime (time, id) {
                const date = time.value();
                const startTime = formatDate(date[0], 'YYYY-MM-DD');
                const endTime = formatDate(date[1], 'YYYY-MM-DD');
                this.$emit('change-date', [startTime, endTime], id);
            }
        }
    };
</script>

<style type="text/css">
    .drop-element.drop-theme-ps-arrow.drop-abutted-left .drop-content:after {
        left: 8px !important;
        right: auto;
    }
</style>

<style lang="scss" scoped>
    @import '../assets/css/components/conf.scss';

    .app-top-bar {
        position: relative;
        font-size: 14px;
        color: #333333;
        background: #FFF;
        z-index: 1;
        height: 50px;
        .bar-container {
            max-width: 1180px;
            /*padding: 0 30px;*/
            margin: auto;
            /*box-shadow: 0px 1px 2px 0px rgba(0,0,0,0.1); */
            border-bottom: 1px solid #e6e9ea;
            height: 50px;
            line-height: 50px;
        }

        .title {
            font-weight: normal;
            color: #313238;
            font-weight: normal;
            display: inline-block;
            line-height: 49px;
            vertical-align: middle;
        }

        .module-title {
            display: inline-block;
            vertical-align: middle;
            font-size: 14px;
            color: #888;
        }

        .span {
            display: inline-block;
            height: 16px;
            width: 1px;
            background: #C4C6CC;
            vertical-align: middle;
            margin: 0 15px;
        }

        .module-name {
            color: #3A84FF;
            font-size: 14px;
            font-style: normal;
            line-height: 16px;
            &.disbled {
                vertical-align: middle;
                color: #c4c6cc;
                cursor: not-allowed;
                &:hover {
                    color: #c4c6cc;
                }
            }
            &:hover {
                color: #699df4;
            }
            &.time-text {
                font-size: 12px
            }
        }

        .icon-time-cls {
            font-size: 13px !important;
            transform: scale(1) !important;
        }
        .icon-down-cls {
            font-size: 13px !important;
        }

        .paasng-icon {
            font-size: 12px;
            transform: scale(0.8);
            display: inline-block;
        }

        .expert {
            height: 50px;
            line-height: 50px;
            display: inline-block;
            padding: 0 22px 0 0px;
            margin-right: 15px;
            background: url(/static/images/expert-icon.svg) 100% center no-repeat;
            background-size: auto 15px;
            > a,
            > span {
                color: #8d8d93;
            }
        }

        .right-slot {
            float: right;
        }
    }

    .bk-dropdown-content {
        height: auto;
        background: #fff;
        padding: 0;
        margin: 0;
        border-radius: 2px;
        box-sizing: border-box;
        transition: all ease 0.3s;
        box-shadow: 0 2px 6px rgba(51,60,72,0.1);
        text-align: left;

        &::-webkit-scrollbar {
            width: 4px;
            background-color: #e6e9ea;
        }
        &::-webkit-scrollbar-thumb {
            height: 5px;
            border-radius: 2px;
            background-color: #e6e9ea;
        }

        &.is-show {
            opacity: 1;
            display: inline-block;
            overflow: auto;
            height: auto;
        }
    }

    .bk-select-extension {
        display: flex;
        justify-content: space-between;
        font-size: 12px;
        padding: 0 16px;
        border-radius: 0 0 2px 2px;
        border-top: 1px solid #dcdee5;
        background: #fafbfd;
        line-height: 32px;

        span {
            display: inline-block;
            line-height: 33px;
        }

        .paasng-plus-circle {
            display: inline-block;
            vertical-align: -1px;
            font-size: 12px;
            margin-right: 4px;
        }

        .help-docu {
            color: #3a84ff;
            cursor: pointer;
            &:hover {
                color: #699df4;
            }
        }
    }

    .bk-dropdown-list {
        min-width: 120px;
        max-height: 166px;
        list-style: none;
        padding: 6px 0;
        margin: 0;
        font-size: 0;
        overflow: auto;

        &::-webkit-scrollbar {
            width: 4px;
            height: 4px;
        }

        &::-webkit-scrollbar-thumb {
            border-radius: 20px;
            background: #dde4eb;
            -webkit-box-shadow: inset 0 0 6px hsla(0,0%,80%,.3);
        }

        > li {
            width: 100%;
            margin: 0;
            display: inline-block;
            > a {
                display: block;
                line-height: 32px;
                padding: 0 15px;
                color: #63656e;
                font-size: 14px;
                text-decoration: none;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;

                &:hover {
                    background: #f4f6fa;
                    color: #3a84ff;
                }
                &.active {
                    background: #eaf3ff;
                    color: #3a84ff;
                }
            }
            .paasng-icon {
                margin-right: 5px;
            }
        }
    }

    @media screen and (max-width: 1920px) {
        .app-top-bar {
            .bar-container {
                max-width: 1180px;
            }
        }
    }

    @media screen and (max-width: 1680px) {
        .app-top-bar {
            .bar-container {
                max-width: 1080px;
            }
        }
    }

    @media screen and (max-width: 1440px) {
        .app-top-bar {
            .bar-container {
                max-width: 980px;
            }
        }
    }
</style>
