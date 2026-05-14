# @author - Sidra Effendi
from collections import Counter
from typing import Any

import pycountry_convert as pc
from iso3166 import Country, countries

_nlp = None


def get_nlp():
    global _nlp
    if _nlp is None:
        import spacy

        _nlp = spacy.load("en_core_web_sm")
    return _nlp


# creating a dict for valid country names
INDEX = {c.name.upper(): c for c in countries}


def country_to_continent(country_name: str) -> str:
    country_alpha2 = pc.country_name_to_country_alpha2(country_name)
    country_continent_code = pc.country_alpha2_to_continent_code(country_alpha2)
    country_continent_name = pc.convert_continent_code_to_continent_name(country_continent_code)
    return str(country_continent_name)


def extract_locations(content: str) -> list[str]:
    """#using namer entity recognition to detect potential location the content
    # some non-locations are also detected to be locations
    # get countries, states, counties and some junk as well

    @type: string
    @param: content extracted from the document
    @rtype: list of string(uppercase)
    @rparam: location detected in the document content
    """

    # using namer entity recognition from spacy
    nlp = get_nlp()
    nlped = nlp(content)

    # get the words/text labelled as GPE
    extracted_locations_list = [(x.text.replace("\n", "").upper()) for x in nlped.ents if x.label_ == "GPE"]

    return extracted_locations_list


def replace_dict_key_name(key_map: dict, dict_with_keys_to_replace: dict) -> dict:
    """replace old key name with a new name

    @type: dict (upper case)
    @param key_map: the key is the name we want to replace and value is what we want to replace it with {oldkey: newkey}
    @type: dict
    @param dict_with_keys_to_replace: locations are the keys and values are their count of occurence in the docuement
    @rtype: dict
    @rparam: listed locations replaced with iso codes
    """
    # replace old key with new key
    for oldkey, newkey in key_map.items():
        # check key is on the dict
        if oldkey in dict_with_keys_to_replace:
            dict_with_keys_to_replace[newkey] = dict_with_keys_to_replace.pop(oldkey)

    return dict_with_keys_to_replace


def detected_potential_countries(content: str) -> dict:
    # extract the countries spacy detects
    loc_list = extract_locations(content)
    if len(loc_list) == 0:
        return {}
    # count location instance
    count_of_locations = dict(Counter(loc_list).most_common())

    # some of the location names are not in accordance with current ISO names
    # replacing them with ISO code enables proper detection
    # set the keys in uppercase
    key_map = {"UK": "GB", "UNITED KINGDOM": "GB", "TURKEY": "Türkiye"}
    clean_loc_dict = replace_dict_key_name(key_map, count_of_locations)

    # get valid country information
    valid_countries_dict = get_valid_countries(clean_loc_dict)

    coun_appearance = []
    continents = set()
    for key, value in valid_countries_dict.items():
        if key in ["GLOBAL", "REGIONAL"]:
            continue
        coun_appearance.append((key, value["no_of_occurences"]))

    # Sort the list by value in descending order
    sorted_countries = sorted(coun_appearance, key=lambda x: x[1], reverse=True)

    for country in sorted_countries:
        if country[0].upper() == "UNITED STATES OF AMERICA":
            continents.add(country_to_continent("United States"))
        else:
            try:
                continents.add(country_to_continent(country[0]))
            except Exception:
                pass

    # Check if the problem is global
    if len(continents) > 2:
        valid_countries_dict["GLOBAL"] = True
    else:
        valid_countries_dict["GLOBAL"] = False

    # check if the problem is regional
    if (len(continents) == 1) and (len(sorted_countries) > 1):
        valid_countries_dict["REGIONAL"] = True
    else:
        valid_countries_dict["REGIONAL"] = False

    return valid_countries_dict


def tuple_to_dict(tuple_to_con: Any, occurence_count: int) -> dict:
    new_dict = tuple_to_con._asdict()
    new_dict["no_of_occurences"] = occurence_count

    return new_dict


def sub_get(partial_name: str) -> Country | None:
    """
    Get the single matching Country from a partial name.
    """
    name = partial_name.upper()
    country = None
    for _, value in INDEX.items():
        if name in value.name.upper():
            if country is not None:
                # Ambiguous partial_name
                raise KeyError
            country = value

    return country


def get_valid_countries(locations_dict: dict) -> dict:
    """check if the dict key is a valid country name or is a subtring of country name
    and return info about it
    """
    with_count_dict: dict[str, Any] = {}
    complete_tuple = {}

    for key_name, value in locations_dict.items():
        try:
            country_info = countries.get(key_name)
            country_name = country_info.name
            if country_name not in with_count_dict:
                dict_with_count = tuple_to_dict(country_info, value)
                complete_tuple[country_name] = country_info
                with_count_dict[country_name] = dict_with_count  # nested dict

        except Exception:
            try:
                # check if it is a substring
                res = sub_get(key_name)
                if res:
                    country_info_sub = countries.get(res.name)
                    country_name_sub = country_info_sub.name
                    if country_name_sub in with_count_dict:
                        with_count_dict[country_name_sub]["no_of_occurences"] = (
                            with_count_dict[country_name_sub]["no_of_occurences"] + value
                        )
                    else:
                        new_dict = tuple_to_dict(country_info_sub, value)
                        with_count_dict[country_name_sub] = new_dict

            except Exception:
                pass

    return with_count_dict
