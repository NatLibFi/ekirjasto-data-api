# E-kirjasto Data API

E-kirjasto Data API is for content providers to view reservation data and history for their collection, made with FastAPI.

E-kirjasto Data Api requires access to E-kirjasto Circulation Manager's Postgres and OpenSearch. Api Tokens are stored in Circulation's database.

## Installation

Install Python (^3.11) and Poetry (^1.8) if you don't have them already.

Install dependencies with:

```
poetry install
```

## Run application locally

You'll need Circulation's Postgres and OpenSearch running and to be accessible for the ekirjasto-data-api app.

Create `.env` file from the example file `.env.example`.

Start the application with:

```
poetry run uvicorn main:app --reload
```

The web UI / documentation is available at http://localhost:8000/docs

## Running tests

Use VSCode's Testing tab (or similar) or run tests on command line with:

```
poetry run pytest
```

## Linting

Use locally installed Black to autoformat code.

You can also run Black from the command line:

```
poetry run black .
```
