<template lang="html">
  <div class="container biz-create-success">
    <div class="ps-top-bar">
      <div class="header-title">
        <i
          class="paasng-icon paasng-arrows-left icon-cls-return mr5"
          @click="goBack"
        />
        {{ $t('新建版本') }}
      </div>
    </div>

    <paas-content-loader
      :is-loading="isLoading"
      placeholder="entry-loading"
      class="app-container middle"
    >
      <div class="app-container middle">
        <!-- <bk-alert type="info" :show-icon="true">
                    <div slot="title">
                        {{ $t('测试版本仅用于测试，不能发布到线上') }}，
                        <a href="" target="_blank" class="detail-doc">{{ $t('详见文档') }}</a>
                    </div>
                </bk-alert> -->
        <div
          v-if="curVersion.current_release"
          class="summary-box status"
        >
          <div class="wrapper default-box">
            <div class="fl mr25">
              {{ $t('当前版本：') }} {{ curVersion.current_release.version || '--' }}
            </div>
            <div class="fl mr25">
              {{ $t('代码分支：') }} {{ curVersion.current_release.source_version_name || '--' }}
            </div>
            <div class="fl mr25">
              {{ $t('CommitID：') }} {{ curVersion.current_release.source_hash || '--' }}
            </div>
            <div class="fl">
              {{ $t('由') }} {{ curVersion.current_release.creator || '--' }} {{ $t(' 于 ') }} {{ curVersion.current_release.created }} {{ $t('发布') }}
            </div>
          </div>
        </div>

        <!-- 表单 -->
        <div class="form-box">
          <bk-form
            ref="versionForm"
            :label-width="120"
            :model="curVersion"
            :rules="rules"
          >
            <!-- 拿去分支数组中的字段 -->
            <bk-form-item
              :label="$t('代码仓库')"
              class="code-warehouse"
            >
              <bk-input
                v-model="curVersion.repository"
                :placeholder="$t('仓库地址')"
                readonly
              />
              <div class="icon-wrapper">
                <a
                  :href="curVersion.repository"
                  target="_blank"
                  style="color: #979BA5;"
                ><i class="paasng-icon paasng-jump-link icon-cls-link mr5" /></a>
                <i
                  class="paasng-icon paasng-general-copy icon-cls-copy"
                  @click="handleCopy(curVersion.repository)"
                />
              </div>
            </bk-form-item>
            <bk-form-item
              :label="$t('代码分支')"
              :required="true"
              :property="'source_versions'"
            >
              <bk-select
                v-model="curVersion.source_versions"
                :disabled="false"
                ext-cls="select-custom"
                searchable
              >
                <bk-option
                  v-for="option in sourceVersions"
                  :id="option.name"
                  :key="option.name"
                  :name="option.name"
                />
              </bk-select>
              <div class="ribbon">
                <div
                  class="mr10"
                  @click="handleShowCommits"
                >
                  <i class="paasng-icon paasng-diff-line" />
                  <span>{{ $t('代码差异') }}</span>
                </div>
                <!-- <div @click.stop="handleTestRecord">
                                    <i class="paasng-icon paasng-debug-fill"></i>
                                    <span>{{ $t('测试记录') }}</span>
                                </div> -->
              </div>
            </bk-form-item>
            <!-- <bk-form-item label="">
                            <bk-alert type="error" :show-icon="true">
                                <div slot="title">
                                    {{ $t('代码分支不符合规范') }}，
                                    <a href="" target="_blank" class="detail-doc">{{ $t('详见指引') }}</a>
                                </div>
                            </bk-alert>
                        </bk-form-item> -->
            <!-- automatic 自动生成 -->
            <bk-form-item
              v-if="curVersion.version_no === 'automatic'"
              :label="$t('版本类型')"
              :required="true"
              :property="'version'"
            >
              <bk-radio-group v-model="curVersion.version">
                <bk-radio :value="curVersion.semver_choices.major">
                  {{ $t('重大版本') }}
                </bk-radio>
                <bk-radio :value="curVersion.semver_choices.minor">
                  {{ $t('次版本') }}
                </bk-radio>
                <bk-radio :value="curVersion.semver_choices.patch">
                  {{ $t('修正版本') }}
                </bk-radio>
              </bk-radio-group>
            </bk-form-item>
            <bk-form-item
              :label="$t('版本号')"
              :required="true"
              :property="'version'"
            >
              <bk-input
                v-model="curVersion.version"
                :placeholder="$t('版本号')"
                :disabled="curVersion.version_no !== 'self-fill'"
              />
            </bk-form-item>
            <bk-form-item
              :label="$t('版本日志')"
              :required="true"
              :property="'comment'"
            >
              <!-- v-model="releaseParams.comment" -->
              <bk-input
                v-model="curVersion.comment"
                :rows="5"
                type="textarea"
              />
            </bk-form-item>
            <!-- extra_fields 后续添加功能 -->
            <!-- <div class="line"></div> -->
            <!-- 测试版 -->
            <!-- <bk-form-item :label="$t('自定义前端')" :required="true" class="cls-test-env">
                            <bk-radio-group>
                                <bk-radio :value="'value1'">{{ $t('是') }}</bk-radio>
                                <bk-radio :value="'value2'">{{ $t('否') }}</bk-radio>
                            </bk-radio-group>
                        </bk-form-item>
                        <bk-form-item :label="$t('适用Job类型')" :required="true" class="cls-test-env">
                            <bk-radio-group>
                                <bk-radio :value="'value1'">{{ $t('编译环境') }}</bk-radio>
                                <bk-radio :value="'value2'">{{ $t('无编译环境') }}</bk-radio>
                            </bk-radio-group>
                            <div class="environment-wrapper">
                                <bk-checkbox-group>
                                    <bk-checkbox :value="'value1'">Linux</bk-checkbox>
                                    <bk-checkbox :value="'value2'">Windows</bk-checkbox>
                                    <bk-checkbox :value="'value3'">macOS</bk-checkbox>
                                </bk-checkbox-group>
                            </div>
                        </bk-form-item> -->
            <bk-form-item label="">
              <bk-button
                theme="primary"
                :loading="isSubmitLoading"
                @click="submitVersionForm"
              >
                {{ $t('提交并发布') }}
              </bk-button>
            </bk-form-item>
          </bk-form>
        </div>
      </div>
    </paas-content-loader>

    <!-- 详情 -->
    <bk-sideslider
      :is-show.sync="versionDetail.isShow"
      :quick-close="true"
      :width="960"
    >
      <div slot="header">
        {{ $t('测试详情') }}
      </div>
      <div
        slot="content"
        class="p20"
      >
        <!-- 数据遍历，前端书写 -->
        <bk-table
          v-bkloading="{ isLoading: isLogLoading }"
          class="ps-version-list"
          :data="versionList"
          :outer-border="false"
          :size="'small'"
          :pagination="pagination"
        >
          <bk-table-column
            :label="$t('Commit ID')"
            prop="name"
            :show-overflow-tooltip="true"
          />
          <bk-table-column
            :label="$t('状态')"
            prop="environment_name"
          >
            <template slot-scope="props">
              <span v-if="props.row.environment_name === 'stag'"> {{ $t('已测试') }} </span>
              <span v-else> {{ $t('未测试') }} </span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('提交者')"
            prop="operator"
          />
          <bk-table-column :label="$t('提交时间')">
            <template slot-scope="{ row }">
              <span v-bk-tooltips="row.message">{{ row.message || '--' }}</span>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('log')">
            <template slot-scope="{ row }">
              <span v-bk-tooltips="row.message">{{ row.message || '--' }}</span>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
    </bk-sideslider>
  </div>
