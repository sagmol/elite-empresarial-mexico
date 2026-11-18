"""
Extract TreeStructure_*.xlsx files → subsidiaries_clean.csv

Reglas (revisadas 2026-11-03):
- Unidad = entidad Refinitiv (Company PermID). Dedup por (company_folder, permid):
  la misma empresa aparece en 'Empresas Mexico 66' y en 'Pack German' con el
  mismo árbol, y antes el dedup por fila (nombre/país) contaba distinto.
- Solo Relationship Type == 'Subsidiary' entra al CSV principal. Los archivos
  crudos usan 'Affiliate' y 'JointVenture' (no 'Associated Company' /
  'Joint Venture'); esos van aparte a subsidiaries_affiliates_jv.csv.
- Se omiten TreeStructure dentro de subcarpetas 'Directors': son árboles de
  empresas ligadas por consejeros (p. ej. Florida Ice & Farm, Costa Rica, en
  150_Fibra Uno), no subsidiarias de la emisora.
- Nombre = primer Level 1..8 no vacío (antes solo Level 1-3 → se perdían las
  subsidiarias de niveles 4-8). Filas sin nombre se conservan con un rótulo.
- Conteo global = PermID únicos (holdings en cascada como Alfa→Alpek o
  Grupo México→Southern Copper repiten entidades entre carpetas; ver
  columna n_folders).
"""
import pandas as pd, glob, os, re

# Country normalization
COUNTRY_NORM = {
    "United States of America": "United States",
    "Ireland; Republic of": "Ireland",
    "Korea; Republic of": "South Korea",
    "Korea; Republic (S. Korea)": "South Korea",
    "Taiwan; Republic of China": "Taiwan",
    "Bolivia; Plurinational State of": "Bolivia",
    "Venezuela; Bolivarian Republic of": "Venezuela",
    "Tanzania; United Republic of": "Tanzania",
    "Congo; Democratic Republic of the": "DR Congo",
    "Virgin Islands (British)": "British Virgin Islands",
    "Virgin Islands (US)": "US Virgin Islands",
    "Cayman Islands": "Cayman Islands",
    "Channel Islands": "Channel Islands",
}

# Tax havens
TAX_HAVENS = {
    'Cayman Islands', 'British Virgin Islands', 'Bermuda', 'Luxembourg',
    'Netherlands', 'Ireland', 'Switzerland', 'Panama', 'Jersey',
    'Guernsey', 'Isle of Man', 'Malta', 'Mauritius', 'Singapore',
    'Hong Kong', 'Bahamas', 'Barbados', 'Curacao', 'Belize',
    'Liechtenstein', 'Monaco', 'Andorra', 'Seychelles',
    'Marshall Islands', 'Gibraltar',
}

