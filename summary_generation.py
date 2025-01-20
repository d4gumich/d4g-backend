# SUMMARY GENERATION
# @author: Takao Kakegawa

import gc
import transformers #import BartForConditionalGeneration, BartTokenizer

model = transformers.BartForConditionalGeneration.from_pretrained('facebook/bart-large-cnn')
tokenizer = transformers.BartTokenizer.from_pretrained('facebook/bart-large-cnn')


del transformers
gc.collect()

def combine_all_metadata_into_input(text_ranks, themes, locations, disasters):
    
    """
    Combine various metadata components into a single string for input into a summary pipeline.

    This function takes lists of ranked sentences, themes, locations, and disasters, and 
    combines them into a cohesive string format to be used as an input for a summary pipeline. 
    If the locations are provided as a list of dictionaries, it extracts the 'name' field 
    from each dictionary.

    Parameters:
    text_ranks (list): A list of top-ranked sentences as string texts.
    themes (list): A list of themes as string texts.
    locations (list): A list of locations as string texts or a list of dictionaries with a "name" key.
    disasters (list): A list of disasters as string texts.

    Returns:
    (str): A single string combining the metadata items and top-ranked sentences for input into the summary pipeline.
    """
    # combine all metadata features
    if isinstance(locations, list) & isinstance(locations[0], dict):
        locations = [location["name"] for location in locations]
    
    
    input_text_ranks, input_themes, input_locations, input_disasters = "", "", "", ""
    if len(text_ranks) != 0:
      input_text_ranks = (" ").join(text_ranks)
    # if len(themes) != 0:
      # input_themes = "The themes discussed in this article are: " + (", ").join(themes) + ". "
    # if len(locations) != 0:
      # input_locations = "The primary locations discussed in this article are: " + (", ").join(locations) + ". "
    # if len(disasters) != 0:
      # input_disasters = "The priary disasters discussed in this article are: " + (", ").join(disasters) + ". "
    
    return input_themes + input_locations + input_disasters + input_text_ranks


def split_text_into_chunks(text, max_tokens=900, overlapPC=5):

    """
    Split text into chunks with specified maximum tokens and overlap.

    This function divides a given text into chunks, each containing up to a specified 
    maximum number of tokens. Consecutive chunks can have an overlap, defined as a 
    percentage of the maximum tokens. It uses a tokenizer to handle the tokenization 
    and conversion back to text.

    Parameters:
    text (str): The content text to be split into chunks.
    max_tokens (int): The maximum number of tokens allowed per chunk (default is 900).
    overlapPC (int): The percentage of overlap across consecutive chunks. Valid range is [0-100] (default is 5).

    Returns:
    (list): A list of text chunks, each represented as a string.
    """
    
    # Split the tokens into pieces with determined amount of overlap:
    tokens = tokenizer.tokenize(text)
    overlap_tokens = int(max_tokens * overlapPC /100)
    chunks = [tokens[i: i + max_tokens] for i in range(0, len(tokens), max_tokens-overlap_tokens)]
    
    text_chunks = [tokenizer.decode(tokenizer.convert_tokens_to_ids(chunk),skip_special_tokens=True) for chunk in chunks]
    
    return text_chunks


def summarize(text, maxSummaryLength=500):

    """
    Generate a summary for the given text using the Facebook-BART-CNN model.

    This function uses a pre-trained Facebook-BART-CNN model to generate a concise 
    summary of the provided text. It encodes the text into tokens, generates the 
    summary, and decodes the tokens back into a string. The summary length is 
    adjustable via the `maxSummaryLength` parameter.

    Parameters:
    text (str): The input text to be summarized.
    maxSummaryLength (int): The maximum length of the generated summary in tokens (default is 500).

    Returns:
    (str): The generated summary of the input text.
    """

    # Encode text as tokens and summarize:
    inputs = tokenizer.encode("summarize: " + text,
                              return_tensors='pt',
                              max_length=1024,
                              truncation=True)
    
    summary_ids = model.generate(inputs,
                                 max_length=maxSummaryLength,
                                 min_length=int(maxSummaryLength/5),
                                 length_penalty=10.0,
                                 num_beams=4,
                                 early_stopping=True)
    
    
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    
    return summary


def recursive_summarize(text, max_length=1000, recursionLevel=0):

    """
    Generate a recursive summary of the given text.

    This function creates a summary of the input text by recursively breaking it 
    into chunks and summarizing each chunk, then concatenating and summarizing 
    again as necessary. It attempts to generate a summary within a specified 
    maximum length of tokens. If the summary exceeds this length, it further 
    condenses it by repeating the summarization process at a higher recursion level.

    Parameters:
    text (str): The content text to be summarized.
    max_length (int): The maximum number of tokens allowed in the summary (default is 1000).
    recursionLevel (int): The current recursion level, used to track the depth 
                          of recursive summarization (default is 0).

    Returns:
    (str): The final summary of the input text.
    """
    
    # Create a summary recursively with input string.
    #print("recursion level: ", recursionLevel)
    recursionLevel = recursionLevel + 1
    tokens = tokenizer.tokenize(text)
    expectedCountOfChunks = len(tokens)/max_length
    max_length = int(len(tokens)/expectedCountOfChunks) + 2

    # Break the text into pieces of max_length
    pieces = split_text_into_chunks(text, max_tokens=max_length)
    summaries=[]
    k=0
    for k in range(0, len(pieces)):
        piece=pieces[k]
        summary =summarize(piece, maxSummaryLength=max_length/3*2)
        summaries.append(summary)

    concatenated_summary = ' '.join(summaries)

    tokens = tokenizer.tokenize(concatenated_summary)


    # Concatenate the summaries and summarize again
    if len(tokens) > max_length:
    # If the concatenated_summary is too long, repeat the process
        return recursive_summarize(concatenated_summary,
                                   max_length=max_length,
                                   recursionLevel=recursionLevel)
    else:
    # Concatenate the summaries and summarize again
        final_summary=concatenated_summary
        if len(pieces) > 1:
            final_summary = summarize(concatenated_summary,
                                  maxSummaryLength=max_length)
        return final_summary
