## Importing libraries and files
import os
from dotenv import load_dotenv
load_dotenv()

from crewai import Agent, LLM
from tools import search_tool, financial_document_tool, investment_analysis_tool, risk_assessment_tool
from llm_observability import track_crewai_call, llm_observability

### Enhanced LLM configuration for NVIDIA NIM with Observability
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

### Define Agents with enhanced capabilities

# Financial Analyst Agent
financial_analyst = Agent(
    role="Senior Financial Analyst",
    goal="Analyze financial documents and extract key insights with comprehensive risk assessment",
    backstory="""You are a seasoned financial analyst with 15+ years of experience in 
    corporate finance, investment analysis, and financial reporting. You excel at identifying 
    key financial trends, ratios, and potential red flags in financial statements.""",
    tools=[financial_document_tool, search_tool],
    llm=llm,
    verbose=True,
    allow_delegation=True,
    memory=True,
    max_iter=3,
    max_execution_time=300
)

# Data Extraction Specialist
data_extractor = Agent(
    role="Financial Data Extraction Specialist", 
    goal="Extract and structure financial data from various document formats with high accuracy",
    backstory="""You are a meticulous data extraction specialist with expertise in 
    processing financial documents, annual reports, and investment materials. You have 
    a keen eye for detail and can accurately extract numerical data and key metrics.""",
    tools=[financial_document_tool],
    llm=llm,
    verbose=True,
    memory=True,
    max_iter=2,
    max_execution_time=200
)

# Investment Analysis Specialist  
investment_analyst = Agent(
    role="Investment Analysis Expert",
    goal="Provide comprehensive investment recommendations based on financial analysis",
    backstory="""You are a senior investment analyst with deep expertise in equity 
    analysis, portfolio management, and investment strategy. You combine quantitative 
    analysis with market insights to provide actionable investment recommendations.""",
    tools=[investment_analysis_tool, search_tool],
    llm=llm,
    verbose=True,
    allow_delegation=True,
    memory=True,
    max_iter=3,
    max_execution_time=300
)

# Risk Assessment Specialist
risk_analyst = Agent(
    role="Risk Assessment Specialist",
    goal="Conduct thorough risk analysis and identify potential financial and operational risks",
    backstory="""You are a risk management expert with extensive experience in identifying, 
    quantifying, and mitigating various types of financial and operational risks. You 
    provide comprehensive risk assessments for investment decisions.""",
    tools=[risk_assessment_tool, search_tool], 
    llm=llm,
    verbose=True,
    memory=True,
    max_iter=2,
    max_execution_time=250
)

### Enhanced agents for comprehensive document processing

# Document Verification Agent
document_verifier = Agent(
    role="Document Quality Assurance Specialist",
    goal="Verify document integrity, completeness, and extract metadata for processing quality assurance", 
    backstory="""You are a document processing expert who ensures that all uploaded 
    documents are properly formatted, complete, and suitable for financial analysis. 
    You identify any issues that might affect the accuracy of the analysis.""",
    tools=[financial_document_tool],
    llm=llm,
    verbose=True,
    memory=True,
    max_iter=1,
    max_execution_time=120
)

# Investment Strategy Specialist
investment_specialist = Agent(
    role="Investment Strategy Consultant", 
    goal="Develop strategic investment recommendations based on comprehensive analysis",
    backstory="""You are a senior investment strategist with expertise in developing 
    long-term investment strategies, portfolio optimization, and market analysis. You 
    synthesize complex financial data into actionable strategic recommendations.""",
    tools=[investment_analysis_tool, search_tool],
    llm=llm,
    verbose=True,
    allow_delegation=True,
    memory=True,
    max_iter=3,
    max_execution_time=400
)

# Risk Assessment Coordinator
risk_assessor = Agent(
    role="Risk Assessment Coordinator",
    goal="Coordinate comprehensive risk evaluation across multiple dimensions",
    backstory="""You are a senior risk management coordinator who oversees comprehensive 
    risk assessments, ensuring all potential risks are identified, analyzed, and properly 
    communicated to stakeholders.""",
    tools=[risk_assessment_tool, search_tool],
    llm=llm,
    verbose=True,
    allow_delegation=True,
    memory=True,
    max_iter=2,
    max_execution_time=300
)

# Report Synthesis Coordinator
report_coordinator = Agent(
    role="Financial Report Synthesis Specialist",
    goal="Synthesize all analysis components into comprehensive, actionable financial reports",
    backstory="""You are an expert in financial reporting and communication who specializes 
    in creating comprehensive, well-structured reports that combine technical analysis 
    with clear, actionable insights for decision-makers.""",
    tools=[financial_document_tool],
    llm=llm,
    verbose=True,
    memory=True,
    max_iter=2,
    max_execution_time=300
)

print("✅ All financial analysis agents initialized successfully with LLM observability")

# Function to get LLM metrics
def get_llm_metrics():
    """Get current LLM observability metrics"""
    return llm_observability.get_metrics_summary()
