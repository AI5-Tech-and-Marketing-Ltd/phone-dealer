import csv
from .models import TacRecord

def parse_csv_row(row: list) -> dict | None:
    """Map a tacdb-style CSV row to a dict suitable for TacRecord."""
    if not row or not row[0].strip().isdigit():
        return None
    
    # tac,brand,name,contributor,comment,gsmarena_1,gsmarena_2,aka
    aka_raw = row[7] if len(row) > 7 else ''
    return {
        'tac':         row[0].strip(),
        'brand':       row[1].strip() if len(row) > 1 else '',
        'name':        row[2].strip() if len(row) > 2 else '',
        'contributor': row[3].strip() if len(row) > 3 else '',
        'comment':     row[4].strip() if len(row) > 4 else '',
        'gsmarena_1':  row[5].strip() if len(row) > 5 else '',
        'gsmarena_2':  row[6].strip() if len(row) > 6 else '',
        'aka':         [a.strip() for a in aka_raw.split(',') if a.strip()],
    }

def upsert_tac_records(records: list[dict]) -> dict:
    """
    Bulk upsert a list of TAC dicts.
    Returns {'created': n, 'updated': n, 'skipped': n, 'errors': [...]}
    """
    created = updated = skipped = 0
    errors = []

    for rec in records:
        tac = rec.get('tac', '').strip()
        if not tac or not tac.isdigit() or len(tac) != 8:
            errors.append({'tac': tac, 'error': 'Invalid TAC — must be 8 digits'})
            skipped += 1
            continue
        try:
            obj, was_created = TacRecord.objects.update_or_create(
                tac=tac,
                defaults={k: v for k, v in rec.items() if k != 'tac'},
            )
            if was_created:
                created += 1
            else:
                updated += 1
        except Exception as e:
            errors.append({'tac': tac, 'error': str(e)})
            skipped += 1

    return {'created': created, 'updated': updated, 'skipped': skipped, 'errors': errors}
