import fetch from 'node-fetch';
import logger from './logger.js';
import { sendOpsMessage } from './discord_utils.js';

function headers() {
  const headers = { 'Content-Type': 'application/json' };
  if (process.env.N8N_API_KEY) headers['x-n8n-api-key'] = process.env.N8N_API_KEY;
  return headers;
}

export async function triggerReiFlow() {
  const webhook = process.env.N8N_REI_DISPO_WEBHOOK_URL;
  if (webhook) {
    const r = await fetch(webhook, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ts: Date.now(), source: 'rei_dispo.trigger' }) });
    return { ok: r.ok, status: r.status };
  }
  const baseUrl = (process.env.N8N_BASE_URL || '').replace(/\/$/, '');
  if (!baseUrl) return { ok: false, error: 'N8N_BASE_URL not set' };
  try {
    const list = await fetch(`${baseUrl}/rest/workflows`, { headers: headers() }).then((r) => r.json());
    const wf = (list?.data || []).find((w) => w.name?.includes('REI_DISPO')) || (list?.data || []).find((w) => w.name?.includes('REI'));
    if (!wf) return { ok: false, error: 'REI workflow not found' };
    const run = await fetch(`${baseUrl}/rest/workflows/${wf.id}/run`, { method: 'POST', headers: headers(), body: JSON.stringify({}) });
    return { ok: run.ok, status: run.status, workflowId: wf.id };
  } catch (e) {
    logger.error({ err: String(e) }, 'REI flow trigger failed');
    await sendOpsMessage(`REI trigger failed: ${String(e)}`);
    return { ok: false, error: String(e) };
  }
}
