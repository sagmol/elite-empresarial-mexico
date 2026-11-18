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

FX = 17.15  # MXN/USD usado para convertir a USD. Market caps son de 2024 (capturados ago-2024 a feb-2025); los estados de resultados son FY2023.

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
    "GrumaBanorte":["Grupo Financiero Banorte", "Gruma"],
    "Femsa":       ["Coca-Cola FEMSA", "FEMSA"],
    "BAL":         ["GNP", "Palacio de Hierro", "Profuturo", "Industrias Peñoles", "Fresnillo"],
    "Bimbo":       ["Grupo Bimbo"],
    "Salinas":     ["Grupo Elektra"],
    "Yucatan":     ["ASUR", "Grupo KUO", "Industrias Bachoco"],
    "Cemex":       ["CEMEX", "GCC"],
    "Alfa":        ["Alfa SAB de CV"],
    "Otro":        ["28 empresas independientes"],
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

# ── 6. PROPIEDAD — BLOQUE DE CONTROL (escenario C del artículo) ─────────────
# Fuente: tabla de controladores últimos del paper (06_paper_propiedad_internacional/
# insumos/controladores_borrador.csv). Reglas: nacionalidad del controlador último
# (Walmex -> Walmart, EUA), custodios fuera, 14 emisoras completadas con reportes
# anuales, control en cascada (emisora de la muestra dueña de otra) incluido en el
# bloque de la filial pero excluido de los agregados de valor (sección 12b).
CTRL_PATH = r'C:\pw\proyectos\06_paper_propiedad_internacional\insumos\controladores_borrador.csv'
ctrl_t = pd.read_csv(CTRL_PATH)
ctrl_t['valor_usd_m'] = ctrl_t['valor_usd_m'].astype(float)

def short_co(name):
    s = re.sub(r'^\d+_', '', str(name))
    for abbr in ['SAB de CV', 'SAB DE CV', 'SAB', 'S.A.B. de C.V.', 'S.A.B.', 'de CV']:
        s = s.replace(abbr, '').strip()
    return s.strip(' .,').strip()[:38]

def ctrl_label(name):
    return re.sub(r'\s*\((emisora de la muestra|subsidiaria)\)', '', str(name)).strip()

folder_to_grp = dict(zip(tree.company_folder, tree.group_short))
blk_rows = ctrl_t[ctrl_t.regla.isin(['control', 'cascada'])].copy()
blk_rows['v'] = blk_rows['valor_usd_m'].fillna(0)
blk_rows['label'] = blk_rows['controlador_ultimo'].apply(ctrl_label)

def tipo_controlante(folder):
    """Misma regla que insumos/cifras_seccion6.py: controlador principal = tenedor
    de control con mayor valor; bloque <10% -> sin controlador identificado."""
    g = blk_rows[blk_rows.company_folder == folder]
    if g.empty:
        return 'Sin controlador identificado'
    top = g.sort_values('v').iloc[-1]
    if pd.isna(top['pct']) and top['nacionalidad_ultima'] == 'México':
        return 'Familia mexicana'          # control sin % (Sanborns, Bachoco)
    if g['pct'].sum() < 0.10:
        return 'Sin controlador identificado'
    if top['regla'] == 'cascada':
        return 'Filial de grupo mexicano'
    if top['nacionalidad_ultima'] != 'México':
        return 'Control extranjero'
    return 'Familia mexicana'

universe_folders = sorted(sh_raw.company_folder.astype(str).unique())
sh_name = sh_raw.drop_duplicates('company_folder').set_index('company_folder')['company_name']
tipos = {f: tipo_controlante(f) for f in universe_folders}

