#!/usr/bin/env node
// firestore-prompt-ops.js — Read/write Firestore prompt variant documents
// Usage:
//   node scripts/firestore-prompt-ops.js read  <stageId> <sessionId> [variantId]
//   node scripts/firestore-prompt-ops.js write <stageId> <sessionId> <variantId> <jsonFile>
//   node scripts/firestore-prompt-ops.js list
//
// Must be run from the functions/ directory (needs firebase-admin).
'use strict'

const admin = require('firebase-admin')
const fs = require('fs')

if (!admin.apps.length) {
  admin.initializeApp()
}
const db = admin.firestore()
// Global prompts live in db-global
const globalDb = new admin.firestore.Firestore({ databaseId: 'db-global' })

async function readVariant(stageId, sessionId, variantId) {
  const sessionRef = globalDb.collection('prompts').doc(stageId)
    .collection('sessions').doc(sessionId)

  if (!variantId) {
    const sessionSnap = await sessionRef.get()
    if (!sessionSnap.exists) throw new Error(`Session not found: ${stageId}/${sessionId}`)
    variantId = sessionSnap.data().activeVariant
  }

  const variantSnap = await sessionRef.collection('variants').doc(variantId).get()
  if (!variantSnap.exists) throw new Error(`Variant not found: ${stageId}/${sessionId}/${variantId}`)

  return { variantId, data: variantSnap.data() }
}

async function writeVariant(stageId, sessionId, variantId, data) {
  const variantRef = globalDb.collection('prompts').doc(stageId)
    .collection('sessions').doc(sessionId)
    .collection('variants').doc(variantId)

  data.updatedAt = admin.firestore.FieldValue.serverTimestamp()
  await variantRef.update(data)
  return { stageId, sessionId, variantId, status: 'updated' }
}

async function listAll() {
  const stagesSnap = await globalDb.collection('prompts').get()
  const results = []

  for (const stageDoc of stagesSnap.docs) {
    const sessionsSnap = await stageDoc.ref.collection('sessions').get()
    for (const sessionDoc of sessionsSnap.docs) {
      const sessionData = sessionDoc.data()
      const variantsSnap = await sessionDoc.ref.collection('variants').get()
      for (const variantDoc of variantsSnap.docs) {
        const vData = variantDoc.data()
        const hasResponseSchema = !!(vData.fieldPrompts && vData.fieldPrompts.responseSchema)
        const hasDataBindings = !!(vData.fieldPrompts && vData.fieldPrompts.dataBindings)
        results.push({
          path: `${stageDoc.id}/${sessionDoc.id}/${variantDoc.id}`,
          activeVariant: sessionData.activeVariant,
          turnsCount: (vData.turns || []).length,
          hasResponseSchema,
          hasDataBindings,
          fieldPromptKeys: vData.fieldPrompts ? Object.keys(vData.fieldPrompts) : [],
        })
      }
    }
  }
  return results
}

async function main() {
  const [,, cmd, ...args] = process.argv

  if (cmd === 'read') {
    const [stageId, sessionId, variantId] = args
    if (!stageId || !sessionId) {
      console.error('Usage: read <stageId> <sessionId> [variantId]')
      process.exit(1)
    }
    const result = await readVariant(stageId, sessionId, variantId)
    console.log(JSON.stringify(result, null, 2))
  }
  else if (cmd === 'write') {
    const [stageId, sessionId, variantId, jsonFile] = args
    if (!stageId || !sessionId || !variantId || !jsonFile) {
      console.error('Usage: write <stageId> <sessionId> <variantId> <jsonFile>')
      process.exit(1)
    }
    const data = JSON.parse(fs.readFileSync(jsonFile, 'utf8'))
    const result = await writeVariant(stageId, sessionId, variantId, data)
    console.log(JSON.stringify(result, null, 2))
  }
  else if (cmd === 'list') {
    const results = await listAll()
    console.log(JSON.stringify(results, null, 2))
  }
  else {
    console.error('Commands: read, write, list')
    process.exit(1)
  }

  process.exit(0)
}

main().catch(err => { console.error(err.message); process.exit(1) })
