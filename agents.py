## Importing libraries and files
import os
from dotenv import load_dotenv
load_dotenv()

from crewai import Agent
from tools import search_tool, financial_document_tool, investment_analysis_tool, risk_assessment_tool
from crewai import LLM

### Loading LLM with optimized configuration
llm = LLM(
    model=os.getenv("MODEL"),
    temperature=0.2,  # Lower temperature for more consistent output
    api_key=os.getenv("NVIDIA_NIM_API_KEY"),
)

# Creating a comprehensive Financial Analyst agent
financial_analyst = Agent(
    role="Senior Financial Analyst",
    goal="""Provide comprehensive, professional financial analysis for the given query: {query}. 
    Read the financial document thoroughly and deliver actionable insights in a structured format.""",
    
    verbose=True,
    memory=True,
    
    backstory="""You are a seasoned Senior Financial Analyst with over 15 years of experience 
    in financial analysis and investment research. You hold a CFA certification and specialize in:

    - Comprehensive financial statement analysis
    - Investment recommendations with clear rationale
    - Risk assessment and market analysis
    - Professional report writing and presentation

    When given a financial document, you:
    1. Read and extract all key financial data
    2. Analyze performance trends and metrics
    3. Provide clear investment recommendations
    4. Present findings in a structured, professional format
    
    You are known for delivering thorough, actionable analysis efficiently.""",
    
    tools=[financial_document_tool, investment_analysis_tool, risk_assessment_tool],
    llm=llm,
    max_iter=5,  # Increased to allow completion
    allow_delegation=False
)

# Keep aliases for compatibility
data_extractor = financial_analyst  
investment_analyst = financial_analyst   
risk_analyst = financial_analyst
