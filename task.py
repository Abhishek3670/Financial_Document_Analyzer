## Importing libraries and files
from crewai import Task
from agents import financial_analyst, data_extractor, investment_analyst, risk_analyst
from tools import search_tool, financial_document_tool, investment_analysis_tool, risk_assessment_tool

# Comprehensive financial analysis task
comprehensive_financial_analysis = Task(
    description="""
    Analyze the financial document at "{file_path}" and provide a comprehensive financial analysis for: "{query}"

    Your analysis should include:
    1. Executive Summary with key findings
    2. Revenue and Profitability Analysis with specific figures
    3. Financial Position Assessment 
    4. Investment Recommendation with rationale
    5. Risk Assessment

    Use the Financial Document Reader tool to read the document first, then provide your analysis.
    Be thorough and include specific numbers from the document.
    """,

    expected_output="""
    # Financial Analysis Report

    ## Executive Summary
    [Key findings and investment thesis - 2-3 paragraphs]

    ## Financial Performance
    ### Revenue Analysis
    - [Specific revenue figures and trends]
    
    ### Profitability Analysis  
    - [Specific margin and profit data]

    ## Investment Analysis
    ### Investment Recommendation: [BUY/HOLD/SELL]
    [Clear rationale with supporting data]

    ### Key Risks
    [Primary risk factors]

    ## Conclusion
    [Summary recommendation and outlook]
    """,

    agent=financial_analyst,
    tools=[financial_document_tool, investment_analysis_tool, risk_assessment_tool],
    async_execution=False
)
