// TODO: Studio mock 活动页快照，待接入真实生成后再移除
export interface CampaignOptions {
  ctaStrong?: boolean;
  countdown?: boolean;
  bg?: string;
}

export const buildCampaignHtml = (options: CampaignOptions = {}) => {
  const {
    ctaStrong = false,
    countdown = false,
    bg = '#f7f3ee',
  } = options;

  const buttonClass = ctaStrong ? 'cta cta--strong' : 'cta';
  const buttonText = ctaStrong ? '立即预约 | 限量名额' : '立即预约';
  const countdownBlock = countdown
    ? `<section class="countdown">
        <p>距预约截止还剩</p>
        <strong id="timer">03:00:00:00</strong>
      </section>`
    : '';
  const countdownScript = countdown
    ? `<script>
        (function () {
          var end = Date.now() + 3 * 24 * 3600 * 1000;
          var el = document.getElementById('timer');
          function pad(n) { return String(n).padStart(2, '0'); }
          function tick() {
            var left = Math.max(0, end - Date.now());
            var d = Math.floor(left / 86400000);
            var h = Math.floor(left / 3600000) % 24;
            var m = Math.floor(left / 60000) % 60;
            var s = Math.floor(left / 1000) % 60;
            el.textContent = pad(d) + ':' + pad(h) + ':' + pad(m) + ':' + pad(s);
          }
          tick();
          setInterval(tick, 1000);
        })();
      </script>`
    : '';

  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>新品预约</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
      color: #1d2129;
      background: ${bg};
    }
    .hero {
      padding: 48px 32px 40px;
      color: #fff;
      background: linear-gradient(135deg, #2b6cb0 0%, #3a84ff 55%, #6aa1ff 100%);
    }
    .hero span { font-size: 12px; opacity: .85; }
    .hero h1 { margin: 8px 0 12px; font-size: 36px; line-height: 1.2; }
    .hero p { max-width: 480px; font-size: 14px; line-height: 1.7; opacity: .92; }
    .panel { padding: 28px 32px 40px; }
    .points { display: flex; gap: 12px; margin-bottom: 24px; }
    .points li {
      flex: 1;
      padding: 16px;
      list-style: none;
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 8px 24px rgba(31, 35, 41, .06);
    }
    .points strong { display: block; margin-bottom: 6px; }
    .points span { color: #86909c; font-size: 12px; }
    .countdown {
      margin-bottom: 20px;
      padding: 16px 20px;
      color: #4e2c00;
      background: #fff4e0;
      border-radius: 12px;
    }
    .countdown p { font-size: 12px; }
    .countdown strong { font-size: 28px; letter-spacing: 2px; }
    .cta {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 168px;
      height: 44px;
      padding: 0 20px;
      color: #fff;
      font-size: 15px;
      font-weight: 600;
      background: #3a84ff;
      border: 0;
      border-radius: 22px;
    }
    .cta--strong {
      min-width: 220px;
      height: 52px;
      font-size: 16px;
      background: linear-gradient(90deg, #ff6a3d 0%, #ff8a1f 100%);
      box-shadow: 0 10px 24px rgba(255, 106, 61, .35);
    }
  </style>
</head>
<body>
  <section class="hero">
    <span>NEW DROP 2026</span>
    <h1>新品预约开启</h1>
    <p>年轻、利落、促销感拉满。留下预约，第一时间拿到发售名额。</p>
  </section>
  <section class="panel">
    <ul class="points">
      <li><strong>限量配色</strong><span>仅开放首发 300 席</span></li>
      <li><strong>会员优先</strong><span>预约用户可提前 2 小时抢</span></li>
      <li><strong>购后礼</strong><span>前 100 名送限定周边</span></li>
    </ul>
    ${countdownBlock}
    <button class="${buttonClass}">${buttonText}</button>
  </section>
  ${countdownScript}
</body>
</html>`;
};
