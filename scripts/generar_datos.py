#!/usr/bin/env python3
"""
Grupo Cementero — Generador de datos.json
Corre diariamente vía GitHub Actions. No requiere PC encendida.
"""
import json, os, sys, time
from datetime import date, timedelta
from collections import defaultdict

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests', '-q'])
    import requests

# ── Credenciales desde GitHub Secrets ────────────────────────────────────────
NAVIXY_HASH = os.environ['NAVIXY_HASH']
NAVIXY_URL  = 'https://api.navixy.com/v2'

TRACKER_ZONES = {408346:'DAVID',1048369:'CHITRE',1051266:'AGUADULCE',1669379:'TOCUMEN'}

# Grupos válidos — solo estos 5 aparecen en el dashboard
VALID_ZONES = {'DAVID', 'CHITRE', 'AGUADULCE', 'TOCUMEN', 'CHORRERA'}

# Nombres de visualización para el dashboard
ZONE_DISPLAY = {
    'DAVID':'David','CHITRE':'Chitre','AGUADULCE':'Agua Dulce',
    'TOCUMEN':'Tocumen','CHORRERA':'Chorrera',
}

GEO_ZONES = {
    'david':'DAVID','chiriqui':'DAVID','chitre':'CHITRE','chitré':'CHITRE',
    'aguadulce':'AGUADULCE','agua dulce':'AGUADULCE',
    'tocumen':'TOCUMEN','chorrera':'CHORRERA','la chorrera':'CHORRERA',
    # Zonas que antes aparecían sueltas → ahora las absorbemos
    'colon':'CHORRERA','colón':'CHORRERA','arraijan':'CHORRERA',
    'arraiján':'CHORRERA','santiago':'CHITRE','divisa':'CHITRE',
    'panama':'TOCUMEN','panamá':'TOCUMEN',
}
ZONE_COLORS = {
    'DAVID':'#F44336','TOCUMEN':'#FF9800','CHITRE':'#009688',
    'CHORRERA':'#8BC34A','AGUADULCE':'#3F51B5',
}

def get_zone(t):
    tid = t.get('tracker_id')
    if tid and tid in TRACKER_ZONES:
        return TRACKER_ZONES[tid]
    text = ' '.join(filter(None, [
        (t.get('location') or {}).get('address',''),
        t.get('description',''), t.get('label','')
    ])).lower()
    for kw, z in GEO_ZONES.items():
        if kw in text: return z
    return 'CHORRERA'

def task_list(offset, limit=100, from_str=None, to_str=None):
    url = f'{NAVIXY_URL}/task/list?hash={NAVIXY_HASH}&limit={limit}&offset={offset}'
    if from_str: url += f'&from={from_str}'
    if to_str:   url += f'&to={to_str}'
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

def tracker_tracks(tracker_id, from_str, to_str):
    """Fetch track list summary for a tracker. Returns total km, trips, hours."""
    try:
        # Construir URL manualmente para evitar que requests encodee los : de la fecha
        url = (f'{NAVIXY_URL}/track/list'
               f'?hash={NAVIXY_HASH}&tracker_id={tracker_id}'
               f'&from={from_str}&to={to_str}&limit=10000')
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        if not data.get('success'):
            return None
        total = data.get('total', {})
        km = round(total.get('length', 0), 1)
        trips = total.get('count', 0)
        # trip_duration is ISO 8601 duration like PT44H56M14S
        dur_str = total.get('trip_duration', 'PT0S')
        hours = _parse_iso_duration_hours(dur_str)
        # avg speed from trips
        lst = data.get('list', [])
        speeds = [t['avg_speed'] for t in lst if t.get('avg_speed', 0) > 0]
        avg_speed = round(sum(speeds)/len(speeds)) if speeds else 0
        return {'km': km, 'trips': trips, 'avg_speed': avg_speed, 'hours': round(hours, 1)}
    except requests.exceptions.HTTPError as e:
        print(f'  GPS error tracker {tracker_id}: {e}')
        try: print(f'  Response body: {e.response.text[:500]}')
        except: pass
        return None
    except Exception as e:
        print(f'  GPS error tracker {tracker_id}: {e}')
        return None

