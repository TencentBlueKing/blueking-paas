<template>
  <div>
    <div>
      <div
        class="process-table-wrapper"
        :class="!allProcesses.length ? 'reset-style' : ''"
      >
        <div
          v-if="allProcesses.length === 0"
          class="ps-no-result"
        >
          <table-empty
            class="pb30"
            empty
          />
        </div>
        <div
          v-for="(process, index) in allProcesses"
          v-else
          :key="index"
          class="process-item"
        >
          <div
            :key="process.status"
            class="process-item-header"
          >
            <div>
              <div
                class="process-basic-info"
                @click="showProcessDetail(process)"
              >
                <div>
                  <a class="ps-icon-btn-circle no-border expanded-icon">
                    <i
                      :class="[
                        'paasng-icon paasng-bold',
                        {
                          'paasng-down-shape': process.name === curProcessKey,
                          'paasng-right-shape': process !== curProcess || !curProcessKey,
                        },
                      ]"
                    />
                  </a>
                  <b
                    v-bk-tooltips="process.name"
                    class="process-name"
                  >
                    {{ process.name }}
                  </b>
                </div>
                <div
                  v-if="process.autoscaling"
                  class="auto-scal"
                >
                  {{ $t('自动扩缩容') }}
                </div>
              </div>
              <div class="instance-count">
                <div>
                  <span>{{ process.available_instance_count }} / {{ process.desired_replicas }}</span>
                </div>
              </div>
            </div>
            <div
              class="process-command"
              @click="showProcessDetail(process)"
            >
              <p v-bk-overflow-tips>
                {{ process.cmd }}
              </p>
            </div>
            <div class="status-container">
              <div
                v-if="process.status === 'Running'"
                class="process-status"
              >
                <span v-if="!process.autoscaling">
                  <img
                    src="/static/images/btn_loading.gif"
                    class="loading"
                  />
                  <span>
                    {{ process.targetStatus === 'start' ? $t('启动中...') : $t('停止中...') }}
                  </span>
                </span>
              </div>
              <div class="process-operate">
                <a
                  slot="trigger"
                  v-bk-tooltips="$t('进程详情')"
                  class="icon-info-l icon-info-base ps-icon-btn-circle no-border"
                  @click="showProcessDetailDialog(process, index)"
                >
                  <i class="paasng-icon paasng-process-file" />
                </a>
                <a
                  slot="trigger"
                  v-bk-tooltips="$t('访问控制台')"
                  class="icon-info-d icon-info-base ps-icon-btn-circle no-border"
                  @click="showProcessDetail(process)"
                >
                  <i class="paasng-icon paasng-diff-2" />
                </a>
                <template v-if="process.targetStatus === 'start'">
                  <div
                    v-bk-tooltips="process.operateIconTitle"
                    class="tool-confirm-wrapper"
                    @click="confirmClick(process)"
                    @mouseover="clearTooltipTimer(process)"
                    @mouseout="hideTooltipConfirm(process)"
                  >
                    <tooltip-confirm
                      ref="tooltipConfirm"
                      :ok-text="$t('确定')"
                      :cancel-text="$t('取消')"
                      :theme="'ps-tooltip'"
                      @ok="updateProcess(process, index)"
                      @cancel="closeProcess(process)"
                      @mouseover="clearTooltipTimer(process, 'show')"
                      @mouseout="hideTooltipConfirm(process)"
                    >
                      <a
                        slot="trigger"
                        class="ps-icon-btn-circle operate-process-icon stop"
                        href="javascript:;"
                        :class="{ disabled: isAppOfflined }"
                      >
                        <div class="square-icon" />
                        <!-- <i></i> -->
                        <img
                          src="/static/images/btn_loading.gif"
                          class="loading"
                          style="margin-right: 0"
                        />
                      </a>
                    </tooltip-confirm>
                  </div>
                </template>
                <template v-else>
                  <a
                    v-bk-tooltips="isAppOfflined ? $t('模块已下架，不可操作') : process.operateIconTitle"
                    class="ps-icon-btn-circle operate-process-icon on start"
                    href="javascript:"
                    :class="{ disabled: isAppOfflined }"
                    @click="patchProcess(process, index)"
                  >
                    <i />
                    <img
                      src="/static/images/btn_loading.gif"
                      class="loading"
                      style="margin-right: 0"
                    />
                  </a>
                </template>
                <bk-dropdown-menu
                  trigger="click"
                  align="right"
                  ext-cls="dropdown-menu-cls"
                >
                  <template slot="dropdown-trigger">
                    <i class="paasng-icon paasng-icon-more" />
                  </template>
                  <ul
                    class="bk-dropdown-list"
                    slot="dropdown-content"
                  >
                    <li
                      class="option"
                      v-bk-tooltips="{
                        content: $t('启动进程后才能进行扩缩容'),
                        disabled: process.available_instance_count || process.desired_replicas,
                      }"
                    >
                      <bk-button
                        text
                        size="small"
                        @click="showProcessConfigDialog(process, index)"
                        :disabled="!process.available_instance_count || !process.desired_replicas"
                      >
                        {{ $t('扩缩容') }}
                      </bk-button>
                    </li>
                    <li class="option">
                      <bk-button
                        text
                        size="small"
                        @click="showRestartPopup('process', process)"
                      >
                        {{ $t('重启进程') }}
                      </bk-button>
                    </li>
                  </ul>
                </bk-dropdown-menu>
              </div>
            </div>
          </div>
          <div
            v-if="process.name === curProcessKey"
            class="process-item-table"
          >
            <div class="header-shadow" />
            <div class="process-item-table-wrapper">
              <table class="ps-table ps-table-default ps-instances-table ps-table-special">
                <thead>
                  <th>{{ $t('实例名称') }}</th>
                  <th>{{ $t('状态') }}</th>
                  <th>{{ $t('重启次数') }}</th>
                  <th>{{ $t('创建时间') }}</th>
                  <th style="min-width: 250px">
                    {{ $t('操作') }}
                  </th>
                </thead>
                <tbody>
                  <template v-if="curProcess && curProcess.instances.length">
                    <tr
                      v-for="(instance, instanceIndex) in curProcess.instances"
                      :key="instanceIndex"
                    >
                      <td class="name">
                        <p v-bk-overflow-tips>
                          {{ instance.display_name }}
                        </p>
                      </td>
                      <td class="run-state">
                        <i
                          class="paasng-icon"
                          :class="instance.ready ? 'paasng-check-circle' : 'paasng-empty'"
                        />
                        <span
                          v-bk-tooltips="{ content: getInstanceStateToolTips(instance) }"
                          v-dashed="9"
                        >
                          {{ instance.rich_status }}
                        </span>
                      </td>
                      <td class="restarts">
                        <span
                          v-bk-tooltips="{
                            content: `<p>reason: ${instance.terminated_info?.reason}</p>exit_code: ${instance.terminated_info?.exit_code}`,
                            disabled: !instance.terminated_info?.reason,
                            allowHTML: true,
                          }"
                          :style="{ 'border-bottom': instance.terminated_info?.reason ? '1px dashed' : 'none' }"
                        >
                          {{ instance.restart_count }}
                        </span>
                      </td>
                      <td class="time">
                        <template v-if="instance.date_time !== 'Invalid date'">
                          {{ $t('创建于') }} {{ instance.date_time }}
                        </template>
                        <template v-else>--</template>
                      </td>
                      <td class="operate-container">
                        <a
                          href="javascript:void(0);"
                          class="blue"
                          @click="showInstanceLog(instance, process)"
                        >
                          {{ $t('查看日志') }}
                        </a>
                        <a
                          href="javascript:void(0);"
                          class="blue ml8"
                          @click="showInstanceConsole(instance, process)"
                        >
                          {{ $t('访问控制台') }}
                        </a>
                        <a
                          href="javascript:void(0);"
                          class="blue ml8"
                          @click="showInstanceEvents(instance, process)"
                        >
                          {{ $t('查看事件') }}
                        </a>
                        <a
                          href="javascript:void(0);"
                          class="blue ml8"
                          @click="showRestartPopup('instance', instance)"
                        >
                          {{ $t('重启实例') }}
                        </a>
                      </td>
                    </tr>
                  </template>
                  <template v-if="!curProcess || !curProcess.instances.length">
                    <tr class="process-empty">
                      <td colspan="4">
                        <div class="ps-no-result">
                          <table-empty
                            :empty-title="$t('暂无实例')"
                            empty
                          />
                        </div>
                      </td>
                    </tr>
                  </template>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
      <bk-sideslider
        :width="750"
        :is-show.sync="chartSlider.isShow"
        :title="chartSlider.title"
        :quick-close="true"
        @hidden="handlerChartHide"
      >
        <div
          slot="content"
          class="p0 chart-wrapper"
        >
          <div
            v-if="platformFeature.RESOURCE_METRICS"
            v-bk-clickoutside="hideDatePicker"
            class="action-box"
          >
            <bk-form
              form-type="inline"
              style="float: right"
            >
              <bk-date-picker
                v-model="initDateTimeRange"
                style="margin-top: 4px"
                :shortcuts="dateShortCut"
                :shortcuts-type="'relative'"
                :format="'yyyy-MM-dd HH:mm:ss'"
                :placement="'bottom-end'"
                :placeholder="$t('选择日期时间范围')"
                :shortcut-close="true"
                :type="'datetimerange'"
                :options="datePickerOption"
                :open="isDatePickerOpen"
                @change="handlerChange"
                @pick-success="handlerPickSuccess"
              >
                <div
                  slot="trigger"
                  style="width: 310px; height: 28px"
                  @click="toggleDatePicker"
                >
                  <button class="action-btn timer fr">
                    <i class="left-icon paasng-icon paasng-clock f16" />
                    <span class="text">{{ $t(timerDisplay) }}</span>
                    <i class="right-icon paasng-icon paasng-down-shape f12" />
                  </button>
                </div>
              </bk-date-picker>
            </bk-form>
          </div>
          <div
            v-if="platformFeature.RESOURCE_METRICS"
            class="chart-box"
          >
            <strong class="title">
              {{ $t('CPU使用') }}
              <span class="sub-title">{{ $t('（单位：核）') }}</span>
            </strong>
            <chart
              ref="cpuLine"
              :options="cpuLine"
              auto-resize
              style="width: 750px; height: 300px; background: #1e1e21"
            />
          </div>
          <div
            v-if="platformFeature.RESOURCE_METRICS"
            class="chart-box"
          >
            <strong class="title">
              {{ $t('内存使用') }}
              <span class="sub-title">{{ $t('（单位：MB）') }}</span>
            </strong>
            <chart
              ref="memoryLine"
              :options="memoryLine"
              auto-resize
              style="width: 750px; height: 300px; background: #1e1e21"
            />
          </div>
          <div class="slider-detail-wrapper">
            <label class="title">{{ $t('详细信息') }}</label>
            <section class="detail-item">
              <label class="label">{{ $t('类型：') }}</label>
              <div class="content">
                {{ processPlan.processType }}
              </div>
            </section>
            <section class="detail-item">
              <label class="label">{{ $t('实例数上限：') }}</label>
              <div class="content">
                {{ processPlan.maxReplicas }}
              </div>
            </section>
            <section class="detail-item">
              <label class="label">{{ $t('单实例资源配额：') }}</label>
              <div class="content">{{ $t('内存:') }} {{ processPlan.memLimit }} / CPU: {{ processPlan.cpuLimit }}</div>
            </section>
            <section class="detail-item">
              <label class="label">{{ $t('进程间访问链接：') }}</label>
              <div class="content">
                {{ processPlan.clusterLink }}
              </div>
            </section>
            <p style="padding-left: 112px; margin-top: 5px; color: #c4c6cc">
              {{
                $t(
                  '注意：进程间访问链接地址只能用于同集群内的不同进程间通信，可在 “模块管理” 页面查看进程的集群信息。更多进程间通信的说明。请参考'
                )
              }}
              <a
                target="_blank"
                :href="GLOBAL.DOC.PROCESS_SERVICE"
              >
                {{ $t('进程间通信') }}
              </a>
            </p>
          </div>
        </div>
      </bk-sideslider>
    </div>

    <!-- 进程实时日志 start -->
    <div
      v-if="isLogShow"
      class="instance-box"
    >
      <h3>{{ curProcessType.toUpperCase() }} {{ $t('进程实时日志') }}</h3>
      <div class="instance-p">
        <div class="instance-input">
          <input
            v-model="filterKeys"
            class="ps-form-control"
            type="text"
            :placeholder="$t('请输入关键字')"
          />
          <input
            class="ps-btn ps-btn-primary"
            type="button"
            :value="$t('过滤')"
            @click.stop.prevent="handleLogsFilter"
          />
        </div>
        <label @click="toggleRealTimeLog">
          <input
            type="checkbox"
            class="ps-checkbox-default"
            value="true"
            checked="checked"
          />
          <span>{{ $t('实时滚动') }}</span>
        </label>
      </div>
      <div class="logscroll">
        <div class="instance-textarea">
          <div class="textarea">
            <div class="inner">
              <p
                v-for="(item, itemIndex) in logDetail"
                :key="itemIndex"
                v-html="item"
              />
            </div>
            <div class="log-loading-container">
              <div class="log-loading">
                {{ $t('实时日志获取中...') }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- 进程实时日志 end -->

    <!-- 查看事件 -->
    <eventDetail
      v-model="instanceEventConfig.isShow"
      :width="computedWidth"
      :config="instanceEventConfig"
      :env="environment"
      :module-id="curModuleId"
      :instance-name="instanceEventConfig.instanceName"
    />

    <!-- 进程设置 -->
    <bk-dialog
      v-model="processConfigDialog.visiable"
      width="576"
      :title="$t('web进程扩缩容')"
      :header-position="'left'"
      :loading="processConfigDialog.isLoading"
      :theme="'primary'"
      :mask-close="false"
      @confirm="saveProcessConfig"
      @cancel="closeProcessConfig"
      @after-leave="afterCloseProcessConfig"
    >
      <div
        v-if="processConfigDialog.showForm"
        style="min-height: 65px"
      >
        <bk-radio-group
          v-model="autoscaling"
          @change="handleAutoChange"
          class="mb20"
        >
          <bk-radio-button
            class="radio-cls"
            :value="false"
          >
            {{ $t('手动调节') }}
          </bk-radio-button>
          <bk-radio-button
            class="radio-cls"
            :value="true"
            :disabled="!autoScalDisableConfig.ENABLE_AUTOSCALING"
            v-bk-tooltips="{
              content: $t('该环境暂不支持自动扩缩容'),
              disabled: autoScalDisableConfig.ENABLE_AUTOSCALING,
            }"
          >
            {{ $t('自动调节') }}
          </bk-radio-button>
        </bk-radio-group>
        <bk-form
          ref="processConfigForm"
          :label-width="110"
          style="width: 520px"
          :model="processPlan"
        >
          <bk-form-item :label="$t('当前副本数：')">
            <span>{{ curTargetReplicas }}</span>
          </bk-form-item>
          <bk-form-item
            v-if="autoscaling"
            :label="$t('触发条件：')"
          >
            <div class="rate-container">
              <span>
                {{ $t('CPU 使用率') }} =
                <bk-input
                  class="w80"
                  v-model="defaultUtilizationRate"
                  disabled
                ></bk-input>
              </span>
              <i
                class="paasng-icon paasng-exclamation-circle uv-tips ml10"
                v-bk-tooltips="autoScalingTip"
              />
            </div>
          </bk-form-item>
          <bk-form-item
            v-if="autoscaling"
            class="desc-form-item"
            :label-width="10"
          >
            <div class="desc-container">
              <p>
                {{ $t('当 CPU 使用率') }} >
                <span class="cpu-num">85%</span>
                {{ $t('时，会触发扩容') }}
              </p>
              <p>
                {{ $t('当 CPU 使用率') }} &lt;
                <span class="cpu-num">{{ shrinkLimit }}</span>
                {{ $t('时，会触发缩容') }}
              </p>
            </div>
          </bk-form-item>
          <!-- 手动调节展示 -->
          <bk-form-item
            v-else
            :label="$t('副本数量：')"
            :required="true"
            :rules="processPlanRules.targetReplicas"
            :property="'targetReplicas'"
            class="manual-form-cls"
            error-display-type="normal"
          >
            <bk-input
              type="number"
              :placeholder="$t('请输入')"
              class="dia-input"
              :min="0"
              v-model="processPlan.targetReplicas"
            />
          </bk-form-item>
        </bk-form>
        <div
          class="auto-container"
          v-if="autoscaling"
        >
          <bk-form
            :rules="scalingRules"
            :model="scalingConfig"
            ref="scalingConfigForm"
            class="auto-form"
            :label-width="0"
            form-type="inline"
          >
            <bk-form-item
              property="minReplicas"
              error-display-type="normal"
            >
              <bk-input
                type="number"
                :placeholder="minReplicasNum + ' - ' + maxReplicasNum"
                class="dia-input"
                v-model="scalingConfig.minReplicas"
                :max="maxReplicasNum"
                :min="0"
              >
                <template slot="prepend">
                  <div class="group-text">{{ $t('最小副本数') }}</div>
                </template>
              </bk-input>
            </bk-form-item>
            <bk-form-item
              property="maxReplicas"
              error-display-type="normal"
              class="ml20"
            >
              <bk-input
                type="number"
                :placeholder="'1 - ' + maxReplicasNum"
                class="dia-input"
                v-model="scalingConfig.maxReplicas"
                :max="maxReplicasNum"
                :min="0"
              >
                <template slot="prepend">
                  <div class="group-text">{{ $t('最大副本数') }}</div>
                </template>
              </bk-input>
            </bk-form-item>
          </bk-form>
        </div>
      </div>
    </bk-dialog>
    <!-- 进程设置 end -->

    <!-- 无法使用控制台 -->
    <bk-dialog
      v-model="processRefuseDialog.visiable"
      width="650"
      :title="$t('无法使用控制台功能')"
      :theme="'primary'"
      :mask-close="false"
      :loading="processRefuseDialog.isLoading"
    >
      <div>
        {{ processRefuseDialog.description }}
        <div class="mt10">
          <a
            :href="processRefuseDialog.link"
            target="_blank"
          >
            {{ $t('文档：') }} {{ processRefuseDialog.title }}
          </a>
        </div>
      </div>
    </bk-dialog>
    <!-- 无法使用控制台 end -->

    <!-- 日志弹窗 -->
    <process-log
      v-if="logConfig.visiable"
      ref="processLogRef"
      v-model="logConfig.visiable"
      :title="logConfig.title"
      :logs="logConfig.logs"
      :loading="logConfig.isLoading"
      :selection-list="logSelectionList"
      :params="logConfig.params"
      :default-condition="'1h'"
      @close="handleClose"
      @change="refreshLogs"
      @refresh="refreshLogs"
      @download="downloadInstanceLog"
    ></process-log>

    <!-- 功能依赖项展示 -->
    <FunctionalDependency
      :show-dialog.sync="showFunctionalDependencyDialog"
      mode="dialog"
      :title="$t('暂无访问控制台功能')"
      :functional-desc="
        $t('访问控制台可以让您进入应用进程的容器，查看线上运行的代码、进行在线调试以及执行一次性命令等操作。')
      "
      :guide-title="$t('如需使用该功能，需要：')"
      :guide-desc-list="[$t('1. 安装 BCS 套餐'), $t('2. 将应用集群来源修改为: BCS 集群')]"
      @gotoMore="gotoMore"
    />
  </div>
