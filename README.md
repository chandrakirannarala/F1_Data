F1 Performance Analysis Platform - Setup Guide
🏁 Quick Start
Key Changes Made:

Removed OAuth Authentication - OpenF1 API is free and public, no credentials needed
Updated API calls - Using simple HTTP requests instead of OAuth
Enhanced data models - Added more comprehensive F1 data structures
Improved caching - Better cache management with Redis support
Fixed dependencies - Proper Poetry configuration

📋 Prerequisites

Python 3.10 or higher
Poetry (recommended) or pip
Optional: Redis for enhanced caching

🚀 Installation
Option 1: Using Poetry (Recommended)
bash# Clone or download the project
cd f1-performance-analysis

# Install dependencies
poetry install

# Optional: Install with Redis support
poetry install --extras redis

# Activate virtual environment
poetry shell

# Run the application
python app.py
Option 2: Using pip
bash# Create virtual environment
python -m venv f1_env
source f1_env/bin/activate  # On Windows: f1_env\Scripts\activate

# Install dependencies
pip install requests pandas dash plotly pydantic cachetools redis

# Run the application
python app.py
🔧 Configuration
Environment Variables (Optional)
bash# For Redis caching (optional)
export REDIS_URL="redis://localhost:6379"

# For development
export FLASK_ENV=development
Cache Configuration
The application uses a two-tier caching system:

In-memory cache - Always active, 10-minute TTL
Redis cache - Optional, configurable TTL per data type

🎮 Usage

Start the application:
bashpython app.py

Open your browser:

Navigate to http://localhost:8050
The dashboard will load with the latest available F1 data


Explore the features:

Select different drivers from the dropdown
View lap time trends and distributions
Compare teammate performance
Analyze tyre strategies and degradation
Examine sector times and pit stop performance