concentration_data = []
for folder in universe_folders:
    g = blk_rows[(blk_rows.company_folder == folder) & blk_rows.pct.notna()]
    # Igual que la figura 2 del artículo: entran las emisoras con algún % (de control
    # o de cartera); las que no tienen bloque cuentan con 0%. Quedan fuera solo las
    # que no traen ningún porcentaje (Sanborns, Bachoco).
    if g.empty and not (sh_raw.loc[sh_raw.company_folder == folder, 'pct_outstanding'].fillna(0) > 0).any():
        continue
    holders = (g.groupby(['label', 'nacionalidad_ultima'], as_index=False)['pct'].sum()
                .sort_values('pct', ascending=False))
    holders['pct'] = holders['pct'] * 100
    block = float(holders['pct'].sum())
    shareholders = [{'name': str(r['label'])[:60], 'pct': round(float(r['pct']), 1),
                     'nac': str(r['nacionalidad_ultima'])} for _, r in holders.head(2).iterrows()]
    if not shareholders:
        shareholders = [{'name': 'Sin bloque de control registrado', 'pct': 0.0, 'nac': ''}]
    rest = block - sum(x['pct'] for x in shareholders)
    if rest > 0.05:
        shareholders.append({'name': f'Resto del bloque ({len(holders) - 2} tenedores)',
                             'pct': round(rest, 1), 'nac': ''})
    grp = folder_to_grp.get(folder, 'Otro')
    concentration_data.append({
        'company'     : short_co(sh_name.get(folder, folder)),
        'folder'      : folder,
        'group'       : grp,
        'color'       : GROUP_COLORS.get(grp, '#aaa'),
        'pct_block'   : round(block, 1),
        'pct_top1'    : shareholders[0]['pct'],
        'investor'    : shareholders[0]['name'],
        'tipo'        : tipos[folder],
        'shareholders': shareholders,
    })
concentration_data.sort(key=lambda x: -x['pct_block'])

no_ctrl = [short_co(sh_name.get(f, f)) for f in universe_folders if tipos[f] == 'Sin controlador identificado']
tipo_counts = pd.Series(tipos).value_counts().to_dict()
n_mx_ctrl = tipo_counts.get('Familia mexicana', 0) + tipo_counts.get('Filial de grupo mexicano', 0)

prop_stats = {
    'n_universe'       : len(universe_folders),
    'n_with_pct'       : len(concentration_data),
    'n_majority'       : sum(1 for c in concentration_data if c['pct_block'] > 50),
    'median_pct'       : round(float(np.median([c['pct_block'] for c in concentration_data])), 1),
    'n_no_controller'  : len(no_ctrl),
    'no_controller'    : no_ctrl,
    'n_with_controller': len(universe_folders) - len(no_ctrl),
    'n_mx_controller'  : n_mx_ctrl,
    'n_family_mx'      : tipo_counts.get('Familia mexicana', 0),
    'n_cascade_mx'     : tipo_counts.get('Filial de grupo mexicano', 0),
    'n_foreign'        : tipo_counts.get('Control extranjero', 0),
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
    "n_directors":      1130,
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
        raw_name = folder_to_name.get(company_folder, company_folder)
        company_short = short_co(raw_name if str(raw_name) != 'nan' else company_folder)
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
        'n_abroad': int((df['country'] != 'Mexico').sum()),
        'n_countries_abroad': int(df.loc[df['country'] != 'Mexico', 'country'].nunique()),
        'n_haven': int(len(havens)),
        'n_classic': int(havens['country'].isin(CLASSIC_HAVENS).sum()),
    }

# Global: una entidad (PermID) cuenta una vez aunque aparezca en varias
# carpetas (holdings en cascada: Alfa→Alpek, Grupo México→Southern Copper)
_subs_u = subs_raw.drop_duplicates('permid')
subs_global = agg_subs(_subs_u)
subs_global['n_companies'] = int(subs_raw['company_folder'].nunique())
subs_global['pct_haven'] = round(float(_subs_u['is_haven'].mean()) * 100, 1)
subs_global['pct_haven_otros'] = round(float(_subs_u.loc[_subs_u['sector'] == 'Otros', 'is_haven'].mean()) * 100, 1)
subs_global['pct_otros'] = round(float((_subs_u['sector'] == 'Otros').mean()) * 100, 1)

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

# ── 12. INSTITUTIONAL INVESTORS DATA ─────────────────────────────────────────
inst = sh_raw[sh_raw['investor_type'] == 'Investment Managers'].copy()
inst = inst[inst['pct_outstanding'].notna()].copy()

# Capa 1 — by country: total value, n_investors
by_country_inst = (inst[inst['country'].notna()]
    .groupby('country')
    .agg(
        total_value_b=('value_usd_m', lambda x: round(x.sum()/1000, 3)),
        n_investors=('investor_name', 'nunique'),
    )
    .reset_index()
    .sort_values('total_value_b', ascending=False)
    .to_dict('records'))

