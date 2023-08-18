# @author - Takao Kakegawa

# pip install markdownify
import markdownify as m

def get_markdown(text):
    ''' converts text in HTML format to MarkDown format
      @type: str
      @param text: string of text in HTML Format
      @rtype: str
      @rparam: string of text in MarkDown format
    '''
    return m.markdownify(text)