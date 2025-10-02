## Importing libraries and files
import os
import time
import logging
from functools import wraps
from dotenv import load_dotenv
load_dotenv()

from crewai import Agent, LLM
from backend.utils.tools import (
    search_tool, financial_document_tool, investment_analysis_tool, risk_assessment_tool,
    financial_search_tool, investment_search_tool, risk_search_tool, industry_search_tool
)
from backend.utils.llm_observability import track_crewai_call, llm_observability

# Configure logging
logger = logging.getLogger(__name__)

@track_crewai_call(model="nvidia_nim/meta/llama-3.1-405b-instruct")
def create_enhanced_llm():
    try:
        # Try NVIDIA NIM configuration first
        llm = LLM(
            model="nvidia_nim/meta/llama-3.1-405b-instruct",
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.getenv("NVIDIA_NIM_API_KEY"),
            temperature=0.1,
        )
        print("✅ NVIDIA NIM LLM configured successfully with observability")
        return llm
    except Exception as e:
        print(f"⚠️ NVIDIA NIM configuration issue: {e}")
        # Fallback to OpenAI compatible configuration
        try:
            llm = LLM(
                model="gpt-3.5-turbo",
                api_key=os.getenv("OPENAI_API_KEY"),
                temperature=0.2,
            )
            print("✅ Fallback LLM configured with observability")
            return llm
        except Exception as e2:
            print(f"❌ Both LLM configurations failed: {e2}")
            raise

# Initialize LLM with observability
llm = create_enhanced_llm()

# Performance tracking for agents
agent_performance_metrics = {}

