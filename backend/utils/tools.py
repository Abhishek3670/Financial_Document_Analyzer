import os
import re
import time
import logging
from functools import wraps
from dotenv import load_dotenv
from crewai_tools import SerperDevTool
from crewai.tools import BaseTool
from langchain_community.document_loaders import PyPDFLoader

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import Redis cache
from backend.utils.redis_cache import cache_result, cache_llm_result, cache_analysis_result

# Creating search tool with Serper
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# Generic search tool (kept for backward compatibility)
search_tool = SerperDevTool(api_key=SERPER_API_KEY)

# Performance tracking for tools
tool_performance_metrics = {}

def track_tool_performance(tool_name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                if tool_name not in tool_performance_metrics:
                    tool_performance_metrics[tool_name] = []
                tool_performance_metrics[tool_name].append(execution_time)
                logger.info(f"Tool {tool_name} completed in {execution_time:.2f} seconds")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Tool {tool_name} failed after {execution_time:.2f} seconds: {e}")
                raise
        return wrapper
    return decorator

class FinancialDocumentReader(BaseTool):
    name: str = "Financial Document Reader"
    description: str = "Reads and processes financial documents from PDF files"

    @cache_analysis_result(ttl=3600)  # Cache for 1 hour
    @track_tool_performance("FinancialDocumentReader")
    def _run(self, file_path: str) -> str:
        """Read and process a financial document from a PDF file.
        
        Args:
            file_path (str): Path to the PDF file to analyze
            
        Returns:
            str: Cleaned and processed text content from the PDF
        """
        try:
            # Validate file exists
            if not os.path.exists(file_path):
                return f"Error: File {file_path} does not exist."
            
            # Validate file extension
            if not file_path.lower().endswith('.pdf'):
                return f"Error: File {file_path} is not a PDF file."
            
            # If the path doesn't start with /, prepend the current directory
            if not file_path.startswith('/'):
                file_path = os.path.join(os.getcwd(), file_path)
            
            # Add timeout mechanism for PDF loading
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("PDF loading timed out after 60 seconds")
            
            # Set up timeout signal
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(60)  # 60 second timeout
            
            try:
                loader = PyPDFLoader(file_path)
                docs = loader.load()
                
                # Cancel the timeout
                signal.alarm(0)
            except TimeoutError:
                return "Error: PDF file loading timed out. File may be too large or corrupted."
            
            if not docs:
                return "Error: PDF file appears to be empty or corrupted."
            
            full_report = ""
            # Process only first 20 pages to prevent excessive processing time
            for i, data in enumerate(docs[:20]):
                content = data.page_content
                # Clean up multiple newlines
                content = re.sub(r'\n+', '\n', content)
                full_report += content + "\n"
                
                # Early exit if we've accumulated enough content
                if len(full_report) > 150000:  # 150KB limit
                    full_report = full_report[:150000] + "\n[Content truncated due to size...]"
                    break
            
            # Limit output size to prevent memory issues
            if len(full_report) > 150000:  # 150KB limit
                full_report = full_report[:150000] + "\n[Content truncated due to size...]"
                
            return full_report
            
        except Exception as e:
            return f"Error reading PDF file: {str(e)}"

class InvestmentAnalyzer(BaseTool):
    name: str = "Investment Analyzer"
    description: str = "Analyzes financial document data and provides investment insights"

    @cache_llm_result(model="investment-analysis", ttl=7200)  # Cache for 2 hours
    @track_tool_performance("InvestmentAnalyzer")
    def _run(self, financial_document_data: str) -> str:
        """Analyze financial document data and provide investment insights.
        
        Args:
            financial_document_data (str): Processed text from financial document
            
        Returns:
            str: Investment analysis and recommendations
        """
        try:
            if not financial_document_data or len(financial_document_data.strip()) == 0:
                return "Error: No financial data provided for analysis."
            
            # Extract key financial metrics using regex patterns
            revenue_pattern = r'(?:revenue|sales).*?(\$[\d,.]+ ?[bmk]?)'
            profit_pattern = r'(?:profit|income|earnings).*?(\$[\d,.]+ ?[bmk]?)'
            margin_pattern = r'(?:margin).*?([\d.]+%)'
            
            analysis = "## Investment Analysis\n\n"
            
            # Look for revenue information
            revenue_matches = re.findall(revenue_pattern, financial_document_data, re.IGNORECASE)
            if revenue_matches:
                analysis += f"**Revenue Highlights:** Found revenue figures: {', '.join(revenue_matches[:3])}\n\n"
            
            # Look for profit information
            profit_matches = re.findall(profit_pattern, financial_document_data, re.IGNORECASE)
            if profit_matches:
                analysis += f"**Profitability:** Identified profit metrics: {', '.join(profit_matches[:3])}\n\n"
            
            # Look for margin information
            margin_matches = re.findall(margin_pattern, financial_document_data, re.IGNORECASE)
            if margin_matches:
                analysis += f"**Margins:** Found margin data: {', '.join(margin_matches[:3])}\n\n"
            
            # Basic sentiment analysis based on key terms
            positive_terms = ['growth', 'increase', 'profit', 'strong', 'improved', 'record']
            negative_terms = ['decline', 'decrease', 'loss', 'weak', 'challenging', 'lower']
            
            positive_count = sum(financial_document_data.lower().count(term) for term in positive_terms)
            negative_count = sum(financial_document_data.lower().count(term) for term in negative_terms)
            
            if positive_count > negative_count:
                analysis += "**Overall Sentiment:** Generally positive financial indicators detected.\n\n"
            elif negative_count > positive_count:
                analysis += "**Overall Sentiment:** Some challenging financial indicators detected.\n\n"
            else:
                analysis += "**Overall Sentiment:** Mixed financial indicators detected.\n\n"
            
            analysis += "**Investment Considerations:**\n"
            analysis += "- Review detailed financial statements for complete analysis\n"
            analysis += "- Consider market conditions and industry trends\n"
            analysis += "- Evaluate long-term growth prospects\n"
            analysis += "- Assess risk factors and competitive position\n"
            
            return analysis
            
        except Exception as e:
            return f"Error analyzing investment data: {str(e)}"

class RiskAssessor(BaseTool):
    name: str = "Risk Assessor"
    description: str = "Assesses risks based on financial document data"

    @cache_llm_result(model="risk-assessment", ttl=7200)  # Cache for 2 hours
    @track_tool_performance("RiskAssessor")
    def _run(self, financial_document_data: str) -> str:
        """Assess risks based on financial document data.
        
        Args:
            financial_document_data (str): Processed text from financial document
            
        Returns:
            str: Risk assessment analysis and warnings
        """
        try:
            if not financial_document_data or len(financial_document_data.strip()) == 0:
                return "Error: No financial data provided for risk assessment."
            
            risk_assessment = "## Risk Assessment\n\n"
            risk_score = 0
            risks_identified = []
            
            # Check for common risk indicators
            risk_indicators = {
                'debt': {'terms': ['debt', 'loan', 'borrowing', 'liability'], 'weight': 2},
                'litigation': {'terms': ['litigation', 'lawsuit', 'legal', 'settlement'], 'weight': 3},
                'regulatory': {'terms': ['regulatory', 'compliance', 'violation', 'investigation'], 'weight': 3},
                'market': {'terms': ['market risk', 'volatility', 'uncertainty', 'competition'], 'weight': 2},
                'operational': {'terms': ['supply chain', 'disruption', 'shortage', 'delay'], 'weight': 2},
                'financial': {'terms': ['loss', 'decline', 'decrease', 'impairment'], 'weight': 2}
            }
            
            for risk_type, data in risk_indicators.items():
                count = sum(financial_document_data.lower().count(term) for term in data['terms'])
                if count > 0:
                    risk_score += count * data['weight']
                    risks_identified.append(f"{risk_type.title()} Risk: {count} indicators found")
            
            # Risk level assessment
            if risk_score <= 10:
                risk_level = "LOW"
                risk_color = "🟢"
            elif risk_score <= 25:
                risk_level = "MODERATE"
                risk_color = "🟡"
            elif risk_score <= 50:
                risk_level = "HIGH"
                risk_color = "🟠"
            else:
                risk_level = "VERY HIGH"
                risk_color = "🔴"
            
            risk_assessment += f"**Overall Risk Level:** {risk_color} {risk_level} (Score: {risk_score})\n\n"
            
            if risks_identified:
                risk_assessment += "**Risk Factors Identified:**\n"
                for risk in risks_identified[:5]:  # Limit to top 5 risks
                    risk_assessment += f"- {risk}\n"
                risk_assessment += "\n"
            
            # Risk mitigation recommendations
            risk_assessment += "**Risk Mitigation Recommendations:**\n"
            risk_assessment += "- Diversify investment portfolio to reduce concentration risk\n"
            risk_assessment += "- Monitor financial metrics and market conditions regularly\n"
            risk_assessment += "- Stay informed about regulatory changes and industry trends\n"
            risk_assessment += "- Consider hedging strategies for market volatility\n"
            risk_assessment += "- Evaluate management quality and corporate governance\n\n"
            
            # Cash flow and liquidity assessment
            if 'cash flow' in financial_document_data.lower():
                risk_assessment += "**Liquidity Assessment:** Cash flow information detected - review for liquidity risks\n"
            
            return risk_assessment
            
        except Exception as e:
            return f"Error assessing risks: {str(e)}"

class DocumentClassifier(BaseTool):
    name: str = "Document Classifier"
    description: str = "Classifies financial documents by type and identifies the industry sector"

    @cache_result(ttl=3600)  # Cache for 1 hour
    @track_tool_performance("DocumentClassifier")
    def _run(self, document_text: str) -> dict:
        """Classify a financial document by type and industry.
        
        Args:
            document_text (str): Text content of the financial document
            
        Returns:
            dict: Classification results including document type and industry
        """
        try:
            if not document_text or len(document_text.strip()) == 0:
                return {
                    "document_type": "unknown",
                    "industry": "general",
                    "processing_speed": "standard",
                    "confidence": 0.0
                }
            
            # Convert to lowercase for easier matching
            text_lower = document_text.lower()
            
            # Identify document type
            document_type = "unknown"
            processing_speed = "standard"
            
            # Check for annual reports (10-K, annual reports)
            if any(term in text_lower for term in ['10-k', '10k', 'annual report', 'form 10-k']):
                document_type = "annual_report"
                processing_speed = "detailed"
            # Check for quarterly reports (10-Q, quarterly reports)
            elif any(term in text_lower for term in ['10-q', '10q', 'quarterly report', 'form 10-q']):
                document_type = "quarterly_report"
                processing_speed = "fast"
            # Check for earnings reports
            elif any(term in text_lower for term in ['earnings', 'results', 'quarterly earnings', 'financial results']):
                document_type = "earnings_report"
                processing_speed = "fast"
            # Check for prospectus
            elif any(term in text_lower for term in ['prospectus', 'registration statement']):
                document_type = "prospectus"
                processing_speed = "detailed"
            # Check for other financial statements
            elif any(term in text_lower for term in ['balance sheet', 'income statement', 'cash flow statement']):
                document_type = "financial_statement"
                processing_speed = "standard"
            
            # Identify industry sector
            industry = "general"
            industry_keywords = {
                "technology": ["technology", "software", "tech", "computer", "internet", "digital", "ai", "artificial intelligence"],
                "finance": ["bank", "financial", "insurance", "investment", "credit", "loan", "mortgage"],
                "healthcare": ["pharmaceutical", "biotech", "medical", "healthcare", "hospital", "drug"],
                "energy": ["energy", "oil", "gas", "petroleum", "renewable", "solar", "wind"],
                "retail": ["retail", "store", "shopping", "consumer", "ecommerce", "e-commerce"],
                "manufacturing": ["manufacturing", "factory", "production", "industrial", "equipment"],
                "automotive": ["automotive", "car", "vehicle", "auto", "motor"],
                "real_estate": ["real estate", "property", "housing", "reit", "realty"]
            }
            
            # Find the industry with the most matching keywords
            industry_scores = {}
            for sector, keywords in industry_keywords.items():
                score = sum(1 for keyword in keywords if keyword in text_lower)
                if score > 0:
                    industry_scores[sector] = score
            
            if industry_scores:
                industry = max(industry_scores, key=industry_scores.get)
            
            # Calculate confidence based on keyword matches
            total_keywords = sum(len(keywords) for keywords in industry_keywords.values())
            confidence = sum(industry_scores.values()) / total_keywords if total_keywords > 0 else 0.0
            confidence = min(confidence, 1.0)  # Cap at 1.0
            
            return {
                "document_type": document_type,
                "industry": industry,
                "processing_speed": processing_speed,
                "confidence": round(confidence, 2)
            }
            
        except Exception as e:
            logger.error(f"Document classification failed: {e}")
            return {
                "document_type": "unknown",
                "industry": "general",
                "processing_speed": "standard",
                "confidence": 0.0,
                "error": str(e)
            }

# Domain-specific search tools with caching to avoid redundant searches
class FinancialSearchTool(BaseTool):
    name: str = "Financial Search Tool"
    description: str = "Searches for financial data, market trends, and economic indicators"

    @cache_result(ttl=1800)  # Cache for 30 minutes
    @track_tool_performance("FinancialSearchTool")
    def _run(self, query: str) -> str:
        """Search for financial-related information"""
        try:
            # Add financial context to the query
            financial_query = f"financial {query}"
            # Use the existing search_tool instance instead of creating a new one
            result = search_tool._run(financial_query)
            return result
        except Exception as e:
            logger.error(f"Financial search failed: {e}")
            return f"Error performing financial search: {str(e)}"

class InvestmentSearchTool(BaseTool):
    name: str = "Investment Search Tool"
    description: str = "Searches for investment opportunities, stock analysis, and portfolio strategies"

    @cache_result(ttl=1800)  # Cache for 30 minutes
    @track_tool_performance("InvestmentSearchTool")
    def _run(self, query: str) -> str:
        """Search for investment-related information"""
        try:
            # Add investment context to the query
            investment_query = f"investment {query}"
            # Use the existing search_tool instance instead of creating a new one
            result = search_tool._run(investment_query)
            return result
        except Exception as e:
            logger.error(f"Investment search failed: {e}")
            return f"Error performing investment search: {str(e)}"

class RiskSearchTool(BaseTool):
    name: str = "Risk Search Tool"
    description: str = "Searches for risk assessment data, regulatory information, and compliance guidelines"

    @cache_result(ttl=1800)  # Cache for 30 minutes
    @track_tool_performance("RiskSearchTool")
    def _run(self, query: str) -> str:
        """Search for risk-related information"""
        try:
            # Add risk context to the query
            risk_query = f"risk {query}"
            # Use the existing search_tool instance instead of creating a new one
            result = search_tool._run(risk_query)
            return result
        except Exception as e:
            logger.error(f"Risk search failed: {e}")
            return f"Error performing risk search: {str(e)}"

class IndustrySearchTool(BaseTool):
    name: str = "Industry Search Tool"
    description: str = "Searches for industry-specific trends, competitors, and market analysis"

    @cache_result(ttl=1800)  # Cache for 30 minutes
    @track_tool_performance("IndustrySearchTool")
    def _run(self, query: str, industry: str = "") -> str:
        """Search for industry-specific information"""
        try:
            # Add industry context to the query
            industry_query = f"{industry} {query}" if industry else query
            # Use the existing search_tool instance instead of creating a new one
            result = search_tool._run(industry_query)
            return result
        except Exception as e:
            logger.error(f"Industry search failed: {e}")
            return f"Error performing industry search: {str(e)}"

# Create tool instances
financial_document_tool = FinancialDocumentReader()
investment_analysis_tool = InvestmentAnalyzer()
risk_assessment_tool = RiskAssessor()
document_classifier_tool = DocumentClassifier()  # New document classifier tool

# Create specialized search tool instances
financial_search_tool = FinancialSearchTool()
investment_search_tool = InvestmentSearchTool()
risk_search_tool = RiskSearchTool()
industry_search_tool = IndustrySearchTool()

def get_tool_performance_summary():
    """Get performance summary for all tools"""
    summary = {}
    for tool_name, times in tool_performance_metrics.items():
        if times:
            summary[tool_name] = {
                "total_executions": len(times),
                "average_time": sum(times) / len(times),
                "min_time": min(times),
                "max_time": max(times),
                "total_time": sum(times)
            }
    return summary
