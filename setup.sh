#!/bin/bash

# Trustworthy RAG System - Setup Script
# This script helps you set up the development environment

set -e  # Exit on error

echo "🛡️  Trustworthy RAG System - Setup"
echo "=================================="
echo ""

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.9"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
    echo "❌ Python 3.9+ required. Found: $python_version"
    exit 1
fi
echo "✅ Python version OK: $python_version"
echo ""

# Create virtual environment
echo "🔧 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --quiet --upgrade pip
echo "✅ pip upgraded"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
pip install --quiet -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Check for .env file
echo "🔐 Checking environment configuration..."
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found"
    echo ""
    read -p "Do you have an OpenAI API key? (y/n): " has_key
    
    if [ "$has_key" == "y" ] || [ "$has_key" == "Y" ]; then
        read -p "Enter your OpenAI API key: " openai_key
        
        # Create .env file
        cat > .env << EOF
# OpenAI Configuration (Required)
OPENAI_API_KEY=$openai_key

# Optional: Pinecone for production vector DB
# PINECONE_API_KEY=your-pinecone-key-here

# Optional: Redis for caching
# REDIS_URL=redis://localhost:6379/0

# Model Configuration
MODEL_NAME=gpt-3.5-turbo
MODEL_TEMPERATURE=0.7

# Logging
LOG_LEVEL=INFO
EOF
        echo "✅ .env file created"
    else
        echo "⚠️  Please obtain an OpenAI API key from https://platform.openai.com/api-keys"
        echo "   Then create a .env file with: OPENAI_API_KEY=your-key-here"
    fi
else
    echo "✅ .env file found"
fi
echo ""

# Create logs directory
echo "📁 Creating logs directory..."
mkdir -p logs
echo "✅ Logs directory created"
echo ""

# Run a simple test
echo "🧪 Running basic tests..."
if pytest tests/ -q --tb=no > /dev/null 2>&1; then
    echo "✅ Tests passed"
else
    echo "⚠️  Some tests failed (this is OK if API keys are not set)"
fi
echo ""

# Summary
echo "=================================="
echo "✅ Setup complete!"
echo ""
echo "📚 Next steps:"
echo ""
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Run the CLI application:"
echo "   make run"
echo "   # or"
echo "   cd src && python app.py"
echo ""
echo "3. Run the API server:"
echo "   make run-api"
echo "   # or"
echo "   cd src && uvicorn api:app --reload"
echo ""
echo "4. Run with Docker:"
echo "   docker-compose up -d"
echo ""
echo "5. View available commands:"
echo "   make help"
echo ""
echo "📖 Documentation:"
echo "   - README.md: User guide and examples"
echo "   - ARCHITECTURE.md: Technical architecture"
echo "   - API docs: http://localhost:8000/docs (when running)"
echo ""
echo "🎉 Happy coding!"
echo ""

