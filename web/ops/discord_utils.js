import fetch from 'node-fetch';
import logger from './logger.js';

export async function sendOpsMessage(message, options = {}) {
  const webhookUrl = options.webhookUrl || process.env.DISCORD_WEBHOOK_OPS;
  if (!webhookUrl) {
    const error = 'DISCORD_WEBHOOK_OPS is not set';
    logger.warn({ error }, 'sendOpsMessage skipped');
    return { ok: false, error };
  }
  const content = typeof message === 'string' ? message : JSON.stringify(message);
  const body = { content };
  const resp = await fetch(webhookUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  const ok = resp.ok;
  if (!ok) {
    const text = await resp.text().catch(() => '');
    logger.error({ status: resp.status, text }, 'Discord webhook failed');
    return { ok: false, status: resp.status, text };
  }
  return { ok: true };
}
