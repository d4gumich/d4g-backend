# -*- coding: utf-8 -*-
"""
Created on Mon Feb 10 15:02:29 2025

@author: Xabier Urruchua Garay
"""

import re


def cleanHtml(text):
    # removes any HTML tags.
    cleantext = re.sub(re.compile('<.*?>'), ' ', str(text))
    return cleantext

def cleanPunc(text):
    # further cleaning of any punctuation or special characters
    res = re.sub(r'[?|!|\'|"|#]',r'',text)
    res = re.sub(r'[.|,|)|(|\|/]',r' ',res)
    res = res.strip()
    res = res.replace("\n"," ")
    return res

def cleanAbbrev(text):
    text = re.sub(r"what's", "what is ", text)
    text = re.sub(r"\'s", " ", text)
    text = re.sub(r"\'ve", " have ", text)
    text = re.sub(r"can't", "cannot ", text)
    text = re.sub(r"n't", " not ", text)
    text = re.sub(r"i'm", "i am ", text)
    text = re.sub(r"\'re", " are ", text)
    text = re.sub(r"\'d", " would ", text)
    text = re.sub(r"\'ll", " will ", text)
    text = re.sub(r"\'scuse", " excuse ", text)
    text = re.sub('\W', ' ', text)
    text = re.sub('\s+', ' ', text)
    text = text.strip(' ')
    return text

def clean_text(text):
    text = text.lower()
    text = cleanHtml(text)
    text = cleanAbbrev(text)
    text = cleanPunc(text)
    return text