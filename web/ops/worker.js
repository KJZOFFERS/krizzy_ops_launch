import 'dotenv/config';
import logger from './logger.js';
import { sendOpsMessage } from './discord_utils.js';
import { triggerReiFlow } from './rei_dispo.js';
import { triggerGovConFlow, pollGovConFeed } from './govcon_subtrap.js';
import { testAuth as testAirtableAuth } from './airtable_utils.js';
import { testAuth as testTwilioAuth } from './twilio_utils.js';

const SLEEP_MS = Number(process.env.WORKER_SLEEP_MS || 60000);

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function startupChecks() {
  const checks = await Promise.allSettled([
    testAirtableAuth({ timeoutMs: 2000 }),
    testTwilioAuth({ timeoutMs: 2000 }),
    pollGovConFeed({ limit: 1 })
  ]);
  logger.info({ checks }, 'worker startup checks complete');
}

async function runOnce() {
  const results = {};
  results.rei = await triggerReiFlow().catch((e) => ({ ok: false, error: String(e) }));
  results.govcon = await triggerGovConFlow().catch((e) => ({ ok: false, error: String(e) }));
  logger.info({ results }, 'worker cycle complete');
  const failures = Object.entries(results).filter(([, r]) => !r.ok);
  if (failures.length > 0) {
    await sendOpsMessage(`Worker cycle had failures: ${JSON.stringify(failures)}`);
  }
}

export async function startWorker() {
  logger.info('worker starting');
  await startupChecks();
  let iteration = 0;
  // periodic timers
  setInterval(async () => {
    try {
      await runOnce();
    } catch (e) {
      logger.error({ err: String(e) }, 'runOnce failed');
    }
  }, Number(process.env.WORKER_CYCLE_MS || 10 * 60 * 1000));

  // heartbeat
  setInterval(async () => {
    iteration += 1;
    logger.info({ iteration, uptimeSec: Math.round(process.uptime()) }, 'worker heartbeat');
  }, SLEEP_MS);

  // keep process alive
  // eslint-disable-next-line no-constant-condition
  while (true) {
    await sleep(60 * 60 * 1000);
  }
}

process.on('uncaughtException', async (err) => {
  logger.error({ err: String(err) }, 'uncaughtException');
  await sendOpsMessage(`Worker uncaughtException: ${String(err)}`);
});
process.on('unhandledRejection', async (err) => {
  logger.error({ err: String(err) }, 'unhandledRejection');
  await sendOpsMessage(`Worker unhandledRejection: ${String(err)}`);
});

if (process.env.WORKER_AUTOSTART !== 'false') {
  startWorker().catch(async (e) => {
    logger.error({ err: String(e) }, 'worker failed to start');
    await sendOpsMessage(`Worker failed to start: ${String(e)}`);
    process.exit(1);
  });
}

export default {
  startWorker,
};