def _parse_iso_duration_hours(s):
    """Parse PT##H##M##S into float hours."""
    import re
    s = s.replace('PT','')
    h = re.search(r'(\d+)H', s)
    m = re.search(r'(\d+)M', s)
    sec = re.search(r'(\d+(?:\.\d+)?)S', s)
    return (int(h.group(1)) if h else 0) + (int(m.group(1)) if m else 0)/60 + (float(sec.group(1)) if sec else 0)/3600

# ── Fecha y periodo ───────────────────────────────────────────────────────────
today = date.today()
meses_corto = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']
meses = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto',
         'septiembre','octubre','noviembre','diciembre']
MES_PREFIX = today.strftime('%Y-%m')
FECHA_ISO  = today.isoformat()
FECHA_LARGA = f'{today.day} de {meses[today.month-1]} de {today.year}'
PERIODO = f'1 {meses_corto[today.month-1]} – {today.day} {meses_corto[today.month-1]} {today.year}'
from_str = f'{MES_PREFIX}-01 00:00:00'
to_str   = f'{FECHA_ISO} 23:59:59'

print(f'Fecha: {FECHA_LARGA}  |  Período: {PERIODO}')

# ── Fetch tareas del mes ──────────────────────────────────────────────────────
print('Obteniendo count...')
r0 = task_list(0, 1, from_str, to_str)
count = r0.get('count', 0)
batches = (count + 99) // 100
print(f'Total tareas mes: {count}  |  Lotes: {batches}')

all_tasks = {}
for i in range(batches):
    print(f'  Lote {i+1}/{batches}...')
    data = task_list(i * 100, 100, from_str, to_str)
    for t in data.get('list', []):
        all_tasks[t['id']] = t
    time.sleep(0.2)  # respetar rate limit

print(f'Tareas únicas del mes: {len(all_tasks)}')

# ── Procesar ──────────────────────────────────────────────────────────────────
active = [t for t in all_tasks.values() if t.get('tracker_id')]
TOTAL   = len(active)
DONE    = sum(1 for t in active if t['status'] == 'done')
DELAYED = sum(1 for t in active if t['status'] in ('failed', 'delayed'))
PCT     = round(DONE / TOTAL * 100, 1) if TOTAL else 0
print(f'Activas: {TOTAL}  |  Done: {DONE}  |  Delayed: {DELAYED}  |  PCT: {PCT}%')

zone_stats = defaultdict(lambda: {'done':0,'delayed':0,'total':0})
day_stats  = defaultdict(int)
# unit_stats: agrupa por CAMIÓN (tracker label), no por cliente
# {'done':0, 'delayed':0, 'zone':'CHORRERA', 'cliente':'...'}
unit_stats = defaultdict(lambda: {'done':0,'delayed':0,'zone':'CHORRERA','cliente':''})
# cli_stats: {cliente: {'count':0, 'destino': str}}
cli_stats  = defaultdict(lambda: {'count':0,'destino':''})
trend_stats = defaultdict(lambda: {'done':0,'delay':0,'unass':0})

# Mapa tracker_id -> nombre del tracker (se llenará después del fetch GPS)
tracker_id_to_label = {}

def get_destino(t):
    """Extrae el nombre del destino de location.address (parte antes del //)."""
    addr = (t.get('location') or {}).get('address', '') or ''
    if '//' in addr:
        return addr.split('//')[0].strip()
    return addr.strip()

