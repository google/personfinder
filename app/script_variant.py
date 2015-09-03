from unidecode import unidecode
import jautils
import logging

def script_variant_western(query):
    if jautils.should_normalize(query):
        hiragana_query = jautils.normalize(query)
        romaji_query = jautils.hiragana_to_romaji(hiragana_query)
        logging.info(unidecode(romaji_query))
    script_varianted_query = unidecode(query)
    return script_varianted_query