# Capa 3 — most connected: n_companies in universe
most_connected = (inst.groupby(['investor_name','country','investor_subtype','investment_style','turnover'])
    .agg(
        n_companies=('company_folder','nunique'),
        total_value_m=('value_usd_m','sum'),
        equity_assets_b=('equity_assets_m','mean'),
    )
    .reset_index()
    .sort_values('n_companies', ascending=False)
    .head(25))
most_connected['equity_assets_b'] = (most_connected['equity_assets_b'] / 1000).round(1)
most_connected['total_value_b'] = (most_connected['total_value_m'] / 1000).round(3)
most_connected = most_connected.drop(columns=['total_value_m']).to_dict('records')

# Capa 7 — weight: equity_assets vs value_in_mexico
weight_data = (inst.groupby(['investor_name','country','investor_subtype','investment_style','turnover'])
    .agg(
        n_companies=('company_folder','nunique'),
        total_value_m=('value_usd_m','sum'),
        equity_assets_m=('equity_assets_m','mean'),
    )
    .reset_index())
weight_data = weight_data[
    (weight_data['total_value_m'] > 200) &   # >$200M en México
    (weight_data['equity_assets_m'] > 0)
].copy()
weight_data['equity_assets_b'] = (weight_data['equity_assets_m'] / 1000).round(1)
weight_data['total_value_b']   = (weight_data['total_value_m'] / 1000).round(3)
weight_data['pct_of_assets']   = (weight_data['total_value_m'] / weight_data['equity_assets_m'] * 100).round(3)
weight_data = (weight_data
    .sort_values('total_value_b', ascending=False)
    .head(20)
    .drop(columns=['total_value_m','equity_assets_m'])
    .to_dict('records'))

# Short name cleaner for investors
def short_inv(name):
    s = str(name)
    for sfx in ['Investment Management', 'Asset Management', 'Global Advisors',
                'Institutional Trust Company, N.A.', 'Management Company LLC',
                'Management & Research Company LLC', 'Advisers, Inc.',
                'Advisors, L.P.', 'Advisors, Ltd.', ', Inc.', ' LLC', ' Ltd.',
                'S.A. de C.V.', 'S.A.B. de C.V.', 'SAB de CV']:
        s = s.replace(sfx, '').strip(' ,()')
    return s.strip()[:35]

for d in most_connected: d['short_name'] = short_inv(d['investor_name'])
for d in weight_data:     d['short_name'] = short_inv(d['investor_name'])

# Summary stats
total_inst_value = round(inst['value_usd_m'].sum() / 1000, 1)
n_countries_inst = int(inst['country'].nunique())
n_investors_inst = int(inst['investor_name'].nunique())

# Per-company institutional data
by_company_inst = {}
for folder, grp in inst.groupby('company_folder'):
    folder = str(folder)
    g = folder_to_grp.get(folder, 'Otro')
    co_name = short_co(folder_to_name.get(folder, folder) if str(folder_to_name.get(folder, folder)) != 'nan' else folder)

    # by country
    co_countries = (grp[grp['country'].notna()]
        .groupby('country')
        .agg(total_value_b=('value_usd_m', lambda x: round(x.sum()/1000, 3)),
             n_investors=('investor_name','nunique'))
        .reset_index()
        .sort_values('total_value_b', ascending=False)
        .to_dict('records'))

    # top investors
    top_inv = (grp.groupby(['investor_name','investor_subtype','investment_style'])
        .agg(total_value_m=('value_usd_m','sum'))
        .reset_index()
        .sort_values('total_value_m', ascending=False)
        .head(15))
    top_inv['total_value_b'] = (top_inv['total_value_m']/1000).round(3)
    top_inv['short_name'] = top_inv['investor_name'].apply(short_inv)
    top_inv_list = top_inv[['short_name','investor_name','investor_subtype','investment_style','total_value_b']].to_dict('records')

    by_company_inst[folder] = {
        'name'        : co_name,
        'group'       : g,
        'color'       : GROUP_COLORS.get(g, '#aaa'),
        'total_value_b': round(float(grp['value_usd_m'].sum()/1000), 2),
        'n_investors' : int(grp['investor_name'].nunique()),
        'by_country'  : co_countries,
        'top_investors': top_inv_list,
    }

