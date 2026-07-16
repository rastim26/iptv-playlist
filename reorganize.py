#!/usr/bin/env python3
"""
Reorganize tv-team.m3u8 groups per approved plan.

Changes:
- Strip old numeric prefixes from all group names
- Renumber all non-Turkish groups 1-29 in final order
- Turkish groups (TR:) left unchanged
"""

import sys
from collections import defaultdict, Counter

INPUT  = '/Users/rastim/dev/iptv-playlist/tv-team.m3u8'
OUTPUT = '/Users/rastim/dev/iptv-playlist/tv-team.m3u8'

# ── Map every current group name → new numbered group name ───────────────────
GROUP_MAP = {
    # Old numbered → new numbered (strip old number, apply new)
    '3. Movies':           '1. Movies',
    '4. Cinemas':          '2. Cinemas',
    'Action':              '3. Action',
    'Adventure':           '4. Adventure',
    'Comedy':              '5. Comedy',
    'Drama':               '6. Drama',
    'Horror':              '7. Horror',
    'Fantasy':             '8. Sci-Fi',   # Fantasy merges into Sci-Fi
    'Sci-Fi':              '8. Sci-Fi',
    'Thriller':            '9. Thriller & Detective',
    'Detective':           '9. Thriller & Detective',
    'Thriller & Detective':'9. Thriller & Detective',
    '6. UHD':              '10. UHD',
    '7. HDR':              '11. HDR',
    'Family':              '12. Family',
    'Kids':                '13. Kids',
    'TV Series':           '14. TV Series',
    'Russian Movies':      '15. Russian Movies',
    'Russian TV Series':   '16. Russian TV Series',
    '1. Federal':          '17. Federal',
    '2. News':             '18. News',
    '5. Авторские каналы': '19. Авторские каналы',
    '9. Sport':            '20. Sport',
    '10. Music':           '21. Music',
    '11. Educational':     '22. Educational',
    '12. Nature':          '23. Nature',
    'Documentary':         '24. Documentary',
    'History':             '25. History',
    # Rest sub-groups (new names already applied from previous run)
    'Cooking & Food':      '26. Cooking & Food',
    'Lifestyle':           '27. Lifestyle',
    'Religion':            '28. Religion',
    'Entertainment':       '29. Entertainment',
    # Turkish groups — unchanged
    'TR: Genel':  'TR: Genel',
    'TR: Haber':  'TR: Haber',
    'TR: Film':   'TR: Film',
    'TR: Dizi':   'TR: Dizi',
    'TR: Kids':   'TR: Kids',
    'TR: Spor':   'TR: Spor',
    'TR: Explore':'TR: Explore',
    # Handle 13. Rest in case file still has it (idempotency)
    '13. Rest':   '29. Entertainment',  # will be overridden by channel-name logic below
}

# ── Channels that belong to specific sub-groups (split from 13. Rest) ────────
COOKING_CHANNELS = {
    'Кухня ТВ HD', 'Foodtime HD', 'Еда', 'Первый Вегетарианский',
    'Food Network HD', 'Аппетитный HD', 'Yosso TV Food', 'BOX Gurman HD',
    'TVPlay Вкусное TV',
}
LIFESTYLE_CHANNELS = {
    'АВТО 24', 'Авто плюс HD', 'Fashion TV HD', 'HТB Cтиль', 'Ю',
    'Сарафан', 'Психология', 'Успех', 'Тонус', 'Театр HD', 'Арт',
}
RELIGION_CHANNELS = {'Спас', 'Союз', 'Доверие'}

REST_GROUPS = {'13. Rest', '26. Cooking & Food', '27. Lifestyle', '28. Religion', '29. Entertainment'}

# ── Final group order ─────────────────────────────────────────────────────────
GROUP_ORDER = [
    '1. Movies', '2. Cinemas', '3. Action', '4. Adventure', '5. Comedy',
    '6. Drama', '7. Horror', '8. Sci-Fi', '9. Thriller & Detective',
    '10. UHD', '11. HDR', '12. Family', '13. Kids', '14. TV Series',
    '15. Russian Movies', '16. Russian TV Series',
    '17. Federal', '18. News', '19. Авторские каналы', '20. Sport',
    '21. Music', '22. Educational', '23. Nature', '24. Documentary', '25. History',
    '26. Cooking & Food', '27. Lifestyle', '28. Religion', '29. Entertainment',
    'TR: Genel', 'TR: Haber', 'TR: Film', 'TR: Dizi',
    'TR: Kids', 'TR: Spor', 'TR: Explore',
]


def remap(name, current_group):
    # Rest channels: determine sub-group by channel name
    if current_group in REST_GROUPS:
        if name in COOKING_CHANNELS: return '26. Cooking & Food'
        if name in LIFESTYLE_CHANNELS: return '27. Lifestyle'
        if name in RELIGION_CHANNELS: return '28. Religion'
        return '29. Entertainment'
    return GROUP_MAP.get(current_group, current_group)


def parse_m3u8(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    header = lines[0].rstrip('\n')
    channels = []
    i = 1
    while i < len(lines):
        line = lines[i].rstrip('\n')
        if line.startswith('#EXTINF:'):
            extinf = line
            name = extinf.split(',')[-1].strip()
            extgrp = url = None
            i += 1
            while i < len(lines):
                nxt = lines[i].rstrip('\n')
                if nxt.startswith('#EXTGRP:'):
                    extgrp = nxt[len('#EXTGRP:'):]
                    i += 1
                elif nxt.startswith('http'):
                    url = nxt
                    i += 1
                    break
                elif nxt == '' or nxt.startswith('#EXTINF:'):
                    break
                else:
                    i += 1
            channels.append({'extinf': extinf, 'extgrp': extgrp, 'url': url, 'name': name})
        else:
            i += 1
    return header, channels


def main():
    print(f'Reading {INPUT}...')
    header, channels = parse_m3u8(INPUT)
    print(f'Parsed {len(channels)} channels')

    # Assign new groups
    for ch in channels:
        ch['new_group'] = remap(ch['name'], ch['extgrp'] or '')

    # Warn about unmapped groups
    known = set(GROUP_ORDER)
    for ch in channels:
        if ch['new_group'] not in known:
            print(f"WARNING: unmapped group {ch['new_group']!r} for channel {ch['name']!r}", file=sys.stderr)

    # Bucket by new group
    buckets = defaultdict(list)
    for ch in channels:
        buckets[ch['new_group']].append(ch)

    # Build output
    out = [header + '\n']
    for group in GROUP_ORDER:
        for ch in buckets.get(group, []):
            out.append(ch['extinf'] + '\n')
            out.append(f'#EXTGRP:{group}\n')
            if ch['url']:
                out.append(ch['url'] + '\n')

    out_count = sum(1 for l in out if l.startswith('#EXTINF:'))
    print(f'Output channels: {out_count}')

    if out_count != len(channels):
        print(f'ERROR: count mismatch {len(channels)} → {out_count}', file=sys.stderr)
        sys.exit(1)

    out_groups = Counter(l[len('#EXTGRP:'):].strip() for l in out if l.startswith('#EXTGRP:'))
    print('\nFinal group counts:')
    for g in GROUP_ORDER:
        if g in out_groups:
            print(f'  {out_groups[g]:4d}  {g}')

    print(f'\nWriting {OUTPUT}...')
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.writelines(out)
    print('Done.')


if __name__ == '__main__':
    main()
