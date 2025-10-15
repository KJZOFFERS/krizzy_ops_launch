import fetch from 'node-fetch';
import { XMLParser } from 'fast-xml-parser';
import logger from './logger.js';
import { sendOpsMessage } from './discord_utils.js';

const parser = new XMLParser({ ignoreAttributes: false });

export async function pollGovConFeed({ limit = 5 } = {}) {
  const feedUrl = process.env.FPDS_ATOM_FEED || 'https://www.fpds.gov/ezsearch/FEEDS/ATOM';
  try {
    const r = await fetch(feedUrl);
    if (!r.ok) return { ok: false, status: r.status };
    const xml = await r.text();
    const json = parser.parse(xml);
    const entries = json?.feed?.entry || [];
    const top = entries.slice(0, limit).map((e) => ({ title: e.title, id: e.id }));
    return { ok: true, count: entries.length, sample: top };
  } catch (e) {
    logger.error({ err: String(e) }, 'GovCon feed poll failed');
    return { ok: false, error: String(e) };
  }
}

export async function triggerGovConFlow() {
  const webhook = process.env.N8N_GOVCON_SUBTRAP_WEBHOOK_URL;
  if (webhook) {
    const r = await fetch(webhook, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ts: Date.now(), source: 'govcon_subtrap.trigger' }) });
    return { ok: r.ok, status: r.status };
  }
  const baseUrl = (process.env.N8N_BASE_URL || '').replace(/\/$/, '');
  if (!baseUrl) return { ok: false, error: 'N8N_BASE_URL not set' };
  try {
    const list = await fetch(`${baseUrl}/rest/workflows`, { headers: { 'x-n8n-api-key': process.env.N8N_API_KEY || '' } }).then((r) => r.json());
    const wf = (list?.data || []).find((w) => w.name?.includes('GOVCON')) || (list?.data || []).find((w) => w.name?.includes('SUBTRAP'));
    if (!wf) return { ok: false, error: 'GovCon workflow not found' };
    const run = await fetch(`${baseUrl}/rest/workflows/${wf.id}/run`, { method: 'POST', headers: { 'x-n8n-api-key': process.env.N8N_API_KEY || '' }, body: JSON.stringify({}) });
    return { ok: run.ok, status: run.status, workflowId: wf.id };
  } catch (e) {
    logger.error({ err: String(e) }, 'GovCon flow trigger failed');
    await sendOpsMessage(`GovCon trigger failed: ${String(e)}`);
    return { ok: false, error: String(e) };
  }
}
