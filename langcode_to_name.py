# @author - Hina Joshua
import pandas as pd
#pip install iso-639
from iso639 import languages

def get_lang_name(lang_code):
    ''' convert language code string to laguagae full name string
      @type: list
      @param lang_list: list of language codes
      @rtype: list
      @rparam: list of language names
    '''
    lang_name = languages.get(alpha2=lang_code).name
    return lang_name
