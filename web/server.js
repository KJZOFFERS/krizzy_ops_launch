import 'dotenv/config';
import express from 'express';
import fetch from 'node-fetch';
import logger from './ops/logger.js';
import { testAuth as testAirtableAuth } from './ops/airtable_utils.js';
import { testAuth as testTwilioAuth } from './ops/twilio_utils.js';
import { sendOpsMessage } from './ops/discord_utils.js';
import { triggerReiFlow } from './ops/rei_dispo.js';
import { triggerGovConFlow, pollGovConFeed } from './ops/govcon_subtrap.js';

const app = express();
app.use(express.json());

app.get('/health', async (req, res) => {
  const health = {
    ok: true,
    ts: Date.now(),
    uptimeMs: Math.round(process.uptime() * 1000),
    env: {
      hasAirtable: Boolean(process.env.AIRTABLE_API_KEY && process.env.AIRTABLE_BASE_ID),
      hasDiscordOps: Boolean(process.env.DISCORD_WEBHOOK_OPS),
      hasTwilio: Boolean(process.env.TWILIO_ACCOUNT_SID && process.env.TWILIO_AUTH_TOKEN)
    }
  };
  res.json(health);
});

app.post('/ops/relay', async (req, res) => {
  try {
    const content = req.body?.content || 'KRIZZY OPS web relay alive';
    const r = await fetch(process.env.DISCORD_WEBHOOK_OPS, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    });
    res.status(r.ok ? 200 : 500).json({ ok: r.ok });
  } catch (e) {
    logger.error({ err: e }, 'ops relay failed');
    res.status(500).json({ ok: false, error: String(e) });
  }
});

app.post('/ops/test/discord', async (req, res) => {
  try {
    await sendOpsMessage('KRIZZY OPS test via /ops/test/discord');
    res.json({ ok: true });
  } catch (e) {
    logger.error({ err: e }, 'discord test failed');
    res.status(500).json({ ok: false, error: String(e) });
  }
});

app.get('/ops/test/airtable', async (req, res) => {
  try {
    const result = await testAirtableAuth({ timeoutMs: 2500 });
    res.status(result.ok ? 200 : 500).json(result);
  } catch (e) {
    logger.error({ err: e }, 'airtable test failed');
    res.status(500).json({ ok: false, error: String(e) });
  }
});

app.get('/ops/test/twilio', async (req, res) => {
  try {
    const result = await testTwilioAuth({ timeoutMs: 2500 });
    res.status(result.ok ? 200 : 500).json(result);
  } catch (e) {
    logger.error({ err: e }, 'twilio test failed');
    res.status(500).json({ ok: false, error: String(e) });
  }
});

app.post('/ops/trigger/rei', async (req, res) => {
  try {
    const result = await triggerReiFlow();
    res.status(result.ok ? 200 : 500).json(result);
  } catch (e) {
    logger.error({ err: e }, 'trigger rei failed');
    res.status(500).json({ ok: false, error: String(e) });
  }
});

app.post('/ops/trigger/govcon', async (req, res) => {
  try {
    const result = await triggerGovConFlow();
    res.status(result.ok ? 200 : 500).json(result);
  } catch (e) {
    logger.error({ err: e }, 'trigger govcon failed');
    res.status(500).json({ ok: false, error: String(e) });
  }
});

app.get('/ops/govcon/sample', async (req, res) => {
  try {
    const result = await pollGovConFeed({ limit: Number(req.query.limit || 5) });
    res.status(result.ok ? 200 : 500).json(result);
  } catch (e) {
    logger.error({ err: e }, 'govcon sample failed');
    res.status(500).json({ ok: false, error: String(e) });
  }
});

export const appInstance = app;

const port = process.env.PORT || 10000;
if (process.env.WEB_AUTOSTART !== 'false') {
  app.listen(port, () => logger.info({ port }, 'web listening'));
}

export default app;
