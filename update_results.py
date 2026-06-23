#!/usr/bin/env python3
"""
Aggiorna automaticamente R1, R2, SC1, SC2 in index.html
con i risultati reali del Mondiale 2026 da football-data.org
"""

import urllib.request
import json
import re
import os
import sys

API_KEY = os.environ.get('FOOTBALL_API_KEY', '')
INDEX_FILE = os.path.join(os.path.dirname(__file__), 'index.html')

# Mappa nomi API (inglese) → nomi italiani usati nel sito
TEAM_MAP = {
    'Mexico':                   'Messico',
    'South Africa':             'Sud Africa',
    'Korea Republic':           'Corea',
    'South Korea':              'Corea',
    'Czech Republic':           'Rep.Ceca',
    'Czechia':                  'Rep.Ceca',
    'Canada':                   'Canada',
    'Bosnia and Herzegovina':   'Bosnia',
    'Qatar':                    'Qatar',
    'Switzerland':              'Svizzera',
    'Brazil':                   'Brasile',
    'Morocco':                  'Marocco',
    'Haiti':                    'Haiti',
    'Scotland':                 'Scozia',
    'United States':            'USA',
    'USA':                      'USA',
    'Paraguay':                 'Paraguay',
    'Australia':                'Australia',
    'Turkey':                   'Turchia',
    'Türkiye':                  'Turchia',
    'Germany':                  'Germania',
    "Côte d'Ivoire":            'C.Avorio',
    'Ivory Coast':              'C.Avorio',
    'Ecuador':                  'Ecuador',
    'Curaçao':                  'Curacao',
    'Netherlands':              'Olanda',
    'Japan':                    'Giappone',
    'Sweden':                   'Svezia',
    'Tunisia':                  'Tunisia',
    'Belgium':                  'Belgio',
    'Egypt':                    'Egitto',
    'Iran':                     'Iran',
    'New Zealand':              'N.Zelanda',
    'Spain':                    'Spagna',
    'Uruguay':                  'Uruguay',
    'Saudi Arabia':             'Arabia',
    'Cape Verde':               'C.Verde',
    'France':                   'Francia',
    'Senegal':                  'Senegal',
    'Norway':                   'Norvegia',
    'Iraq':                     'Iraq',
    'Argentina':                'Argentina',
    'Algeria':                  'Algeria',
    'Austria':                  'Austria',
    'Jordan':                   'Giordania',
    'Portugal':                 'Portogallo',
    'Colombia':                 'Colombia',
    'Uzbekistan':               'Uzbekistan',
    'DR Congo':                 'Dr Congo',
    'Congo DR':                 'Dr Congo',
    'England':                  'Inghilterra',
    'Croatia':                  'Croazia',
    'Ghana':                    'Ghana',
    'Panama':                   'Panama',
}

# Le 13 partite per turno (nomi italiani, formato "Casa-Ospite")
MT1 = [
    "Messico-Sud Africa", "Canada-Bosnia", "USA-Paraguay", "Brasile-Marocco",
    "Australia-Turchia", "Olanda-Giappone", "Svezia-Tunisia", "Belgio-Egitto",
    "Francia-Senegal", "Austria-Giordania", "Inghilterra-Croazia",
    "Ghana-Panama", "Uzbekistan-Colombia"
]
MT2 = [
    "Rep.Ceca-Sud Africa", "Canada-Qatar", "Scozia-Marocco", "Turchia-Paraguay",
    "Germania-C.Avorio", "Tunisia-Giappone", "Belgio-Iran", "N.Zelanda-Egitto",
    "Argentina-Austria", "Norvegia-Senegal", "Giordania-Algeria",
    "Inghilterra-Ghana", "Colombia-Dr Congo"
]
MT3 = [
    "Svizzera-Canada", "Bosnia-Qatar", "Sud Africa-Corea", "Rep.Ceca-Messico",
    "Ecuador-Germania", "Tunisia-Olanda", "Giappone-Svezia", "Turchia-USA",
    "Norvegia-Francia", "Uruguay-Spagna", "Egitto-Iran", "Colombia-Portogallo",
    "Algeria-Austria"
]


