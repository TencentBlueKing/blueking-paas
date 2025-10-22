/**
 * 用于统一处理构建过程中的时间显示格式
 */
import dayjs from 'dayjs';

/**
 * 格式化持续时间显示（保留一位小数）
 * @param {number} totalSeconds - 总秒数
 * @returns {string} 格式化后的时间字符串
 */
export function formatDuration(totalSeconds) {
  const theTime = parseFloat(totalSeconds.toFixed(1));

  if (theTime < 1) {
    return '< 1秒';
  }

  let minutes = 0;
  let hours = 0;
  let remainingSeconds = theTime;

  if (theTime >= 60) {
    minutes = Math.floor(theTime / 60);
    remainingSeconds = parseFloat((theTime % 60).toFixed(1));

    if (minutes >= 60) {
      hours = Math.floor(minutes / 60);
      minutes = minutes % 60;
    }
  }

  let result = '';

  if (remainingSeconds > 0) {
    result = `${remainingSeconds}秒`;
  }
  if (minutes > 0) {
    result = `${minutes}分${result}`;
  }
  if (hours > 0) {
    result = `${hours}时${result}`;
  }

  return result;
}

/**
 * 计算两个时间点之间的时间差（使用dayjs优化，保留一位小数）
 * @param {string|Date|dayjs} startTime - 开始时间
 * @param {string|Date|dayjs} endTime - 结束时间 (可选，默认为当前时间)
 * @returns {string} 格式化后的时间差字符串
 */
export function calculateTimeDiff(startTime, endTime = null) {
  if (!startTime) {
    return '';
  }

  try {
    const start = dayjs(startTime);
    const end = endTime ? dayjs(endTime) : dayjs();

    // 验证时间是否有效
    if (!start.isValid() || !end.isValid()) {
      console.warn('时间格式无效:', { startTime, endTime });
      return '';
    }

    // 计算时间差（秒）
    const diffInSeconds = end.diff(start, 'second', true); // true 表示保留小数

    if (diffInSeconds <= 0) {
      return '< 1秒';
    }

    return formatDuration(diffInSeconds);
  } catch (error) {
    return '';
  }
}

/**
 * 根据时间字符串格式计算时间差
 * @param {string} startTime - 开始时间 (格式: "2025-10-16 17:38:54")
 * @param {string} endTime - 结束时间 (格式: "2025-10-16 17:38:54")
 * @returns {string} 格式化后的时间差字符串
 */
export function calculateDeployTime(startTime, endTime) {
  return calculateTimeDiff(startTime, endTime);
}

/**
 * 映射API状态到组件状态
 * @param {string} apiStatus - API返回的状态 (successful, failed, pending, interrupted)
 * @returns {string} 组件状态 (successful, failed, pending, skip, default)
 */
export function mapPhaseStatus(apiStatus) {
  const statusMap = {
    successful: 'successful',
    failed: 'failed',
    pending: 'pending',
    interrupted: 'skip',
  };
  return statusMap[apiStatus] || 'default';
}

export default {
  formatDuration,
  calculateTimeDiff,
  calculateDeployTime,
  mapPhaseStatus,
};
