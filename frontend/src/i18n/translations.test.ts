import { describe, expect, it } from 'vitest'
import { translations } from './translations'

describe('translations', () => {
  it('has a non-empty English and Spanish value for every key', () => {
    for (const [key, entry] of Object.entries(translations)) {
      expect(entry.en.trim().length, `${key}.en is empty`).toBeGreaterThan(0)
      expect(entry.es.trim().length, `${key}.es is empty`).toBeGreaterThan(0)
    }
  })

  it('never has an English and Spanish value that are byte-identical for prose keys', () => {
    // A handful of keys are legitimately identical across languages
    // (e.g. "SQL", "Vault" -- product/technical nouns that don't
    // translate) -- this only flags accidental copy-paste on the rest.
    const identicalAllowed = new Set(['sandbox.sql', 'nav.vault', 'tutorChat.speakerTutor'])
    for (const [key, entry] of Object.entries(translations)) {
      if (identicalAllowed.has(key)) continue
      expect(entry.en, `${key} has identical en/es text`).not.toBe(entry.es)
    }
  })
})
