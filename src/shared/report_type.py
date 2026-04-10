# @author Sidra Effendi

def check_pattern_present(pattern_list, doc_title):
    for pattern in pattern_list:
        if pattern.lower() in doc_title.lower():
            return True
        else:
            return False


def detect_report_type(doc_title):
    ''' detect report type by looking at the title
    '''
    sitrep_pattern = ["situation", "sitrep", "situation overview"]
    news_report_pattern = ["news", "press release", "newsletter"]
    financial_pattern = ["financial", "finance ", "budget", "tax"]
    annual_pattern = ['annual']
    analysis = ["analysis"]
    appeal = ["appeal", "fundraising"]
    assessment = ["assessment"]
    evaluation = ["evaluation", "lessons", "learned"]
    infographic = ["infographic"]
    interactive = ["interactive"]
    manual = ["manual", "guideline"]
    press = ["news", "press"]

    doc_title = doc_title.replace(' ', '')

    # True if pattern in doc_title.lower() for pattern in sitrep_pattern
    if check_pattern_present(sitrep_pattern, doc_title):
        report_type = 'Situation Report'
    elif check_pattern_present(news_report_pattern, doc_title):
        report_type = 'News Report'
    elif check_pattern_present(financial_pattern, doc_title):
        report_type = 'Finance Report'
    elif check_pattern_present(annual_pattern, doc_title):
        report_type = 'Annual Report'
    elif check_pattern_present(analysis, doc_title):
        report_type = 'Analysis'
    elif check_pattern_present(appeal, doc_title):
        report_type = 'Appeal'
    elif check_pattern_present(assessment, doc_title):
        report_type = 'Assessment'
    elif check_pattern_present(evaluation, doc_title):
        report_type = 'Evaluation and Lessons Learned'
    elif check_pattern_present(infographic, doc_title):
        report_type = 'Infographic'
    elif check_pattern_present(interactive, doc_title):
        report_type = 'Interactive'
    elif check_pattern_present(manual, doc_title):
        report_type = 'Manual and Guideline'
    elif check_pattern_present(press, doc_title):
        report_type = 'News and Press Release'

    else:
        report_type = None

    return report_type
