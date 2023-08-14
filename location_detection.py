# @author - Sidra Effendi
import spacy
from iso3166 import countries, Country
from collections import Counter

nlp = spacy.load('en_core_web_md')

# creating a dict for valid country names
INDEX = {c.name.upper(): c for c in countries}

def extract_locations(content):
    '''#using namer entity recognition to detect potential location the content
    # some non-locations are also detected to be locations
    # get countries, states, counties and some junk as well

    @type: string
    @param: content extracted from the document
    @rtype: list of string(uppercase)
    @rparam: location detected in the document content
    '''

    # using namer entity recognition from spacy
    nlped = nlp(content)

    # get the words/text labelled as GPE
    extracted_locations_list = [(x.text.replace('\n', '').upper())
                                for x in nlped.ents if x.label_ == 'GPE']

    return extracted_locations_list


def replace_dict_key_name(key_map, dict_with_keys_to_replace):
    ''' replace old key name with a new name

      @type: dict (upper case)
      @param key_map: the key is the name we want to replace and value is what we want to replace it with {oldkey: newkey}
      @type: dict
      @param dict_with_keys_to_replace: locations are the keys and values are their count of occurence in the docuement
      @rtype: dict
      @rparam: listed locations replaced with iso codes
    '''
    # replace old key with new key
    for (oldkey, newkey) in key_map.items():
        # check key is on the dict
        if oldkey in dict_with_keys_to_replace:
            dict_with_keys_to_replace[newkey] = dict_with_keys_to_replace.pop(
                oldkey)

    return dict_with_keys_to_replace


def detected_potential_countries(content):
    # extract the countries spacy detects
    loc_list = extract_locations(content)
    if len(loc_list) == 0:
        return {}
    # count location instance
    count_of_locations = dict(Counter(loc_list).most_common())
    

    # for test demo
    # capitalized_loc_list = [x.capitalize() for x in loc_list] #can be deleted later
    # pretty_print_dict(dict(Counter(capitalized_loc_list)))

    # some of the location names are not in accordance with current ISO names
    # replacing them with ISO code enables proper detection
    # set the keys in uppercase
    key_map = {'UK': 'GB', 'UNITED KINGDOM': 'GB',
               'TURKEY': 'Türkiye'}
    clean_loc_dict = replace_dict_key_name(key_map, count_of_locations)


    # get valid country information
    valid_countries_dict = get_valid_countries(clean_loc_dict)
    return valid_countries_dict


def tuple_to_dict(tuple_to_con, occurence_count):
    new_dict = {}
    new_dict = tuple_to_con._asdict()
    new_dict['no_of_occurences'] = occurence_count

    return new_dict


def sub_get(partial_name: str) -> Country or None:
    """
    Get the single matching Country from a partial name.
    partial_name:  The country name, or sub-string thereof, to find.
    Return:  None, or the fuzzy matching country name.

    This function is copied from https://github.com/deactivated/python-iso3166/issues/28
    """
    name = partial_name.upper()
    country = None
    for key in INDEX:
        if name in key:  # Crux   ###
            if country is not None:
                # Ambiguous partial_name
                raise KeyError
            country = INDEX[key]

    return country


def get_valid_countries(locations_dict):
    ''' check if the dict key is a valid country name or is a subtring of country name
       and return info about it

      @type: dict
      @param locations_list: list of locations to check
      @rtype: list of tuples
      @rparam: tuple with info of valid countries detected along with no.of occurences
    '''
    # it is best to first just check for the general way and then add the sub string part on it
    # Country(name='United States of America', alpha2='US', alpha3='USA', numeric='840', apolitical_name='United States of America')

    # new_dict={}
    with_count_dict = {}
    complete_tuple = {}

    for key_name in locations_dict.keys():
        try:
            country_info = countries.get(key_name)
            country_name = country_info.name
            if country_name not in with_count_dict:
                dict_with_count = tuple_to_dict(
                    country_info, locations_dict[key_name])
                complete_tuple[country_name] = country_info
                with_count_dict[country_name] = dict_with_count  # nested dict

        except:
            try:
                # check if it is a substring
                country_info_sub = countries.get(sub_get(key_name).name)
                country_name_sub = country_info_sub.name
                if country_name_sub in with_count_dict:
                    with_count_dict[country_name_sub]['no_of_occurences'] = with_count_dict[
                        country_name_sub]['no_of_occurences'] + locations_dict[key_name]
                else:
                    new_dict = tuple_to_dict(
                        country_info_sub, locations_dict[key_name])
                    with_count_dict[country_name_sub] = new_dict

            except:
                pass

    #
    # #i can give option to extract the different codes from the name and other things as well
    # # I can cross-reference the about country on the title page
    # #replace uk by GB because it won't be detected otherwise
    # #to detect where the document was written I can look at the last few pages and see the address

    return with_count_dict
