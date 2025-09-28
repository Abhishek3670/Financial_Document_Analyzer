## Importing libraries and files
from crewai import Task
from agents import (
    document_verifier, financial_analyst, investment_specialist, 
    risk_assessor, report_coordinator,
    # Legacy aliases for compatibility
    data_extractor, investment_analyst, risk_analyst
)
from tools import (
    search_tool, financial_document_tool, investment_analysis_tool, risk_assessment_tool,
    financial_search_tool, investment_search_tool, risk_search_tool, industry_search_tool
)

# Task 1: Document Verification and Validation (Simplified)
document_verification_task = Task(
    description="""
    Verify the financial document at "{file_path}" is authentic and complete.
    
    Your verification should include:
    1. Confirm the file contains financial data
    2. Identify document type (earnings report, 10-K, etc.)
    3. Check data quality and readability
    
    Provide a brief verification summary.
    """,

    expected_output="""
    Document Status: [VERIFIED/ISSUES FOUND]
    Document Type: [Type of financial document]
    Key Data Present: [Yes/No - revenue, expenses, cash flow data found]
    Quality Assessment: [Brief assessment]
    """,

    agent=document_verifier,
    tools=[financial_document_tool],
    async_execution=True  # Enable async execution for better performance
)

# Task 2: Financial Data Analysis (Focused)
financial_analysis_task = Task(
    description="""
    Analyze the financial document at "{file_path}" to answer: "{query}"
    
    Focus on extracting and analyzing:
    1. Revenue figures and growth trends
    2. Profitability metrics (margins, net income)
    3. Cash flow and liquidity position
    4. Key financial ratios
    
    Provide specific numbers from the document.
    """,

    expected_output="""
    # Financial Analysis Summary
    
    ## Revenue Performance
    - Revenue: $[amount] ([growth rate]% change)
    
    ## Profitability
    - Net Income: $[amount] 
    - Profit Margins: [percentage]
    
    ## Financial Position
    - Cash Position: $[amount]
    - Key Ratios: [list important ratios]
    
    ## Key Insights
    [2-3 bullet points of main findings]
    """,

    agent=financial_analyst,
    tools=[financial_document_tool, financial_search_tool],  # Use specialized financial search tool
    async_execution=True,
    context=[document_verification_task]
)

# Task 3: Investment Analysis (Concise)
investment_analysis_task = Task(
    description="""
    Based on the financial analysis, provide investment recommendations for: "{query}"
    
    Your analysis should include:
    1. Valuation assessment (expensive/cheap/fair)
    2. Investment recommendation (BUY/HOLD/SELL)
    3. Clear rationale for the recommendation
    4. Key catalysts or concerns
    """,

    expected_output="""
    # Investment Recommendation
    
    ## Recommendation: [BUY/HOLD/SELL]
    
    ## Valuation: [Expensive/Fair/Cheap]
    
    ## Rationale:
    [2-3 key reasons for recommendation]
    
    ## Key Catalysts:
    - [Positive factor 1]
    - [Positive factor 2]
    
    ## Key Risks:
    - [Risk factor 1]
    - [Risk factor 2]
    """,

    agent=investment_specialist,
    tools=[investment_analysis_tool, investment_search_tool],  # Use specialized investment search tool
    async_execution=True,
    context=[document_verification_task, financial_analysis_task]
)

# Task 4: Risk Assessment (Streamlined)
risk_assessment_task = Task(
    description="""
    Conduct risk analysis based on the financial data for: "{query}"
    
    Assess:
    1. Financial risks (debt levels, liquidity)
    2. Business risks (market conditions, competition)
    3. Overall risk rating
    4. Risk mitigation suggestions
    """,

    expected_output="""
    # Risk Assessment
    
    ## Overall Risk Rating: [LOW/MODERATE/HIGH]
    
    ## Financial Risks:
    - Debt Level: [assessment]
    - Liquidity: [assessment]
    
    ## Business Risks:
    - [Key business risk 1]
    - [Key business risk 2]
    
    ## Risk Mitigation:
    [1-2 practical risk management suggestions]
    """,

    agent=risk_assessor,
    tools=[risk_assessment_tool, risk_search_tool],  # Use specialized risk search tool
    async_execution=True,
    context=[document_verification_task, financial_analysis_task]
    # Removed dependency on investment_analysis_task to enable parallel execution
)

# Task 5: Report Synthesis (Efficient)
report_synthesis_task = Task(
    description="""
    Create a comprehensive financial analysis report addressing: "{query}"
    
    Synthesize findings from:
    1. Document verification
    2. Financial analysis  
    3. Investment recommendation
    4. Risk assessment
    
    Create a professional executive summary.
    """,

    expected_output="""
    # Executive Financial Analysis Report
    
    ## Executive Summary
    [2-3 sentence overview of key findings]
    
    ## Investment Recommendation: [BUY/HOLD/SELL]
    ## Risk Rating: [LOW/MODERATE/HIGH]
    
    ## Key Financial Metrics
    - Revenue: [figure]
    - Profitability: [assessment]
    - Financial Health: [strong/moderate/weak]
    
    ## Investment Thesis
    [Brief rationale for recommendation]
    
    ## Key Risks & Opportunities
    [Main points for investors to consider]
    """,

    agent=report_coordinator,
    tools=[search_tool, industry_search_tool],  # Use generic search and industry search tools
    async_execution=False,  # Keep as False since this is the final task
    context=[document_verification_task, financial_analysis_task, investment_analysis_task, risk_assessment_task]
)

# Main comprehensive task (updated for better performance)
comprehensive_financial_analysis = Task(
    description="""
    Provide comprehensive financial analysis for the document at "{file_path}" addressing: "{query}"
    
    This analysis should be thorough yet concise, covering:
    1. Key financial metrics and trends
    2. Investment recommendation with rationale
    3. Risk assessment and mitigation
    4. Clear, actionable insights
    
    Focus on delivering practical, professional analysis.
    """,

    expected_output="""
    # Comprehensive Financial Analysis
    
    ## Executive Summary
    [Key findings in 2-3 sentences]
    
    ## Financial Performance
    [Revenue, profitability, cash flow highlights]
    
    ## Investment Analysis  
    ### Recommendation: [BUY/HOLD/SELL]
    [Clear rationale with supporting data]
    
    ## Risk Assessment
    [Key risks and mitigation strategies]
    
    ## Conclusion
    [Final investment thesis and outlook]
    """,

    agent=report_coordinator,
    tools=[financial_document_tool, investment_analysis_tool, risk_assessment_tool, search_tool, industry_search_tool],
    async_execution=False
)

# Legacy compatibility
legacy_comprehensive_analysis = comprehensive_financial_analysis
