// Live human-readable interpretation of machine-coded field values
// (PTC/PFC pairs, PUS type/subtype), shown as gray inline hints that update
// while typing and flag invalid combinations.

import type { PtcEntry, PusService } from '../types'

export interface ValueHint {
  text: string
  invalid?: boolean
}

const isInt = (s: string) => /^\d+$/.test(s)

export function ptcHint(catalog: PtcEntry[], ptcRaw: string): ValueHint | null {
  if (ptcRaw === '') return null
  if (!isInt(ptcRaw)) return { text: 'invalid', invalid: true }
  const e = catalog.find((x) => x.ptc === Number(ptcRaw))
  return e ? { text: e.name } : { text: 'invalid PTC', invalid: true }
}

export function pfcHint(catalog: PtcEntry[], ptcRaw: string, pfcRaw: string): ValueHint | null {
  if (pfcRaw === '') return null
  if (!isInt(pfcRaw)) return { text: 'invalid', invalid: true }
  if (ptcRaw === '' || !isInt(ptcRaw)) return { text: 'set PTC first', invalid: true }
  const e = catalog.find((x) => x.ptc === Number(ptcRaw))
  if (!e) return { text: 'invalid PTC', invalid: true }
  const pfc = Number(pfcRaw)
  if (e.pfc) {
    const v = e.pfc.find((x) => x.pfc === pfc)
    return v ? { text: v.label } : { text: `invalid PFC for ${e.name}`, invalid: true }
  }
  const r = e.pfc_rule!
  if (pfc < r.min || pfc > r.max) {
    return { text: `invalid PFC for ${e.name}`, invalid: true }
  }
  const bits = r.bits === 'pfc*8' ? pfc * 8 : pfc
  return { text: bits ? `${bits} bit${bits === 1 ? '' : 's'}` : 'variable length' }
}

/** One combined label for a PTC/PFC pair, e.g. "Unsigned integer · 16 bits". */
export function typePairHint(catalog: PtcEntry[], ptcRaw: string, pfcRaw: string): ValueHint | null {
  const p = ptcHint(catalog, ptcRaw)
  if (!p) return null
  if (p.invalid) return p
  const f = pfcHint(catalog, ptcRaw, pfcRaw)
  if (!f) return p
  if (f.invalid) return f
  return { text: `${p.text} · ${f.text}` }
}

export function pusTypeHint(services: PusService[], typeRaw: string): ValueHint | null {
  if (typeRaw === '') return null
  if (!isInt(typeRaw) || Number(typeRaw) > 255) return { text: 'invalid', invalid: true }
  const s = services.find((x) => x.service === Number(typeRaw))
  return s ? { text: s.name } : { text: 'custom/unknown service' }
}

export function pusSubtypeHint(services: PusService[], side: 'tm' | 'tc',
                               typeRaw: string, stypeRaw: string): ValueHint | null {
  if (stypeRaw === '') return null
  if (!isInt(stypeRaw) || Number(stypeRaw) > 255) return { text: 'invalid', invalid: true }
  if (typeRaw === '' || !isInt(typeRaw)) return null
  const s = services.find((x) => x.service === Number(typeRaw))
  if (!s) return { text: 'custom/unknown' }
  const st = (side === 'tm' ? s.tm : s.tc).find((x) => x.subtype === Number(stypeRaw))
  return st ? { text: st.name } : { text: 'custom subtype' }
}

/** One combined label for a (type,subtype) pair, e.g. "Housekeeping — HK report". */
export function pusPairHint(services: PusService[], side: 'tm' | 'tc',
                            typeRaw: string, stypeRaw: string): ValueHint | null {
  const t = pusTypeHint(services, typeRaw)
  if (!t) return null
  if (t.invalid) return t
  const st = pusSubtypeHint(services, side, typeRaw, stypeRaw)
  if (st?.invalid) return st
  return st ? { text: `${t.text} — ${st.text}` } : t
}