def track_agent_performance(agent_name):
    """Decorator to track agent performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                if agent_name not in agent_performance_metrics:
                    agent_performance_metrics[agent_name] = []
                agent_performance_metrics[agent_name].append(execution_time)
                logger.info(f"Agent {agent_name} completed in {execution_time:.2f} seconds")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Agent {agent_name} failed after {execution_time:.2f} seconds: {e}")
                # Still track the failure
                if agent_name not in agent_performance_metrics:
                    agent_performance_metrics[agent_name] = []
                agent_performance_metrics[agent_name].append(execution_time)
                raise
        return wrapper
    return decorator

def get_agent_performance_summary():
    """Get performance summary for all agents"""
    summary = {}
    for agent_name, times in agent_performance_metrics.items():
        if times:
            summary[agent_name] = {
                "total_executions": len(times),
                "average_time": sum(times) / len(times),
                "min_time": min(times),
                "max_time": max(times),
                "total_time": sum(times)
            }
    return summary

# Creating a Document Verification Specialist
document_verifier = Agent(
    role="Financial Document Verification Specialist",
    goal="""Thoroughly verify and validate financial documents for authenticity, completeness, and data integrity.
    Ensure the document is a legitimate financial report with proper structure and readable content.""",
    
    verbose=True,
    memory=True,
    
    backstory="""You are a Financial Document Verification Specialist with 12+ years of experience 
    in financial compliance and document authentication. You hold certifications in:
    
    - Financial document forensics and validation
    - Regulatory compliance (SEC, GAAP, IFRS)
    - Document structure and format analysis
    - Data integrity verification
    
    Your expertise includes:
    1. Identifying authentic financial documents vs. fraudulent ones
    2. Validating document structure and required financial sections
    3. Ensuring data completeness and consistency
    4. Flagging potential red flags or inconsistencies
    5. Providing preliminary document quality assessment
    
    You serve as the first line of defense in the analysis pipeline, ensuring only 
    high-quality, legitimate financial documents proceed to detailed analysis.""",
    
    tools=[financial_document_tool],
    llm=llm,
    max_iter=3,
    max_execution_time=120,  # Increased from 60 to 120 seconds to prevent timeout issues
    allow_delegation=True  # Can delegate to other specialists after verification
)

# Creating a comprehensive Financial Data Extraction and Analysis agent
financial_analyst = Agent(
    role="Senior Financial Data Analyst",
    goal="""Extract, analyze, and interpret key financial data from verified documents. 
    Provide comprehensive financial statement analysis including performance trends, 
    ratios, and comparative analysis for the query: {query}""",
    
    verbose=True,
    memory=True,
    
    backstory="""You are a Senior Financial Data Analyst with over 15 years of experience 
    in financial analysis and investment research. You hold a CFA certification and specialize in:

    - Advanced financial statement analysis and ratio interpretation
    - Performance trend analysis and benchmarking
    - Cash flow and liquidity analysis  
    - Profitability and efficiency metrics
    - Financial modeling and forecasting

    Your analytical process includes:
    1. Extracting key financial metrics from statements
    2. Calculating important financial ratios
    3. Analyzing performance trends over time
    4. Identifying strengths and weaknesses in financial position
    5. Providing context through industry comparisons
    
    You work collaboratively with investment and risk specialists to provide 
    comprehensive insights that inform investment decisions.""",
    
    tools=[financial_document_tool, financial_search_tool],  # Use specialized financial search tool
    llm=llm,
    max_iter=4,
    max_execution_time=300,  # Increased from 180 to 300 seconds (5 minutes)
    allow_delegation=True
)

# Creating an Investment Recommendations Specialist
investment_specialist = Agent(
    role="Senior Investment Strategy Specialist",
    goal="""Based on financial analysis, provide professional investment recommendations 
    with clear rationale, target prices, and strategic outlook for the query: {query}""",
    
    verbose=True,
    memory=True,
    
    backstory="""You are a Senior Investment Strategy Specialist with 18+ years of experience 
    in equity research and portfolio management. Your credentials include:
    
    - CFA Charter and CAIA designation
    - Former buy-side and sell-side equity research experience
    - Expertise in valuation methodologies (DCF, comparable analysis, sum-of-parts)
    - Sector specialization across multiple industries
    - Track record of successful investment recommendations
    
    Your investment process includes:
    1. Fundamental valuation using multiple methodologies
    2. Competitive positioning and market analysis
    3. Growth prospects and strategic initiatives evaluation
    4. Recommendation formulation (BUY/HOLD/SELL) with price targets
    5. Investment thesis development with supporting rationale
    
    You synthesize financial data analysis with market intelligence to generate 
    actionable investment recommendations for institutional and retail investors.""",
    
    tools=[investment_analysis_tool, investment_search_tool],  # Use specialized investment search tool
    llm=llm,
    max_iter=4,
    max_execution_time=240,  # Increased from 150 to 240 seconds (4 minutes)
    allow_delegation=True
)

# Creating a Risk Assessment Specialist
risk_assessor = Agent(
    role="Senior Risk Assessment Specialist",
    goal="""Conduct comprehensive risk analysis of financial positions, market conditions, 
    and investment scenarios. Identify and quantify key risk factors for the query: {query}""",
    
    verbose=True,
    memory=True,
    
    backstory="""You are a Senior Risk Assessment Specialist with 16+ years of experience 
    in financial risk management and analysis. Your expertise encompasses:
    
    - Financial Risk Manager (FRM) certification
    - Enterprise risk management and regulatory compliance
    - Market, credit, operational, and liquidity risk analysis
    - Scenario analysis and stress testing
    - Risk-adjusted return calculations and portfolio optimization
    
    Your risk assessment framework includes:
    1. Financial risk identification (leverage, liquidity, credit quality)
    2. Market risk analysis (volatility, correlation, beta analysis)
    3. Operational and business model risks
    4. Regulatory and compliance risk factors
    5. Scenario analysis and downside protection strategies
    6. Risk-adjusted performance metrics
    
    You provide critical risk intelligence that complements investment analysis, 
    ensuring stakeholders understand both opportunities and potential pitfalls.""",
    
    tools=[risk_assessment_tool, risk_search_tool],  # Use specialized risk search tool
    llm=llm,
    max_iter=4,
    max_execution_time=240,  # Increased from 150 to 240 seconds (4 minutes)
    allow_delegation=False  # Final specialist in the chain
)

# Creating a Report Synthesis Coordinator
report_coordinator = Agent(
    role="Financial Analysis Report Coordinator",
    goal="""Synthesize inputs from all specialists to create a comprehensive, 
    professional financial analysis report that addresses: {query}""",
    
    verbose=True,
    memory=True,
    
    backstory="""You are a Financial Analysis Report Coordinator with 14+ years of experience 
    in investment research and client communication. Your role involves:
    
    - Senior equity research analyst background
    - Expert in financial writing and presentation
    - Client relationship management and communication
    - Report quality assurance and regulatory compliance
    
    Your coordination responsibilities include:
    1. Integrating analysis from document verification, financial analysis, investment, and risk teams
    2. Ensuring consistency and coherence across all analysis components
    3. Presenting findings in clear, professional format
    4. Highlighting key insights and actionable recommendations
    5. Quality control and final report validation
    
    You serve as the final checkpoint, ensuring that all analysis components 
    work together to provide clients with comprehensive, actionable financial insights.""",
    
    tools=[search_tool, industry_search_tool],  # Use generic search and industry search tools
    llm=llm,
    max_iter=3,
    max_execution_time=180,  # Increased from 120 to 180 seconds (3 minutes)
    allow_delegation=False
)

# Apply performance tracking to the document verifier
# Apply performance tracking to the financial analyst
# Apply performance tracking to the investment specialist
# Apply performance tracking to the risk assessor
# Apply performance tracking to the report coordinator
# Legacy compatibility aliases (for backward compatibility with existing code)
data_extractor = financial_analyst
investment_analyst = investment_specialist
risk_analyst = risk_assessor

def create_dynamic_agents(document_type: str = "unknown", industry: str = "general", processing_speed: str = "standard"):
    """Create dynamic agent configurations based on document type and industry.
    
    Args:
        document_type (str): Type of document (annual_report, quarterly_report, etc.)
        industry (str): Industry sector of the company
        processing_speed (str): Required processing speed (fast, standard, detailed)
        
    Returns:
        dict: Configured agents with appropriate settings
    """
    
    # Base execution times
    base_times = {
        "fast": {"document_verifier": 90, "financial_analyst": 240, "investment_specialist": 180, "risk_assessor": 180, "report_coordinator": 120},
        "standard": {"document_verifier": 120, "financial_analyst": 300, "investment_specialist": 240, "risk_assessor": 240, "report_coordinator": 180},
        "detailed": {"document_verifier": 180, "financial_analyst": 420, "investment_specialist": 360, "risk_assessor": 360, "report_coordinator": 240}
    }
    
    # Select execution times based on processing speed
    exec_times = base_times.get(processing_speed, base_times["standard"])
    
    # Adjust times based on document type
    if document_type == "annual_report":
        # Annual reports need more time for detailed analysis
        exec_times = {k: int(v * 1.5) for k, v in exec_times.items()}
    elif document_type == "quarterly_report":
        # Quarterly reports need less time for faster processing
        exec_times = {k: int(v * 0.7) for k, v in exec_times.items()}
    
    # Create specialized agents based on industry
    industry_specialists = {
        "technology": "Tech",
        "finance": "Financial Services", 
        "healthcare": "Healthcare",
        "energy": "Energy",
        "retail": "Retail",
        "manufacturing": "Manufacturing",
        "automotive": "Automotive",
        "real_estate": "Real Estate"
    }
    
    industry_suffix = industry_specialists.get(industry, "")
    
    # Document Verifier
    document_verifier = Agent(
        role="Financial Document Verification Specialist",
        goal=f"""Thoroughly verify and validate {document_type.replace('_', ' ') if document_type != 'unknown' else 'financial'} documents for authenticity, completeness, and data integrity.
        Ensure the document is a legitimate financial report with proper structure and readable content.""",
        
        verbose=True,
        memory=True,
        
        backstory=f"""You are a Financial Document Verification Specialist with 12+ years of experience 
        in financial compliance and document authentication. You hold certifications in:
        
        - Financial document forensics and validation
        - Regulatory compliance (SEC, GAAP, IFRS)
        - Document structure and format analysis
        - Data integrity verification
        
        Your expertise includes:
        1. Identifying authentic financial documents vs. fraudulent ones
        2. Validating document structure and required financial sections
        3. Ensuring data completeness and consistency
        4. Flagging potential red flags or inconsistencies
        5. Providing preliminary document quality assessment
        
        You serve as the first line of defense in the analysis pipeline, ensuring only 
        high-quality, legitimate financial documents proceed to detailed analysis.""",
        
        tools=[financial_document_tool],
        llm=llm,
        max_iter=3,
        max_execution_time=exec_times["document_verifier"],
        allow_delegation=True
    )
    
    # Financial Analyst
    financial_analyst = Agent(
        role=f"Senior {industry_suffix} Financial Data Analyst" if industry_suffix else "Senior Financial Data Analyst",
        goal=f"""Extract, analyze, and interpret key financial data from verified {document_type.replace('_', ' ') if document_type != 'unknown' else 'financial'} documents. 
        Provide comprehensive financial statement analysis including performance trends, 
        ratios, and comparative analysis for the query: {{query}}""",
        
        verbose=True,
        memory=True,
        
        backstory=f"""You are a Senior {industry_suffix} Financial Data Analyst with over 15 years of experience 
        in financial analysis and investment research. You hold a CFA certification and specialize in:

        - Advanced financial statement analysis and ratio interpretation
        - Performance trend analysis and benchmarking
        - Cash flow and liquidity analysis  
        - Profitability and efficiency metrics
        - Financial modeling and forecasting
        {f"- {industry_suffix} industry expertise and sector-specific metrics" if industry_suffix else ""}

        Your analytical process includes:
        1. Extracting key financial metrics from statements
        2. Calculating important financial ratios
        3. Analyzing performance trends over time
        4. Identifying strengths and weaknesses in financial position
        5. Providing context through industry comparisons
        
        You work collaboratively with investment and risk specialists to provide 
        comprehensive insights that inform investment decisions.""",
        
        tools=[financial_document_tool, financial_search_tool],
        llm=llm,
        max_iter=4,
        max_execution_time=exec_times["financial_analyst"],
        allow_delegation=True
    )
    
    # Investment Specialist
    investment_specialist = Agent(
        role=f"Senior {industry_suffix} Investment Strategy Specialist" if industry_suffix else "Senior Investment Strategy Specialist",
        goal=f"""Based on financial analysis of {document_type.replace('_', ' ') if document_type != 'unknown' else 'financial'} documents, provide professional investment recommendations 
        with clear rationale, target prices, and strategic outlook for the query: {{query}}""",
        
        verbose=True,
        memory=True,
        
        backstory=f"""You are a Senior {industry_suffix} Investment Strategy Specialist with 18+ years of experience 
        in equity research and portfolio management. Your credentials include:
        
        - CFA Charter and CAIA designation
        - Former buy-side and sell-side equity research experience
        - Expertise in valuation methodologies (DCF, comparable analysis, sum-of-parts)
        {f"- {industry_suffix} sector specialization" if industry_suffix else "- Sector specialization across multiple industries"}
        - Track record of successful investment recommendations
        
        Your investment process includes:
        1. Fundamental valuation using multiple methodologies
        2. Competitive positioning and market analysis
        3. Growth prospects and strategic initiatives evaluation
        4. Recommendation formulation (BUY/HOLD/SELL) with price targets
        5. Investment thesis development with supporting rationale
        {f"6. {industry_suffix} industry trends and sector-specific factors analysis" if industry_suffix else ""}
        
        You synthesize financial data analysis with market intelligence to generate 
        actionable investment recommendations for institutional and retail investors.""",
        
        tools=[investment_analysis_tool, investment_search_tool],
        llm=llm,
        max_iter=4,
        max_execution_time=exec_times["investment_specialist"],
        allow_delegation=True
    )
    
    # Risk Assessor
    risk_assessor = Agent(
        role=f"Senior {industry_suffix} Risk Assessment Specialist" if industry_suffix else "Senior Risk Assessment Specialist",
        goal=f"""Conduct comprehensive risk analysis of financial positions, market conditions, 
        and investment scenarios for {document_type.replace('_', ' ') if document_type != 'unknown' else 'financial'} documents. 
        Identify and quantify key risk factors for the query: {{query}}""",
        
        verbose=True,
        memory=True,
        
        backstory=f"""You are a Senior {industry_suffix} Risk Assessment Specialist with 16+ years of experience 
        in financial risk management and analysis. Your expertise encompasses:
        
        - Financial Risk Manager (FRM) certification
        - Enterprise risk management and regulatory compliance
        - Market, credit, operational, and liquidity risk analysis
        - Scenario analysis and stress testing
        - Risk-adjusted return calculations and portfolio optimization
        {f"- {industry_suffix} industry-specific risks and regulatory considerations" if industry_suffix else ""}
        
        Your risk assessment framework includes:
        1. Financial risk identification (leverage, liquidity, credit quality)
        2. Market risk analysis (volatility, correlation, beta analysis)
        3. Operational and business model risks
        4. Regulatory and compliance risk factors
        5. Scenario analysis and downside protection strategies
        6. Risk-adjusted performance metrics
        {f"7. {industry_suffix} sector-specific risk factors" if industry_suffix else ""}
        
        You provide critical risk intelligence that complements investment analysis, 
        ensuring stakeholders understand both opportunities and potential pitfalls.""",
        
        tools=[risk_assessment_tool, risk_search_tool],
        llm=llm,
        max_iter=4,
        max_execution_time=exec_times["risk_assessor"],
        allow_delegation=False
    )
    
    # Report Coordinator
    report_coordinator = Agent(
        role=f"{industry_suffix} Financial Analysis Report Coordinator" if industry_suffix else "Financial Analysis Report Coordinator",
        goal=f"""Synthesize inputs from all specialists to create a comprehensive, 
        professional financial analysis report for {document_type.replace('_', ' ') if document_type != 'unknown' else 'financial'} documents 
        that addresses: {{query}}""",
        
        verbose=True,
        memory=True,
        
        backstory=f"""You are a {industry_suffix} Financial Analysis Report Coordinator with 14+ years of experience 
        in investment research and client communication. Your role involves:
        
        - Senior equity research analyst background
        - Expert in financial writing and presentation
        - Client relationship management and communication
        - Report quality assurance and regulatory compliance
        {f"- {industry_suffix} industry reporting standards and practices" if industry_suffix else ""}
        
        Your coordination responsibilities include:
        1. Integrating analysis from document verification, financial analysis, investment, and risk teams
        2. Ensuring consistency and coherence across all analysis components
        3. Presenting findings in clear, professional format
        4. Highlighting key insights and actionable recommendations
        5. Quality control and final report validation
        {f"6. {industry_suffix} sector-specific reporting considerations" if industry_suffix else ""}
        
        You serve as the final checkpoint, ensuring that all analysis components 
        work together to provide clients with comprehensive, actionable financial insights.""",
        
        tools=[search_tool, industry_search_tool],
        llm=llm,
        max_iter=3,
        max_execution_time=exec_times["report_coordinator"],
        allow_delegation=False
    )
    
    return {
        "document_verifier": document_verifier,
        "financial_analyst": financial_analyst,
        "investment_specialist": investment_specialist,
        "risk_assessor": risk_assessor,
        "report_coordinator": report_coordinator
    }

# Function to get LLM metrics
def get_llm_metrics():
    """Get current LLM observability metrics"""
    return llm_observability.get_metrics_summary()