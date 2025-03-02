# Entity Viewer

A modern web application for viewing and managing business entity data with risk assessments, sanctions information, and compliance data.

## Features

- Dynamic card-based layout for each entity
- Advanced search and filtering capabilities
- Detailed view of business relationships and risk indicators
- Modern UI with intuitive navigation
- Support for various data types including sanctions, compliance, and business relationships

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Place your CSV data file in the `data` directory

3. Run the application:
```bash
python app.py
```

4. Access the application at `http://localhost:5000`

## Project Structure

```
entity-viewer/
├── app.py              # Main Flask application
├── data/              # Data directory for CSV files
├── static/
│   ├── css/          # Stylesheets
│   └── js/           # JavaScript files
├── templates/         # HTML templates
└── requirements.txt   # Python dependencies
```

## Data Structure

The application expects a CSV file with specific fields as documented in the data structure section. Key fields include:

- Entity identification (`_id`, `name`, `fullname`, `reference`)
- Risk indicators (`currentSanctions`, `lawEnforcement`, etc.)
- Supporting documentation (`documents`, `evidences`)
- Business relationships and addresses
