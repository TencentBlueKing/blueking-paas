import Vue from 'vue';

/**
 * 埋点
 * @param {*} config id action category 埋点信息
 */
Vue.prototype.sendEventTracking = function (config) {
  try {
    // 是否有站点标识、埋点脚本
    if (window.BK_ANALYSIS_SITE_NAME && window.BKANALYSIS) {
      window.BKANALYSIS.sendEvent(config);
    }
  } catch (e) {
    console.warn(e);
  }
};
