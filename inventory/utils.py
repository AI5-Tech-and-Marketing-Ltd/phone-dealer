import requests

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
    Placeholder for 3rd-party IMEI API integration.
    You can use services like imei.info or similar.
    """
    # Placeholder implementation
    return {
        "imei": imei,
        "valid": validate_imei(imei),
        "brand_guess": "Unknown",
        "model_guess": "Unknown",
    }
