/** Demo risk points per country (0 low .. 30 high). Invented for the prototype. */
export const COUNTRIES: Record<string, number> = {
  CO: 0,
  US: 0,
  ES: 0,
  CL: 0,
  MX: 5,
  EC: 5,
  PE: 5,
  BR: 5,
  AR: 10,
  PA: 10,
  VE: 25,
  OTHER: 15,
};

export const COUNTRY_CODES = Object.keys(COUNTRIES);
