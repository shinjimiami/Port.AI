/**
 * fetch_quotes.js — CLI bridge for PortAI backend
 *
 * Usage:  node fetch_quotes.js <EXCHANGE:SYMBOL> [<EXCHANGE:SYMBOL> ...]
 * Output: JSON object { "EXCHANGE:SYMBOL": { price, open, high, low, volume, change_pct, currency, name } }
 *
 * Exit 0 always (errors per-symbol are embedded in the output).
 */

const TradingView = require('@mathieuc/tradingview');

const symbols = process.argv.slice(2);

if (!symbols.length) {
  process.stdout.write('{}\n');
  process.exit(0);
}

const client = new TradingView.Client();
const results = {};
let pending = symbols.length;

// Hard timeout so Python subprocess never hangs indefinitely
const hardTimeout = setTimeout(() => {
  process.stdout.write(JSON.stringify(results) + '\n');
  client.end();
  process.exit(0);
}, 25000);

function checkDone() {
  pending -= 1;
  if (pending <= 0) {
    clearTimeout(hardTimeout);
    process.stdout.write(JSON.stringify(results) + '\n');
    client.end();
    process.exit(0);
  }
}

symbols.forEach((symbol) => {
  const chart = new client.Session.Chart();

  chart.setMarket(symbol, { timeframe: 'D' });

  chart.onError((...err) => {
    results[symbol] = { error: String(err) };
    checkDone();
  });

  chart.onUpdate(() => {
    // onUpdate fires multiple times; only capture once
    if (results[symbol] && !results[symbol]._pending) return;

    const p = chart.periods;
    if (!p || !p[0]) return;

    const latest = p[0];
    const prev   = p[1];

    const changePct = prev && prev.close
      ? ((latest.close - prev.close) / prev.close) * 100
      : 0;

    results[symbol] = {
      price:      latest.close,
      open:       latest.open,
      high:       latest.max,
      low:        latest.min,
      volume:     latest.volume || 0,
      change_pct: parseFloat(changePct.toFixed(4)),
      currency:   chart.infos.currency_id || '',
      name:       chart.infos.description || symbol,
    };

    checkDone();
  });
});
