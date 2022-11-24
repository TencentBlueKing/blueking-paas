<template>
  <div class="establish">
    <form
      id="form-create-app"
      data-test-id="createDefault_form_appInfo"
      @submit.stop.prevent="submitCreateForm"
    >
      <div class="ps-tip-block default-info mt15">
        <i
          style="color: #3A84FF;"
          class="paasng-icon paasng-info-circle"
        />
        {{ $t('基于容器镜像来部署应用，支持用 YAML 格式文件描述应用模型，可使用进程管理、云 API 权限及各类增强服务等平台基础能力。') }}
      </div>

      <!-- 基本信息 -->
      <div
        class="create-item"
        data-test-id="createDefault_item_baseInfo"
      >
        <div class="item-title">
          {{ $t('基本信息') }}
        </div>
        <div
          class="form-group"
          style="margin-top: 10px;"
        >
          <label class="form-label"> {{ $t('应用 ID') }} </label>
          <div class="form-group-flex">
            <p>
              <input
                type="text"
                autocomplete="off"
                name="code"
                data-parsley-required="true"
                :data-parsley-required-message="$t('该字段是必填项')"
                data-parsley-maxlength="16"
                data-parsley-pattern="[a-z][a-z0-9-]+"
                :data-parsley-pattern-message="$t('格式不正确，只能包含：小写字母、数字、连字符(-)，首字母必须是字母，长度小于 16 个字符')"
                data-parsley-trigger="input blur"
                class="ps-form-control"
                :placeholder="$t('由小写字母、数字、连字符(-)组成，首字母必须是字母，长度小于 16 个字符')"
              >
            </p>
            <p class="whole-item-tips">
              {{ $t('应用的唯一标识，创建后不可修改') }}
            </p>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label"> {{ $t('应用名称') }} </label>
          <p class="form-group-flex">
            <input
              type="text"
              autocomplete="off"
              name="name"
              data-parsley-required="true"
              :data-parsley-required-message="$t('该字段是必填项')"
              data-parsley-maxlength="20"
              data-parsley-pattern="[a-zA-Z\d\u4e00-\u9fa5]+"
              :data-parsley-pattern-message="$t('格式不正确，只能包含：汉字、英文字母、数字，长度小于 20 个字符')"
              data-parsley-trigger="input blur"
              class="ps-form-control"
              :placeholder="$t('由汉字、英文字母、数字组成，长度小于 20 个字符')"
            >
          </p>
        </div>
        <div
          v-if="platformFeature.REGION_DISPLAY"
          class="form-group"
          style="margin-top: 7px;"
        >
          <label class="form-label"> {{ $t('应用版本') }} </label>
          <div
            v-for="region in regionChoices"
            :key="region.key"
            class="form-group-flex-radio"
          >
            <div class="form-group-radio">
              <bk-radio-group
                v-model="regionChoose"
                style="width: 72px;"
              >
                <bk-radio
                  :key="region.key"
                  :value="region.key"
                >
                  {{ region.value }}
                </bk-radio>
              </bk-radio-group>
              <p class="whole-item-tips">
                {{ region.description }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div
        class="create-item"
        data-test-id="createDefault_item_baseInfo"
      >
        <div class="item-title">
          {{ $t('容器信息') }}
          <i
            v-bk-tooltips="cloudInfoTip"
            class="paasng-icon paasng-info-circle"
          />
        </div>
        <div
          class="form-group-dir form-group"
          style="margin-top: 10px;"
        >
          <label class="form-label">
            {{ $t('镜像地址') }}
            <i
              v-bk-tooltips="mirrorUrlTip"
              class="paasng-icon paasng-info-circle"
            />
          </label>
          <!-- ((https|http|ftp|rtsp|mms)?:\/\/) -->
          <div class="form-group-flex">
            <p>
              <input
                ref="imageUrl"
                type="text"
                autocomplete="off"
                name="source_tp_url"
                data-parsley-required="true"
                :data-parsley-required-message="$t('该字段是必填项')"
                data-parsley-pattern="^(?:(?=[^:\/]{1,253})(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(?:\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*(?::[0-9]{1,5})?\/)?((?![._-])(?:[a-z0-9._-]*)(?<![._-])(?:\/(?![._-])[a-z0-9._-]*(?<![._-]))*)(?::(?![.-])[a-zA-Z0-9_.-]{1,128})?$"
                :data-parsley-pattern-message="$t('地址格式不正确')"
                data-parsley-trigger="input blur"
                class="ps-form-control"
                :placeholder="$t('请输入带标签的镜像地址')"
              >
            </p>
            <p class="whole-item-tips">
              {{ $t('示例镜像：mirrors.tencent.com/bkpaas/django-helloworld:latest') }}&nbsp;
              <span
                class="whole-item-tips-text"
                @click="useExample"
              >{{ $t('使用示例镜像') }}</span>
            </p>
            <p :class="['whole-item-tips', localLanguage === 'en' ? '' : 'no-wrap']">
              <span>{{ $t('镜像应监听“容器端口”处所指定的端口号，或环境变量值 $PORT 来提供 HTTP 服务') }}</span>&nbsp;
              <a
                target="_blank"
                :href="GLOBAL.DOC.BUILDING_MIRRIRS_DOC"
              >{{ $t('帮助：如何构建镜像') }}</a>
            </p>
            <!-- <p class="whole-item-tips"> {{ $t('示例镜像：mirrors.tencent.com/foo/bar') }} </p>
                        <p class="whole-item-tips"> {{ $t('镜像应监听环境变量值$PORT端口，提供HTTP服务') }} </p> -->
          </div>
        </div>

        <div
          class="form-group-dir"
          style="margin-top: 10px;"
        >
          <label class="form-label"> {{ $t('启动命令') }} </label>
          <div class="form-group-flex">
            <bk-tag-input
              v-model="command"
              ext-cls="tag-extra"
              :placeholder="$t('留空将使用镜像的默认 entry point 命令')"
              :allow-create="allowCreate"
              :allow-auto-match="true"
              :has-delete-icon="hasDeleteIcon"
              :paste-fn="copyCommand"
            />
            <p class="whole-item-tips">
              {{ $t('示例：start_server，多个命令可用回车键分隔') }}
            </p>
          </div>
        </div>

        <div
          class="form-group-dir"
          style="margin-top: 10px;"
        >
          <label class="form-label"> {{ $t('命令参数') }} </label>
          <div class="form-group-flex">
            <bk-tag-input
              v-model="args"
              ext-cls="tag-extra"
              :placeholder="$t('请输入命令参数')"
              :allow-create="allowCreate"
              :allow-auto-match="true"
              :has-delete-icon="hasDeleteIcon"
              :paste-fn="copyCommandParameter"
            />
            <p class="whole-item-tips">
              {{ $t('示例：--env prod，多个参数可用回车键分隔') }}
            </p>
          </div>
        </div>

        <div
          class="form-group-dir"
          style="margin-top: 10px;"
        >
          <label class="form-label"> {{ $t('容器端口') }} </label>
          <div class="form-group-flex">
            <p>
              <input
                type="text"
                autocomplete="off"
                name="target_port"
                :data-parsley-pattern-message="$t('只能输入数字')"
                data-parsley-pattern="^[0-9]*$"
                data-parsley-trigger="input blur"
                class="ps-form-control"
                :placeholder="$t('请输入 1 - 65535 的整数，非必填')"
              >
            </p>
            <p class="whole-item-tips">
              {{ $t('请求将会被发往容器的这个端口。推荐不指定具体端口号，让容器监听 $PORT 环境变量') }}
            </p>
          </div>
        </div>
      </div>

      <div
        v-if="isShowAdvancedOptions"
        class="create-item"
        data-test-id="createDefault_item_appSelect"
      >
        <div class="item-title">
          {{ $t('高级选项') }}
        </div>
        <div
          id="choose-cluster"
          class="form-group-dir"
        >
          <label class="form-label"> {{ $t('选择集群') }} </label>
          <bk-select
            v-model="clusterName"
            style="width: 520px; margin-top: 7px;"
            searchable
            :style="errorSelectStyle"
          >
            <bk-option
              v-for="option in clusterList"
              :id="option"
              :key="option"
              :name="option"
            />
          </bk-select>
          <p
            v-if="isShowError"
            class="error-tips"
          >
            {{ $t('该字段是必填项') }}
          </p>
        </div>
      </div>

      <div
        v-if="formLoading"
        class="form-loading"
      >
        <img src="/static/images/create-app-loading.svg">
        <p> {{ $t('应用创建中，请稍候') }} </p>
      </div>
      <div
        v-else
        class="form-actions"
        data-test-id="createDefault_btn_createApp"
      >
        <bk-button
          theme="primary"
          size="large"
          class="submit-mr"
          type="submit"
        >
          {{ $t('创建应用') }}
        </bk-button>
        <bk-button
          size="large"
          class="reset-ml ml15"
          @click.prevent="back"
        >
          {{ $t('返回') }}
        </bk-button>
      </div>
    </form>
  </div>
</template>
<script>
    import _ from 'lodash';
    import i18n from '@/language/i18n.js';
    export default {
        data () {
            return {
                formLoading: false,
                regionChoices: [],
                regionDescription: '',
                regionChoose: 'default',
                command: [],
                args: [],
                allowCreate: true,
                hasDeleteIcon: true,
                isShowAdvancedOptions: false,
                clusterName: '',
                advancedOptionsObj: {},
                isShowError: false,
                cloudInfoTip: i18n.t('当前为web进程配置，创建成功后可添加其他进程'),
                mirrorUrlTip: i18n.t('私有镜像需要在创建应用后，在应用的“镜像凭证”页面中管理镜像账号信息')
            };
        },
        computed: {
            platformFeature () {
                return this.$store.state.platformFeature;
            },
            clusterList () {
                return this.advancedOptionsObj[this.regionChoose] || [];
            },
            errorSelectStyle () {
                if (this.isShowError) {
                    return { borderColor: '#ff3737' };
                }
                return {};
            },
            localLanguage () {
                return this.$store.state.localLanguage;
            }
        },
        watch: {
            regionChoose () {
                this.clusterName = '';
            }
        },
        mounted () {
            this.form = $('#form-create-app').parsley();
            this.$form = this.form.$element;

            // Auto clearn ServerError message for field
            this.form.on('form:validated', (target) => {
                _.each(target.fields, (field) => {
                    field.removeError('serverError');
                });
            });
            window.Parsley.on('field:error', function () {
                // 防止出现多条错误提示
                this.$element.parsley().removeError('serverError');
            });
        },
        created () {
            this.fetchAdvancedOptions();
            this.fetchSpecsByRegion();
        },
        methods: {
            submitCreateForm () {
                if (!this.form.isValid()) {
                    return;
                }
                const formData = this.$form.serializeObject();

                const params = {
                    region: this.regionChoose || formData.region,
                    code: formData.code,
                    name: formData.name,
                    cloud_native_params: {
                        image: formData.source_tp_url,
                        command: this.command,
                        args: this.args
                    },
                    advanced_options: {
                        cluster_name: this.clusterName
                    }
                };
                // 没有选择高级选项需要删除
                if (!this.isShowAdvancedOptions || !this.clusterName) {
                    delete params.advanced_options;
                }
                // 有端口才需要加入端口
                if (formData.target_port) {
                    params.cloud_native_params.target_port = formData.target_port;
                }
                this.$http.post(BACKEND_URL + '/api/bkapps/cloud-native/', params).then((resp) => {
                    const objectKey = `SourceInitResult${Math.random().toString(36)}`;
                    if (resp.source_init_result) {
                        localStorage.setItem(objectKey, JSON.stringify(resp.source_init_result.extra_info));
                    }
                    const path = `/developer-center/apps/${resp.application.code}/create/success`;
                    this.$router.push({
                        path: path,
                        query: { objectKey: objectKey }
                    });
                }, (resp) => {
                    this.$paasMessage({
                        theme: 'error',
                        message: resp.detail
                    });
                }).then(
                    () => {
                        this.formLoading = false;
                    }
                );
            },
            fetchSpecsByRegion () {
                this.$http.get(BACKEND_URL + '/api/bkapps/regions/specs').then((resp) => {
                    this.allRegionsSpecs = resp;
                    _.forEachRight(this.allRegionsSpecs, (value, key) => {
                        this.regionChoices.push({
                            key: key,
                            value: value.display_name,
                            description: value.description
                        });
                    });
                    this.regionChoose = this.regionChoices[0].key;
                    this.regionDescription = this.allRegionsSpecs[this.regionChoose].description;
                });
            },
            back () {
                this.$router.push({
                    name: 'myApplications'
                });
            },
            async fetchAdvancedOptions () {
                let res;
                try {
                    res = await this.$store.dispatch('createApp/getOptions');
                } catch (e) {
                    // 请求接口报错时则不显示高级选项
                    this.isShowAdvancedOptions = false;
                    return;
                }

                // 如果返回当前用户不支持“高级选项”，停止后续处理
                if (!res.allow_adv_options) {
                    this.isShowAdvancedOptions = false;
                    return;
                }

                // 高级选项：解析分 Region 的集群信息
                this.isShowAdvancedOptions = true;
                const advancedRegionClusters = res.adv_region_clusters || [];
                advancedRegionClusters.forEach(item => {
                    if (!this.advancedOptionsObj.hasOwnProperty(item.region)) {
                        this.$set(this.advancedOptionsObj, item.region, item.cluster_names);
                    }
                });
            },
            trimStr (str) {
                return str.replace(/(^\s*)|(\s*$)/g, '');
            },
            copyCommand (val) {
                const value = this.trimStr(val);
                if (!value) {
                    this.$bkMessage({ theme: 'error', message: this.$t('粘贴内容不能为空'), delay: 2000, dismissable: false });
                    return [];
                }
                const commandArr = value.split(',');
                commandArr.forEach(item => {
                    if (!this.command.includes(item)) {
                        this.command.push(item);
                    }
                });
                return this.command;
            },
            copyCommandParameter (val) {
                const value = this.trimStr(val);
                if (!value) {
                    this.$bkMessage({ theme: 'error', message: this.$t('粘贴内容不能为空'), delay: 2000, dismissable: false });
                    return [];
                }
                const commandArr = value.split(',');
                commandArr.forEach(item => {
                    if (!this.args.includes(item)) {
                        this.args.push(item);
                    }
                });
                return this.args;
            },

            // 使用示例参数
            useExample () {
                this.$refs.imageUrl.value = 'mirrors.tencent.com/bkpaas/django-helloworld:latest';
                this.command = [];
                this.command.push(...['bash', '/app/start_web.sh']);
            }
        }
    };
</script>
<style lang="scss">
    .tag-extra, .tag-extra .bk-tag-input {
        min-height: 40px;
    }
    .tag-extra .bk-tag-input .placeholder {
        line-height: 38px;
    }
    .paas-info-command-cls .bk-form-input{
        padding: 20px 10px;
    }
</style>
<style lang="scss" scoped>
    @import './default.scss';
</style>