institutional_data = {
    'by_country'     : by_country_inst,
    'most_connected' : most_connected,
    'weight_data'    : weight_data,
    'by_company'     : by_company_inst,
    'stats': {
        'total_value_b'  : total_inst_value,
        'n_countries'    : n_countries_inst,
        'n_investors'    : n_investors_inst,
    }
}
institutional_data = to_native(institutional_data)

# ── 12b. CAPITAL STRUCTURE: control vs. float, filiales, comportamiento ──────
# Filiales: clasificación del capital institucional mexicano
FILIALES_UNIVERSO = {
    'Operadora Inbursa':            'Slim / Inbursa',
    'Operadora de Fondos Banorte':  'GrumaBanorte / Banorte',
    'GBM Administradora':           'GBM (independiente MX)',
    'Operadora de Fondos GBM':      'GBM (independiente MX)',
    'Impulsora del Fondo M':        'GBM (independiente MX)',
    'Nexxus Capital':               'Nexxus (independiente MX)',
    'Actinver':                     'Actinver (independiente MX)',
    'Operadora de Fondos Finamex':  'Finamex (independiente MX)',
}
FILIALES_GLOBALES = {
    'BlackRock Mexico':             'BlackRock',
    'BBVA Asset Management M':      'BBVA',
    'Gestión Santander Mexico': 'Santander',
    'Scotia Fondos':                'Scotiabank',
    'HSBC Global Asset Management': 'HSBC',
    'Compass Investments de M':     'Compass / Bancomer',
    'Sura Investment Management':   'Sura (Colombia)',
}
def classify_filial(name):
    if pd.isna(name): return 'C. Capital MX genuino'
    n = str(name)
    for key in FILIALES_UNIVERSO:
        if key in n: return 'A. Filial de grupo del universo'
    for key in FILIALES_GLOBALES:
        if key in n: return 'B. Filial local de banco global'
    return 'C. Capital MX genuino'

# Comportamiento: permanente / activo / oportunista por origen
PERMANENTE = ['Index', 'Core Value', 'Core Growth', 'Yield']
ACTIVO     = ['GARP', 'Growth']
def origen_capital(row):
    if row['country'] != 'Mexico':
        return 'Extranjero'
    cat = classify_filial(row['investor_name'])
    if cat == 'B. Filial local de banco global':
        return 'Filial banco global'
    return 'Gestor MX (universo/local)'
def tipo_capital(style):
    if style in PERMANENTE: return 'Permanente'
    if style in ACTIVO:     return 'Activo'
    if style == 'Deep Value': return 'Oportunista'
    return 'Sin clasificar'

# Cartera = todos los tenedores que no son Strategic Entities (gestoras, casas de
# bolsa, instituciones), menos los reclasificados en la tabla de controladores
# (Indigo Partners en Volaris -> control; Slim Family en Sites -> duplicado).
_rec = ctrl_t[ctrl_t.origen == 'Refinitiv (reclasificado de cartera)']
_rec_keys = set(_rec.company_folder + '|' + _rec.tenedor_registrado)
cart_all = sh_raw[sh_raw.investor_type != 'Strategic Entities'].copy()
cart_all = cart_all[~(cart_all.company_folder + '|' + cart_all.investor_name).isin(_rec_keys)]
# Nacionalidad de la gestora por su matriz (misma regex que figuras/fig_propiedad.py):
# filiales mexicanas de gestoras extranjeras cuentan como extranjeras.
FILIALES_EXT_RE = (r'BlackRock|BBVA|Sura|Santander|Scotia|Principal|HSBC|Citi|Franklin|Compass|'
                   r'Invesco|J\.?P\.? ?Morgan|Goldman|UBS|Credit Suisse|Allianz')
cart_all['mx_matriz'] = ((cart_all.country == 'Mexico')
                         & ~cart_all.investor_name.str.contains(FILIALES_EXT_RE, case=False, regex=True, na=False))

