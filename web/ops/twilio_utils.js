import twilio from 'twilio';
import logger from './logger.js';

function getMissingEnv(keys) {
  return keys.filter((k) => !process.env[k] || String(process.env[k]).trim() === '');
}

function getTwilioClient() {
  const { TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN } = process.env;
  const missing = getMissingEnv(['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN']);
  if (missing.length > 0) {
    throw new Error(`Missing env for Twilio: ${missing.join(', ')}`);
  }
  return twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN);
}

export async function testAuth({ timeoutMs = 2500 } = {}) {
  try {
    const { TWILIO_ACCOUNT_SID } = process.env;
    const client = getTwilioClient();
    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(), timeoutMs);
    // Fetch account details to validate credentials
    const acc = await client.api.v2010.accounts(TWILIO_ACCOUNT_SID).fetch();
    clearTimeout(t);
    return { ok: true, accountSid: acc.sid, status: acc.status };
  } catch (err) {
    logger.error({ err: String(err) }, 'Twilio testAuth failed');
    const missing = getMissingEnv(['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN']);
    return { ok: false, error: String(err), missing };
  }
}

export async function sendSms({ to, body }) {
  const { TWILIO_MESSAGING_SERVICE_SID } = process.env;
  const client = getTwilioClient();
  const msg = await client.messages.create({
    to,
    body,
    messagingServiceSid: TWILIO_MESSAGING_SERVICE_SID
  });
  return { sid: msg.sid };
}