# Industry grouping (Refinitiv → broader sector)
SECTOR_MAP = {
    "Food Processing": "Alimentos y bebidas",
    "Non-Alcoholic Beverages": "Alimentos y bebidas",
    "Food Retail & Distribution": "Alimentos y bebidas",
    "Restaurants & Bars": "Alimentos y bebidas",
    "Agricultural Commodities/Milling": "Alimentos y bebidas",
    "Brewers": "Alimentos y bebidas",
    "Distillers & Vintners": "Alimentos y bebidas",
    "Construction Materials": "Construcción y materiales",
    "Construction & Engineering": "Construcción y materiales",
    "Iron & Steel": "Minería y metales",
    "Specialty Mining & Metals": "Minería y metales",
    "Gold Mining": "Minería y metales",
    "Silver Mining": "Minería y metales",
    "Copper": "Minería y metales",
    "Coal": "Minería y metales",
    "Commodity Chemicals": "Química y petroquímica",
    "Specialty Chemicals": "Química y petroquímica",
    "Oil & Gas Refining and Marketing": "Química y petroquímica",
    "Plastics": "Química y petroquímica",
    "Integrated Telecommunications Services": "Telecomunicaciones y medios",
    "Broadcasting": "Telecomunicaciones y medios",
    "Cable & Satellite": "Telecomunicaciones y medios",
    "Wireless Telecommunications": "Telecomunicaciones y medios",
    "Internet": "Telecomunicaciones y medios",
    "Investment Holding Companies": "Holding e inversión",
    "Asset Management & Custody Banks": "Holding e inversión",
    "Business Support Services": "Servicios empresariales",
    "Diversified Support Services": "Servicios empresariales",
    "Professional & Commercial Services": "Servicios empresariales",
    "Department Stores": "Retail",
    "Food & Drug Retailing": "Retail",
    "Specialty Retail": "Retail",
    "Electric Utilities": "Energía",
    "Gas Utilities": "Energía",
    "Renewable Energy": "Energía",
    "Air Freight & Logistics": "Transporte y logística",
    "Ground Transportation": "Transporte y logística",
    "Marine": "Transporte y logística",
    "Airport Operators": "Transporte y logística",
    "Airlines": "Transporte y logística",
    "Real Estate": "Bienes raíces",
    "Diversified REITs": "Bienes raíces",
    "Industrial REITs": "Bienes raíces",
    "Real Estate Rental, Development & Operations": "Bienes raíces",
    "Real Estate Services": "Bienes raíces",
    "Homebuilding": "Bienes raíces",
    "Banks": "Servicios financieros",
    "Insurance": "Servicios financieros",
    "Diversified Financial Services": "Servicios financieros",
    "Corporate Financial Services": "Servicios financieros",
    "Investment Management & Fund Operators": "Servicios financieros",
    "Investment Banking & Brokerage Services": "Servicios financieros",
    "Financial & Commodity Market Operators & Service Providers": "Servicios financieros",
    "Multiline Insurance & Brokers": "Servicios financieros",
    "Pension Funds": "Servicios financieros",
    "UK Investment Trusts": "Servicios financieros",
    "Construction Supplies & Fixtures": "Construcción y materiales",
    "Wireless Telecommunications Services": "Telecomunicaciones y medios",
    "Ground Freight & Logistics": "Transporte y logística",
    "Courier, Postal, Air Freight & Land-based Logistics": "Transporte y logística",
    "Highways & Rail Tracks": "Transporte y logística",
    "Airport Operators & Services": "Transporte y logística",
    "Non-Gold Precious Metals & Minerals": "Minería y metales",
    "Gold": "Minería y metales",
    "Aluminum": "Minería y metales",
    "Non-Paper Containers & Packaging": "Química y petroquímica",
    "Oil & Gas Exploration and Production": "Química y petroquímica",
    "Oil Related Services and Equipment": "Química y petroquímica",
    "Oil & Gas Drilling": "Química y petroquímica",
    "Auto, Truck & Motorcycle Parts": "Manufactura",
    "Industrial Machinery & Equipment": "Manufactura",
    "Heavy Machinery & Vehicles": "Manufactura",
    "Software": "Tecnología",
    "Online Services": "Tecnología",
    "Advertising & Marketing": "Servicios empresariales",
    "Fishing & Farming": "Alimentos y bebidas",
}

def norm_country(c):
    if pd.isna(c): return None
    c = str(c).strip()
    return COUNTRY_NORM.get(c, c)

def norm_sector(ind):
    if pd.isna(ind): return "Otros"
    ind = str(ind).strip()
    return SECTOR_MAP.get(ind, "Otros")

def parse_tree(f):
    df = pd.read_excel(f, sheet_name=0, header=None, skiprows=4)
    df.columns = df.iloc[1].astype(str).str.strip()
    df = df.iloc[2:].reset_index(drop=True)
    df = df[pd.to_numeric(df['Company PermID'], errors='coerce').notna()].copy()
    return df

BASE = r"C:\pw\Envio2German\2\Empresas Mexico 66"
files = glob.glob(BASE + r"\**\TreeStructure_*.xlsx", recursive=True)

# Also Pack German
pack_files = glob.glob(r"C:\pw\Pack German\**\TreeStructure_*.xlsx", recursive=True)
files += pack_files

LEVELS = [f'Level {i}' for i in range(1, 9)]
KEEP_REL = 'Subsidiary'
OTHER_REL = ('Affiliate', 'JointVenture')

def to_num(v, cast=float):
    if pd.isna(v): return None
    try: return cast(float(str(v).replace('$', '').replace(',', '').strip()))
    except ValueError: return None