def compute_capital_structure(folder=None):
    """Estructura de capital del universo (folder=None) o de una emisora.
    Universo: excluye control en cascada (ya esta dentro del valor de la duena).
    Emisora: la cascada SI es su bloque de control (cuenta como control mexicano)."""
    reglas = ['control'] if folder is None else ['control', 'cascada']
    c = ctrl_t[ctrl_t.regla.isin(reglas)]
    cart = cart_all
    sub = sh_raw
    if folder is not None:
        c = c[c.company_folder == folder]
        cart = cart[cart.company_folder == folder]
        sub = sub[sub.company_folder == folder]
    ctrl_mx_m = float(c.loc[c.nacionalidad_ultima == 'México', 'valor_usd_m'].sum())
    ctrl_ex_m = float(c.loc[c.nacionalidad_ultima != 'México', 'valor_usd_m'].sum())
    cart_mx_m = float(cart.loc[cart.mx_matriz, 'value_usd_m'].sum())
    cart_ex_m = float(cart.loc[~cart.mx_matriz, 'value_usd_m'].sum())
    ctrl_m, cart_m = ctrl_mx_m + ctrl_ex_m, cart_mx_m + cart_ex_m
    total_m = ctrl_m + cart_m
    if total_m <= 0:
        return None
    pct = lambda x, d: round(x / d * 100, 1) if d > 0 else 0.0

    capital_global = {
        'total_b'       : round(total_m/1000, 2),
        'strategic_b'   : round(ctrl_m/1000, 2),
        'strategic_pct' : pct(ctrl_m, total_m),
        'ctrl_mx_b'     : round(ctrl_mx_m/1000, 2),
        'ctrl_mx_pct'   : pct(ctrl_mx_m, total_m),
        'ctrl_ex_b'     : round(ctrl_ex_m/1000, 2),
        'ctrl_ex_pct'   : pct(ctrl_ex_m, total_m),
        'ctrl_mx_share' : pct(ctrl_mx_m, ctrl_m),
        'float_b'       : round(cart_m/1000, 2),
        'float_pct'     : pct(cart_m, total_m),
        'float_mx_b'    : round(cart_mx_m/1000, 2),
        'float_mx_pct'  : pct(cart_mx_m, cart_m),
        'float_ext_b'   : round(cart_ex_m/1000, 2),
        'float_ext_pct' : pct(cart_ex_m, cart_m),
        'mx_total_pct'  : pct(ctrl_mx_m + cart_mx_m, total_m),
    }

    # Filiales y comportamiento: solo gestoras de inversion (Investment Managers)
    inst_df = sub[(sub['investor_type'] == 'Investment Managers')
                  & sub['pct_outstanding'].notna()].copy()
    im_mx = inst_df[inst_df['country'] == 'Mexico'].copy()
    im_mx_m = float(im_mx['value_usd_m'].sum())
    im_mx['categoria_filial'] = im_mx['investor_name'].apply(classify_filial)
    filiales_cat = (im_mx.groupby('categoria_filial')['value_usd_m'].sum() / 1000).round(3)
    filiales_data = []
    for cat in ['A. Filial de grupo del universo', 'B. Filial local de banco global', 'C. Capital MX genuino']:
        val_b = float(filiales_cat.get(cat, 0.0))
        filiales_data.append({
            'categoria': cat,
            'valor_b': round(val_b, 3),
            'pct': round(val_b/im_mx_m*1000*100, 1) if im_mx_m > 0 else 0.0,
        })

    inst_b = inst_df.copy()
    comportamiento_data = []
    if len(inst_b):
        inst_b['origen'] = inst_b.apply(origen_capital, axis=1)
        inst_b['tipo_capital'] = inst_b['investment_style'].apply(tipo_capital)
        for origen, grp in inst_b.groupby('origen'):
            tot = float(grp['value_usd_m'].sum())
            if tot <= 0: continue
            by_tipo = (grp.groupby('tipo_capital')['value_usd_m'].sum() / tot * 100).round(1)
            comportamiento_data.append({
                'origen'   : origen,
                'total_b'  : round(tot/1000, 3),
                'permanente_pct'  : float(by_tipo.get('Permanente', 0.0)),
                'activo_pct'      : float(by_tipo.get('Activo', 0.0)),
                'oportunista_pct' : float(by_tipo.get('Oportunista', 0.0)),
                'sin_clasificar_pct': float(by_tipo.get('Sin clasificar', 0.0)),
            })
    comportamiento_data.sort(key=lambda d: -d['total_b'])

    return {
        'global'        : capital_global,
        'filiales'      : filiales_data,
        'im_mx_sede_b'  : round(im_mx_m/1000, 2),
        'comportamiento': comportamiento_data,
        'n_inst'        : int(len(inst_df)),
        'n_strat'       : int(len(c)),
    }