</template>

<script>
    import appBaseMixin from '@/mixins/app-base-mixin';

    export default {
        mixins: [appBaseMixin],
        data () {
            return {
                isLoading: false,
                keyword: '',
                versionDetail: {
                    isShow: false
                },
                versionList: [],
                pagination: {
                    current: 1,
                    count: 0,
                    limit: 10
                },
                isAppOffline: false,
                curVersion: {
                    // 仓库地址
                    repository: '',
                    // 代码分支
                    source_versions: '',
                    // 版本类型
                    semver_choices: {},
                    // 版本号
                    version: '',
                    // 版本日志
                    comment: ''
                },
                sourceVersions: [],
                isLogLoading: false,
                isSubmitLoading: false,
                rules: {
                    source_versions: [
                        {
                            required: true,
                            message: this.$t('该字段是必填项'),
                            trigger: 'blur'
                        }
                    ],
                    comment: [
                        {
                            required: true,
                            message: this.$t('该字段是必填项'),
                            trigger: 'blur'
                        }
                    ]
                }
            };
        },
        computed: {
            pdId () {
                return this.$route.params.pluginTypeId;
            },
            pluginId () {
                return this.$route.params.id;
            }
        },
        watch: {
            'curVersion.source_versions' (value) {
                if (this.curVersion.version_no === 'revision' || this.curVersion.version_no === 'commit-hash') {
                    const versionData = this.sourceVersions.filter(item => item.name === this.curVersion.source_versions);
                    if (this.curVersion.version_no === 'revision') {
                        this.curVersion.version = versionData[0].name;
                    } else {
                        this.curVersion.version = versionData[0].revision;
                    }
                }
            }
        },
        created () {
            this.init();
        },
        methods: {
            init () {
                this.getNewVersionFormat();
            },

            handleTestRecord () {
                this.versionDetail.isShow = true;
            },

            // 获取新建版本表单格式
            async getNewVersionFormat () {
                this.isLoading = true;
                const data = {
                    pdId: this.pdId,
                    pluginId: this.pluginId
                };
                try {
                    const res = await this.$store.dispatch('plugin/getNewVersionFormat', data);
                    this.curVersion.doc = res.doc;
                    this.curVersion.current_release = res.current_release;
                    // 代码仓库
                    this.curVersion.repository = res.source_versions[0].url;
                    this.sourceVersions = res.source_versions;
                    // version_no 版本号生成规则, 自动生成(automatic),与代码版本一致(revision),与提交哈希一致(commit-hash),用户自助填写(self-fill)
                    this.curVersion.semver_choices = res.semver_choices;
                    if (res.version_no === 'revision') {
                        // 与代码版本一致(revision)
                        this.curVersion.version = res.source_versions[0].name;
                    } else if (res.version_no === 'commit-hash') {
                        // 提交哈希一致(commit-hash)
                        this.curVersion.version = res.source_versions[0].revision;
                    } else if (res.version_no === 'automatic') {
                        // 自动生成(automatic)
                        this.curVersion.version = this.curVersion.semver_choices.major;
                    } else if (res.version_no === 'self-fill') {
                        // 用户自助填写(self-fill)
                        this.curVersion.version = '';
                    }
                    this.curVersion.version_no = res.version_no;

                    console.log('this.curVersion', this.curVersion);
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    setTimeout(() => {
                        this.isLoading = false;
                    }, 200);
                }
            },

            submitVersionForm () {
                this.$refs.versionForm.validate().then(validator => {
                    this.isSubmitLoading = true;
                    this.createVersion();
                }).catch(() => {
                    this.isSubmitLoading = false;
                });
            },

            // 新建版本并发布
            async createVersion () {
                // 当前选中分支的数据
                const versionData = this.sourceVersions.filter(item => item.name === this.curVersion.source_versions);

                const data = {
                    source_version_type: versionData[0].type,
                    source_version_name: versionData[0].name,
                    version: this.curVersion.version,
                    comment: this.curVersion.comment
                    // 'extra_fields": {
                    //     "additionalProp1": "string"
                    // },
                    // 'semver_type': 'string'
                };

                // 仅 versionNo=automatic 需要传递
                if (this.curVersion.version_no === 'automatic') {
                    for (const key in this.curVersion.semver_choices) {
                        if (this.curVersion.semver_choices[key] === this.curVersion.version) {
                            data.semver_type = key;
                        }
                    }
                }

                const params = {
                    pdId: this.pdId,
                    pluginId: this.pluginId,
                    data
                };
                try {
                    const res = await this.$store.dispatch('plugin/createVersion', params);
                    this.$bkMessage({
                        theme: 'success',
                        message: this.$t('新建成功!')
                    });
                    // 跳转至发布详情
                    this.goRelease(res);
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    this.isSubmitLoading = false;
                }
            },

            handleCopy (url) {
                const el = document.createElement('textarea');
                el.value = url;
                el.setAttribute('readonly', '');
                el.style.position = 'absolute';
                el.style.left = '-9999px';
                document.body.appendChild(el);
                const selected = document.getSelection().rangeCount > 0 ? document.getSelection().getRangeAt(0) : false;
                el.select();
                document.execCommand('copy');
                document.body.removeChild(el);
                if (selected) {
                    document.getSelection().removeAllRanges();
                    document.getSelection().addRange(selected);
                }
                this.$bkMessage({ theme: 'success', message: this.$t('复制成功'), delay: 2000, dismissable: false });
            },

            goBack () {
                this.$router.push({
                    name: 'pluginVersionManager'
                });
            },

            goRelease (data) {
                // 重新获取列表，赛选出当
                const stagesData = data.all_stages.map((e, i) => {
                    e.icon = i + 1;
                    e.title = e.name;
                    return e;
                });
                this.$router.push({
                    name: 'pluginVersionRelease',
                    query: {
                        stage_id: data.current_stage.stage_id,
                        release_id: data.id,
                        stagesData: JSON.stringify(stagesData)
                    }
                });
            },

            async handleShowCommits () {
                if (!this.curVersion.source_versions) {
                    this.$paasMessage({
                        theme: 'error',
                        message: this.$t('请选择代码分支')
                    });
                    return false;
                }

                const fromRevision = this.curVersion.current_release.source_hash;
                const curCodeItem = this.sourceVersions.filter(item => item.name === this.curVersion.source_versions);
                const toRevision = `${curCodeItem[0].type}:${curCodeItem[0].name}`;
                const win = window.open();
                const res = await this.$store.dispatch('plugin/getGitCompareUrl', {
                    pdId: this.pdId,
                    pluginId: this.pluginId,
                    fromRevision,
                    toRevision
                });
                win.location.href = res.result;
            }
        }
    };
