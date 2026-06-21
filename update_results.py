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
MT3 = []  # da definire


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
    """Costruisce dizionario {Casa-Ospite: {result, score_str}} dai dati API."""
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

        key = f"{home_it}-{away_it}"
        if status == 'FINISHED' and hs is not None and as_ is not None:
            if hs > as_:
                result = '1'
            elif hs == as_:
                result = 'X'
            else:
                result = '2'
            lookup[key] = {
                'result': result,
                'score': f"{hs}-{as_}"
            }
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
    """
    R = []
    SC = []
    for i, name in enumerate(match_names):
        api = lookup.get(name)
        cur_r = existing_R[i] if i < len(existing_R) else None
        cur_sc = existing_SC[i] if i < len(existing_SC) else None

        if api:
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
    return R, SC


def update_html(r1, sc1, r2, sc2):
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
    content = replace_var(content, 'SC1', sc1, let=False)
    content = replace_var(content, 'SC2', sc2, let=False)

    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(content)


if __name__ == '__main__':
    if not API_KEY:
        print("Errore: variabile FOOTBALL_API_KEY non impostata", file=sys.stderr)
        sys.exit(1)

    print("Fetching risultati da football-data.org...")
    data = fetch_matches()
    print(f"Partite ricevute: {data.get('count', '?')}")

    lookup = build_lookup(data)
    print(f"Partite finite trovate nell'API: {len(lookup)}")

    # Leggi i valori attualmente in index.html (mai sovrascrivere con null)
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        current = f.read()
    existing_r1 = parse_existing(current, 'R1', let=True)
    existing_sc1 = parse_existing(current, 'SC1', let=False)
    existing_r2 = parse_existing(current, 'R2', let=True)
    existing_sc2 = parse_existing(current, 'SC2', let=False)

    print("\nT1:")
    r1, sc1 = build_arrays(MT1, lookup, existing_r1, existing_sc1)
    print("\nT2:")
    r2, sc2 = build_arrays(MT2, lookup, existing_r2, existing_sc2)

    update_html(r1, sc1, r2, sc2)
    print("\nindex.html aggiornato.")