</template>

<script>
import ECharts from 'vue-echarts/components/ECharts.vue';
import 'echarts/lib/chart/line';
import 'echarts/lib/component/tooltip';
import tooltipConfirm from '@/components/ui/TooltipConfirm';
import moment from 'moment';
import chartOption from '@/json/instance-chart-option';
import appBaseMixin from '@/mixins/app-base-mixin';
import $ from 'jquery';
import i18n from '@/language/i18n.js';
import sidebarDiffMixin from '@/mixins/sidebar-diff-mixin';
import eventDetail from '@/views/dev-center/app/engine/cloud-deploy-manage/comps/event-detail.vue';
import processLog from '@/components/process-log-dialog/log.vue';
import FunctionalDependency from '@blueking/functional-dependency/vue2/index.umd.min.js';
import { downloadTxt } from '@/common/tools';

let maxReplicasNum = 0;

const initEndDate = moment().format('YYYY-MM-DD HH:mm:ss');
const initStartDate = moment().subtract(1, 'hours').format('YYYY-MM-DD HH:mm:ss');
let timeRangeCache = '';
let timeShortCutText = '';
export default {
  components: {
    tooltipConfirm,
    chart: ECharts,
    eventDetail,
    processLog,
    FunctionalDependency,
  },
  mixins: [appBaseMixin, sidebarDiffMixin],
  props: {
    environment: {
      type: String,
    },
  },
  data() {
    const dateShortCut = [
      {
        text: i18n.t('最近5分钟'),
        value() {
          const end = new Date();
          const start = new Date();
          start.setTime(start.getTime() - 60 * 1000 * 5);
          return [start, end];
        },
        onClick() {
          timeRangeCache = '5m';
          timeShortCutText = i18n.t('最近5分钟');
        },
      },
      {
        text: i18n.t('最近1小时'),
        value() {
          const end = new Date();
          const start = new Date();
          start.setTime(start.getTime() - 3600 * 1000 * 1);
          return [start, end];
        },
        onClick() {
          timeRangeCache = '1h';
          timeShortCutText = i18n.t('最近1小时');
        },
      },
      {
        text: i18n.t('最近3小时'),
        value() {
          const end = new Date();
          const start = new Date();
          start.setTime(start.getTime() - 3600 * 1000 * 3);
          return [start, end];
        },
        onClick() {
          timeRangeCache = '3h';
          timeShortCutText = i18n.t('最近3小时');
        },
      },
      {
        text: i18n.t('最近12小时'),
        value() {
          const end = new Date();
          const start = new Date();
          start.setTime(start.getTime() - 3600 * 1000 * 12);
          return [start, end];
        },
        onClick() {
          timeRangeCache = '12h';
          timeShortCutText = i18n.t('最近12小时');
        },
      },
      {
        text: i18n.t('最近1天'),
        value() {
          const end = new Date();
          const start = new Date();
          start.setTime(start.getTime() - 3600 * 1000 * 24);
          return [start, end];
        },
        onClick() {
          timeRangeCache = '1d';
          timeShortCutText = i18n.t('最近1天');
        },
      },
    ];

    if (this.type === 'customLog' || this.type === 'accessLog') {
      dateShortCut.push({
        text: i18n.t('最近7天'),
        value() {
          const end = new Date();
          const start = new Date();
          start.setTime(start.getTime() - 3600 * 1000 * 24 * 7);
          return [start, end];
        },
        onClick() {
          timeRangeCache = '7d';
          timeShortCutText = i18n.t('最近7天');
        },
      });
    }
    return {
      processConfigDialog: {
        isLoading: false,
        visiable: false,
        showForm: false,
      },
      processRefuseDialog: {
        isLoading: false,
        visiable: false,
        description: '',
        title: '',
        link: '',
      },
      curProcess: {
        instances: [],
      },
      allProcesses: [],
      curInstance: {
        name: '',
      },
      // 进程操作相关变量
      loading: true,
      isAppOfflined: false,
      deploymentReady: false,
      pendingProcessList: [],
      processInterval: undefined,
      timer: 0,
      processPlan: {
        processType: 'unkonwn',
        targetReplicas: 0,
        maxReplicas: 0,
      },
      processPlanRules: {
        targetReplicas: [
          {
            required: true,
            message: i18n.t('请填写实例数'),
            trigger: 'blur',
          },
          {
            regex: /^[1-9][0-9]*$/,
            message: i18n.t('请填写大于0的整数'),
            trigger: 'blur',
          },
          {
            validator(val) {
              return val <= maxReplicasNum;
            },
            message() {
              return `${i18n.t('实例数不能大于最大上限')}${maxReplicasNum}`;
            },
            trigger: 'blur',
          },
        ],
      },
      // 实时日志相关变量
      logDetail: [],
      isLogShow: false,
      isRealTimeOpen: false,
      curOpenLogIndex: -1,
      curProcessType: '',
      curProcessKey: '',
      logInterval: undefined,
      filterKeys: '',
      logIds: {},
      chartSlider: {
        isShow: false,
        title: '',
      },
      tooltipTimer: 0,
      curChartInstance: {
        name: '',
      },
      cpuLine: chartOption.cpu,
      memoryLine: chartOption.memory,
      isChartLoading: true,
      curChartTimeRange: '1h',
      curLogTimeRange: '1h',
      logSelectionList: [
        {
          id: '1h',
          name: i18n.t('最近1小时'),
        },
        {
          id: '6h',
          name: i18n.t('最近6小时'),
        },
        {
          id: '12h',
          name: i18n.t('最近12小时'),
        },
        {
          id: '1d',
          name: i18n.t('最近24小时'),
        },
      ],
      currentClickObj: {
        operateIconTitle: '',
        index: 0,
      },
      prevProcessVersion: 0,
      prevInstanceVersion: 0,
      serverTimeout: 30,
      serverEvent: null,

      timerDisplay: i18n.t('最近1小时'),
      datePickerOption: {
        // 小于今天的都不能选
        disabledDate(date) {
          return date && date.valueOf() > Date.now() - 86400;
        },
      },
      dateParams: {
        start_time: initStartDate,
        end_time: initEndDate,
      },
      dateShortCut,
      initDateTimeRange: [initStartDate, initEndDate],
      isDatePickerOpen: false,
      curTargetReplicas: 0,
      autoscaling: false,
      scalingConfig: {
        minReplicas: '',
        maxReplicas: '',
        metrics: [
          {
            metric: 'cpuUtilization',
            value: '85',
          },
        ],
      },
      scalingRules: null,
      maxReplicasNum: 0,
      minReplicasNum: 0,
      autoScalingTip: {
        theme: 'light',
        allowHtml: true,
        content: this.$t('提示信息'),
        html: `<a target="_blank" href="${
          this.GLOBAL.LINK.BK_APP_DOC
        }topics/paas/paas3_autoscaling" style="color: #3a84ff">${this.$t('查看动态扩缩容计算规则')}</a>`,
        placements: ['right'],
      },
      autoScalDisableConfig: {},
      curTargetMaxReplicas: 0,
      curTargetMinReplicas: 0,
      defaultUtilizationRate: '85%',
      serverEventErrorTimer: 0,
      serverEventEOFTimer: 0,
      instanceEventConfig: {
        isShow: false,
        name: '',
        processName: '',
        instanceName: '',
      },
      logConfig: {
        visiable: false,
        isLoading: false,
        title: '',
        logs: [],
      },
      showFunctionalDependencyDialog: false,
      defaultCondition: '1h',
    };
  },
  computed: {
    envName() {
      return this.environment === 'prod' ? this.$t('生产环境') : this.$t('预发布环境');
    },
    platformFeature() {
      return this.$store.state.platformFeature;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    envEventData() {
      return this.$store.state.envEventData;
    },
    shrinkLimit() {
      return `${(((this.curTargetReplicas - 1) / this.curTargetReplicas) * 85).toFixed(1)}%`;
    },
    isCloudNative() {
      return this.curAppInfo.application?.type === 'cloud_native';
    },
    // 滑框的宽度
    computedWidth() {
      const defaultWidth = 980;
      const maxWidth = window.innerWidth * 0.8;
      return Math.min(defaultWidth, maxWidth);
    },
  },
  watch: {
    $route() {
      this.init();
      this.getAutoScalFlag(); // 切换路由也需要获取featureflag
    },
    'processConfigDialog.visiable'(val) {
      if (val) {
        const that = this;
        this.scalingRules = {
          maxReplicas: [
            {
              required: true,
              message: i18n.t('请填写最大副本数'),
              trigger: 'blur',
            },
            {
              regex: /^[1-9][0-9]*$/,
              message: i18n.t('请填写大于0的整数'),
              trigger: 'blur',
            },
            {
              validator(val) {
                const maxReplicas = Number(val);
                return maxReplicas <= maxReplicasNum;
              },
              message() {
                return `${i18n.t('最大副本数最大值')}${maxReplicasNum}`;
              },
              trigger: 'blur',
            },
            {
              validator(v) {
                const maxReplicas = Number(v);
                const minReplicas = Number(that.scalingConfig.minReplicas);
                return maxReplicas >= minReplicas;
              },
              message() {
                return `${i18n.t('最大副本数不可小于最小副本数')}`;
              },
              trigger: 'blur',
            },
          ],
          minReplicas: [
            {
              required: true,
              message: i18n.t('请填写最小副本数'),
              trigger: 'blur',
            },
            {
              regex: /^[1-9][0-9]*$/,
              message: i18n.t('请填写大于0的整数'),
              trigger: 'blur',
            },
            {
              validator(val) {
                const maxReplicas = Number(val);
                return maxReplicas <= maxReplicasNum;
              },
              message() {
                return `${i18n.t('最小副本数最大值')}${maxReplicasNum}`;
              },
              trigger: 'blur',
            },
            {
              validator(v) {
                const minReplicas = Number(v);
                const maxReplicas = Number(that.scalingConfig.maxReplicas);
                return minReplicas <= maxReplicas;
              },
              message() {
                return `${i18n.t('最小副本数不可大于最大副本数')}`;
              },
              trigger: 'blur',
              message() {
                return `${i18n.t('缩容下限不可大于扩容上限')}`;
              },
              trigger: 'blur',
            },
          ],
        };
      }
    },
    'scalingConfig.maxReplicas'(val) {
      if (val >= this.scalingConfig.minReplicas) {
        this.$refs.scalingConfigForm?.clearError();
      }
    },
    'scalingConfig.minReplicas'(val) {
      if (val <= this.scalingConfig.maxReplicas) {
        this.$refs.scalingConfigForm?.clearError();
      }
    },
    autoscaling() {
      this.$refs.processConfigForm?.clearError();
      this.$refs.scalingConfigForm?.clearError();
    },
  },
  created() {
    // moment日期中英文显示
    moment.locale(this.localLanguage);
    this.init();
    // 切换路由前清空定时器
    this.$router.beforeEach((to, from, next) => {
      this.closeServerPush();
      next();
    });
    this.isDateChange = false;
    this.getAutoScalFlag();
  },
  beforeDestroy() {
    this.closeServerPush();
    this.closeLogDetail();
  },
  methods: {
    init() {
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/envs/${this.environment}/released_state/`;

      this.$http.get(url).then(
        (res) => {
          if (res.offline) {
            this.isAppOfflined = true;
          } else {
            this.isAppOfflined = false;
          }
          this.getProcessList();
        },
        (res) => {
          this.allProcesses = [];
          this.$emit('data-ready', this.environment);
        }
      );
    },

    handlerChange(dates) {
      this.dateParams.start_time = dates[0];
      this.dateParams.end_time = dates[1];
      this.dateParams.time_range = timeRangeCache || 'customized';
      if (timeShortCutText) {
        this.timerDisplay = timeShortCutText;
      } else {
        this.timerDisplay = `${dates[0]} - ${dates[1]}`;
      }
      this.isDateChange = true;
      timeShortCutText = ''; // 清空
      timeRangeCache = ''; // 清空
    },

    hideDatePicker() {
      this.isDatePickerOpen = false;
    },

    handlerPickSuccess() {
      this.isDatePickerOpen = false;
      if (this.isDateChange) {
        this.getInstanceChart(this.curProcess);
        this.isDateChange = false;
      }
    },

    toggleDatePicker() {
      this.isDatePickerOpen = !this.isDatePickerOpen;
    },

    clearTooltipTimer(process, type = '') {
      clearTimeout(this.tooltipTimer);
      if (type === 'show') {
        process.isShowTooltipConfirm = true;
      }
      if (process.isShowTooltipConfirm) {
        process.operateIconTitle = '';
      } else {
        if (!process.operateIconTitle) {
          process.operateIconTitle = process.operateIconTitleCopy;
        }
      }
    },

    hideTooltipConfirm(process) {
      clearTimeout(this.tooltipTimer);
      this.tooltipTimer = setTimeout(() => {
        this.$refs.tooltipConfirm.forEach((tooltip) => {
          tooltip.cancel();
        });
        process.isShowTooltipConfirm = false;
        if (!process.operateIconTitle) {
          process.operateIconTitle = process.operateIconTitleCopy;
        }
      }, 300);
    },

    closeProcess(process) {
      process.isShowTooltipConfirm = false;
      process.operateIconTitle = process.operateIconTitleCopy;
    },

    confirmClick(process) {
      process.isShowTooltipConfirm = !process.isShowTooltipConfirm;
      if (process.isShowTooltipConfirm) {
        process.operateIconTitle = '';
      } else {
        process.operateIconTitle = process.operateIconTitleCopy;
      }
    },

    /**
     * 展示实例日志侧栏
     * @param {Object} instance 实例对象
     */
    showInstanceLog(instance, process) {
      this.curInstance = instance;
      this.logConfig.visiable = true;
      this.logConfig.isLoading = true;
      this.logConfig.params = {
        appCode: this.appCode,
        moduleId: this.curModuleId,
        env: this.environment,
        processType: process.name,
        instanceName: instance.name,
      };
      this.logConfig.title = `${this.$t('实例')} ${this.curInstance.display_name}${this.$t('控制台输出日志')}`;
      this.$nextTick(() => {
        this.loadInstanceLog();
      });
    },

    getParams() {
      return {
        start_time: '',
        end_time: '',
        time_range: this.curLogTimeRange,
        log_type: 'STANDARD_OUTPUT',
      };
    },

    /**
     * 构建过滤参数
     */
    getFilterParams() {
      const params = {
        query: {
          terms: {},
        },
      };

      params.query.terms.pod_name = [this.curInstance.name];
      params.query.terms.environment = [this.environment];

      return params;
    },

    /**
     * 加载实例日志
     */
    async loadInstanceLog() {
      try {
        const { appCode } = this;
        const moduleId = this.curModuleId;
        const params = this.getParams();
        const filter = this.getFilterParams();

        const res = await this.$store.dispatch('log/getStreamLogList', {
          appCode,
          moduleId,
          params,
          filter,
        });
        const data = res.logs.reverse();
        data.forEach((item) => {
          item.podShortName = item.pod_name.split('-').reverse()[0];
        });
        this.logConfig.logs = data;
      } catch (e) {
        this.logConfig.logs = [];
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.logConfig.isLoading = false;
      }
    },

    /**
     * 显示进程实例列表
     * @param {Object} data 进程
     */
    showProcessDetail(data) {
      // 当前项折叠
      if (data.name === this.curProcessKey) {
        this.curProcess = {
          instances: [],
        };
        this.curProcessKey = '';
        return false;
      }
      this.curProcessKey = data.name;
      this.curProcess = data;
    },

    // 查看访问控制台文档
    gotoMore() {
      window.open(this.GLOBAL.DOC.WEB_CONSOLE, '_blank');
    },

    /**
     * 显示进程webConsole
     * @param {Object} instance, processes
     */
    async showInstanceConsole(instance, processes) {
      // 暂无访问控制台功能
      if (!this.platformFeature.WEB_CONSOLE) {
        this.showFunctionalDependencyDialog = true;
        return;
      }
      this.processRefuseDialog.isLoading = true;
      try {
        const params = {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
          instanceName: instance.name,
          processType: processes.name,
        };
        const res = await this.$store.dispatch('processes/getInstanceConsole', params);
        if (res.web_console_url) {
          window.open(res.web_console_url);
        }
      } catch (e) {
        if (e.status === 403) {
          this.processRefuseDialog.visiable = true;
          this.processRefuseDialog.isLoading = false;
          this.processRefuseDialog.description = e.description;
          this.processRefuseDialog.title = e.title;
          this.processRefuseDialog.link = e.link;
        } else {
          this.$paasMessage({
            theme: 'error',
            message: e.detail || e.message || this.$t('接口异常'),
          });
        }
      }
    },

    /**
     * 图表初始化
     * @param  {Object} instanceData 数据
     * @param  {String} type 类型
     * @param  {Object} ref 图表对象
     */
    renderChartNew(instanceData, type, ref) {
      const series = [];
      let xAxisData = [];
      instanceData.forEach((item) => {
        const chartData = [];
        xAxisData = [];
        item.results.forEach((itemData) => {
          xAxisData.push(moment(itemData[0] * 1000).format('MM-DD HH:mm'));
          // 内存由Byte转MB
          if (type === 'mem') {
            const dataMB = Math.ceil(itemData[1] / 1024 / 1024);
            chartData.push(dataMB);
          } else {
            chartData.push(itemData[1]);
          }
        });

        if (item.type_name === 'current') {
          series.push({
            name: item.display_name,
            type: 'line',
            smooth: true,
            symbol: 'none',
            areaStyle: {
              normal: {
                opacity: 0.2,
              },
            },
            data: chartData,
          });
        } else {
          series.push({
            name: item.display_name,
            type: 'line',
            smooth: true,
            symbol: 'none',
            lineStyle: {
              normal: {
                width: 1,
                type: 'dashed',
              },
            },
            areaStyle: {
              normal: {
                opacity: 0,
              },
            },
            data: chartData,
          });
        }
      });

      ref.mergeOptions({
        xAxis: [
          {
            data: xAxisData,
          },
        ],
        series,
      });
    },

    async fetchMetric(conf) {
      // 请求数据
      const fetchData = (type, processType) => {
        const params = {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
          metric_type: type,
          // time_range_str: this.curChartTimeRange,
          process_type: processType,
          start_time: this.dateParams.start_time,
          end_time: this.dateParams.end_time,
        };
        return this.$store.dispatch('processes/getInstanceMetrics', params);
      };
      // 数据处理
      const getData = (payload) => {
        const datas = [];
        let limitDatas = null;
        payload.result.forEach((instance) => {
          const instanceName = instance.display_name;
          instance.results.forEach((item) => {
            const dataList = item.results;

            if (item.type_name === 'cpu') {
              dataList.forEach((data) => {
                if (data.type_name === 'current') {
                  data.display_name = `${instanceName}-${data.display_name}`;
                  datas.push(data);
                } else if (data.type_name === 'limit') {
                  limitDatas = data;
                }
              });
            } else {
              dataList.forEach((data) => {
                if (data.type_name === 'current') {
                  data.display_name = `${instanceName}-${data.display_name}`;
                  datas.push(data);
                } else if (data.type_name === 'limit') {
                  limitDatas = data;
                }
              });
            }
          });
        });
        limitDatas && datas.unshift(limitDatas);
        return datas;
      };
      try {
        const res = await Promise.all([fetchData('cpu', conf.processes.name), fetchData('mem', conf.processes.name)]);
        const [res1, res2] = res;
        const cpuData = getData(res1);
        const memData = getData(res2);
        this.renderChartNew(cpuData, 'cpu', conf.cpuRef);
        this.renderChartNew(memData, 'mem', conf.memRef);
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
        this.clearChart();
      } finally {
        this.isChartLoading = false;
        conf.cpuRef?.hideLoading();
        conf.memRef?.hideLoading();
      }
    },

    /**
     * 从接口获取Metric 数据
     * @param {Object} conf 配置参数
     */
    async getInstanceMetric(conf) {
      this.isChartLoading = true;
      try {
        const params = {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
          process_type: conf.processes.name,
          instance_name: conf.instance.name,
          time_range_str: this.curChartTimeRange,
        };
        const res = await this.$store.dispatch('processes/getInstanceMetrics', params);
        res.result.forEach((item) => {
          this.renderChart(item.results, item.type_name, conf[`${item.type_name}Ref`]);
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
        this.clearChart();
      } finally {
        this.isChartLoading = false;
        conf.cpuRef.hideLoading();
        conf.memRef.hideLoading();
      }
    },

    /**
     * 图表初始化
     * @param  {Object} instanceData 数据
     * @param  {String} type 类型
     * @param  {Object} ref 图表对象
     */
    renderChart(instanceData, type, ref) {
      const series = [];
      let xAxisData = [];
      instanceData.forEach((item) => {
        const chartData = [];
        xAxisData = [];
        item.results.forEach((itemData) => {
          xAxisData.push(moment(itemData[0] * 1000).format('MM-DD HH:mm'));
          // 内存由Byte转MB
          if (type === 'mem') {
            const dataMB = Math.ceil(itemData[1] / 1024 / 1024);
            chartData.push(dataMB);
          } else {
            chartData.push(itemData[1]);
          }
        });

        if (item.type_name === 'current') {
          series.push({
            name: item.display_name,
            type: 'line',
            smooth: true,
            symbol: 'none',
            areaStyle: {
              normal: {
                opacity: 0.2,
              },
            },
            data: chartData,
          });
        } else {
          series.push({
            name: item.display_name,
            type: 'line',
            smooth: true,
            symbol: 'none',
            lineStyle: {
              normal: {
                width: 2,
                type: 'dotted',
              },
            },
            areaStyle: {
              normal: {
                opacity: 0,
              },
            },
            data: chartData,
          });
        }
      });

      ref.mergeOptions({
        xAxis: [
          {
            data: xAxisData,
          },
        ],
        series,
      });
    },

    /**
     * 图标侧栏隐藏回调处理
     */
    handlerChartHide() {
      this.dateParams = Object.assign(
        {},
        {
          start_time: initStartDate,
          end_time: initEndDate,
        }
      );
      this.initDateTimeRange = [initStartDate, initEndDate];
      this.isDatePickerOpen = false;
      this.clearChart();
    },

    /**
     * 清空图表数据
     */
    clearChart() {
      const cpuRef = this.$refs.cpuLine;
      const memRef = this.$refs.memoryLine;

      cpuRef &&
        cpuRef.mergeOptions({
          xAxis: [
            {
              data: [],
            },
          ],
          series: [
            {
              name: '',
              type: 'line',
              smooth: true,
              symbol: 'none',
              areaStyle: {
                normal: {
                  opacity: 0,
                },
              },
              data: [0],
            },
          ],
        });

      memRef &&
        memRef.mergeOptions({
          xAxis: [
            {
              data: [],
            },
          ],
          series: [
            {
              name: '',
              type: 'line',
              smooth: true,
              symbol: 'none',
              areaStyle: {
                normal: {
                  opacity: 0,
                },
              },
              data: [0],
            },
          ],
        });
    },

    // 对数据进行处理
    formatProcesses(processesData) {
      this.allProcesses = [];

      // 保存上次的版本号
      this.prevProcessVersion = processesData.processes.metadata.resource_version;
      this.prevInstanceVersion = processesData.instances.metadata.resource_version;

      // 遍历进行数据组装
      const extraInfos = processesData.processes.extra_infos;
      const packages = processesData.process_packages;
      const instances = processesData.instances.items;

      processesData.processes.items.forEach((processItem) => {
        const { type, name: processName } = processItem;
        const extraInfo = extraInfos.find((item) => item.type === type);
        const packageInfo = packages.find((item) => item.name === type);

        const processInfo = {
          ...processItem,
          ...packageInfo,
          ...extraInfo,
          instances: [],
        };

        instances.forEach((instance) => {
          if (instance.process_type === type) {
            processInfo.instances.push(instance);
          }
        });

        // 状态设置
        let operateIconTitle = this.$t('停止进程');
        if (processInfo.instances.length === 0) {
          operateIconTitle = this.$t('启动进程');
        }
        if (this.isAppOfflined) {
          operateIconTitle = this.$t('模块已下架，不可操作');
        }

        // 作数据转换，以兼容原逻辑
        const process = {
          name: processInfo.name,
          instance: processInfo.instances.length,
          instances: processInfo.instances,
          targetReplicas: processInfo.target_replicas,
          isStopTrigger: false,
          targetStatus: processInfo.target_status,
          isActionLoading: false, // 用于记录进程启动/停止接口是否已完成
          maxReplicas: processInfo.max_replicas,
          status: 'Stopped',
          cmd: processInfo.command,
          operateIconTitle,
          operateIconTitleCopy: operateIconTitle,
          isShowTooltipConfirm: false,
          desired_replicas: processInfo.replicas,
          available_instance_count: processInfo.success,
          failed: processInfo.failed,
          resourceLimit: processInfo.resource_limit,
          clusterLink: processInfo.cluster_link,
          scalingConfig: processInfo.scaling_config,
          autoscaling: processInfo.autoscaling,
          processName,
        };

        this.updateProcessStatus(process);

        // 日期转换
        process.instances.forEach((item) => {
          item.date_time = moment(item.start_time).startOf('minute').fromNow();
        });

        // 如果有当前展开项
        if (this.curProcessKey && this.curProcessKey === processInfo.name) {
          this.curProcess = process;
        }

        this.allProcesses.push(process);
      });

      return this.allProcesses;
    },

    updateProcessStatus(process) {
      /*
       * 设置进程状态
       * targetStatus: 进行的操作，start\stop\scale
       * status: 操作状态，Running\stoped
       *
       * 如何判断进程当前是否为操作中（繁忙状态）？
       * 主要根据 process_packages 里面的 target_status 判断：
       * 如果 target_status 为 stop，仅当 processes 里面的 success 为 0 且实例为 0 时正常，否则为操作中
       * 如果 target_status 为 start，仅当 success 与 target_replicas 一致，而且 failed 为 0 时正常，否则为操作中
       */
      if (process.targetStatus === 'stop') {
        process.operateIconTitle = this.$t('启动进程');
        process.operateIconTitleCopy = this.$t('启动进程');
        if (process.available_instance_count === 0 && process.instances.length === 0) {
          process.status = 'Stopped';
        } else {
          process.status = 'Running';
        }
      } else if (process.targetStatus === 'start') {
        process.operateIconTitle = this.$t('停止进程');
        process.operateIconTitleCopy = this.$t('停止进程');
        if (process.available_instance_count === process.targetReplicas && process.failed === 0) {
          process.status = 'Stopped';
        } else {
          process.status = 'Running';
        }
      }
    },

    watchServerPush() {
      if (this.envEventData.includes(this.environment)) return;
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/envs/${this.environment}/processes/watch/?rv_proc=${this.prevProcessVersion}&rv_inst=${this.prevInstanceVersion}&timeout_seconds=${this.serverTimeout}`;
      this.serverEvent = new EventSource(url, {
        withCredentials: true,
      });
      this.$store.commit('updataEnvEventData', [this.environment]);

      // 收藏服务推送消息
      this.serverEvent.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(this.$t('接受到推送'), data);
        if (data.object_type === 'process') {
          this.updateProcessData(data);
        } else if (data.object_type === 'instance') {
          this.updateInstanceData(data);
        } else if (data.type === 'ERROR') {
          // 判断 event.type 是否为 ERROR 即可，如果是 ERROR，就等待 2 秒钟后，重新发起 list/watch 流程
          clearTimeout(this.timer);
          this.timer = setTimeout(() => {
            this.getProcessList();
          }, 2000);
        }
      };

      // 服务异常
      this.serverEvent.onerror = (event) => {
        // 异常后主动关闭，否则会继续重连
        console.error(this.$t('推送异常'), event);
        this.serverEvent.close();

        clearTimeout(this.serverEventErrorTimer);
        // 推迟调用，防止过于频繁导致服务性能问题
        this.serverEventErrorTimer = setTimeout(() => {
          this.$store.commit('updataEnvEventData', []);
          this.watchServerPush();
        }, 10000);
      };

      // 服务结束
      this.serverEvent.addEventListener('EOF', (event) => {
        console.log(this.$t('推送结束发起重连'), event);
        this.serverEvent.close();

        clearTimeout(this.serverEventEOFTimer);
        // 推迟调用，防止过于频繁导致服务性能问题
        this.serverEventEOFTimer = setTimeout(() => {
          this.$store.commit('updataEnvEventData', []);
          this.watchServerPush();
        }, 10000);
      });
    },

    // 更新进程
    updateProcessData(data) {
      const processData = data.object || {};
      this.prevProcessVersion = data.resource_version || 0;

      if (data.type === 'ADDED') {
        this.getProcessList();
      } else if (data.type === 'MODIFIED') {
        this.allProcesses.forEach((process) => {
          if (process.name === processData.type) {
            process.available_instance_count = processData.success;
            process.desired_replicas = processData.replicas;
            process.failed = processData.failed;
            this.updateProcessStatus(process);
          }
        });
      } else if (data.type === 'DELETED') {
        this.allProcesses = this.allProcesses.filter((process) => process.name !== processData.type);
      }
    },

    // 更新实例
    updateInstanceData(data) {
      const instanceData = data.object || {};
      this.prevInstanceVersion = data.resource_version || 0;

      instanceData.date_time = moment(instanceData.start_time).startOf('minute').fromNow();
      this.allProcesses.forEach((process) => {
        if (process.name === instanceData.process_type) {
          // 新增
          if (data.type === 'ADDED') {
            // 防止在短时间内重复推送
            process.instances.forEach((instance, index) => {
              if (instance.name === instanceData.name) {
                process.instances.splice(index, 1);
              }
            });
            process.instances.push(instanceData);
          } else {
            process.instances.forEach((instance, index) => {
              if (instance.name === instanceData.name) {
                if (data.type === 'DELETED') {
                  // 删除
                  process.instances.splice(index, 1);
                } else {
                  // 更新
                  process.instances.splice(index, 1, instanceData);
                }
              }
            });
          }
          this.updateProcessStatus(process);
        }
      });
    },

    closeServerPush() {
      // 把当前服务监听关闭
      if (this.serverEvent) {
        this.serverEvent.close();
      }
    },

    // 获取进程列表
    async getProcessList(callback) {
      this.closeServerPush();
      try {
        const res = await this.$store.dispatch('processes/getProcesses', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
        });
        const processes = this.formatProcesses(res);
        callback && callback(processes);

        // 发起服务监听
        this.$store.commit('updataEnvEventData', []);
        this.watchServerPush();
      } catch (e) {
        // 无法获取进程目前状态
        this.$paasMessage({
          theme: 'error',
          message: this.$t('查询进程状态失败，请稍后再试。'),
        });
      } finally {
        this.$emit('data-ready', this.environment);
      }
    },

    showProcessConfigDialog(process) {
      if (this.isAppOfflined) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('模块已下架，不可操作'),
        });
        return false;
      }

      maxReplicasNum = process.maxReplicas;
      this.maxReplicasNum = maxReplicasNum;
      this.minReplicasNum = this.environment === 'prod' ? 2 : 1;
      this.processPlan = {
        replicas: process.instances.length,
        processType: process.name,
        targetReplicas: process.available_instance_count,
        maxReplicas: process.maxReplicas,
        status: process.status,
      };

      this.scalingConfig.maxReplicas = process?.scalingConfig?.max_replicas || this.maxReplicasNum;
      this.scalingConfig.minReplicas = process?.scalingConfig?.min_replicas || this.minReplicasNum;
      this.curTargetMaxReplicas = this.scalingConfig.maxReplicas;
      this.curTargetMinReplicas = this.scalingConfig.minReplicas;
      this.processConfigDialog.visiable = true;
      this.processConfigDialog.showForm = true;
      this.autoscaling = process.autoscaling;
      this.curTargetReplicas = this.processPlan.targetReplicas;
    },

    showProcessDetailDialog(process) {
      this.processPlan = {
        replicas: process.instance,
        processType: process.name,
        targetReplicas: process.targetReplicas,
        maxReplicas: process.maxReplicas,
        status: process.status,
        cpuLimit: this.transfer_cpu_unit(process.resourceLimit.cpu),
        memLimit: process.resourceLimit.memory,
        clusterLink: process.clusterLink,
      };
      this.curProcess = process;
      this.curProcessKey = process.name;
      this.chartSlider.title = `${this.$t('进程')} ${process.name}${this.$t('详情')}`;
      this.chartSlider.isShow = true;
      this.initSidebarFormData(this.initDateTimeRange);
      if (this.platformFeature.RESOURCE_METRICS) {
        this.getInstanceChart(process);
      }
    },

    /**
     * 显示实例指标数据
     */
    getInstanceChart(processes) {
      this.$nextTick(() => {
        const cpuRef = this.$refs.cpuLine;
        const memRef = this.$refs.memoryLine;

        cpuRef &&
          cpuRef.mergeOptions({
            xAxis: [
              {
                data: [],
              },
            ],
            series: [],
          });

        memRef &&
          memRef.mergeOptions({
            xAxis: [
              {
                data: [],
              },
            ],
            series: [],
          });

        cpuRef &&
          cpuRef.showLoading({
            text: this.$t('正在加载'),
            color: '#30d878',
            textColor: '#fff',
            maskColor: 'rgba(255, 255, 255, 0.8)',
          });

        memRef &&
          memRef.showLoading({
            text: this.$t('正在加载'),
            color: '#30d878',
            textColor: '#fff',
            maskColor: 'rgba(255, 255, 255, 0.8)',
          });

        // this.getInstanceMetric({
        //     cpuRef: cpuRef,
        //     memRef: memRef,
        //     instance: instance,
        //     processes: processes
        // })

        this.fetchMetric({
          cpuRef,
          memRef,
          processes,
        });
      });
    },

    transfer_cpu_unit(cpuLimit) {
      if (cpuLimit.endsWith('m')) {
        cpuLimit = parseInt(/^\d+/.exec(cpuLimit)) / 1000;
      }
      return cpuLimit + this.$t('核');
    },

    saveProcessConfig() {
      this.processConfigDialog.isLoading = true;
      setTimeout(async () => {
        try {
          const manualValidate = await this.$refs?.processConfigForm?.validate();
          const autoValidate = await this.$refs?.scalingConfigForm?.validate();
          if (!this.autoscaling && manualValidate) {
            this.processConfigDialog.isLoading = false;
            this.processConfigDialog.visiable = false;
            this.$store.commit('updataEnvEventData', []);
            this.updateProcessConfig();
          }
          if (this.autoscaling && autoValidate) {
            this.processConfigDialog.isLoading = false;
            this.processConfigDialog.visiable = false;
            this.$store.commit('updataEnvEventData', []);
            this.updateProcessConfig();
          }
        } catch (error) {
          this.processConfigDialog.isLoading = false;
        }
      });
    },

    closeProcessConfig() {
      this.processConfigDialog.visiable = false;
    },

    afterCloseProcessConfig() {
      this.processConfigDialog.showForm = false;
      this.autoscaling = false;
      this.scalingConfig.minReplicas = '';
      this.scalingConfig.maxReplicas = '';
    },

    // 进程实例设置
    async updateProcessConfig() {
      // 不允许小于1或者大于最大值，如果没有改变也不允许操作
      if (
        !this.autoscaling &&
        (this.processPlan.targetReplicas < 1 ||
          this.processPlan.targetReplicas > this.processPlan.maxReplicas ||
          this.processPlan.targetReplicas === this.processPlan.replicas)
      ) {
        return;
      }

      const { processType } = this.processPlan;
      const planForm = {
        process_type: processType,
        operate_type: 'scale',
        target_replicas: this.processPlan.targetReplicas,
        autoscaling: this.autoscaling,
        scaling_config: {
          min_replicas: this.scalingConfig.minReplicas,
          max_replicas: this.scalingConfig.maxReplicas,
          metrics: this.scalingConfig.metrics,
        },
      };
      this.pendingProcessList.push(processType);

      try {
        await this.$store.dispatch('processes/updateProcess', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
          data: planForm,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('扩缩容策略已更新'),
        });
      } catch (err) {
        this.$paasMessage({
          theme: 'error',
          message: err.message,
        });
      } finally {
        this.getProcessList();
      }
    },

    // 进程启动和停止操作
    patchProcess(process, index) {
      // 停止操作
      if (process.targetStatus === 'start') {
        process.isStopTrigger = true;
        this.currentClickObj = Object.assign(
          {},
          {
            operateIconTitle: process.operateIconTitle,
            index,
          }
        );
      } else {
        // 启动操作
        this.updateProcess(process, index);
      }
    },

    async updateProcess(process, index) {
      // 判断上次操作是否结束
      if (process.isActionLoading) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('进程操作过于频繁，请间隔 3 秒再试'),
        });
        return false;
      }
      process.isActionLoading = true;

      // 判断是否已经下架
      if (this.isAppOfflined) {
        return false;
      }

      process.isShowTooltipConfirm = false;
      if (!process.operateIconTitle) {
        process.operateIconTitle = process.operateIconTitleCopy;
      }

      this.currentClickObj = Object.assign(
        {},
        {
          operateIconTitle: process.operateIconTitle,
          index,
        }
      );

      const processType = process.name;
      const { targetStatus } = process;
      const patchForm = {
        process_type: processType,
        operate_type: targetStatus === 'start' ? 'stop' : 'start',
      };

      try {
        await this.$store.dispatch('processes/updateProcess', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
          data: patchForm,
        });

        // 更新当前操作状态
        if (targetStatus === 'start') {
          process.targetStatus = 'stop';
        } else {
          process.targetStatus = 'start';
        }
      } catch (err) {
        this.$paasMessage({
          theme: 'error',
          message: err.message,
        });
      } finally {
        this.getProcessList();
        process.isActionLoading = false;
      }
    },

    // 切换tab时关闭实时日志
    closeLogDetail() {
      clearInterval(this.logInterval);
      this.isLogShow = false;
      this.curOpenLogIndex = -1;
    },

    // 实时滚动开关
    toggleRealTimeLog() {
      this.isRealTimeOpen = !this.isRealTimeOpen;
      if (!this.isRealTimeOpen) {
        clearInterval(this.logInterval);
      } else {
        clearInterval(this.logInterval);
        if (this.filterKeys !== '') {
          this.realTimeLogScroll(this.filterKeys);
        } else {
          this.realTimeLogScroll();
        }
      }
    },

    handleLogsFilter() {
      // 进程过滤事件
      clearInterval(this.logInterval);
      this.isRealTimeOpen = true;
      this.realTimeLogScroll(this.filterKeys);
    },

    realTimeLogScroll(key) {
      // 开启实时日志后, 保证勾选框状态一致性
      this.isLogShow = true;
      this.logInterval = setInterval(() => {
        let curParams;
        if (key) {
          curParams = {
            process_type: this.curProcessType,
            keyword: key,
          };
        } else {
          curParams = {
            process_type: this.curProcessType,
          };
        }
        this.$http
          .get(
            `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/envs/${this.environment}/realtimelogs/`,
            { params: curParams }
          )
          .then((res) => {
            const logInfo = res;
            // 实时日志数等于上一次请求则无新日志产生 不追加
            // if(logInfo.count == countNum) return;
            // countNum = logInfo.count;
            // 不能用数量, 也不能用lastItemId判定(es查询出来排序可能两次之间会变, 但是lastItemId不变-时间精度只到s)
            if (logInfo.count > 0) {
              logInfo.results.forEach((item) => {
                // 追加ID不重复日志
                if (!(item.id in this.logIds)) {
                  this.logIds[item.id] = undefined;
                  const htmlItem = this.keyLight(item);
                  this.logDetail.push(htmlItem);
                }
              });
              setTimeout(() => {
                const currentHeight = $('.textarea .inner').height() + 100;
                $('.textarea').scrollTop(currentHeight);
              }, 0);
            }
          });
      }, 1000);
    },

    // 实时日志列表 时间 | 进程名 高亮
    keyLight(item) {
      const text =
        `<span style="color: #4491e1">[${item.ts}]</span>` +
        ` <span style="color: #ffa65f">${item.process_name}</span>: ${item.message}`;
      return text;
    },

    // 获取进程状态 tooltips 展示内容
    getInstanceStateToolTips(instance) {
      if (!(instance.state_message && instance.state_message.length)) {
        return instance.rich_status;
      }
      return instance.state_message;
    },

    async getAutoScalFlag() {
      try {
        const res = await this.$store.dispatch('deploy/getAutoScalFlagWithEnv', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
        });
        this.autoScalDisableConfig = res;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    handleAutoChange() {
      // 切换tab 数据重置
      this.processPlan.targetReplicas = this.curTargetReplicas;
      this.scalingConfig.maxReplicas = this.curTargetMaxReplicas;
      this.scalingConfig.minReplicas = this.curTargetMinReplicas;
    },

    showInstanceEvents(instance, process) {
      this.instanceEventConfig.isShow = true;
      this.instanceEventConfig.name = instance.display_name;
      this.instanceEventConfig.processName = process.name;
      this.instanceEventConfig.instanceName = instance.name;
    },

    handleClose() {
      this.logConfig.visiable = false;
      this.defaultCondition = '1h';
      this.logConfig.logs = [];
    },

    // 刷新日志
    refreshLogs(data) {
      this.$set(this.logConfig, 'isLoading', true);
      if (data.type === 'realtime') {
        this.curLogTimeRange = data.value;
        this.loadInstanceLog();
      } else {
        this.getPreviousLogs();
      }
    },

    // 重启日志
    async getPreviousLogs() {
      try {
        const logs = await this.$store.dispatch('log/getPreviousLogs', this.logConfig.params);
        this.logConfig.logs = logs;
      } catch (e) {
        this.logConfig.logs = [];
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.logConfig.isLoading = false;
      }
    },

    // 下载日志
    async downloadInstanceLog(type) {
      if (type === 'realtime') {
        return;
      }
      const { params } = this.logConfig;
      try {
        const logs = await this.$store.dispatch('log/downloadPreviousLogs', {
          ...params,
        });
        if (!logs || !logs?.length) {
          this.$paasMessage({
            theme: 'warning',
            message: this.$t('暂时没有日志记录'),
          });
          return;
        }
        downloadTxt(logs, params.instanceName);
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },

    // 重启进程、实例弹窗
    showRestartPopup(type, row) {
      const restartInstance = type === 'instance';
      this.$bkInfo({
        title: restartInstance ? this.$t('确认重启当前实例？') : this.$t('确认滚动重启当前进程下所有实例？'),
        confirmFn: () => {
          if (restartInstance) {
            this.handleRestartInstance(row);
          } else {
            this.handleRestartProcess(row);
          }
        },
      });
    },

    // 重启进程
    async handleRestartProcess(row) {
      try {
        await this.$store.dispatch('processes/restartProcess', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
          processName: row.processName,
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 重启实例
    async handleRestartInstance(instance) {
      try {
        await this.$store.dispatch('processes/restartInstance', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
          instanceName: instance.name,
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
  },
};
</script>

<style lang="scss" scoped>
@import '~@/assets/css/mixins/ellipsis.scss';
.process-table-wrapper {
  &.reset-style {
    border: 1px solid #dcdee5;
  }
  .process-item {
    margin-bottom: 10px;
  }
  .process-item-header {
    line-height: 18px;
    font-size: 12px;
    color: #63656e;
    border: solid 1px #dcdee5;
    background: #fff;
    display: flex;
    justify-content: space-between;
    .process-basic-info {
      display: flex;
      padding: 16px 0 0px 24px;
      width: 230px;
      vertical-align: middle;
      cursor: pointer;
      .expanded-icon {
        position: relative;
        top: 8px;
        margin-right: 10px;
        color: #979ba5;
        &:hover {
          color: #3a84ff;
        }
      }
      .process-name {
        display: inline-block;
        max-width: 150px;
        color: #313238;
        font-weight: bold;
        font-size: 14px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        padding-top: 3px;
      }
      .auto-scal {
        width: 76px;
        height: 22px;
        line-height: 22px;
        background: #e4faf0;
        border-radius: 2px;
        color: #14a568;
        font-size: 12px;
        text-align: center;
        margin-left: 8px;
      }
    }
    .instance-count {
      padding-left: 56px;
    }
    .process-command {
      width: 490px;
      cursor: pointer;
      min-height: 75px;
      display: flex;
      align-items: center;

      p {
        @include multiline-ellipsis;
      }
    }

    .process-status {
      display: inline-block;
      padding: 26px 0 0 0;

      img,
      span {
        vertical-align: middle;
        margin-right: 3px;
      }
    }

    .status-container {
      width: 260px;
      .process-operate {
        position: relative;
        display: inline-block;
        padding: 24px 0 0 0;
        margin-right: 27px;
        width: 55px;
        vertical-align: middle;
        float: right;
        .icon-info-base {
          font-size: 24px;
        }
        .icon-info-l {
          position: absolute;
          left: -45px;
          top: 21px;
        }
        .icon-info-d {
          position: absolute;
          left: -90px;
          top: 21px;
        }
        .a-more {
          position: relative;
          top: 0;
          left: 10px;
          .paasng-icon-more {
            font-size: 24px;
          }
          &:hover {
            .paasng-icon-more:before {
              color: #3a84ff !important;
            }
          }
        }
      }
    }
  }

  .ps-table-special {
    thead {
      th {
        border-top: none !important;
        border-right: none !important;
      }
    }
  }

  .process-item-table {
    background: #fff;
    border-right: 1px solid #dcdee5;
    border-bottom: 1px solid #dcdee5;
    border-left: 1px solid #dcdee5;

    .header-shadow {
      width: 100%;
      height: 5px;
      background: linear-gradient(180deg, rgba(99, 101, 110, 1) 0%, rgba(99, 101, 110, 0) 100%);
      opacity: 0.05;
    }

    .process-item-table-wrapper {
      padding: 0 30px !important;
      .ps-table {
        td {
          font-size: 12px;
        }
      }
    }

    td {
      box-sizing: border-box;
    }

    .instance-textarea {
      border: none;
      border-radius: 0;
    }

    .name {
      width: 130px;

      > p {
        max-width: 300px;
        display: inline-block;
        color: #63656e;
        text-overflow: ellipsis;
        overflow: hidden;
        white-space: nowrap;
        vertical-align: middle;
      }
    }

    .run-state {
      > p {
        max-width: 300px;
        display: inline-block;
        text-overflow: ellipsis;
        overflow: hidden;
        white-space: nowrap;
        vertical-align: middle;
      }

      .paasng-icon {
        position: relative;
        top: 1px;
        margin-right: 2px;
        &.paasng-check-circle {
          color: #5bd18b;
        }
        &.paasng-empty {
          color: #ff6669;
        }
      }
    }

    .operate-container {
      width: 280px;

      .ps-icon-btn {
        float: none;

        &.on {
          background: #3a84ff;
          border: solid 1px #3a84ff;
          color: #fff;
        }
      }
    }
  }
}

.ps-table {
  thead {
    th {
      background-color: #fff;
      font-weight: bold;
      font-size: 12px;
    }
  }

  tbody {
    tr {
      td {
        border-bottom: 1px solid #e6e9ea;
      }
    }
    tr {
      &:last-child {
        td {
          border-bottom: none;
        }
      }
    }
  }
}
.ps-instances-table {
  width: 100%;

  &.ps-table th,
  &.ps-table td {
    line-height: 24px;
    // padding: 8px 24px;
    position: relative;
  }
}

.realtime-log-icon {
  cursor: not-allowed;

  &.on {
    cursor: pointer;
  }
}

.operate-process-icon {
  display: flex;
  justify-content: center;
  align-items: center;
  border-radius: 50%;
  .loading {
    display: none;
    margin-top: 2px;
  }

  &.disabled {
    background-color: #fff !important;
    border: solid 1px #e9edee !important;
    cursor: not-allowed;

    i {
      background-position: 1px -24px !important;
    }
  }

  &.is-loading {
    background-color: #fff !important;
    border: solid 1px #e9edee !important;
    cursor: default;

    i {
      display: none;
    }

    .loading {
      display: inline-block;
    }
  }
}

.link-input {
  height: 30px;
}

.operate-process-icon i,
.realtime-log-icon i {
  display: inline-block;
  overflow: hidden;
  width: 10px;
  height: 12px;
  background: url('/static/images/instance-icon2.png') no-repeat;
}

.operate-process-icon i {
  background-position: 0 -85px;
}

.operate-process-icon {
  position: relative;

  .upLoading {
    position: absolute;
    left: -1px;
    top: -1px;
    line-height: 18px !important;
    padding: 0;
    width: 24px;
    height: 24px;
    text-align: center;
    background: rgba(255, 255, 255, 0.5);

    img {
      width: 16px;
      height: 16px;
      display: inline-block;
      margin: 4px;
    }
  }
}

.operate-process-icon .square-icon {
  width: 10px;
  height: 10px;
  background: #ea3636;
  border-radius: 1px;
}

.operate-process-icon:hover {
  background-color: #ea3636;
  & .square-icon {
    background-color: #fff;
  }
}

.operate-process-icon:hover i {
  background-position: 0 0;
}

.operate-process-icon.on i {
  background-position: 1px -42px;
}

.operate-process-icon.on:hover {
  background-color: #2dcb56;
}

.operate-process-icon.on:hover i {
  background-position: 1px -60px;
}

.realtime-log-icon i {
  background-position: -34px -42px;
}

.realtime-log-icon.on i {
  background-position: -34px -84px;
}

.realtime-log-icon.show i,
.realtime-log-icon.on:hover i {
  background-position: -34px 0;
}

.realtime-log-icon.show,
.realtime-log-icon.on:hover {
  background: #3a84ff;
  border: solid 1px #3a84ff;
}

/* 整体样式 */
.green {
  color: #5bd18b;
}

.stopped {
  color: #ccc;
}

.pending {
  color: #f0a63a;
}

.instance-box {
  margin-top: 0;
  margin-bottom: 43px;
  border-bottom: solid 1px #dfe4e5;
}

.instance-box h3 {
  color: #333;
  width: 882px;
  display: table;
}

.instance-box {
  display: block;
  box-sizing: border-box;
}

.instance-p {
  width: 882px;
  padding-bottom: 20px;
  line-height: 36px;
  /*width: 100%;*/
  display: table;
}

.instance-input {
  float: left;
  margin-right: 20px;
}

.instance-input input[type='text'] {
  float: left;
  width: 668px;
  padding: 0 12px;
  line-height: 34px;
  box-sizing: border-box;
  height: 34px;
}

.instance-input input[type='button'] {
  float: left;
  box-sizing: border-box;
  height: 34px;
  width: 80px;
  vertical-align: top;
  margin: 0 0 0 -1px;
}

.instance-textarea {
  border-radius: 2px;
  line-height: 19px;
  font-size: 12px;
  padding: 10px 20px 10px 20px;

  p {
    padding: 0px 0;
    padding-bottom: 5px;
  }
}

.textarea {
  height: 300px;
  overflow: auto;
  word-wrap: break-word;
  word-break: normal;
}

.textarea::-webkit-scrollbar {
  width: 6px;
  height: 5px;
  background-color: #002b36;
}

.textarea::-webkit-scrollbar-thumb {
  border-radius: 20px;
  background: #a5a5a5;
  -webkit-box-shadow: inset 0 0 6px hsla(0, 0%, 80%, 0.3);
}

.textarea::-webkit-scrollbar-track {
  background-color: #002b36;
}

input[type='button'].checkbox {
  -webkit-appearance: none;
  appearance: none;
  outline: none;
  border: none;
}

.log-loading-container {
  height: 25px;
}

.log-loading {
  text-align: left;
  width: 100%;
  vertical-align: middle;
  color: rgba(147, 161, 161, 0.72);
}

.ps-form-title {
  width: 100%;
  display: inline-block;
  font-size: 22px;
  color: #333;
  text-align: center;
  line-height: 34px;
  padding-bottom: 15px;
}

.ps-form-group {
  margin: 10px 20px;
}

.ps-form-group + .ps-form-group {
  margin: 0 20px;
}

.ps-form-group + .ps-form-button {
  margin: 20px 20px 0;
}

.ps-form-group + .ps-form-text {
  margin: 0 20px 10px;
}

.ps-form-group > * {
  padding-top: 7px;
  padding-bottom: 8px;
}

.ps-form-group > label {
  text-align: right;
}

.ps-form-input {
  width: 100%;
}

.ps-form-text {
  line-height: 24px;
  font-size: 14px;
  color: #666;
  border: 1px solid #ccc;
  padding: 5px 5px 5px 5px;
  border-radius: 2px;
}

.ps-form-button {
  margin-left: 0px;
  margin-right: 0px;
  background: #fafafa;
  text-align: right;
  padding: 1em 0 0 0;
  border-top: solid 1px #e5e5e5;
}

.ps-btn-primary-ghost {
  span {
    color: #7b7d8a;
  }

  &:hover {
    span {
      color: #fff;
    }
  }
}

.ps-btn-width {
  width: 80px;

  &.ps-btn-primary {
    margin-right: 10px;
  }
}

.blur {
  display: none;
}

.blur-busy {
  display: block;
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 10;
  background-color: rgba(220, 220, 220, 0.2);
}

.paasng-icon {
  &.loading {
    width: 13px;
    vertical-align: middle;
  }
}

.loading-img {
  position: absolute;
  top: 50%;
  left: 50%;
  padding: 0;
  width: 16px;
  height: 16px;
  margin: -8px 0 0 -8px;
}

.blur-busy + div {
  filter: blur(1px);
}

.chart-wrapper {
  height: 100%;
  overflow: auto;
  background: #fafbfd;

  .chart-box {
    margin-bottom: 10px;
    border-top: 1px solid #dde4eb;
    border-bottom: 1px solid #dde4eb;

    .title {
      font-size: 14px;
      display: block;
      color: #666;
      font-weight: normal;
      padding: 10px 20px;
    }

    .sub-title {
      font-size: 12px;
    }
    background-color: #fff !important;
  }
}

.action-box {
  position: absolute;
  top: 7px;
  right: 10px;
}

.ps-no-result {
  height: auto;

  .text {
    height: 155px;
  }
}

.tool-confirm-wrapper {
  width: 24px;
  height: 24px;
  display: inline-block;
  float: left;
  margin-right: 5px;

  .ps-icon-btn {
    clear: both;
    float: none;
  }
}

.chart-action-box {
  background-color: #fafafa;
  padding: 10px;
  border-top: 1px solid #ddd;
  overflow: hidden;
}

.radio-cls {
  /deep/ .bk-radio-button-text {
    padding: 0 102px;
  }
}

.manual-form-cls {
  /deep/ .bk-form-content .tooltips-icon {
    right: 156px !important;
  }
}

.stream-log {
  display: flex;
  margin-bottom: 8px;
  font-family: Consolas, 'source code pro', 'Bitstream Vera Sans Mono', Consolas, Courier, monospace, '微软雅黑',
    'Arial';

  .pod-name {
    min-width: 75px;
    text-align: right;
    margin-right: 15px;
    color: #979ba5;
  }
  .message {
    flex: 1;
  }
}

.slider-detail-wrapper {
  padding: 0 20px 20px 20px;
  line-height: 32px;
  .title {
    display: block;
    padding-bottom: 2px;
    color: #313238;
    border-bottom: 1px solid #dcdee5;
  }
  .detail-item {
    display: flex;
    justify-content: flex-start;
    line-height: 32px;
    .label {
      color: #313238;
    }
  }
}

.action-btn {
  position: relative;
  height: 28px;
  line-height: 28px;
  min-width: 28px;
  display: flex;
  border-radius: 2px;
  cursor: pointer;

  .text {
    min-width: 90px;
    line-height: 28px;
    text-align: left;
    color: #63656e;
    font-size: 12px;
    display: inline-block;
  }

  .left-icon,
  .right-icon {
    width: 28px;
    height: 28px;
    line-height: 28px;
    color: #c4c6cc;
    display: inline-block;
    text-align: center;
  }

  &.refresh {
    width: 28px;
  }
}
.process-empty {
  height: 280px;
}
.auto-container {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #dcdee5;
  .auto-form {
    display: flex;
    // width: 280px;
    /deep/ .bk-form-content .form-error-tip {
      padding-left: 90px !important;
    }
  }
}
.desc-container {
  background: #f0f1f5;
  padding: 10px 20px;
  .cpu-num {
    color: #ff9c01;
    font-weight: 700;
  }
}
.dia-input {
  width: 250px;
}
.dropdown-menu-cls {
  left: 10px;
  i {
    font-size: 24px;
    color: #3a84ff;
    cursor: pointer;
  }
}
.bk-form-control .group-box .group-text {
  line-height: 32px;
}
.rate-container {
  display: flex;
  align-items: center;
  .w80 {
    width: 80px;
  }
}
.bk-dropdown-list {
  text-align: center;
  .option {
    height: 32px;
    line-height: 32px;
    white-space: nowrap;
    padding: 0 4px;
    &:hover {
      background-color: #eaf3ff;
      color: #3a84ff;
    }
  }
}
</style>
