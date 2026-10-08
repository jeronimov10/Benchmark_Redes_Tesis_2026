# Redfacil — demo frontend

Interactive **dummy** prototype that recommends one of six networks
(Tempo, Aptos, Canton, Polygon, Arbitrum, Celo) for a hypothetical COP→USDT
transaction. All network data in `src/data/networks.ts` is invented; nothing
here is measured. The thesis benchmark in the repo root is a separate pipeline.

```
npm install
npm run dev     # http://localhost:3000  (es default, /en for English)
npm test        # engine + i18n key parity
npm run build
```

- `src/engine/` — pure recommendation engine (no React). Scenarios, the
  qualification standard (`risk-standard.ts`), scoring, explanation.
- `src/data/` — demo data. Replace to plug in real data later.
- `messages/{es,en}.json` — every UI string. Add a language: new JSON + one
  line in `src/i18n/routing.ts`.
- State lives in `localStorage` (multiple users, each with a history).
