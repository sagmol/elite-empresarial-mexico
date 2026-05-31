"""
Extract TreeStructure_*.xlsx files → subsidiaries_clean.csv
"""
import pandas as pd, glob, os, re

# Country normalization
COUNTRY_NORM = {
    "United States of America": "United States",
    "Ireland; Republic of": "Ireland",
    "Korea; Republic of": "South Korea",
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

rows = []
for f in files:
    try:
        folder = os.path.basename(os.path.dirname(f))
        df = parse_tree(f)
        if df is None or len(df) == 0:
            continue

        # First row is the parent company itself
        for _, r in df.iterrows():
            rel = str(r.get('Relationship Type', '')).strip()
            # Skip parent row and non-subsidiaries
            if rel not in ('Subsidiary', 'Associated Company', 'Joint Venture'):
                continue

            # Build company name from Level columns
            name = None
            for col in ['Level 1', 'Level 2', 'Level 3', 'Company Name']:
                if col in df.columns and pd.notna(r.get(col)):
                    name = str(r[col]).strip()
                    break
            if not name:
                continue

            country_raw = r.get('Country/Region', None)
            country = norm_country(country_raw)
            industry_raw = r.get('Industry', None)
            sector = norm_sector(industry_raw)

            # Revenue
            rev = None
            if 'Total Revenue' in df.columns and pd.notna(r.get('Total Revenue')):
                rev_str = str(r['Total Revenue']).replace('$','').replace(',','').strip()
                try: rev = float(rev_str)
                except: pass

            # Employees
            emp = None
            if 'Employees' in df.columns and pd.notna(r.get('Employees')):
                try: emp = int(float(str(r['Employees']).replace(',','')))
                except: pass

            rows.append({
                'company_folder': folder,
                'sub_name': name,
                'relationship': rel,
                'country': country,
                'industry': str(industry_raw).strip() if pd.notna(industry_raw) else None,
                'sector': sector,
                'is_haven': country in TAX_HAVENS if country else False,
                'revenue_usd': rev,
                'employees': emp,
            })
    except Exception as e:
        print(f"ERROR {os.path.basename(f)}: {e}")

df_out = pd.DataFrame(rows)
out_path = r"C:\pw\proyectos\01_directors_extraction\exploracion\subsidiaries_clean.csv"
df_out.to_csv(out_path, index=False, encoding='utf-8-sig')
print(f"Guardado: {len(df_out)} subsidiarias de {df_out['company_folder'].nunique()} empresas")
print()
print("Top países:")
print(df_out['country'].value_counts().head(15).to_string())
print()
print("Top sectores:")
print(df_out['sector'].value_counts().to_string())