</script>

<style lang="scss" scoped>

    .ps-main {
        margin-top: 15px;
    }
    .header-title {
        display: flex;
        align-items: center;
        .app-code {
            color: #979BA5;
        }
        .arrows {
            margin: 0 9px;
            transform: rotate(-90deg);
            font-size: 12px;
            font-weight: 600;
            color: #979ba5;
        }
    }

    .detail-wrapper {
        .item-info {
            display: flex;
            height: 40px;
            line-height: 40px;
            border-top: 1px solid #dfe0e5;

            &:last-child {
                border-bottom: 1px solid #dfe0e5;
            }

            .describe,
            .content {
                display: flex;
                align-items: center;
            }

            .describe {
                flex-direction: row-reverse;
                width: 100px;
                text-align: right;
                padding-right: 16px;
                font-size: 12px;
                color: #979BA5;
                background: #FAFBFD;
            }
            .content {
                flex: 1;
                font-size: 12px;
                color: #63656E;
                padding: 10px 0 10px 16px;
                border-left: 1px solid #F0F1F5;
            }
        }

        .h-auto {
            height: auto;
            line-height: 22px;
        }
    }

    .detail-doc {
        color: #3A84FF;
        cursor: pointer;
    }

    .form-box {
        margin-top: 22px;
        width: 650px;

        & /deep/ .bk-form-control .group-box {
            border-left: none;
            border-color: #3A84FF !important;
        }

        .icon-wrapper {
            display: flex;
            align-items: center;
            position: absolute;
            right: 0px;
            top: 0px;
            height: 100%;
            font-size: 16px;
            padding-right: 6px;
            color: #979BA5;

            .icon-cls-link:hover,
            .icon-cls-copy:hover {
                cursor: pointer;
                color: #3A84FF;
            }
        }

        .ribbon {
            display: flex;
            position: absolute;
            right: -98px;
            top: 0px;
            color: #3A84FF;

            div {
                cursor: pointer;
            }
        }

        .environment-wrapper {
            margin-top: 5px;
            padding: 5px 0;
            background: #F5F7FA;
            border-radius: 2px;
            padding-left: 28px;
        }
    }

    .icon-cls-return {
        font-weight: 700;
        font-size: 16px;
        cursor: pointer;
        color: #3A84FF;
    }

    .summary-box {
        padding: 10px 0 20px;
        padding-bottom: 0;
        background: #FFF;
        font-size: 12px;

        // & + .summary-box {
        //     padding-top: 0;
        // }

        .wrapper {
            // padding: 20px;
            // background: #F5F6FA;
            // border-radius: 2px;
            // padding: 11px 12px 11px 20px;
            // line-height: 16px;
            height: 64px;
            background: #F5F6FA;
            border-radius: 2px;
            line-height: 64px;
            padding: 0 20px;

            &::after {
                display: block;
                clear: both;
                content: "";
                font-size: 0;
                height: 0;
                visibility: hidden;
            }

            &.default-box {
                padding: 11px 12px 11px 20px;
                height: auto;
                line-height: 16px;
                color: #979BA5;
                .span {
                    height: 16px;
                }
            }

            &.not-deploy {
                height: 42px;
                line-height: 42px;
            }

            &.primary {
                background: #E1ECFF;
                color: #979BA5;
            }

            &.warning {
                background: #FFF4E2;
                border-color: #FFDFAC;

                .paasng-icon {
                    color: #fe9f07;
                }
            }

            &.danger {
                background: #FFECEC;
                color: #979BA5;

                .paasng-icon {
                    color: #eb3635;
                    position: relative;
                    top: 4px;
                    font-size: 32px;
                }
            }

            &.success {
                background: #E7FCFA;
                color: #979BA5;

                .paasng-icon {
                    position: relative;
                    top: 4px;
                    color: #3fc06d;
                    font-size: 32px;
                }
            }
        }
    }

    .line {
        position: relative;
        margin: 26px 0;
        max-width: 1080px;
        min-width: 1080px;
        border-top: 1px solid #F0F1F5;
    }

</style>

<style lang="css">
    .form-box .code-warehouse .bk-form-input {
        padding-right: 50px !important;
    }
    .form-box .cls-test-env .bk-form-content .bk-form-control>.bk-form-radio:first-child {
        width: 82px;
    }
</style>
