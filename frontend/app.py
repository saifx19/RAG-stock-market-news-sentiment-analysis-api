import streamlit as st
import requests
import re


API_URL = "http://127.0.0.1:8000/generate_report/"


def highlight_bold_sections(text):
    """Find text between ** ** and apply bold styling"""
    highlighted_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    return highlighted_text


st.title("Stock Market News & Sentiment Analysis")

stocks = ['', 'AAPL', 'AMZN', 'GOOGL', 'META', 'MSFT']
stock_name = st.selectbox('Choose a stock symbol', stocks)

if st.button('Generate Report'):
    if not stock_name:
        st.error('Please enter a stock symbol.')
    else:
        payload = {"symbol": stock_name}

        response = requests.post(API_URL, json=payload)

        if response.status_code == 200:
            report = response.json().get("report", "")
            if report:
                st.subheader(f"Report for {stock_name}")
                
                highlighted_report = highlight_bold_sections(report)
                
                st.write(highlighted_report, unsafe_allow_html=True)
            else:
                st.error("No report generated. Please try again later.")
        else:
            st.error(f"Error fetching the report: {response.status_code}")