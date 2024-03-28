# ekirjasto-data-api

E-kirjasto Data API is for content providers to view reservation data and history for their collection, made with FastAPI.

E-kirjasto Data Api requires access to E-kirjasto Circulation Manager's Postgres and OpenSearch. Api Tokens are stored in Circulation's database.

## Installation

Create `.env` file from the example file `.env.example`.

### Install dependencies using pip and venv

Create and activate virtual environment and install dependencied with
`pip install -r requirements`

### Install dependencies using Conda

Create environment from requirements with
`conda create --name <env> --file requirements.txt`

## Run application locally

Start the application with
`uvicorn main:app --reload`

The web UI / documentation is available at http://localhost:8000/docs