# Agregado de todo el universo (vista "Todos")
capital_structure_data = compute_capital_structure(None)
capital_structure_data['n_companies'] = int(sh_raw.company_folder.nunique())
capital_structure_data['cascade_excluded_b'] = round(float(
    ctrl_t.loc[ctrl_t.regla == 'cascada', 'valor_usd_m'].sum()) / 1000, 1)
_b3 = sh_raw[(sh_raw.investor_type == 'Investment Managers')
             & sh_raw.investor_name.str.contains('BlackRock|Vanguard|State Street|SSGA', case=False, na=False)]
capital_structure_data['big3_n_companies'] = int(_b3.company_folder.nunique())
capital_structure_data['big3_median_pct'] = round(float(
    _b3.groupby('company_folder').pct_outstanding.sum().median()) * 100, 1)
capital_structure_data = to_native(capital_structure_data)

# Desglose por empresa (para el selector interactivo)
capital_by_company = {}
for folder in sh_raw['company_folder'].astype(str).unique():
    res = compute_capital_structure(folder)
    if res is None:
        continue
    raw_name = folder_to_name.get(folder, folder)
    res['name'] = short_co(raw_name if str(raw_name) != 'nan' else folder)
    capital_by_company[folder] = res
capital_structure_by_company = to_native(capital_by_company)

# ── 12c. INTERNACIONALIZACIÓN: % ingresos vs % subsidiarias fuera ────────────
INTL_PATH = r'C:\pw\proyectos\04_internacionalizacion\outputs\internacionalizacion.csv'
intl_df = pd.read_csv(INTL_PATH, encoding='utf-8-sig')

# Tres modelos de expansión (clasificación manual, sesión 2026-06-09/10)
MODELOS_EXPANSION = {
    '170_Grupo Bimbo'                          : 'construccion',
    '162_Gruma SAB de CV'                      : 'construccion',
    '070_CEMEX SAB de CV'                      : 'adquisicion',
    '014_America Móvil'                        : 'adquisicion',
    '187_Grupo Mexico SAB de CV'                : 'adquisicion',
    '197_Grupo Televisa SAB'                   : 'ficcion',
    '172_Grupo Carso SAB de CV'                : 'ficcion',
}
MODELO_LABELS = {
    'construccion': 'Construcción — operación real en mercados nuevos',
    'adquisicion' : 'Adquisición — compra de activos/empresas existentes',
    'ficcion'     : 'Ficción documental — subsidiarias formales, ingresos marginales',
}

intl_data = []
for _, r in intl_df.iterrows():
    folder = str(r['company_folder'])
    if folder == 'Directors':
        continue
    rev_intl = r.get('rev_intl_pct')
    pct_fuera = r.get('pct_fuera')
    if pd.isna(rev_intl) and pd.isna(pct_fuera):
        continue
    intl_data.append({
        'company_folder': folder,
        'empresa'       : short_co(folder_to_name.get(folder, r.get('empresa', folder))),
        'group'         : folder_to_grp.get(folder, 'Otro'),
        'pct_fuera_subs': None if pd.isna(pct_fuera) else round(float(pct_fuera), 1),
        'rev_intl_pct'  : None if pd.isna(rev_intl) else round(float(rev_intl), 1),
        'divergencia'   : None if pd.isna(r.get('divergencia')) else round(float(r['divergencia']), 1),
        'n_paises'      : None if pd.isna(r.get('n_paises')) else int(r['n_paises']),
        'modelo'        : MODELOS_EXPANSION.get(folder),
    })
intl_data.sort(key=lambda d: (d['rev_intl_pct'] is None, -(d['rev_intl_pct'] or 0)))