for t in active:
    z = get_zone(t)
    zone_stats[z]['total'] += 1
    if t['status'] == 'done':               zone_stats[z]['done'] += 1
    elif t['status'] in ('failed','delayed'): zone_stats[z]['delayed'] += 1
    d = (t.get('from','') or '')[:10]
    if d: day_stats[d] += 1

    # Unidad = nombre del camión (tracker), Cliente = label de la tarea
    tid = t.get('tracker_id')
    camion = tracker_id_to_label.get(tid, f'Tracker {tid}') if tid else 'Sin asignar'
    cliente = t.get('label','Sin cliente').strip()
    unit_stats[camion]['zone'] = z
    unit_stats[camion]['cliente'] = cliente
    if t['status'] == 'done':               unit_stats[camion]['done'] += 1
    elif t['status'] in ('failed','delayed'): unit_stats[camion]['delayed'] += 1

    # cli_stats: Top Clientes
    cli = cliente or 'Sin cliente'
    destino = get_destino(t)
    if cli:
        cli_stats[cli]['count'] += 1
        if not cli_stats[cli]['destino'] and destino:
            cli_stats[cli]['destino'] = destino

for t in all_tasks.values():
    d = (t.get('from','') or '')[:10]
    if not d: continue
    if t['status'] == 'done':               trend_stats[d]['done'] += 1
    elif t['status'] in ('failed','delayed'): trend_stats[d]['delay'] += 1
    else:                                    trend_stats[d]['unass'] += 1

# Todos los días del mes con zeros
start_d = date(today.year, today.month, 1)
sorted_days = []
d_iter = start_d
while d_iter <= today:
    sorted_days.append(d_iter.isoformat())
    d_iter += timedelta(days=1)

# Solo los 6 grupos válidos, en orden fijo
ZONE_ORDER = ['DAVID','CHITRE','AGUADULCE','TOCUMEN','CHORRERA']
sorted_zones = [z for z in ZONE_ORDER if z in zone_stats]
# sorted_units se calcula DESPUÉS del re-proceso de unit_stats (ver abajo)
sorted_cli    = sorted(cli_stats.keys(), key=lambda c: -cli_stats[c]['count'])[:12]
sorted_trend  = sorted(trend_stats.keys())

def unit_pct(u):
    tot = unit_stats[u]['done'] + unit_stats[u]['delayed']
    return round(unit_stats[u]['done'] / tot * 100, 1) if tot > 0 else 0.0

def unit_color(pct):
    if pct >= 90: return '#8BC34A'
    if pct >= 70: return '#FF9800'
    if pct >= 50: return '#E65100'
    return '#C62828'

# ── Fetch lista de trackers → llenar tracker_id_to_label ─────────────────────
print('Obteniendo lista de trackers...')
all_trackers = []
try:
    tr = requests.get(f'{NAVIXY_URL}/tracker/list', params={'hash': NAVIXY_HASH}, timeout=30)
    tr.raise_for_status()
    all_trackers = tr.json().get('list', [])
    for tk in all_trackers:
        tracker_id_to_label[tk['id']] = tk.get('label', str(tk['id']))
    print(f'  {len(all_trackers)} trackers mapeados')
except Exception as e:
    print(f'  Error listando trackers: {e}')

# ── Re-procesar unit_stats ahora que tenemos tracker_id_to_label ──────────────
# (El loop anterior usó tracker_id_to_label vacío, re-hacemos unit_stats)
unit_stats.clear()
for t in active:
    z = get_zone(t)
    tid = t.get('tracker_id')
    camion = tracker_id_to_label.get(tid, f'Tracker {tid}') if tid else 'Sin asignar'
    cliente = t.get('label','Sin cliente').strip()
    unit_stats[camion]['zone'] = z
    unit_stats[camion]['cliente'] = cliente
    if t['status'] == 'done':               unit_stats[camion]['done'] += 1
    elif t['status'] in ('failed','delayed'): unit_stats[camion]['delayed'] += 1

# Ahora sí calculamos sorted_units con los nombres reales de camiones
sorted_units = sorted(unit_stats.keys(), key=lambda u: -(unit_stats[u]['done']+unit_stats[u]['delayed']))[:15]
print(f'  Unidades en ranking: {sorted_units[:5]}...')

