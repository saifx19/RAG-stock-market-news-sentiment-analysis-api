from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
import os
from pydantic import BaseModel
import requests
from datetime import datetime, timedelta
from groq import Groq


app = FastAPI()

load_dotenv()
ALPHAVANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


class StockRequest(BaseModel):
    symbol: str

# Function to get date 90 days before today
def get_date_90_days_ago():
    now = datetime.now()
    date_90_days_ago = now - timedelta(days=90)
    return date_90_days_ago.strftime('%Y%m%dT%H%M')


@app.post("/generate_report/")
async def generate_report(request: StockRequest):
    symbol = request.symbol
    time_from = get_date_90_days_ago()
    sort = "RELEVANCE"
    
    # Construct URL for API request
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol}&time_from={time_from}&sort={sort}&apikey={ALPHAVANTAGE_API_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()
        sentiment_score_def = data.get("sentiment_score_definition", "")
        relevance_score_def = data.get("relevance_score_definition", "")
        feed_data = data.get("feed", [])
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail="Error fetching data from AlphaVantage")

    # Structure data
    structured_data = f"""
    Definitions:
    - Sentiment Score: {sentiment_score_def}
    - Relevance Score: {relevance_score_def}
    News Data:
    """
    
    # Process each item in feed
    for i, item in enumerate(feed_data, 1):
        title = item.get("title", "N/A")
        time_published = item.get("time_published", "N/A")
        author = ", ".join(item.get("authors", [])) if item.get("authors") else "N/A"
        summary = item.get("summary", "N/A")
        overall_sentiment = item.get("overall_sentiment_score", "N/A")
        overall_sentiment_label = item.get("overall_sentiment_label", "N/A")

        # Filter ticker sentiment for selected symbol and relevance > 0.4
        filtered_ticker_sentiments = [
            f"- {ts['ticker']}: Relevance {ts['relevance_score']}, Sentiment {ts['ticker_sentiment_score']} ({ts['ticker_sentiment_label']})"
            for ts in item.get("ticker_sentiment", [])
            if ts['ticker'] == symbol and float(ts['relevance_score']) > 0.4
        ]

        if not filtered_ticker_sentiments:
            continue
        
        # Append news item to structured input
        structured_data += f"""
        {i}. Title: {title}
           Time Published: {time_published}
           Author: {author}
           Summary: {summary}
           Sentiment Scores:
           - Overall Sentiment: {overall_sentiment} ({overall_sentiment_label})
           - Ticker Sentiments:
             {' '.join(filtered_ticker_sentiments)}
        """
        if i % 5 == 0:
            structured_data += "\n--- Batch Break ---\n"
    
    # Initialize Groq client
    client = Groq(api_key=GROQ_API_KEY)

    system_prompt = "You are an expert financial analyst specializing in stock market reports. Your task is to create a concise, easy-to-understand stock report about the selected company. The report should focus on the news highlights, potential implications for investors, and sentiment analysis. Use plain language, and avoid technical jargon such as bearish, bullish, sentiment score, and relevance score. Ensure the tone is professional yet approachable, catering to an audience with basic investment knowledge."

    # Generate chat completion using Groq API
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": structured_data},
        ], 
        model="llama-3.1-70b-versatile",
        temperature=0.5,
        top_p=0.9,
    )
    
    # Return generated message content
    return {"report": chat_completion.choices[0].message.content}
