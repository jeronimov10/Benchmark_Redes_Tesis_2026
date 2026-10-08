# Redfacil (frontend)

Interactive prototype that recommends in which network to settle a payment in
Colombia (COP converted to USDT), using the model of the thesis
(`docs/tesis-apa7.pdf`, section 5.4) and traffic lights on top.

```
npm install
npm run dev     # http://localhost:3000 (language follows the browser; /es, /en)
npm test        # reproduces thesis Tables 11 and 13 + i18n key parity
npm run build
```

## Data

- `src/data/profiles.ts` holds the **measured** values.
  - Polygon, Celo, Arbitrum: Table 12 of the thesis (90-day window).
  - Tempo, Aptos, Canton: preliminary pass of the benchmark in this repo
    (`resultados/metrics.csv`), reduced samples. Metrics not comparable with the
    thesis definition are left out (value `null`) and flagged.
- The Monte Carlo error of each metric is a fixed relative value (8% / 25%)
  until the per-metric bootstrap is published. Everything else is the thesis model.
- COP to USDT uses a demo rate (`src/engine/fx.ts`).

## Engine (`src/engine/`, no React)

`model.ts` normalization, aggregation, interpolation of weights, certainty;
`montecarlo.ts` 10,000 replicas, bands, pairwise probabilities;
`recommend.ts` gates, determinant metric, traffic lights; `explain.ts` structured
reasons (the UI translates them). `thesis.test.ts` checks the engine against the
thesis tables.

## i18n

`messages/{es,en}.json`, `next-intl`, locale from the browser (`Accept-Language`).
Add a language: new JSON + one line in `src/i18n/routing.ts`.

State (users, history) lives in `localStorage`; there is no backend.
