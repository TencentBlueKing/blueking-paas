import { Message as BkMessage } from 'bkui-vue';

/** 没单独写 delay 的提示，停留 1.5 秒。 */
const DEFAULT_MESSAGE_DELAY = 1500;

type MessageOptions = {
  delay?: number;
  message?: string;
  theme?: string;
  [key: string]: unknown;
};

const Message = (options: string | MessageOptions) => {
  if (typeof options === 'string') {
    return BkMessage({ message: options, delay: DEFAULT_MESSAGE_DELAY });
  }
  return BkMessage({
    delay: DEFAULT_MESSAGE_DELAY,
    ...options,
  });
};

export default Message;
