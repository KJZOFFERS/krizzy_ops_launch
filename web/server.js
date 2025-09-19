import express from 'express';
import fetch from 'node-fetch';
const app = express();
app.use(express.json());

app.get('/health', (req, res) => res.json({ ok: true, ts: Date.now() }));

app.post('/ops', async (req, res) => {
  try {
    const r = await fetch(process.env.DISCORD_WEBHOOK_OPS, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: req.body?.content || 'KRIZZY OPS web relay alive' })
    });
    res.status(r.ok ? 200 : 500).json({ ok: r.ok });
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e) });
  }
});

const port = process.env.PORT || 10000;
app.listen(port, () => console.log('web listening', port));
