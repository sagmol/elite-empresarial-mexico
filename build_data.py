"""
build_data.py
Genera data_web.js con todos los datos para la página
elite-empresarial-mexico
"""
import json, math, re
import pandas as pd
import numpy as np

BASE = r'C:\pw\proyectos\01_directors_extraction\exploracion'
OUT  = r'C:\pw\proyectos\elite-empresarial-mexico\data_web.js'

# ── Cargar CSVs ────────────────────────────────────────────────────────────────
fin_grp = pd.read_csv(f'{BASE}\\financials_by_group.csv')

fin_co  = pd.read_csv(f'{BASE}\\financials_with_groups.csv')
edu     = pd.read_csv(f'{BASE}\\education_clean.csv')
dirs    = pd.read_csv(f'{BASE}\\directors_raw.csv')
roles   = pd.read_csv(f'{BASE}\\bio_roles_clean.csv')
tree    = pd.read_csv(f'{BASE}\\tree_groups.csv')
sh_raw  = pd.read_csv(f'{BASE}\\shareholders_clean.csv')
dsum    = pd.read_csv(f'{BASE}\\directors_summary.csv')

with open(f'{BASE}\\network_data.json', encoding='utf-8') as f:
    net = json.load(f)

FX = 17.15  # MXN/USD 2023

# ── Colores de grupo (adaptados para fondo claro) ───────────────────────────
GROUP_COLORS = {
    "Slim":        "#1B365D",
    "Gmexico":     "#c44a8a",
    "GrumaBanorte":"#8c564b",
    "Femsa":       "#e07b39",
    "BAL":         "#5b8db8",
    "Bimbo":       "#7b52ab",
    "Salinas":     "#17a0b0",
    "Yucatan":     "#5a9e3e",
    "Cemex":       "#d62728",
    "Alfa":        "#2ca02c",
    "Otro":        "#a8a8a8",
    "Sin Grupo":   "#cccccc",
}

# ── Empresas representativas por grupo ─────────────────────────────────────
GROUP_COMPANIES = {
    "Slim":        ["América Móvil", "Grupo Carso", "Inbursa", "IDEAL", "Sanborns"],
    "Gmexico":     ["Grupo México", "GMexico Transportes"],
    "GrumaBanorte":["Grupo Financiero Banorte", "Gruma", "Grupo Herdez"],
    "Femsa":       ["Coca-Cola FEMSA"],
    "BAL":         ["GNP", "Palacio de Hierro", "Profuturo", "Industrias Peñoles", "Fresnillo"],
    "Bimbo":       ["Grupo Bimbo"],
    "Salinas":     ["Grupo Elektra"],
    "Yucatan":     ["ASUR", "Grupo KUO", "Industrias Bachoco"],
    "Cemex":       ["CEMEX", "GCC"],
    "Alfa":        ["Alfa SAB de CV"],
    "Otro":        ["27 empresas independientes"],
}

