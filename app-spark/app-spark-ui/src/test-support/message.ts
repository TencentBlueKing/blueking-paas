/** 测试里顶替 `@/common/message`，只记下弹过什么，见 scripts/test-hooks.mjs。 */
export const shownMessages: unknown[] = [];

export default (options: unknown) => {
  shownMessages.push(options);
};