rows = []
skipped = []
for f in files:
    try:
        parent_dir = os.path.dirname(f)
        if os.path.basename(parent_dir) == 'Directors':
            skipped.append(os.path.relpath(f, os.path.dirname(os.path.dirname(parent_dir))))
            continue
        folder = os.path.basename(parent_dir)
        source = 'Pack German' if f.startswith(r"C:\pw\Pack German") else 'Empresas Mexico 66'
        df = parse_tree(f)
        if df is None or len(df) == 0:
            continue

        for _, r in df.iterrows():
            rel = str(r.get('Relationship Type', '')).strip()
            # Skip parent row
            if rel not in (KEEP_REL,) + OTHER_REL:
                continue

            depth = next((i for i, c in enumerate(LEVELS, 1) if c in df.columns and pd.notna(r.get(c))), None)
            name = str(r[LEVELS[depth - 1]]).strip() if depth else None
            if not name and pd.notna(r.get('Company Name')):
                name = str(r['Company Name']).strip()
            if not name:
                # 9 PermIDs sin nombre en Refinitiv: son entidades reales, se conservan
                name = f"[sin nombre, PermID {int(float(r['Company PermID']))}]"

            country = norm_country(r.get('Country/Region', None))
            inc_country = norm_country(r.get('Incorporated Country/Region', None))
            industry_raw = r.get('Industry', None)

            rows.append({
                'company_folder': folder,
                'sub_name': name,
                'relationship': rel,
                'country': country,
                'industry': str(industry_raw).strip() if pd.notna(industry_raw) else None,
                'sector': norm_sector(industry_raw),
                'is_haven': country in TAX_HAVENS if country else False,
                'revenue_usd': to_num(r.get('Total Revenue')),
                'employees': to_num(r.get('Employees'), int),
                'permid': int(float(r['Company PermID'])),
                'level': depth,
                'incorporated_country': inc_country,
                'is_haven_incorporated': inc_country in TAX_HAVENS if inc_country else False,
                'ownership_pct': to_num(r.get('Ownership Percentage')),
                'source': source,
            })
    except Exception as e:
        print(f"ERROR {os.path.basename(f)}: {e}")

for s_ in skipped:
    print(f"Omitido (subcarpeta Directors, no es subsidiaria): {s_}")

df_all = pd.DataFrame(rows)
# Dedup por entidad dentro de cada empresa; si la misma carpeta viene de las
# dos fuentes se conserva una sola fila (los árboles son idénticos).
before = len(df_all)
df_all = (df_all.sort_values(['company_folder', 'permid', 'source'])
                .drop_duplicates(['company_folder', 'permid', 'relationship'])
                .drop(columns='source')
                .reset_index(drop=True))
print(f"Dedup (company_folder, permid): {before} -> {len(df_all)} filas")

df_out = df_all[df_all['relationship'] == KEEP_REL].copy()
df_out['n_folders'] = df_out.groupby('permid')['company_folder'].transform('nunique')
df_out = df_out.reset_index(drop=True)
df_oth = df_all[df_all['relationship'].isin(OTHER_REL)].reset_index(drop=True)

out_dir = r"C:\pw\proyectos\01_directors_extraction\exploracion"
df_out.to_csv(os.path.join(out_dir, 'subsidiaries_clean.csv'), index=False, encoding='utf-8-sig')
df_oth.to_csv(os.path.join(out_dir, 'subsidiaries_affiliates_jv.csv'), index=False, encoding='utf-8-sig')
print(f"Guardado: {len(df_out)} filas Subsidiary de {df_out['company_folder'].nunique()} empresas "
      f"(+ {len(df_oth)} Affiliate/JointVenture en subsidiaries_affiliates_jv.csv)")

# ── Resumen reproducible (cifras citadas en el paper / sitio) ────────────────
uniq = df_out.drop_duplicates('permid')
abroad = uniq[uniq['country'] != 'Mexico']
print()
print("=== Resumen global (Subsidiary, PermID únicos) ===")
print(f"Total subsidiarias:  {len(uniq):,}")
print(f"En México:           {(uniq['country'] == 'Mexico').sum():,}")
print(f"Fuera de México:     {len(abroad):,}  en {abroad['country'].nunique()} países")
print(f"PermID en >1 carpeta: {(uniq['n_folders'] > 1).sum():,}")
print(f"Paraísos/hubs (país de operación):    {uniq['is_haven'].sum()}")
print(f"Paraísos/hubs (país de incorporación): {uniq['is_haven_incorporated'].sum()}"
      f"  [incorporated_country disponible solo en {uniq['incorporated_country'].notna().mean():.0%} de las filas]")
print()
per = (df_out.assign(abroad=df_out['country'] != 'Mexico')
             .groupby('company_folder')
             .agg(total=('permid', 'size'), abroad=('abroad', 'sum'),
                  paises=('country', lambda c: c[c != 'Mexico'].nunique()),
                  havens=('is_haven', 'sum'))
             .sort_values('total', ascending=False))
print("Top 15 empresas (por carpeta, sin dedup entre carpetas):")
print(per.head(15).to_string())
print()
print("Top países (PermID únicos):")
print(uniq['country'].value_counts().head(15).to_string())
print()
print("Top sectores (PermID únicos):")
print(uniq['sector'].value_counts().to_string())