# ── 1. GROUPS DATA ──────────────────────────────────────────────────────────
def clean(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return v

groups_data = []
for _, r in fin_grp.sort_values('mktcap_mxn_b', ascending=False).iterrows():
    g = r['group_short']
    groups_data.append({
        "group":       g,
        "color":       GROUP_COLORS.get(g, "#aaa"),
        "companies":   GROUP_COMPANIES.get(g, []),
        "n":           int(r['n_empresas']),
        "mktcap_usd":  round(r['mktcap_mxn_b'] * 1000 / FX / 1000, 1),   # USD B
        "revenue_usd": round(r['revenue_mxn_b'] * 1000 / FX / 1000, 1),
        "ebitda_usd":  round(r['ebitda_mxn_b']  * 1000 / FX / 1000, 1),
        "empleados":   int(r['empleados']) if clean(r['empleados']) else 0,
        "mktcap_pct":  round(float(r['mktcap_pct']), 1),
        "ebitda_margin": round(float(r['ebitda_margin_avg']), 1) if clean(r['ebitda_margin_avg']) else None,
        "roe":         round(float(r['roe_avg']), 1) if clean(r['roe_avg']) else None,
    })

# ── 2. COMPANIES DATA (treemap) ──────────────────────────────────────────────
companies_data = []
for _, r in fin_co.iterrows():
    mc = r.get('mktcap_mxn_m')
    if not mc or (isinstance(mc, float) and math.isnan(mc)):
        continue
    folder = str(r['company_folder'])
    label = re.sub(r'^\d+_', '', folder)
    for abbr, full in [('SAB de CV',''), ('SAB DE CV',''), ('SAB',''),
                       ('Sociedad Anonima',''), ('  ',' ')]:
        label = label.replace(abbr, full).strip()
    rev = r.get('revenue_lfy_mxn_m')
    emp = r.get('employees')
    ebm = r.get('ebitda_margin_pct')
    roe = r.get('roe_km_pct')
    companies_data.append({
        "id":     folder,
        "label":  label[:35],
        "group":  str(r.get('group_short', 'Otro')),
        "color":  GROUP_COLORS.get(str(r.get('group_short', '')), "#aaa"),
        "mc_usd": round(float(mc) / FX, 0),
        "mc_mxn": round(float(mc), 0),
        "rev_usd": round(float(rev) / FX, 1) if rev and not (isinstance(rev, float) and math.isnan(rev)) else None,
        "emp":    int(emp) if emp and not (isinstance(emp, float) and math.isnan(emp)) else None,
        "ebm":    round(float(ebm), 1) if ebm and not (isinstance(ebm, float) and math.isnan(ebm)) else None,
        "roe":    round(float(roe), 1) if roe and not (isinstance(roe, float) and math.isnan(roe)) else None,
    })

# ── 3. EDUCATION DATA ────────────────────────────────────────────────────────
# Top institutions
top_inst_raw = edu.groupby('institution').size().sort_values(ascending=False).head(20)
institutions = [{"name": k, "n": int(v)} for k, v in top_inst_raw.items()]

# Institution type classification
INST_TYPE = {
    "ITESM / Tec de Monterrey": "Privada MX",
    "ITAM": "Privada MX",
    "Universidad Iberoamericana": "Privada MX",
    "UNAM": "Pública MX",
    "Universidad Anáhuac": "Privada MX",
    "IPADE": "Privada MX",
    "CPA": "Certificación",
    "Harvard University": "Extranjera",
    "Stanford University": "Extranjera",
    "Universidad Panamericana": "Privada MX",
    "University of Texas at Austin": "Extranjera",
    "University of Chicago": "Extranjera",
    "Columbia University": "Extranjera",
    "MIT": "Extranjera",
    "University of California": "Extranjera",
    "Northwestern University (Kellogg)": "Extranjera",
    "Yale University": "Extranjera",
    "Universidad La Salle": "Privada MX",
    "University of Pennsylvania (Wharton)": "Extranjera",
    "Escuela Libre de Derecho": "Privada MX",
}
for inst in institutions:
    inst["type"] = INST_TYPE.get(inst["name"], "Otra")

# Fix encoding
for inst in institutions:
    inst["name"] = inst["name"].replace("Anã¿huac", "Anáhuac")

# Top fields
top_fields_raw = edu['field'].value_counts().head(15)
fields_data = [{"field": k, "n": int(v)} for k, v in top_fields_raw.items()]

# Degree levels
levels_raw = edu['degree_type'].value_counts()
levels_data = [{"level": k, "n": int(v)} for k, v in levels_raw.items() if k not in ['nan', 'None']]

# Sector of institution summary
mx_priv  = sum(i["n"] for i in institutions if i["type"] == "Privada MX")
mx_pub   = sum(i["n"] for i in institutions if i["type"] == "Pública MX")
extran   = sum(i["n"] for i in institutions if i["type"] == "Extranjera")

# ── 4. TOP CAREER FLOWS ──────────────────────────────────────────────────────
career_edges = net['edges_career']
# Top 15 flows (both internal and external, by weight)
career_top = sorted(career_edges, key=lambda x: x['weight'], reverse=True)[:20]

def clean_node_label(node_id):
    if node_id.startswith('ext_'):
        label = node_id[4:].replace('_', ' ').title()
        return label
    label = re.sub(r'^\d+_', '', node_id)
    for abbr in ['SAB de CV', 'SAB DE CV', 'SAB', '  ']:
        label = label.replace(abbr, ' ').strip()
    return label[:30]

career_data = []
for e in career_top:
    career_data.append({
        "source": clean_node_label(e['source']),
        "target": clean_node_label(e['target']),
        "weight": e['weight'],
        "is_external": e['source'].startswith('ext_') or e['target'].startswith('ext_'),
    })

# ── 5. TOP INTERLOCKS ────────────────────────────────────────────────────────
inter_edges = net['edges_interlock']
inter_top = sorted(inter_edges, key=lambda x: x['weight'], reverse=True)[:15]
interlock_data = []
for e in inter_top:
    src_label = clean_node_label(e['source'])
    tgt_label = clean_node_label(e['target'])
    # Get group for color
    src_group = next((c.get('group','Otro') for c in companies_data if c['id'] == e['source']), 'Otro')
    interlock_data.append({
        "source": src_label,
        "target": tgt_label,
        "weight": e['weight'],
        "group":  src_group,
        "color":  GROUP_COLORS.get(src_group, "#aaa"),
    })

# ── 6. PROPIEDAD — SHAREHOLDERS ─────────────────────────────────────────────
strat = sh_raw[sh_raw.investor_type == 'Strategic Entities'].copy()
strat = strat[strat.pct_outstanding.notna()].copy()
strat['pct'] = strat['pct_outstanding'] * 100

def short_co(name):
    s = re.sub(r'^\d+_', '', str(name))
    for abbr in ['SAB de CV', 'SAB DE CV', 'SAB', 'S.A.B. de C.V.', 'S.A.B.', 'de CV']:
        s = s.replace(abbr, '').strip()
    return s.strip(' .,').strip()[:38]

strat_pos = strat[strat.pct > 0].copy()
# Exclude Southern Copper (pure subsidiary listed abroad)
strat_pos = strat_pos[~strat_pos.company_folder.astype(str).str.startswith('299_')].copy()

folder_to_grp = dict(zip(tree.company_folder, tree.group_short))

concentration_data = []
for folder, grp in strat_pos.sort_values('pct', ascending=False).groupby('company_folder', sort=False):
    folder = str(folder)
    top3 = grp.sort_values('pct', ascending=False).head(3)
    g = folder_to_grp.get(folder, 'Otro')
    shareholders = []
    for _, r in top3.iterrows():
        shareholders.append({
            'name'   : str(r['investor_name'])[:50],
            'pct'    : round(float(r['pct']), 1),
            'subtype': str(r['investor_subtype']),
        })
    pct_top1  = shareholders[0]['pct'] if shareholders else 0
    pct_total = round(float(top3['pct'].sum()), 1)
    company_name = grp.iloc[0]['company_name']
    concentration_data.append({
        'company'     : short_co(company_name),
        'folder'      : folder,
        'group'       : g,
        'color'       : GROUP_COLORS.get(g, '#aaa'),
        'pct_top1'    : pct_top1,
        'pct_total'   : pct_total,
        'investor'    : shareholders[0]['name'],
        'subtype'     : shareholders[0]['subtype'],
        'shareholders': shareholders,
    })

concentration_data.sort(key=lambda x: -x['pct_top1'])

all_sh_folders   = set(sh_raw.company_folder.astype(str).unique())
strat_folders_set = set(strat_pos.company_folder.astype(str).unique())
no_strat_list = []
for f in sorted(all_sh_folders - strat_folders_set):
    if f.startswith('299_'):
        continue
    rows = sh_raw[sh_raw.company_folder.astype(str) == f]
    if len(rows):
        no_strat_list.append(short_co(rows.iloc[0]['company_name']))

n_majority  = sum(1 for c in concentration_data if c['pct_top1'] >= 50)
median_conc = round(float(np.median([c['pct_top1'] for c in concentration_data])), 1)

prop_stats = {
    'n_with_strategic' : len(concentration_data),
    'n_majority'       : n_majority,
    'n_no_strategic'   : len(no_strat_list),
    'median_pct'       : median_conc,
    'no_strategic'     : no_strat_list,
}

# ── 7. PERMANENCIA — BOARD TENURE ────────────────────────────────────────────
curr_dirs = dsum[dsum.is_current == True].copy()
curr_dirs = curr_dirs[curr_dirs.years_in_position.notna()].copy()

# Top 20 longest-serving current directors
top_tenure = (curr_dirs.sort_values('years_in_position', ascending=False)
              .head(20)[['name','company_name','position','age','years_in_position']]
              .copy())

tenure_data = []
for _, r in top_tenure.iterrows():
    g = folder_to_grp.get('', 'Otro')
    # Find group from company_name
    match = dsum[dsum.company_name == r['company_name']]
    grp = match.iloc[0]['group_short'] if len(match) else 'Otro'
    tenure_data.append({
        'name'    : str(r['name'])[:40],
        'company' : short_co(r['company_name']),
        'position': str(r['position'])[:40],
        'age'     : int(r['age']) if pd.notna(r.get('age')) else None,
        'years'   : int(r['years_in_position']),
        'group'   : grp,
        'color'   : GROUP_COLORS.get(grp, '#aaa'),
    })

# Board stats for summary cards
avg_age     = round(float(curr_dirs[curr_dirs.age.notna()].age.dropna().mean()), 1) \
              if curr_dirs.age.notna().any() else None
med_tenure  = round(float(curr_dirs.years_in_position.median()), 1)
avg_tenure  = round(float(curr_dirs.years_in_position.mean()), 1)

# Turnover ratio per company (ex-directors / current directors)
co_curr  = dsum[dsum.is_current == True].groupby('company_name').size()
co_prev  = dsum[dsum.is_current == False].groupby('company_name').size()
turnover = (co_prev / co_curr).dropna().sort_values(ascending=False)
top_turnover = []
for co, ratio in turnover.head(10).items():
    curr_n = int(co_curr.get(co, 0))
    prev_n = int(co_prev.get(co, 0))
    grp = dsum[dsum.company_name == co].iloc[0]['group_short'] if len(dsum[dsum.company_name == co]) else 'Otro'
    top_turnover.append({
        'company': short_co(co),
        'ratio'  : round(float(ratio), 1),
        'current': curr_n,
        'previous': prev_n,
        'group'  : grp,
        'color'  : GROUP_COLORS.get(grp, '#aaa'),
    })

board_stats = {
    'avg_age'      : avg_age,
    'med_tenure'   : med_tenure,
    'avg_tenure'   : avg_tenure,
    'n_current'    : int(dsum[dsum.is_current == True].shape[0]),
    'n_previous'   : int(dsum[dsum.is_current == False].shape[0]),
    'n_companies'  : int(dsum.company_name.nunique()),
}

# ── 8. SUMMARY STATS ─────────────────────────────────────────────────────────
total_mktcap_usd = sum(c['mc_usd'] for c in companies_data)
total_revenue_usd = fin_grp['revenue_mxn_b'].sum() * 1000 / FX / 1000
total_emp = int(fin_grp['empleados'].sum())
pct_interlocked = round(
    sum(g['mktcap_pct'] for g in groups_data if g['group'] != 'Otro'), 1
)

# Director coverage stats
n_dirs_unique = int(dirs['name'].nunique())
n_dirs_with_edu   = int(edu[edu['is_junk'] != True]['name'].nunique())
n_dirs_with_roles = int(roles['name'].nunique())
n_dirs_with_bio   = int(dirs[dirs['bio'].notna() & (dirs['bio'].str.strip() != '')]['name'].nunique())

stats = {
    "n_companies":      51,
    "n_directors":      1106,
    "n_dirs_unique":    n_dirs_unique,
    "n_dirs_with_bio":  n_dirs_with_bio,
    "n_dirs_with_edu":  n_dirs_with_edu,
    "n_dirs_with_roles": n_dirs_with_roles,
    "n_groups":         11,
    "total_mktcap":     round(total_mktcap_usd / 1000, 0),   # USD B
    "total_revenue":    round(total_revenue_usd, 0),
    "total_emp":        total_emp,
    "pct_interlocked":  pct_interlocked,
    "slim_pct":         round(next(g['mktcap_pct'] for g in groups_data if g['group']=='Slim'), 1),
    "gmexico_pct":      round(next(g['mktcap_pct'] for g in groups_data if g['group']=='Gmexico'), 1),
    "edu_mx_priv":      mx_priv,
    "edu_extranjera":   extran,
    "edu_mx_pub":       mx_pub,
}

# ── Escribir data_web.js ──────────────────────────────────────────────────────
def to_native(obj):
    if isinstance(obj, dict):
        return {k: to_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_native(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    return obj

stats              = to_native(stats)
groups_data        = to_native(groups_data)
companies_data     = to_native(companies_data)
# ── 9. NETWORK DATA (D3 force graph) ─────────────────────────────────────────
mc_by_id = {c['id']: c.get('mc_usd', 0) or 0 for c in companies_data}

net_d3_nodes = []
for node in net['nodes']:
    if node['type'] != 'dataset':
        continue
    mc = mc_by_id.get(node['id'], 0) or 0
    net_d3_nodes.append({
        'id'    : node['id'],
        'label' : node['label'],
        'group' : node['group'],
        'color' : node['color'],
        'mc_usd': round(float(mc), 0),
    })

net_d3_edges = []
for edge in net['edges_interlock']:
    if edge.get('is_subsidiary_link', False):
        continue   # Solo interlocks entre pares, sin subsidiarias
    net_d3_edges.append({
        'source'   : edge['source'],
        'target'   : edge['target'],
        'weight'   : edge['weight'],
        'directors': edge['directors'][:8],
    })

network_d3 = {'nodes': net_d3_nodes, 'edges': net_d3_edges}

# ── Serializar ────────────────────────────────────────────────────────────────
concentration_data = to_native(concentration_data)
prop_stats         = to_native(prop_stats)
tenure_data        = to_native(tenure_data)
top_turnover       = to_native(top_turnover)
board_stats        = to_native(board_stats)
network_d3         = to_native(network_d3)

# ── 10. COMMUNITY GRAPH (Sección 01) ─────────────────────────────────────────
comm_res = pd.read_csv(f'{BASE}\\community_results_full.csv') if \
    __import__('os').path.exists(f'{BASE}\\community_results_full.csv') else \
    pd.read_csv(f'{BASE}\\community_full_results.csv')

# Colores por comunidad
COMM_COLORS = {
    0:  '#d62728', 3:  '#1B365D', 9:  '#7b52ab', 12: '#bbbbbb',
    14: '#5b8db8', 15: '#e07b39', 16: '#c44a8a', 17: '#8c564b',
    18: '#17a0b0', 20: '#2ca02c', 24: '#a8a8a8', 25: '#5a9e3e',
    27: '#cccccc',
}
COMM_NAMES = {
    0:  'Cemex · Alfa', 3:  'Slim', 9:  'Arca · Fibra · Comer',
    12: 'Fragua', 14: 'BAL', 15: 'Femsa · Consumer',
    16: 'Gmexico', 17: 'Gruma · Bimbo · Banorte', 18: 'Bajío · GAP',
    20: 'Salinas · ASUR', 24: 'CH · Simec', 25: 'Infraestructura · CFE',
    27: 'Megacable',
}

# Nodos: dataset companies con su comunidad
comm_map = {r['node_id']: r['community'] for _, r in comm_res.iterrows()}
comm_nodes = []
for node in net['nodes']:
    if node['type'] != 'dataset':
        continue
    mc  = mc_by_id.get(node['id'], 0) or 0
    cid = comm_map.get(node['id'], -1)
    comm_nodes.append({
        'id'        : node['id'],
        'label'     : node['label'],
        'group_manual': node['group'],
        'community' : int(cid),
        'comm_name' : COMM_NAMES.get(int(cid), f'C{cid}'),
        'color'     : COMM_COLORS.get(int(cid), '#aaaaaa'),
        'mc_usd'    : round(float(mc), 0),
    })

# Aristas: interlocks + career entre dataset nodes
dataset_ids = {n['id'] for n in net['nodes'] if n['type'] == 'dataset'}
comm_edges = []
seen = set()
for edge in net['edges_interlock'] + net.get('edges_career', []):
    s, t = edge['source'], edge['target']
    if s not in dataset_ids or t not in dataset_ids:
        continue
    if edge.get('is_subsidiary_link'):
        continue
    key = tuple(sorted([s, t]))
    if key in seen:
        continue
    seen.add(key)
    comm_edges.append({
        'source': s, 'target': t,
        'weight': edge.get('weight', 1),
        'type'  : edge.get('network', 'interlock'),
    })

community_graph = to_native({'nodes': comm_nodes, 'edges': comm_edges})

# ── 11. SUBSIDIARIES DATA ────────────────────────────────────────────────────
subs_raw = pd.read_csv(f'{BASE}\\subsidiaries_clean.csv', encoding='utf-8-sig')
subs_raw = subs_raw[subs_raw['company_folder'].notna()].copy()

# Map folder → group/color/short name
folder_to_name  = {}
folder_to_group = {}
for _, r in tree.iterrows():
    folder_to_name[str(r['company_folder'])]  = str(r['company_name'])
    folder_to_group[str(r['company_folder'])] = str(r['group_short'])

# Also get short name from financial data
fin_folder_name = {}
for _, r in fin_co.iterrows():
    folder_to_name[str(r.get('company_folder',''))] = str(r.get('company_name',''))

# Classic tax havens: zero or tiny real economy, purely fiscal
CLASSIC_HAVENS = {
    'Cayman Islands', 'British Virgin Islands', 'Bermuda', 'Panama',
    'Jersey', 'Guernsey', 'Isle of Man', 'Malta', 'Mauritius',
    'Bahamas', 'Barbados', 'Curacao', 'Belize', 'Liechtenstein',
    'Monaco', 'Andorra', 'Seychelles', 'Marshall Islands', 'Gibraltar',
}
# Fiscal hubs: real economies but commonly used for tax optimization
FISCAL_HUBS = {
    'Netherlands', 'Ireland', 'Luxembourg', 'Switzerland', 'Singapore', 'Hong Kong',
}
TAX_HAVENS = CLASSIC_HAVENS | FISCAL_HUBS

# Shell-like name keywords (holding/finance vehicles, not operational)
SHELL_KEYWORDS = ['holding', 'holdings', 'investment', 'investments', 'finance',
                  'financing', 'treasury', 'capital', 'ventures', 'assets',
                  ' re ', ' re ltd', 'reinsur', 'overseas', 'offshore',
                  'rig owning', 'owning co']

OPERATIONAL_SIGNALS = ['claro', 'coca-cola', 'coke', 'bimbo', 'cemex', 'starbucks',
                       'telcel', 'telmex', 'femsa', 'walmart', 'oxxo', 'sanborns',
                       'restaurant', 'hotel', 'cement', 'concrete', 'steel',
                       'mining', 'telecom', 'television', 'broadcast', 'airport',
                       'arawak', 'donut', 'bread', 'bakery', 'wavin']

def is_operational(name, industry):
    nl = str(name or '').lower()
    il = str(industry or '').lower()
    if any(k in nl for k in OPERATIONAL_SIGNALS): return True
    op_ind = ['food', 'beverage', 'cement', 'construction material', 'retail',
              'restaurant', 'broadcast', 'steel', 'airline', 'telecom service']
    return any(k in il for k in op_ind)

def is_shell_like(name, industry):
    if not name or str(name) == 'nan': return False
    if is_operational(name, industry): return False
    nl = str(name).lower()
    il = str(industry or '').lower()
    return (any(k in nl for k in SHELL_KEYWORDS) or
            'holding' in il or 'investment' in il)

def agg_subs(df):
    """Return {by_country, by_sector, by_haven, haven_details, total, n_haven}"""
    by_country = (df.groupby('country').size()
                    .reset_index(name='n')
                    .sort_values('n', ascending=False)
                    .to_dict('records'))
    by_sector = (df[df['sector'] != 'Otros'].groupby('sector').size()
                   .reset_index(name='n')
                   .sort_values('n', ascending=False)
                   .to_dict('records'))

    # All havens for counts
    havens = df[df['is_haven'] == True].copy()
    by_haven = (havens.groupby('country').size()
                      .reset_index(name='n')
                      .sort_values('n', ascending=False)
                      .to_dict('records'))

    # Notable cases: classic tax havens OR fiscal hubs with shell-like names
    notable = []
    seen = set()
    for _, r in havens.iterrows():
        name = str(r.get('sub_name', '') or '').strip()
        country = str(r.get('country', '')).strip()
        industry = str(r.get('industry', '') or '').strip()
        if not name or name == 'nan':
            continue
        in_classic = country in CLASSIC_HAVENS
        in_hub_shell = country in FISCAL_HUBS and is_shell_like(name, industry)
        if not (in_classic or in_hub_shell):
            continue
        key = (name, country)
        if key in seen: continue
        seen.add(key)
        company_folder = str(r.get('company_folder', '')).strip()
        if company_folder in ('nan', '', 'Directors'): continue
        company_short  = short_co(folder_to_name.get(company_folder, company_folder))
        notable.append({
            'name': name[:55],
            'company': company_short[:28],
            'country': country,
            'haven_type': 'Paraíso clásico' if in_classic else 'Hub fiscal',
            'industry': industry if industry and industry != 'nan' else '',
        })

    return {
        'by_country': by_country,
        'by_sector': by_sector,
        'by_haven': by_haven,
        'haven_details': notable[:25],
        'total': len(df),
        'n_haven': int(len(havens)),
        'n_classic': int(havens['country'].isin(CLASSIC_HAVENS).sum()),
    }

# Global
subs_global = agg_subs(subs_raw)

# Per company
subs_by_company = {}
for folder, grp in subs_raw.groupby('company_folder'):
    folder = str(folder)
    g = folder_to_group.get(folder, 'Otro')
    agg = agg_subs(grp)
    agg['name']  = short_co(folder_to_name.get(folder, folder))
    agg['group'] = g
    agg['color'] = GROUP_COLORS.get(g, '#aaa')
    subs_by_company[folder] = agg

subsidiaries_data = {
    'global': subs_global,
    'by_company': subs_by_company,
}
subsidiaries_data = to_native(subsidiaries_data)

# ── 12. COMPANIES TABLE (tabla enriquecida con red) ───────────────────────────
from collections import Counter

# Grado: n empresas con interlock (peer only)
degree_map = Counter()
for e in net['edges_interlock']:
    if not e.get('is_subsidiary_link'):
        degree_map[e['source']] += 1
        degree_map[e['target']] += 1

# Betweenness y comunidad desde full results
comm_ds = comm_res[comm_res['is_dataset'] == True].copy()
betw_map  = dict(zip(comm_ds['node_id'].astype(str), comm_ds['betweenness']))
comm_id_map = dict(zip(comm_ds['node_id'].astype(str), comm_ds['community']))

def betw_cat(b):
    if b is None or (isinstance(b, float) and math.isnan(b)): return ''
    if b > 0.04:  return 'Alto'
    if b > 0.01:  return 'Medio'
    return 'Bajo'

# Empresas financieras (P/S no es comparable)
FINANCIAL_KEYWORDS = ['financiero', 'banco', 'profuturo', 'gentera', 'seguros', 'cfe', 'asegura']
def is_financial(name):
    return any(k in str(name).lower() for k in FINANCIAL_KEYWORDS)

companies_table = []
for c in companies_data:
    fid = c['id']
    betw = betw_map.get(fid, 0.0)
    cid  = comm_id_map.get(fid, -1)

    # P/S ratio — solo para no-financieras con datos
    ps = None
    if c.get('rev_usd') and c['rev_usd'] > 0 and c.get('mc_usd') and not is_financial(c['label']):
        ps = round(c['mc_usd'] / 1000 / (c['rev_usd'] / 1000), 2)

    companies_table.append({
        'id'        : fid,
        'label'     : c['label'],
        'group'     : c['group'],
        'color'     : c['color'],
        'comm_name' : COMM_NAMES.get(int(cid), '—') if int(cid) >= 0 else '—',
        'mc_usd_b'  : round(c['mc_usd'] / 1000, 1) if c.get('mc_usd') else None,
        'rev_usd_b' : round(c['rev_usd'] / 1000, 1) if c.get('rev_usd') else None,
        'emp'       : c.get('emp'),
        'degree'    : int(degree_map.get(fid, 0)),
        'betw_cat'  : betw_cat(betw),
        'betw_raw'  : round(float(betw), 4),
        'price_sales': ps,
        'financial' : is_financial(c['label']),
    })

# Ordenar: primero grupos nombrados (por mktcap desc), luego independientes
group_order = ['Slim','Gmexico','GrumaBanorte','BAL','Bimbo','Salinas','Femsa','Yucatan','Cemex','Alfa']
def sort_key(r):
    gi = group_order.index(r['group']) if r['group'] in group_order else 99
    mc = -(r['mc_usd_b'] or 0)
    return (gi, mc)
companies_table.sort(key=sort_key)
companies_table = to_native(companies_table)

js = f"""// data_web.js — Elite Empresarial México
// Generado automáticamente. No editar manualmente.

const STATS = {json.dumps(stats, ensure_ascii=False, indent=2)};

const GROUPS_DATA = {json.dumps(groups_data, ensure_ascii=False, indent=2)};

const COMPANIES_DATA = {json.dumps(companies_data, ensure_ascii=False, indent=2)};

const INSTITUTIONS_DATA = {json.dumps(institutions, ensure_ascii=False, indent=2)};

const FIELDS_DATA = {json.dumps(fields_data, ensure_ascii=False, indent=2)};

const LEVELS_DATA = {json.dumps(levels_data, ensure_ascii=False, indent=2)};

const CAREER_DATA = {json.dumps(career_data, ensure_ascii=False, indent=2)};

const INTERLOCK_DATA = {json.dumps(interlock_data, ensure_ascii=False, indent=2)};

const CONCENTRATION_DATA = {json.dumps(concentration_data, ensure_ascii=False, indent=2)};

const PROP_STATS = {json.dumps(prop_stats, ensure_ascii=False, indent=2)};

const TENURE_DATA = {json.dumps(tenure_data, ensure_ascii=False, indent=2)};

const TURNOVER_DATA = {json.dumps(top_turnover, ensure_ascii=False, indent=2)};

const BOARD_STATS = {json.dumps(board_stats, ensure_ascii=False, indent=2)};

const NETWORK_D3 = {json.dumps(network_d3, ensure_ascii=False, indent=2)};

const COMMUNITY_GRAPH = {json.dumps(community_graph, ensure_ascii=False, indent=2)};

const COMPANIES_TABLE = {json.dumps(companies_table, ensure_ascii=False, indent=2)};

const SUBSIDIARIES_DATA = {json.dumps(subsidiaries_data, ensure_ascii=False, indent=2)};
"""

with open(OUT, 'w', encoding='utf-8') as f:
    f.write(js)

print(f"data_web.js escrito ({len(js):,} chars)")
print(f"Grupos: {len(groups_data)}, Empresas: {len(companies_data)}")
print(f"Concentración: {len(concentration_data)} empresas, {prop_stats['n_majority']} con mayoría")
print(f"Tenure: {len(tenure_data)} directores top, board_stats={board_stats}")
