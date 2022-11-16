<template>
  <div class="port-config">
    <div class="ps-top-card">
      <p class="main-title">
        {{ $t('进程服务管理') }}
      </p>
      <p class="desc">
        {{ $t('进程服务管理允许你修改应用暴露服务的方式。使用前请先阅读') }}
        <a
          :href="GLOBAL.DOC.PROCESS_SERVICE"
          target="blank"
        > {{ $t('详细使用说明') }} </a>
      </p>
    </div>
    <div class="content">
      <bk-tab
        :active.sync="env"
        type="unborder-card"
      >
        <bk-tab-panel
          v-for="(panel, panelIndex) in panels"
          :key="panelIndex"
          v-bind="panel"
        >
          <section
            v-bkloading="{ isLoading: isConfigLoading, opacity: 1 }"
            class="ps-accordion"
            style="min-height: 70px;"
          >
            <template v-if="processServices.length">
              <div
                v-for="(service, serviceIndex) of processServices"
                :key="serviceIndex"
                class="item"
              >
                <div
                  class="main"
                  @click="service.isExpanded = !service.isExpanded"
                >
                  <div class="toggle-icon">
                    <template v-if="service.isExpanded">
                      <i class="paasng-icon paasng-down-shape" />
                    </template>
                    <template v-else>
                      <i class="paasng-icon paasng-right-shape" />
                    </template>
                  </div>
                  <div
                    class="metedata"
                    style="cursor: pointer;"
                  >
                    <strong class="title">{{ service.process_type }}</strong>
                    <p class="desc">
                      <label class="label"> {{ $t('端口规则：') }} {{ service.ports.length }} {{ $t('个') }} </label>
                      <label class="label"> {{ $t('服务名称：') }} {{ service.name }}</label>
                    </p>
                    <span
                      v-if="processIngress.service_name === service.name"
                      class="mark"
                    > {{ $t('已设置为主入口') }} </span>
                  </div>
                  <div
                    class="action"
                    @click.stop.prevent="stop"
                  >
                    <bk-dropdown-menu
                      :ref="`dropdown${serviceIndex}`"
                      align="right"
                    >
                      <button
                        slot="dropdown-trigger"
                        class="ps-more-btn"
                      >
                        <i class="paasng-icon paasng-more" />
                      </button>
                      <ul
                        slot="dropdown-content"
                        class="bk-dropdown-list"
                      >
                        <li
                          v-for="(port, index) of service.ports"
                          :key="index"
                          class="reset-dropdown-li"
                          @click.stop.prevent="showDialog(service, port, serviceIndex)"
                        >
                          <a
                            href="javascript:;"
                            :class="processIngress.service_port_name === port.name && processIngress.service_name === service.name ? 'disabled' : ''"
                            :title="processIngress.service_port_name === port.name && processIngress.service_name === service.name ? `${port.name}端口已设置为主入口` : `设置${port.name}端口为主入口`"
                          >
                            <template v-if="processIngress.service_port_name === port.name && processIngress.service_name === service.name">
                              <span
                                class="ps-text ps-text-ellipsis f12"
                                style="max-width: 80px;"
                              >{{ port.name }}</span> {{ $t('端口已设置为主入口') }}
                            </template>
                            <template v-else>
                              {{ $t('设置') }} <span
                                class="ps-text ps-text-ellipsis f12"
                                style="max-width: 80px;"
                              >{{ port.name }}</span> {{ $t('端口为主入口') }}
                            </template>
                          </a>
                        </li>
                      </ul>
                    </bk-dropdown-menu>
                  </div>
                </div>
                <div
                  v-if="service.isExpanded"
                  class="params-box"
                >
                  <div class="params-header">
                    <strong class="title"> {{ $t('端口配置') }} </strong>
                    <template v-if="!service.isEdited">
                      <button
                        class="bk-text-button"
                        @click.stop.prevent="service.isEdited = !service.isEdited"
                      >
                        {{ $t('编辑') }}
                      </button>
                    </template>
                    <template v-else>
                      <button
                        class="bk-text-button"
                        @click.stop.prevent="service.isEdited = false"
                      >
                        {{ $t('取消') }}
                      </button>
                      <button
                        class="bk-text-button"
                        @click.stop.prevent="updateServicePorts(service)"
                      >
                        {{ $t('保存') }}
                      </button>
                    </template>
                  </div>

                  <template v-if="!service.isEdited">
                    <table
                      class="ps-table"
                      style="width: 100%;"
                    >
                      <thead>
                        <tr>
                          <th style="width: 200px;">
                            {{ $t('名称') }}
                          </th>
                          <th> {{ $t('协议') }} </th>
                          <th style="width: 180px;">
                            {{ $t('服务端口') }}
                          </th>
                          <th style="width: 100px;" />
                          <th style="width: 180px;">
                            {{ $t('进程内端口') }}
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr
                          v-for="(port, portIndex) of service.ports"
                          :key="portIndex"
                        >
                          <td>
                            <span>{{ port.name }}</span>
                            <label
                              v-if="port.isMainEntry"
                              class="ps-label primary ml5"
                            >
                              <span> {{ $t('主入口') }} </span>
                            </label>
                          </td>
                          <td>{{ port.protocol }}</td>
                          <td>{{ port.port }}</td>
                          <td>
                            <i class="paasng-icon paasng-arrows-right f18" />
                          </td>
                          <td>{{ port.target_port }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </template>
                  <template v-else>
                    <table
                      class="ps-table"
                      style="width: 100%;"
                    >
                      <thead>
                        <tr>
                          <th style="width: 200px;">
                            {{ $t('名称') }}
                          </th>
                          <th> {{ $t('协议') }} </th>
                          <th style="width: 150px;">
                            {{ $t('服务端口') }}
                          </th>
                          <th style="width: 80px;" />
                          <th style="width: 150px;">
                            {{ $t('进程内端口') }}
                          </th>
                          <th style="width: 50px;">
                            {{ $t('操作') }}
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr
                          v-for="(port, portIndex) of service.editPorts"
                          :key="portIndex"
                        >
                          <td>
                            <bk-form
                              :label-width="0"
                              :model="port"
                              style="padding-right: 25px;"
                            >
                              <bk-form-item
                                :rules="portRules.name"
                                :property="'name'"
                              >
                                <bk-input
                                  v-model="port.name"
                                  :maxlength="32"
                                  :placeholder="$t('请输入32个字符以内')"
                                  :readonly="port.isMainEntry"
                                />
                              </bk-form-item>
                            </bk-form>
                          </td>
                          <td>
                            <bk-form
                              :label-width="0"
                              style="padding-right: 25px;"
                            >
                              <bk-form-item>
                                <bk-select
                                  v-model="port.protocol"
                                  :clearable="false"
                                >
                                  <bk-option
                                    v-for="(option, index) in protocolList"
                                    :id="option.id"
                                    :key="index"
                                    :name="option.name"
                                  />
                                </bk-select>
                              </bk-form-item>
                            </bk-form>
                          </td>
                          <td>
                            <bk-form
                              :label-width="0"
                              :model="port"
                              style="padding-right: 25px;"
                            >
                              <bk-form-item
                                :rules="portRules.port"
                                :property="'port'"
                              >
                                <bk-num-input
                                  type="number"
                                  placeholder="1-65535"
                                  style="display: inline-block;"
                                  :min="1"
                                  :max="65535"
                                  :value.sync="port.port"
                                />
                              </bk-form-item>
                            </bk-form>
                          </td>
                          <td>
                            <i class="paasng-icon paasng-arrows-right f18" />
                          </td>
                          <td>
                            <bk-form
                              :label-width="0"
                              :model="port"
                              style="padding-right: 25px;"
                            >
                              <bk-form-item
                                :rules="portRules.targetPort"
                                :property="'target_port'"
                              >
                                <bk-num-input
                                  type="number"
                                  placeholder="1-65535"
                                  style="display: inline-block;"
                                  :min="1"
                                  :max="65535"
                                  :value.sync="port.target_port"
                                />
                              </bk-form-item>
                            </bk-form>
                          </td>
                          <td>
                            <template v-if="port.isMainEntry">
                              <bk-popover :content="$t('不能删除主入口')">
                                <button
                                  class="bk-text-button is-disabled"
                                  disabled
                                >
                                  {{ $t('删除') }}
                                </button>
                              </bk-popover>
                            </template>
                            <template v-else>
                              <template v-if="service.editPorts.length > 1">
                                <button
                                  class="bk-text-button"
                                  @click="removeServicePort(service, portIndex)"
                                >
                                  {{ $t('删除') }}
                                </button>
                              </template>
                              <template v-else>
                                <bk-popover :content="$t('至少保留一项')">
                                  <button
                                    class="bk-text-button is-disabled"
                                    disabled
                                  >
                                    {{ $t('删除') }}
                                  </button>
                                </bk-popover>
                              </template>
                            </template>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                    <button
                      class="ps-block-btn"
                      @click.stop.prevent="addServicePort(service)"
                    >
                      {{ $t('点击添加') }}
                    </button>
                  </template>
                </div>
              </div>
            </template>
            <template v-else>
              <div
                v-if="!isConfigLoading"
                class="ps-no-result"
              >
                <div class="text">
                  <p>
                    <i class="paasng-icon paasng-empty" />
                  </p>
                  <p class="f13">
                    {{ $t('未找到进程服务，请尝试') }}
                    <router-link
                      class="bk-text-button"
                      :to="{ name: 'appDeploy', params: { id: appCode }, query: { focus: env } }"
                    >
                      {{ $t('部署') }}
                    </router-link>
                    {{ $t('后刷新') }}
                  </p>
                </div>
              </div>
            </template>
          </section>
        </bk-tab-panel>
      </bk-tab>

      <bk-dialog
        v-model="changeEntryDialog.visiable"
        width="650"
        :theme="'primary'"
        :mask-close="false"
        :loading="changeEntryDialog.isLoading"
        @confirm="setServiceMainEntry"
        @cancel="changeEntryDialog.visiable = false"
      >
        <div slot="header">
          <p style="white-space: normal; line-height: 32px;">
            {{ changeEntryDialog.title }}
          </p>
        </div>
        <div class="tc">
          {{ $t('切换主入口可能会造成应用无法正常访问，操作前请确认目标进程与端口运行正常') }}
        </div>
      </bk-dialog>
    </div>
  </div>
</template>

<script type="text/javascript">
    import appBaseMixin from '@/mixins/app-base-mixin';
    import bkNumInput from '@/components/ui/bkInput';

    export default {
        components: {
            bkNumInput
        },
        mixins: [appBaseMixin],
        data () {
            return {
                env: 'stag',
                processServices: [],
                changeEntryDialog: {
                    visiable: false,
                    title: ''
                },
                processIngress: {
                    service_name: ''
                },
                isConfigLoading: true,
                portRules: {
                    name: [
                        {
                            required: true,
                            message: this.$t('名称不能为空'),
                            trigger: 'blur'
                        },
                        {
                            regex: /^[a-z0-9]([-a-z0-9]*[a-z0-9])?$/,
                            message: this.$t('小写字母或数字开头结尾，中间可以有中划线'),
                            trigger: 'blur'
                        }
                    ],
                    port: [
                        {
                            required: true,
                            message: this.$t('服务端口不能为空'),
                            trigger: 'blur'
                        }
                    ],
                    targetPort: [
                        {
                            required: true,
                            message: this.$t('进程内端口不能为空'),
                            trigger: 'blur'
                        }
                    ]
                },
                protocolList: [
                    {
                        id: 'TCP',
                        name: 'TCP'
                    },
                    {
                        id: 'UDP',
                        name: 'UDP'
                    }
                ],
                panels: [
                    { name: 'stag', label: this.$t('预发布环境') },
                    { name: 'prod', label: this.$t('生产环境') }
                ]
            };
        },
        watch: {
            '$route' () {
                this.init();
            },
            env () {
                this.init();
            }
        },
        created () {
            this.init();
        },
        methods: {
            /**
             * 数据初始化入口
             */
            async init () {
                this.getProcessServices();
            },

            /**
             * 获取所有某个部署环境下的所有进程服务
             */
            async getProcessServices () {
                this.isConfigLoading = true;

                try {
                    const params = {
                        appCode: this.appCode,
                        moduleId: this.curModuleId,
                        env: this.env
                    };
                    const res = await this.$store.dispatch('entryConfig/getProcessServices', params);

                    if (res.default_ingress) {
                        this.processIngress = res.default_ingress;
                    }

                    if (res.proc_services) {
                        this.processServices = res.proc_services.map(service => {
                            service.ports.forEach(port => {
                                // 当前端口为主入口
                                if (this.processIngress.service_name === service.name && this.processIngress.service_port_name === port.name) {
                                    port.isMainEntry = true;
                                }
                            });
                            return {
                                isEdited: false,
                                isExpanded: false,
                                editPorts: JSON.parse(JSON.stringify(service.ports)), // 编辑时，防止和原数据冲突
                                ...service
                            };
                        });
                    }
                } catch (e) {
                    this.processServices = [];
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message
                    });
                } finally {
                    this.isConfigLoading = false;
                    this.$emit('data-ready', 'port-config');
                }
            },

            /**
             * 数据校验
             */
            checkPortData (service) {
                for (const port of service.editPorts) {
                    if (!port.name) {
                        this.$paasMessage({
                            theme: 'error',
                            message: this.$t('端口名称不能为空！')
                        });
                        return false;
                    }
                    if (!/^[a-z0-9]([-a-z0-9]*[a-z0-9])?$/.test(port.name)) {
                        this.$paasMessage({
                            theme: 'error',
                            message: this.$t('端口名称只能以小写字母或数字开头结尾，中间可以有中划线！')
                        });
                        return false;
                    }
                    if (!port.port) {
                        this.$paasMessage({
                            theme: 'error',
                            message: this.$t('服务端口不能为空')
                        });
                        return false;
                    }
                    if (!port.target_port) {
                        this.$paasMessage({
                            theme: 'error',
                            message: this.$t('进程内端口不能为空')
                        });
                        return false;
                    }
                }
                return true;
            },

            /**
             * 修改进程服务的端口列表
             * @param {Object} service 服务对象
             */
            async updateServicePorts (service) {
                if (!this.checkPortData(service)) {
                    return false;
                }
                try {
                    const ports = service.editPorts;
                    const params = {
                        serviceName: service.name,
                        appCode: this.appCode,
                        moduleId: this.curModuleId,
                        env: this.env,
                        ports: ports
                    };
                    await this.$store.dispatch('entryConfig/updateServicePorts', params);
                    service.ports = JSON.parse(JSON.stringify(service.editPorts));
                    service.isEdited = false;

                    this.updateMainEntry();
                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('保存成功！')
                    });
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message
                    });
                }
            },

            /**
             * 更新主入口
             */
            updateMainEntry () {
                this.processServices.forEach(service => {
                    service.ports.forEach(port => {
                        // 当前端口为主入口
                        if (this.processIngress.service_name === service.name && this.processIngress.service_port_name === port.name) {
                            port.isMainEntry = true;
                        } else {
                            port.isMainEntry = false;
                        }
                    });
                });
            },

            /**
             * 添加进程服务编辑的端口
             * @param {Object} service 服务对象
             */
            addServicePort (service) {
                service.editPorts.push({
                    name: '',
                    protocol: 'TCP',
                    port: '',
                    target_port: ''
                });
            },

            /**
             * 删除进程服务端口
             * @param {Object} service 服务对象
             * @param {Number} index 端口索引
             */
            removeServicePort (service, index) {
                service.editPorts.splice(index, 1);
            },

            /**
             * 显示设置主入口确认提示框
             */
            showDialog (service, port, serviceIndex) {
                if (this.processIngress.service_name === service.name && this.processIngress.service_port_name === port.name) {
                    return;
                }
                this.changeEntryDialog.title = `确认设置${service.process_type}进程的${port.name}端口为主入口？`;
                this.curService = service;
                this.curPort = port;
                this.curServiceIndex = serviceIndex;
                this.changeEntryDialog.visiable = true;
            },

            /**
             * 设置模块主入口
             * @param {Object} service 服务对象
             * @param {Object} port 端口
             */
            async setServiceMainEntry () {
                const service = this.curService;
                const port = this.curPort;
                const serviceIndex = this.curServiceIndex;
                const dropdownKey = `dropdown${serviceIndex}`;
                if (this.$refs[dropdownKey]) {
                    this.$refs[dropdownKey][0].hide();
                }
                try {
                    const params = {
                        serviceName: service.name,
                        servicePortName: port.name,
                        appCode: this.appCode,
                        moduleId: this.curModuleId,
                        env: this.env
                    };
                    const res = await this.$store.dispatch('entryConfig/setServiceMainEntry', params);
                    this.processIngress = res;

                    this.getProcessServices();
                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('设置成功！')
                    });
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message
                    });
                }
            },

            /**
             * 跳转到部署页面
             */
            gotoDeploy () {
                // this.$router
            },

            stop () {}
        }
    };
</script>

<style lang="scss" scoped>
    .reset-dropdown-li {
        > a {
            &.disabled {
                color: #c4c6cc;
                cursor: not-allowed;
                &:hover {
                    background: #fff;
                    color: #c4c6cc;
                }
            }
        }
    }
    .port-config {
        margin-bottom: 15px;
    }
    .ps-more-btn {
        margin: 16px 0 0 22px;
    }
    .paasng-arrows-right {
        font-size: 18px;
        color: #dcdee5;
        font-weight: bold;
    }
    .ps-no-result {
        width: 100%;
        border-radius: 2px;
        border: 1px solid #dcdee5;
    }
</style>
