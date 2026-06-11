#!/usr/bin/env node
// Lightweight OTLP HTTP/JSON receiver for ab-test token tracking.
// Captures claude_code.token.usage metrics and attributes them to
// the current variant (set via POST /api/variant/:name).
//
// Usage:
//   node otel-token-collector.mjs [data-file-path]
//   # Then set env vars before launching Claude Code:
//   #   CLAUDE_CODE_ENABLE_TELEMETRY=1
//   #   OTEL_METRICS_EXPORTER=otlp
//   #   OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
//   #   OTEL_EXPORTER_OTLP_PROTOCOL=http/json

import { createServer } from 'node:http'
import { writeFileSync } from 'node:fs'

const PORT = parseInt(process.env.OTEL_COLLECTOR_PORT || '4318')
const DATA_FILE = process.argv[2] || 'testing/data/otel-tokens.json'

// Per-variant accumulated token counts
const variants = {}
let currentVariant = null

function ensureVariant(name) {
  if (!variants[name]) {
    variants[name] = { input: 0, output: 0, cacheRead: 0, cacheCreation: 0 }
  }
  return variants[name]
}

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = ''
    req.on('data', chunk => { body += chunk })
    req.on('end', () => {
      try { resolve(JSON.parse(body)) }
      catch (e) { resolve(null) }
    })
    req.on('error', reject)
  })
}

function extractTokenMetrics(data) {
  if (!data || !currentVariant) return
  const v = ensureVariant(currentVariant)
  for (const rm of data.resourceMetrics || []) {
    for (const sm of rm.scopeMetrics || []) {
      for (const metric of sm.metrics || []) {
        if (metric.name !== 'claude_code.token.usage') continue
        const points = metric.sum?.dataPoints || metric.gauge?.dataPoints || []
        for (const dp of points) {
          const typeAttr = (dp.attributes || []).find(a => a.key === 'type')
          const type = typeAttr?.value?.stringValue
          const value = parseInt(dp.asInt || dp.asDouble || '0')
          if (type && value > 0 && type in v) {
            v[type] += value
          }
        }
      }
    }
  }
}

const server = createServer(async (req, res) => {
  // OTLP metrics ingestion
  if (req.method === 'POST' && req.url === '/v1/metrics') {
    extractTokenMetrics(await parseBody(req))
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end('{}')
    return
  }

  // Control: set active variant
  if (req.method === 'POST' && req.url?.startsWith('/api/variant/')) {
    currentVariant = decodeURIComponent(req.url.split('/api/variant/')[1])
    ensureVariant(currentVariant)
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ variant: currentVariant }))
    return
  }

  // Control: read accumulated data
  if (req.method === 'GET' && req.url === '/api/summary') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify(variants, null, 2))
    return
  }

  // Control: save data and exit
  if (req.method === 'POST' && req.url === '/api/shutdown') {
    writeFileSync(DATA_FILE, JSON.stringify(variants, null, 2))
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ saved: DATA_FILE }))
    setTimeout(() => process.exit(0), 200)
    return
  }

  // Health check
  if (req.method === 'GET' && req.url === '/api/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ status: 'ok', currentVariant, variants: Object.keys(variants) }))
    return
  }

  res.writeHead(404)
  res.end('Not found')
})

server.listen(PORT, () => {
  process.stderr.write(`otel-token-collector listening on :${PORT}, data → ${DATA_FILE}\n`)
})
