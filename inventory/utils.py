import csv
import os
from django.conf import settings

def validate_imei(imei: str) -> bool:
    """Luhn checksum validation for 15-digit IMEI."""
    if not imei.isdigit() or len(imei) != 15:
        return False

    imei_list = [int(d) for d in imei]
    check_sum = 0
    
    for i in range(14):
        d = imei_list[i]
        if i % 2 == 1: # 2nd digit in a 2-pair set
            d *= 2
            if d > 9:
                d = (d // 10) + (d % 10)
        check_sum += d
    
    return (10 - (check_sum % 10)) % 10 == imei_list[14]

def fetch_imei_info(imei: str):
    """
    Fetch device details from tacdb.csv based on the TAC (first 8 digits).
    """
    tac = imei[:8]
    file_path = os.path.join(settings.BASE_DIR, 'tacdb.csv')
    
    if not os.path.exists(file_path):
         return {
             "imei": imei,
             "valid": validate_imei(imei),
             "error": "TAC database not found."
         }

    try:
        with open(file_path, mode='r', encoding='utf-8') as csvfile:
            # Skip the first comment line
            # Osmocom TAC database under CC-BY-SA v3.0 (c) Harald Welte 2016
            next(csvfile)
            
            reader = csv.reader(csvfile)
            header = next(reader) # tac,name,name,contributor,comment,gsmarena,gsmarena,aka
            
            for row in reader:
                if len(row) > 0 and row[0] == tac:
                    # Found the record
                    # Index 1: name (brand), Index 2: name (device), Index 7: aka
                    brand = row[1] if len(row) > 1 else "Unknown"
                    model = row[2] if len(row) > 2 else "Unknown"
                    aka_raw = row[7] if len(row) > 7 else ""
                    aka_list = [a.strip() for a in aka_raw.split(',')] if aka_raw else []

                    return {
                        "imei": imei,
                        "tac": tac,
                        "brand": brand,
                        "name": model,
                        "aka": aka_list,
                        "valid": validate_imei(imei)
                    }
    except Exception as e:
        return {
            "imei": imei,
            "valid": validate_imei(imei),
            "error": str(e)
        }

    return {
        "imei": imei,
        "tac": tac,
        "valid": validate_imei(imei),
        "found": False,
        "message": "TAC not found in database."
    }
