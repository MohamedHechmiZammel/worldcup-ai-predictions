// Maps team codes → ISO 3166-1 alpha-2 lowercase, used by the flag-icons CSS library.
// Covers both our 3-letter DB codes (MEX, RSA…) and ESPN 2-letter abbreviations (MX, ZA…).
const FLAG_ISO2: Record<string, string> = {
  // 3-letter DB codes
  MEX: 'mx', RSA: 'za', KOR: 'kr', CZE: 'cz',
  CAN: 'ca', BIH: 'ba', QAT: 'qa', SUI: 'ch',
  BRA: 'br', MAR: 'ma', HAI: 'ht', SCO: 'gb-sct',
  USA: 'us', PAR: 'py', AUS: 'au', TUR: 'tr',
  GER: 'de', CUW: 'cw', CIV: 'ci', ECU: 'ec',
  NED: 'nl', JPN: 'jp', SWE: 'se', TUN: 'tn',
  BEL: 'be', EGY: 'eg', IRN: 'ir', NZL: 'nz',
  ESP: 'es', CPV: 'cv', KSA: 'sa', URU: 'uy',
  FRA: 'fr', SEN: 'sn', IRQ: 'iq', NOR: 'no',
  ARG: 'ar', ALG: 'dz', AUT: 'at', JOR: 'jo',
  POR: 'pt', COD: 'cd', UZB: 'uz', COL: 'co',
  ENG: 'gb-eng', CRO: 'hr', GHA: 'gh', PAN: 'pa',
  // ESPN 2-letter abbreviations (for GroupStandings from live ESPN feed)
  MX: 'mx', ZA: 'za', KR: 'kr', CZ: 'cz',
  CA: 'ca', BA: 'ba', QA: 'qa', CH: 'ch',
  BR: 'br', MA: 'ma', HT: 'ht',
  US: 'us', PY: 'py', AU: 'au', TR: 'tr',
  DE: 'de', CW: 'cw', CI: 'ci', EC: 'ec',
  NL: 'nl', JP: 'jp', SE: 'se', TN: 'tn',
  BE: 'be', EG: 'eg', IR: 'ir', NZ: 'nz',
  ES: 'es', CV: 'cv', SA: 'sa', UY: 'uy',
  FR: 'fr', SN: 'sn', IQ: 'iq', NO: 'no',
  AR: 'ar', DZ: 'dz', AT: 'at', JO: 'jo',
  PT: 'pt', CD: 'cd', UZ: 'uz', CO: 'co',
  HR: 'hr', GH: 'gh', PA: 'pa',
};

/** Returns the ISO-2 code for use with flag-icons CSS (fi fi-{code}). */
export function getFlagCode(code: string | null | undefined): string | null {
  if (!code) return null;
  return FLAG_ISO2[code.toUpperCase()] ?? null;
}

/** @deprecated Use <FlagIcon> component instead. Returns emoji flag as fallback only. */
export function getFlag(code: string | null | undefined): string {
  const iso2 = getFlagCode(code);
  return iso2 ? `fi-${iso2}` : '';
}