# ── Fetch GPS stats (km, viajes, velocidad) por tracker ──────────────────────
print('Obteniendo GPS stats por tracker...')
tracker_gps = {}  # label -> {km, trips, avg_speed, hours}
for tk in all_trackers:
    tid = tk['id']
    lbl = tk.get('label', str(tid))
    try:
        print(f'  Tracker {lbl} (id={tid})...')
        stats = tracker_tracks(tid, from_str, to_str)
        if stats:
            tracker_gps[lbl] = stats
            print(f'    -> km={stats["km"]} viajes={stats["trips"]}')
        else:
            print(f'    -> sin datos')
    except Exception as e2:
        print(f'    -> error: {e2}')
    time.sleep(0.3)
print(f'  GPS stats: {len(tracker_gps)} trackers con datos')

# taskList completo
task_list_data = []
for t in sorted(all_tasks.values(), key=lambda x: x.get('from','') or ''):
    loc = t.get('location') or {}
    gz = get_zone(t)
    task_list_data.append({
        'label':   t.get('label','Sin asignar'),
        'destino': get_destino(t),
        'date':    (t.get('from','') or '')[:10],
        'status':  t['status'],
        'zone':    ZONE_DISPLAY.get(gz, gz),
        'color':   ZONE_COLORS.get(gz, '#9E9E9E'),
        'lat':     loc.get('lat') or 0,
        'lng':     loc.get('lng') or 0,
    })

datos = {
    'generado': FECHA_ISO,
    'fecha':    FECHA_LARGA,
    'periodo':  PERIODO,
    'kpi': {'total':TOTAL,'done':DONE,'delayed':DELAYED,'pct':PCT,'units':len(unit_stats)},
    'fleet': {
        'km':'N/A','trips':0,'speed_kmh':0,'idle_h':0,'mov_h':0,
        'units_active': f'{len([u for u in unit_stats if unit_stats[u]["done"]>0])}/{len(unit_stats)}'
    },
    'diasLabels':  [d[5:] for d in sorted_days],
    'diasVals':    [day_stats.get(d, 0) for d in sorted_days],
    'zoneNames':   [ZONE_DISPLAY.get(z, z) for z in sorted_zones],
    'zoneDone':    [zone_stats[z]['done']    for z in sorted_zones],
    'zoneDelay':   [zone_stats[z]['delayed'] for z in sorted_zones],
    'zoneTotals':  [zone_stats[z]['total']   for z in sorted_zones],
    'zoneColors':  [ZONE_COLORS.get(z,'#9E9E9E') for z in sorted_zones],
    'cliLabels':   sorted_cli,
    'cliDestinos': [cli_stats[c]['destino'] for c in sorted_cli],
    'cliVals':     [cli_stats[c]['count'] for c in sorted_cli],
    'trendLabels': [d[5:] for d in sorted_trend],
    'trendDone':   [trend_stats[d]['done']  for d in sorted_trend],
    'trendDelay':  [trend_stats[d]['delay'] for d in sorted_trend],
    'trendUnass':  [trend_stats[d]['unass'] for d in sorted_trend],
    'unitLabels':   sorted_units,
    'unitClientes': [unit_stats[u]['cliente'] for u in sorted_units],
    'unitDone':    [unit_stats[u]['done']    for u in sorted_units],
    'unitDelay':   [unit_stats[u]['delayed'] for u in sorted_units],
    'unitPct':     [unit_pct(u)             for u in sorted_units],
    'unitColors':  [unit_color(unit_pct(u)) for u in sorted_units],
    'ralentiData': [],
    'ralentiZones': [],
    'taskList':    task_list_data,
    'gpsStats':    tracker_gps,
}

with open('datos.json', 'w', encoding='utf-8') as f:
    json.dump(datos, f, ensure_ascii=False)

print(f'✅ datos.json generado — {len(task_list_data)} tareas en taskList')