internacionalizacion_data = to_native({
    'companies': intl_data,
    'modelos'  : MODELO_LABELS,
})

# ── 12d. SEGMENTACIÓN DEL UNIVERSO COMPLETO (no solo "≥10 países") ──────────
# El corte binario "n_paises >= 10" (Vector A) solo distinguía 9 multilatinas.
# Aquí se segmentan las 60 empresas del universo según n° de países Y de
# continentes alcanzados (exploracion/11_segmentacion_universo.py).
SEG_PATH = r'C:\pw\proyectos\04_internacionalizacion\outputs\segmentacion_universo.csv'
seg_df = pd.read_csv(SEG_PATH, encoding='utf-8-sig')

SEGMENTO_LABELS = {
    '1. Multilatina global'     : 'Multilatina global — ≥10 países en ≥3 continentes',
    '2. Multinacional regional' : 'Multinacional regional — ≥3 países en ≥2 continentes',
    '3. Presencia puntual'      : 'Presencia puntual — 1-2 países',
    '4. Doméstica'              : 'Doméstica — sin subsidiarias fuera de México',
}

folder_by_empresa = {str(r['empresa']): str(r['company_folder']) for _, r in intl_df.iterrows()}

seg_companies = []
for _, r in seg_df.iterrows():
    folder = folder_by_empresa.get(r['empresa'])
    seg_companies.append({
        'empresa'       : short_co(folder_to_name.get(folder, r['empresa'])) if folder else r['empresa'],
        'group'         : folder_to_grp.get(folder, 'Otro') if folder else 'Otro',
        'segmento'      : r['segmento'],
        'fuera_mexico'  : int(r['fuera_mexico']),
        'pct_fuera'     : round(float(r['pct_fuera']), 1),
        'n_paises'      : int(r['n_paises']),
        'n_continentes' : int(r['n_continentes']),
        'continentes'   : None if r['continentes'] == '—' else r['continentes'],
        'rev_intl_pct'  : None if pd.isna(r['rev_intl_pct']) else round(float(r['rev_intl_pct']), 1),
    })

seg_summary = seg_df.groupby('segmento').size().reindex(sorted(SEGMENTO_LABELS.keys())).fillna(0).astype(int)

segmentacion_data = to_native({
    'companies': seg_companies,
    'labels'   : SEGMENTO_LABELS,
    'summary'  : {k: int(v) for k, v in seg_summary.items()},
})

# ── 13. COMPANIES TABLE (tabla enriquecida con red) ───────────────────────────
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

const INSTITUTIONAL_DATA = {json.dumps(institutional_data, ensure_ascii=False, indent=2)};

const CAPITAL_STRUCTURE_DATA = {json.dumps(capital_structure_data, ensure_ascii=False, indent=2)};

const CAPITAL_STRUCTURE_BY_COMPANY = {json.dumps(capital_structure_by_company, ensure_ascii=False, indent=2)};

const INTERNACIONALIZACION_DATA = {json.dumps(internacionalizacion_data, ensure_ascii=False, indent=2)};

const SEGMENTACION_DATA = {json.dumps(segmentacion_data, ensure_ascii=False, indent=2)};
"""

with open(OUT, 'w', encoding='utf-8') as f:
    f.write(js)

print(f"data_web.js escrito ({len(js):,} chars)")
print(f"Grupos: {len(groups_data)}, Empresas: {len(companies_data)}")
print(f"Bloque de control: {prop_stats['n_majority']} de {prop_stats['n_with_pct']} >50%, mediana {prop_stats['median_pct']}%; "
      f"control mexicano {prop_stats['n_mx_controller']} de {prop_stats['n_with_controller']}; sin controlador {prop_stats['n_no_controller']}")
_cg = capital_structure_data['global']
print(f"Capital: total ${_cg['total_b']}B | ctrl MX {_cg['ctrl_mx_pct']}% | ctrl EXT {_cg['ctrl_ex_pct']}% | "
      f"cartera {_cg['float_pct']}% ({_cg['float_ext_pct']}% ext. por matriz) | mexicano total {_cg['mx_total_pct']}%")
print(f"Tenure: {len(tenure_data)} directores top, board_stats={board_stats}")
