# TITLE DETECTION
# @author: Hina Joshua

#import requirements

import pandas as pd
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTLine, LTTextLine

def extract_fontsize_title(fpath, title_character_size = 13):
    '''
    @type fpath: str
    @param pdf filepath 
    @type title_character_size: int 
    @param minimum fontsize to retain on first page of pdf
    @rtype cleaned_title: str 
    @rparam Title of pdf
    '''

    title_placeholder_text = 'Title not Found'
    try:
        title_texts =[] #initialize list of title strings
        for page_layout in extract_pages(fpath, page_numbers=[0], maxpages=5): #extract first page of pdf
            for element in page_layout: # iterate over each element on first page
                if isinstance(element, LTTextContainer): #confirm if element if a text container
                    for text_line in element: #iterate over each line in element
                        if isinstance(text_line, LTTextLine): #confirm that each line is a text line
                            for character in text_line: #iterate over each character of line
                                if isinstance(character, LTChar): #confirm that character is a text character
                                    if character.size > title_character_size: #if fontsize of charachter is above 13
                                        if len(element.get_text()) < 250: #get the text from this element if len str<250
                                            title_texts.append(element.get_text()) #append to title str list

        title_set = sorted(set(title_texts), key=title_texts.index) #remove duplicate string from title list
        titles_cleaned=[title.replace('\n', ' ') for title in title_set] #clean the strings
        cleaned_title =  ' '.join(titles_cleaned) #join all strings from the list to return one str

        return cleaned_title
    except:
        return title_placeholder_text 

