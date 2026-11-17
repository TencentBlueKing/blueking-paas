import type { PublicationAppNameValidationRet } from '../http/types';

/** 开发者中心应用名的长度上限，和名称输入框的 maxlength 一致。 */
export const APP_NAME_MAX_LENGTH = 20;

/** 一轮最多问几次推荐名。每次都是不同的三位数。 */
export const SUGGESTION_ATTEMPTS = 5;

/** 三位数从 100 开始，避免 007 这种补零。 */
export const SUGGESTION_DIGIT_MIN = 100;

/** 三位数到 999 结束，含两端，一共 900 个。 */
export const SUGGESTION_DIGIT_MAX = 999;

const SUGGESTION_DIGIT_SPAN = SUGGESTION_DIGIT_MAX - SUGGESTION_DIGIT_MIN + 1;

/** 后缀是连接符加三位数字，长度固定，截断时按这个长度给原名留位置。 */
const SUGGESTION_SUFFIX_LENGTH = 4;

/** available 带上检查接口过滤后实际会用的名字，界面展示和填入的都是它。 */
export type SuggestionCheck =
  | { status: 'available'; name: string }
  | { status: 'unavailable' }
  | { status: 'failed' };

/**
 * 从 100 到 999 不放回地抽最多 5 个三位数。
 *
 * 同一个默认名如果按 -2、-3 递增，每个人都会先撞同一个后缀。随机数把推荐散开。
 * random 供测试注入；返回值超出 [0, 1) 时丢掉这一抽，避免造出范围外的数字。
 */
export const drawSuggestionNumbers = (random: () => number = Math.random): number[] => {
  const drawn = new Set<number>();
  // 随机函数如果总返回同一个值，不能无限循环。
  let guard = 0;
  while (drawn.size < SUGGESTION_ATTEMPTS && guard < SUGGESTION_ATTEMPTS * 20) {
    guard += 1;
    const roll = random();
    if (roll < 0 || roll >= 1) continue;
    drawn.add(SUGGESTION_DIGIT_MIN + Math.floor(roll * SUGGESTION_DIGIT_SPAN));
  }
  return [...drawn];
};

/**
 * 把三位数接到过滤后的原名上。超过 20 个字符时从原名末尾截，后缀保持完整。
 * 原名被截空、或数字不是三位数时返回 null，调用方不再拿它去检查。
 */
export const buildSuggestedAppName = (
  normalizedName: string,
  suffixNumber: number,
): string | null => {
  if (!Number.isInteger(suffixNumber)
    || suffixNumber < SUGGESTION_DIGIT_MIN
    || suffixNumber > SUGGESTION_DIGIT_MAX) {
    return null;
  }

  const suffix = `-${suffixNumber}`;
  // 按码点截，和开发者中心数长度的方式一致，也不会把一个字符的代理对从中间切开。
  const chars = Array.from(normalizedName);
  const stem = chars.slice(0, APP_NAME_MAX_LENGTH - SUGGESTION_SUFFIX_LENGTH).join('');
  if (!stem || suffix.length !== SUGGESTION_SUFFIX_LENGTH) return null;

  return `${stem}${suffix}`;
};

/**
 * 把检查接口的回答折成推荐结论。
 *
 * 发布时报重名那条路径拿到的是用户原样输入（如「Spa rk」），候选会被接口过滤成「Spark-123」，
 * 所以不要求名字和候选逐字相同；只要求可用、且过滤后仍以这次的后缀结尾。
 */
export const classifySuggestionCheck = (
  candidate: string,
  result: PublicationAppNameValidationRet,
): Exclude<SuggestionCheck, { status: 'failed' }> => {
  const suffix = candidate.slice(-SUGGESTION_SUFFIX_LENGTH);
  if (!result.is_available || !result.name.endsWith(suffix)) return { status: 'unavailable' };

  return { status: 'available', name: result.name };
};

/**
 * 按抽出的顺序询问候选，返回第一个可用的名字。
 *
 * 某个候选明确不可用才问下一个。请求失败、原名已变、或五个都不可用时返回 null，
 * 不再继续问，也不展示没检查过的名字。
 */
export const findAvailableSuggestion = async (
  normalizedName: string,
  check: (candidate: string) => Promise<SuggestionCheck>,
  options: {
    random?: () => number;
    isCurrent?: () => boolean;
  } = {},
): Promise<string | null> => {
  if (!normalizedName) return null;

  const numbers = options.random
    ? drawSuggestionNumbers(options.random)
    : drawSuggestionNumbers();

  for (const suffixNumber of numbers) {
    if (options.isCurrent && !options.isCurrent()) return null;

    const candidate = buildSuggestedAppName(normalizedName, suffixNumber);
    if (!candidate) return null;

    const outcome = await check(candidate);
    // 等待期间用户可能已经改了名，迟到的可用结论不能再展示。
    if (options.isCurrent && !options.isCurrent()) return null;
    if (outcome.status === 'failed') return null;
    if (outcome.status === 'available') return outcome.name;
  }

  return null;
};
