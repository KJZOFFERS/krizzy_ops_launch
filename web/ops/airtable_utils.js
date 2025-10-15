import Airtable from 'airtable';
import logger from './logger.js';

function getMissingEnv(keys) {
  return keys.filter((k) => !process.env[k] || String(process.env[k]).trim() === '');
}

function getAirtableBase() {
  const { AIRTABLE_API_KEY, AIRTABLE_BASE_ID } = process.env;
  const missing = getMissingEnv(['AIRTABLE_API_KEY', 'AIRTABLE_BASE_ID']);
  if (missing.length > 0) {
    throw new Error(`Missing env for Airtable: ${missing.join(', ')}`);
  }
  const base = new Airtable({ apiKey: AIRTABLE_API_KEY }).base(AIRTABLE_BASE_ID);
  return base;
}

export async function testAuth({ timeoutMs = 2500 } = {}) {
  try {
    const kpiTable = process.env.AIRTABLE_TABLE_KPI || 'KPI_Log';
    const base = getAirtableBase();
    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(), timeoutMs);
    const records = await base(kpiTable)
      .select({ maxRecords: 1, pageSize: 1 })
      .all();
    clearTimeout(t);
    return { ok: true, table: kpiTable, count: records.length };
  } catch (err) {
    logger.error({ err: String(err) }, 'Airtable testAuth failed');
    const missing = getMissingEnv(['AIRTABLE_API_KEY', 'AIRTABLE_BASE_ID']);
    return { ok: false, error: String(err), missing };
  }
}

export async function insertKPI(fields) {
  const base = getAirtableBase();
  const kpiTable = process.env.AIRTABLE_TABLE_KPI || 'KPI_Log';
  const created = await base(kpiTable).create([{ fields }], { typecast: true });
  return created?.[0]?.id || null;
}
