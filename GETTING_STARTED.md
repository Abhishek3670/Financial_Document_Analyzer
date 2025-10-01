# Get Started with Financial Document Analyzer

This guide will help you set up and run the Financial Document Analyzer project on your local machine.

## Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.8 or higher
- Node.js 14 or higher
- npm 6 or higher
- Git

## Initial Setup

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd wingily-project
   ```

2. **Set Up the Backend**
   ```bash
   # Create a virtual environment
   python -m venv .venv
   
   # Activate the virtual environment
   source .venv/bin/activate  # On Linux/Mac
   # or
   .venv\Scripts\activate     # On Windows
   
   # Install Python dependencies
   pip install -r requirements.txt
   ```

3. **Set Up the Frontend**
   ```bash
   # Navigate to frontend directory
   cd frontend
   
   # Install Node dependencies
   npm install
   
   # Return to project root
   cd ..
   ```

## Environment Configuration

1. **Create Environment File**
   ```bash
   cp .env.example .env
   ```

2. **Configure Required API Keys in .env**
   - OpenAI API key (for LLM functionality)
   - Serper API key (for search functionality)
   - NVIDIA NIM API key (alternative LLM provider)
   - SECRET_KEY for JWT token signing

## Database Initialization

1. **Run Database Migration**
   ```bash
   python migrate_auth_schema.py
   ```

2. **Verify Database Schema**
   The migration script will:
   - Create a backup of your existing database
   - Add authentication columns to the users table
   - Create necessary indexes for performance
   - Verify the migration was successful

## Running the Application

1. **Start the Backend Server**
   ```bash
   # Make sure virtual environment is activated
   source .venv/bin/activate  # On Linux/Mac
   
   # Run the backend
   python main.py
   ```
   The backend will be available at http://localhost:8000

2. **Start the Frontend Development Server**
   ```bash
   # In a new terminal window
   cd frontend
   
   # Start the development server
   npm start
   ```
   The frontend will be available at http://localhost:3000

3. **Optional: Start Redis for Caching**
   ```bash
   # If you have Docker installed
   docker-compose -f docker-compose.prod.yml up -d redis
   ```

## Accessing the Application

1. Open your browser and navigate to http://localhost:3000
2. The application will automatically show the document upload interface
3. You can register a new account or use the application anonymously
4. Upload a PDF financial document to analyze
5. View analysis results in the history tab

## Development Features

- **Hot Reload**: Both frontend and backend support hot reload for development
- **API Documentation**: Access FastAPI documentation at http://localhost:8000/docs
- **Database**: SQLite database is automatically created in the project directory
- **Caching**: Redis caching is optional but recommended for better performance

## Troubleshooting

1. **Port Conflicts**: If ports 3000 or 8000 are in use, modify the configuration
2. **Database Issues**: Delete [financial_analyzer.db](file:///home/aatish/wingily/wingily-project/financial_analyzer.db) and re-run migration script
3. **Missing Dependencies**: Run `pip install -r requirements.txt` again
4. **Frontend Build Issues**: Clear npm cache with `npm cache clean --force`

## Production Deployment

For production deployment:
1. Use PostgreSQL instead of SQLite
2. Configure proper environment variables
3. Set up Redis for caching
4. Use docker-compose.prod.yml for containerized deployment

## Next Steps

1. Upload a financial document (PDF) using the interface
2. Explore the analysis results
3. Check your analysis history
4. Try different analysis queries

The application is now ready for use!