## Importing libraries and files
import os
from dotenv import load_dotenv

from crewai_tools import SerperDevTool
from crewai.tools import BaseTool
from langchain_community.document_loaders import PyPDFLoader

# Load environment variables
load_dotenv()
from dotenv import load_dotenv
load_dotenv()

from crewai_tools import SerperDevTool
from crewai.tools import BaseTool
from langchain_community.document_loaders import PyPDFLoader

## Creating search tool with Serper
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
        # If the path doesn't start with /, prepend the current directory
        if not file_path.startswith('/'):
            file_path = os.path.join(os.getcwd(), file_path)
        loader = PyPDFLoader(file_path)
        docs = loader.load()        
        full_report = ""
        for data in docs:
            content = data.page_content
            while "\n\n" in content:
                content = content.replace("\n\n", "\n")
            full_report += content + "\n"
            
        return full_report

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
        processed_data = financial_document_data
        
        # Clean up the data format
        i = 0
        while i < len(processed_data):
            if processed_data[i:i+2] == "  ":  # Remove double spaces
                processed_data = processed_data[:i] + processed_data[i+1:]
            else:
                i += 1
                
        # TODO: Implement investment analysis logic here
        return "Investment analysis functionality to be implemented"

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
        # TODO: Implement risk assessment logic here
        return "Risk assessment functionality to be implemented"

# Create tool instances
financial_document_tool = FinancialDocumentReader()
investment_analysis_tool = InvestmentAnalyzer()
risk_assessment_tool = RiskAssessor()