def fetch_matches():
    url = 'https://api.football-data.org/v4/competitions/WC/matches?season=2026'
    req = urllib.request.Request(url, headers={'X-Auth-Token': API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"Errore fetch API: {e}", file=sys.stderr)
        sys.exit(1)


def build_lookup(data):
    """Costruisce dizionario {Casa-Ospite: {result, score, date}} dai dati API.
    Indicizza entrambi gli ordini (Casa-Ospite e Ospite-Casa) per resistere
    a discrepanze home/away rispetto ai nomi hardcoded in MT1/MT2.
    """
    from datetime import datetime, timezone, timedelta

    lookup = {}
    for m in data.get('matches', []):
        home_api = m['homeTeam']['name']
        away_api = m['awayTeam']['name']
        home_it = TEAM_MAP.get(home_api, home_api)
        away_it = TEAM_MAP.get(away_api, away_api)
        status = m.get('status', '')
        score = m.get('score', {}).get('fullTime', {})
        hs = score.get('home')
        as_ = score.get('away')

        # Estrai data/ora CET (UTC+2 in estate)
        utc_date = m.get('utcDate', '')
        date_str = None
        if utc_date:
            try:
                dt_utc = datetime.fromisoformat(utc_date.replace('Z', '+00:00'))
                dt_cet = dt_utc + timedelta(hours=2)
                date_str = dt_cet.strftime('%d/%m - %H:%M')
            except Exception:
                pass

        entry_fwd = {'date': date_str}
        entry_rev = {'date': date_str}

        if status == 'FINISHED' and hs is not None and as_ is not None:
            if hs > as_:
                result_fwd, result_rev = '1', '2'
            elif hs == as_:
                result_fwd = result_rev = 'X'
            else:
                result_fwd, result_rev = '2', '1'
            entry_fwd.update({'result': result_fwd, 'score': f"{hs}-{as_}"})
            entry_rev.update({'result': result_rev, 'score': f"{as_}-{hs}"})

        lookup[f"{home_it}-{away_it}"] = entry_fwd
        lookup[f"{away_it}-{home_it}"] = entry_rev

    return lookup


def parse_existing(content, name, let=True):
    """Legge il valore attuale di una variabile JS dall'HTML."""
    kw = 'let' if let else 'const'
    m = re.search(rf'{kw} {name} = \[(.*?)\];', content)
    if not m:
        return [None] * 13
    raw = m.group(1).split(',')
    result = []
    for v in raw:
        v = v.strip()
        if v == 'null':
            result.append(None)
        else:
            result.append(v.strip('"'))
    return result


def build_arrays(match_names, lookup, existing_R, existing_SC):
    """
    Regola fondamentale: aggiorna solo se l'API restituisce FINISHED.
    Non sovrascrive mai un valore esistente con null.
    Restituisce anche le date (DT) per ogni partita.
    """
    R = []
    SC = []
    DT = []
    for i, name in enumerate(match_names):
        api = lookup.get(name)
        cur_r = existing_R[i] if i < len(existing_R) else None
        cur_sc = existing_SC[i] if i < len(existing_SC) else None

        date_val = f'"{api["date"]}"' if api and api.get('date') else 'null'
        DT.append(date_val)

        if api and api.get('result'):
            # L'API ha un risultato confermato → aggiorna sempre
            R.append(f'"{api["result"]}"')
            SC.append(f'"{api["score"]}"')
            if cur_r and cur_r != api["result"]:
                print(f"  UPDATE {name}: {cur_r} → {api['result']} ({api['score']})")
            elif not cur_r:
                print(f"  NEW    {name}: {api['result']} ({api['score']})")
        elif cur_r:
            # API non ha il risultato ma ne abbiamo già uno → mantieni
            R.append(f'"{cur_r}"')
            SC.append(f'"{cur_sc}"' if cur_sc else 'null')
            print(f"  KEEP   {name}: {cur_r} (non trovato in API)")
        else:
            # Nessuno ha niente → null
            R.append('null')
            SC.append('null')
    return R, SC, DT


def update_html(r1, sc1, r2, sc2, r3, sc3, dt1, dt2, dt3):
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    def replace_var(content, name, values, let=True):
        kw = 'let' if let else 'const'
        new_val = f'{kw} {name} = [{",".join(values)}];'
        pattern = rf'{kw} {name} = \[.*?\];'
        updated, n = re.subn(pattern, new_val, content)
        if n == 0:
            print(f"WARN: {name} non trovato in index.html", file=sys.stderr)
        return updated

    content = replace_var(content, 'R1', r1, let=True)
    content = replace_var(content, 'R2', r2, let=True)
    content = replace_var(content, 'R3', r3, let=True)
    content = replace_var(content, 'SC1', sc1, let=False)
    content = replace_var(content, 'SC2', sc2, let=False)
    content = replace_var(content, 'SC3', sc3, let=False)
    content = replace_var(content, 'DT1', dt1, let=True)
    content = replace_var(content, 'DT2', dt2, let=True)
    content = replace_var(content, 'DT3', dt3, let=True)

    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(content)


if __name__ == '__main__':
    if not API_KEY:
        print("Errore: variabile FOOTBALL_API_KEY non impostata", file=sys.stderr)
        sys.exit(1)

    print("Fetching risultati da football-data.org...")
    data = fetch_matches()
    n_matches = len(data.get('matches', []))
    print(f"Partite ricevute: {n_matches}")

    lookup = build_lookup(data)
    print(f"Partite finite trovate nell'API: {len(lookup)}")

    # Leggi i valori attualmente in index.html (mai sovrascrivere con null)
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        current = f.read()
    existing_r1 = parse_existing(current, 'R1', let=True)
    existing_sc1 = parse_existing(current, 'SC1', let=False)
    existing_r2 = parse_existing(current, 'R2', let=True)
    existing_sc2 = parse_existing(current, 'SC2', let=False)
    existing_r3 = parse_existing(current, 'R3', let=True)
    existing_sc3 = parse_existing(current, 'SC3', let=False)

    print("\nT1:")
    r1, sc1, dt1 = build_arrays(MT1, lookup, existing_r1, existing_sc1)
    print("\nT2:")
    r2, sc2, dt2 = build_arrays(MT2, lookup, existing_r2, existing_sc2)
    print("\nT3:")
    r3, sc3, dt3 = build_arrays(MT3, lookup, existing_r3, existing_sc3)

    update_html(r1, sc1, r2, sc2, r3, sc3, dt1, dt2, dt3)
    print("\nindex.html aggiornato.")
