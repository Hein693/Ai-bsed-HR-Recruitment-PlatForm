# Nexus Recruitment AI

A local-first recruitment support system for Nexus, built with Python, FastAPI, SQLite, and transparent machine learning.

It helps a recruiter create jobs, store candidates, rank role-specific matches, collect structured screening results, create fair interview material, and train an optional classifier from human-reviewed qualification examples. The application never makes a final hiring decision.

## Features

- Job and candidate records stored in SQLite
- Transparent baseline ranking using TF-IDF text similarity and required-skill coverage
- Optional logistic-regression model trained only from human-reviewed qualification outcomes
- Structured evidence, gaps, and suggested screening questions for every result
- Copy-ready Nexus core system prompt and workflow prompts
- A browser dashboard and documented API at `/docs`

## Run it

1. Install Python 3.11 or newer, then create and activate a virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Start the application: `uvicorn app.main:app --reload`
4. Open `http://127.0.0.1:8000`

The database is created automatically at `data/nexus.db`. Copy `.env.example` to `.env` if you want to configure a database URL or model location.

## Responsible use

The matching score is decision support, not an eligibility or hiring decision. Recruiters must review every result and use role-specific, job-relevant evidence. Do not include protected characteristics, health details, immigration status beyond confirmed work authorization where legally appropriate, or unrelated personal details in the model data.

The supervised model requires at least four human-reviewed examples and both qualification labels. Review its training data periodically for bias and keep a human reviewer responsible for all outcomes.
