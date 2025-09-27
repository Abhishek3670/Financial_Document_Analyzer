#!/bin/bash

echo "Testing financial document analysis..."

# Check if test file exists
if [ ! -f "data/TSLA-Q2-2025-Update.pdf" ]; then
    echo "Test PDF file not found. Using any available PDF..."
    TEST_FILE=$(ls data/*.pdf | head -1)
    if [ -z "$TEST_FILE" ]; then
        echo "No PDF files found in data/ directory"
        exit 1
    fi
else
    TEST_FILE="data/TSLA-Q2-2025-Update.pdf"
fi

echo "Using test file: $TEST_FILE"

# Make the analysis request
echo "Making analysis request..."
curl -X POST \
  -F "file=@${TEST_FILE}" \
  -F "query=Provide a brief financial analysis of this document" \
  -F "keep_file=true" \
  http://localhost:8000/analyze \
  -w "\nHTTP Status: %{http_code}\n" \
  -o analysis_result.json

echo ""
echo "Response saved to analysis_result.json"

# Check if the response is valid JSON and show key info
if [ -f analysis_result.json ]; then
    echo ""
    echo "=== Analysis Response Summary ==="
    
    # Extract key fields
    STATUS=$(python3 -c "import json; data=json.load(open('analysis_result.json')); print(data.get('status', 'unknown'))" 2>/dev/null || echo "unknown")
    ANALYSIS_ID=$(python3 -c "import json; data=json.load(open('analysis_result.json')); print(data.get('analysis_id', 'unknown'))" 2>/dev/null || echo "unknown")
    ANALYSIS_LENGTH=$(python3 -c "import json; data=json.load(open('analysis_result.json')); print(len(data.get('analysis', '')) if data.get('analysis') else 0)" 2>/dev/null || echo "0")
    
    echo "Status: $STATUS"
    echo "Analysis ID: $ANALYSIS_ID"
    echo "Analysis Length: $ANALYSIS_LENGTH characters"
    
    if [ "$ANALYSIS_LENGTH" -gt 100 ]; then
        echo ""
        echo "=== First 300 characters of analysis ==="
        python3 -c "import json; data=json.load(open('analysis_result.json')); print(data.get('analysis', 'No analysis')[:300] + '...' if len(data.get('analysis', '')) > 300 else data.get('analysis', 'No analysis'))" 2>/dev/null
    else
        echo ""
        echo "=== Full analysis (short) ==="
        python3 -c "import json; data=json.load(open('analysis_result.json')); print(data.get('analysis', 'No analysis'))" 2>/dev/null
    fi
    
    # If analysis ID is available, fetch the full result from the API
    if [ "$ANALYSIS_ID" != "unknown" ] && [ "$ANALYSIS_ID" != "" ]; then
        echo ""
        echo "=== Fetching from /analysis/$ANALYSIS_ID endpoint ==="
        curl -s "http://localhost:8000/analysis/$ANALYSIS_ID" > analysis_from_db.json
        
        DB_ANALYSIS_LENGTH=$(python3 -c "import json; data=json.load(open('analysis_from_db.json')); print(len(data.get('analysis', {}).get('result', '')) if data.get('analysis') else 0)" 2>/dev/null || echo "0")
        echo "Analysis length from database: $DB_ANALYSIS_LENGTH characters"
        
        if [ "$DB_ANALYSIS_LENGTH" -gt 100 ]; then
            echo ""
            echo "=== First 300 characters from database ==="
            python3 -c "import json; data=json.load(open('analysis_from_db.json')); print(data.get('analysis', {}).get('result', 'No analysis')[:300] + '...' if len(data.get('analysis', {}).get('result', '')) > 300 else data.get('analysis', {}).get('result', 'No analysis'))" 2>/dev/null
        else
            echo ""
            echo "=== Full analysis from database (short) ==="
            python3 -c "import json; data=json.load(open('analysis_from_db.json')); print(data.get('analysis', {}).get('result', 'No analysis'))" 2>/dev/null
        fi
    fi
fi

echo ""
echo "Test completed."
