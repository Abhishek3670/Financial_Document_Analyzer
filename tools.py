import os
import re
from dotenv import load_dotenv
from crewai_tools import SerperDevTool
from crewai.tools import BaseTool
from langchain_community.document_loaders import PyPDFLoader

# Load environment variables
load_dotenv()

# Creating search tool with Serper
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
search_tool = SerperDevTool(api_key=SERPER_API_KEY)

class FinancialDocumentReader(BaseTool):
    name: str = "Financial Document Reader"
    description: str = "Reads and processes financial documents from PDF files"

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
            
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            
            if not docs:
                return "Error: PDF file appears to be empty or corrupted."
            
            full_report = ""
            for data in docs:
                content = data.page_content
                # Clean up multiple newlines
                content = re.sub(r'\n+', '\n', content)
                full_report += content + "\n"
            
            # Limit output size to prevent memory issues
            if len(full_report) > 100000:  # 100KB limit
                full_report = full_report[:100000] + "\n[Content truncated due to size...]"
                
            return full_report
            
        except Exception as e:
            return f"Error reading PDF file: {str(e)}"

class InvestmentAnalyzer(BaseTool):
    name: str = "Investment Analyzer"
    description: str = "Analyzes financial document data and provides investment insights"

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

# Create tool instances
financial_document_tool = FinancialDocumentReader()
investment_analysis_tool = InvestmentAnalyzer()
risk_assessment_tool = RiskAssessor()
