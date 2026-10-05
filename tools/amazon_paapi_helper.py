#!/usr/bin/env python3
import sys
import os
import json

def get_short_amazon_url(asin, tag=""):
    """
    Genera la URL Canónica Oficial de Amazon compatible con OneLink.
    Los enlaces creados con OneLink redirigen automáticamente a EE.UU., UK y España.
    """
    if not asin:
        return ""
    clean_tag = tag.strip() if tag else ""
    if not clean_tag:
        return f"https://www.amazon.es/dp/{asin}"
    return f"https://www.amazon.es/dp/{asin}?tag={clean_tag}"

if __name__ == "__main__":
    test_asin = sys.argv[1] if len(sys.argv) > 1 else "B00Y09PZPW"
    tag_input = sys.argv[2] if len(sys.argv) > 2 else ""
    print(get_short_amazon_url(test_asin, tag_input))
