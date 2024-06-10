# -*- coding: utf-8 -*-
"""
Created on Sun Jun  9 20:08:37 2024

@author: socam
"""

import fitz


def scrape(file):
    results = [] # list of tuples that store the information as (text, font size, font name)
    pdf = fitz.open(stream=file, filetype="pdf") # filePath is a string that contains the path to the pdf
    page = pdf[0]
    dict = page.get_text("dict", sort=True)
    blocks = dict["blocks"]
    for block in blocks:
        if "lines" in block.keys():
            spans = block['lines']
            for span in spans:
                data = span['spans']
                for lines in data:
                    results.append((lines['text'], lines['size'], lines['font']))
                        # lines['text'] -> string, lines['size'] -> font size, lines['font'] -> font name
    pdf.close()
    return results


def print_titles(file):
    
    page_blocks = scrape(file)

    text_blocks = []
    aux_list = list(page_blocks[0])
    
    for line_num in range(1,len(page_blocks)):
        
        if (page_blocks[line_num][0] == " ") | (page_blocks[line_num][0] == ""):
            continue
    
        if (round(page_blocks[line_num][1],2) == round(page_blocks[line_num-1][1],2)
           ) & (page_blocks[line_num][2] == page_blocks[line_num-1][2]):
            aux_list[0] += " " + page_blocks[line_num][0]
        else:
            aux_list[1] = round(aux_list[1],2)
            text_blocks.append(tuple(aux_list))
            aux_list = list(page_blocks[line_num])
            
    aux_list[1] = round(aux_list[1],2)
    text_blocks.append(tuple(aux_list))
    
    biggest_char_sizes = 2
    biggest_vals = list(set([block[1] for block in text_blocks]))
    biggest_vals.sort(reverse=True)
    biggest_vals = biggest_vals[:biggest_char_sizes]
    

    
    title_options_list = []
    page1_text = ""
    for block in text_blocks:
        
        page1_text += " " + block[0]
        
        if (block[1] in biggest_vals) & (len(block[0])<=200):
            
            title_options_list.append((block[1], block[0]))
            

    return title_options_list, page1_text