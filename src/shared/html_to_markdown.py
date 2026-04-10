# @author - XabUG07

import re
import markdownify as m

def get_markdown(text):
    ''' converts text in HTML format to MarkDown format
      @type: str
      @param text: string of text in HTML Format
      @rtype: str
      @rparam: string of text in MarkDown format
    '''
    return m.markdownify(text)



def fitz_to_markdown(pdf):
    ''' converts fitz object to markdown format
      @type: fitz object
      @param fitz: object containing pdf details
      @rtype: str
      @rparam: string of text in MarkDown format
    '''

    markdown_text = []

    # Go through each page
    for page_number in range(len(pdf)):
        page = pdf.load_page(page_number)
        # Extract the text from the page
        text = page.get_text()

        # Optionally, you can add a page header in markdown
        markdown_text.append(f"# Page {page_number + 1}\n\n")

        # Basic formatting rules may include:
        # Convert multiple newlines to a single newline
        text = re.sub(r'\n+', '\n', text)

        # Convert each newline to a double newline for paragraph break (Markdown uses two newlines to separate paragraphs)
        text = text.replace('\n', '\n\n')

        # Add the cleaned text to our markdown list
        markdown_text.append(text)

    # Join the collected text into a single markdown string
    markdown_document = '\n'.join(markdown_text)
    
    return markdown_document