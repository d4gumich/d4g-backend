# SUMMARY GENERATION
# @author: Takao Kakegawa

# from transformers import BartForConditionalGeneration, BartTokenizer
# model = BartForConditionalGeneration.from_pretrained('facebook/bart-large-cnn')
# tokenizer = BartTokenizer.from_pretrained('facebook/bart-large-cnn')
from transformers import pipeline

def summarize(text_ranks=[], themes=[], locations=[], disasters=[],
              maxSummaryLength=1000):
  
  def combine_all_metadata_into_input(text_ranks=[], themes=[], locations=[], disasters=[]):
    # combine all metadata features
    input_text_ranks, input_themes, input_locations, input_disasters = "", "", "", ""
    if len(text_ranks) > 0:
      input_text_ranks = (" ").join(text_ranks)
    if len(themes) > 0:
      input_themes = f"The themes discussed in this article are: " + (", ").join(themes) + ". "
    if len(locations) > 0:
      if isinstance(locations, list) & isinstance(locations[0], dict):
        locations = [location["name"] for location in locations]

      input_locations = f"The primary locations discussed in this article are: " + (", ").join(locations) + ". "
    if len(disasters) > 0:
      input_disasters = f"The priary disasters discussed in this article are: " + (", ").join(disasters) + ". "

    return input_themes + input_locations + input_disasters + input_text_ranks


  def split_text_into_chunks(text, max_tokens=400, overlapPC=5):
  #   # Split the tokens into pieces with determined amount of overlap:
    tokens = text.split(" ")
    overlap_tokens = int(max_tokens * overlapPC /100)
    chunks = [" ".join(tokens[i: i + max_tokens]) for i in range(0, len(tokens), max_tokens-overlap_tokens)]

    return chunks
  
  agg_input = combine_all_metadata_into_input(text_ranks, themes, locations, disasters)
  
  if len(agg_input.split(" ")) <= 100:
    return agg_input

  
  model_name = "t5-small"
  summarization_pipeline = pipeline("summarization", model=model_name)
  
  def summarise_helper(text, max_chunkLength):
  # Encode text as tokens and summarize:
    summary = summarization_pipeline(text, max_length=max_chunkLength, min_length=30)
    res = summary[0]['summary_text']
    return res
  
  def recursive_summarize(text, max_length=1000, recursionLevel=0):
    recursionLevel = recursionLevel + 1
    token_num = len(text.split(" "))
    expectedCountOfChunks = token_num/max_length
    max_length = int(token_num/expectedCountOfChunks) + 2

    # Break the text into pieces of max_length
    pieces = split_text_into_chunks(text, max_tokens=max_length)

    concatenated_summary = ' '.join([summarise_helper(piece, max_chunkLength=int(max_length/3*2)) for piece in pieces])

    if len(concatenated_summary.split(" ")) > max_length:
    # If the concatenated_summary is too long, repeat the process
        return recursive_summarize(concatenated_summary,
                                   max_length=max_length,
                                   recursionLevel=recursionLevel)
    else:
    # Concatenate the summaries and summarize again
        return summarise_helper(concatenated_summary,
                                  max_chunkLength=max_length)


  return recursive_summarize(agg_input, max_length=maxSummaryLength)



# def recursive_summarize(text, max_length=1000, recursionLevel=0):
#     '''
#     @type text: str
#     @param content text 
#     @type max_length: int
#     @param maximum number of tokens of summary
#     @type recursionLevel: int
#     @param recursion level
#     @rtype final_summary: str 
#     @rparam string of final summary
#     '''
#     # Create a summary recursively with input string.

#     recursionLevel = recursionLevel + 1
#     tokens = len(text.split(" "))
#     expectedCountOfChunks = len(tokens)/max_length
#     max_length = int(len(tokens)/expectedCountOfChunks) + 2

#     # Break the text into pieces of max_length
#     pieces = split_text_into_chunks(text, max_tokens=max_length)
#     summaries=[]
#     k=0
#     for k in range(0, len(pieces)):
#         piece=pieces[k]
#         summary =summarize(piece, maxSummaryLength=max_length/3*2)
#         summaries.append(summary)

#     concatenated_summary = ' '.join(summaries)

#     tokens = tokenizer.tokenize(concatenated_summary)

#     if len(tokens) > max_length:
#     # If the concatenated_summary is too long, repeat the process
#         return recursive_summarize(concatenated_summary,
#                                    max_length=max_length,
#                                    recursionLevel=recursionLevel)
#     else:
#     # Concatenate the summaries and summarize again
#         final_summary=concatenated_summary
#         if len(pieces) > 1:
#             final_summary = summarize(concatenated_summary,
#                                   maxSummaryLength=max_length)
#         return final_summary