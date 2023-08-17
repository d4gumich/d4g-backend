import markdownify as m

def html_to_markdown(text):
    '''converts text in HTML format to MarkDown format
    Args:
        text (str): text in HTML Format
    Returns:
        str: text in MarkDown format
    '''  
    return m.markdownify(text)