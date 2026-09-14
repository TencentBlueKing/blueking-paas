// TODO: Studio 本地 mock Agent，仅 /studio 使用
import { buildCampaignHtml } from './snapshots/campaign';
import type { AgentEvent } from './types';

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

const splitText = (text: string) => text.match(/[^，。！、；：\s]+[，。！、；：\s]*/g) || [text];

interface Scenario {
  reply: string;
  summary: string[];
  html?: string;
}

const parseCampaign = (html: string) => ({
  ctaStrong: html.includes('cta--strong'),
  countdown: html.includes('id="timer"'),
  bg: html.match(/background: (#[0-9a-fA-F]{3,8})/)?.[1] || '#f7f3ee',
});

const matchScenario = (input: string, currentHtml: string): Scenario => {
  const text = input.toLowerCase();
  const current = currentHtml ? parseCampaign(currentHtml) : {
    ctaStrong: false,
    countdown: false,
    bg: '#f7f3ee',
  };

  if (/倒计时|countdown/.test(text)) {
    const html = buildCampaignHtml({ ...current, countdown: true });
    return {
      reply: '好的，我在预约区上方加了一块活动倒计时，中间预览会马上更新。',
      summary: ['新增活动倒计时模块', '倒计时与预约按钮一起出现在首屏'],
      html,
    };
  }

  if (/背景/.test(text)) {
    const nextBg = current.bg === '#f7f3ee' ? '#eef6ff' : '#f7f3ee';
    const html = buildCampaignHtml({ ...current, bg: nextBg });
    return {
      reply: '已经换了页面底色，整体还是偏年轻的促销风格。',
      summary: ['调整活动页背景色'],
      html,
    };
  }

  if (/按钮|预约|渐变|醒目|强调|号召/.test(text)) {
    const html = buildCampaignHtml({ ...current, ctaStrong: true });
    return {
      reply: '预约按钮改成红橙渐变，并加上「立即预约 | 限量名额」的行动号召。',
      summary: ['主按钮改为红橙渐变', '文案改为更强的行动号召'],
      html,
    };
  }

  if (!currentHtml || /做|生成|活动页|预约页/.test(text)) {
    return {
      reply: '已生成新品预约活动页骨架，风格偏年轻、促销感强一些。中间区域可以实时预览。',
      summary: [
        '生成活动页：首屏主视觉 + 卖点 + 预约区',
        '预留倒计时、按钮强化等可继续修改的能力',
      ],
      html: buildCampaignHtml(),
    };
  }

  return {
    reply: '我先记下这个需求。当前预览先保持上一版，你可以更具体地说要改按钮、背景或加倒计时。',
    summary: [],
  };
};

export async function* runMockAgent(input: string, currentHtml: string): AsyncGenerator<AgentEvent> {
  await sleep(420);
  const scenario = matchScenario(input, currentHtml);

  for (const chunk of splitText(scenario.reply)) {
    yield { type: 'delta', text: chunk };
    await sleep(28);
  }

  if (scenario.summary.length) {
    await sleep(120);
    yield { type: 'summary', items: scenario.summary };
  }

  if (scenario.html) {
    yield { type: 'files', files: [{ path: 'index.html', content: scenario.html }] };
  }

  yield { type: 'done' };
}
