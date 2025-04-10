import csv
from flask import Flask, render_template, jsonify, request, redirect, url_for
import requests
from deep_translator import GoogleTranslator
from api import news_api_key, groq_api_key
from groq import Groq
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq

app = Flask(__name__)
global preferred_language

# Route for the signup page
@app.route('/signup', methods=['POST'])
def signup():
    name = request.form.get('name')
    email = request.form.get('email')
    language = request.form.get('language')

    # Save details to a CSV file
    with open('users.csv', mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([name, email, language])

    return redirect(url_for('prefer_page'))

# Route for the login page
@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')

    # Check if the email exists in the CSV file
    with open('users.csv', mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            if row[1] == email:  # Check if the email matches
                global preferred_language
                preferred_language = row[2]  # Get the preferred language from the CSV
                return redirect(url_for('home_page'))

    return "Login failed. Email not found.", 401

@app.route('/prefer')
def prefer_page():
    return render_template('prefer.html')

@app.route('/prefer', methods=['POST', 'GET'])
def prefer():
    if request.method == 'POST':
        global preferred_language
        preferred_language = request.form.get('language')
        print(preferred_language)
        return redirect(url_for('home_page'))

@app.route('/home')
def home_page():
    global preferred_language
    return render_template('home.html', preferred_language=preferred_language)

@app.route('/chat')
def chat_page():
    global preferred_language
    return render_template('chat.html', preferred_language=preferred_language)

chat_history = []

@app.route('/chat', methods=['POST'])
def chat():
    global preferred_language
    data = request.json
    user_question = data.get('question')

    groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name='llama3-8b-8192')
    memory = ConversationBufferWindowMemory(k=5)

    conversation = ConversationChain(
        llm=groq_chat,
        memory=memory
    )

    translator = GoogleTranslator(source='auto', target='en')
    translated_question = translator.translate(user_question)

    # Adjust the prompt to include allowed topics
    prompt = (
        "You are an assistant that only answers questions related to the following topics in India: "
        "government orders, local news, services, articles, laws, constitution, opportunities, rights, and women. "
        "If the question is unrelated, politely decline to answer. "
        f"Here is the question: {translated_question}"
    )

    response = conversation(prompt)
    translated_response = GoogleTranslator(source='en', target=preferred_language).translate(response['response'])

    message = {'human': user_question, 'AI': translated_response}
    chat_history.append(message)

    return jsonify({'response': translated_response, 'history': chat_history})

@app.route('/news')
def news():
    global preferred_language
    api_key = news_api_key
    url = f'https://newsapi.org/v2/top-headlines?sources=bbc-news&apiKey={api_key}'
    
    try:
        response = requests.get(url)
        news_data = response.json()
        print("API Response:", news_data)  # Debugging log
        print("Preferred Language:", preferred_language)  # Debugging log

        articles = [
            {
                "author": "author :" + (article.get("author") or "Unknown"),
                "title": "title :" + (article.get("title") or "Untitled"),
                "url": article.get("url")
            }
            for article in news_data.get("articles", [])
        ]

        translator = GoogleTranslator(source='auto', target=preferred_language)

        for article in articles:
            if article["title"]:
                article["title"] = translator.translate(article["title"])
            if article["author"]:
                article["author"] = translator.translate(article["author"])

        return render_template("news.html", articles=articles, preferred_language=preferred_language)
    except Exception as e:
        print("Error:", str(e))  # Debugging log
        return jsonify({"error": str(e)}), 500
    
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
