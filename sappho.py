from flask import Flask, render_template, request, jsonify
import os
#from peewee import *
from text_analysis import analyze_text
#from model import db_proxy, Text
#from datetime import datetime
#from time import time

app = Flask(__name__)
app.config.update(**os.environ)
# Preserve the former URL-encoded form bound, including encoded field overhead.
try:
    app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 500_000))
except ValueError:
    raise ValueError('MAX_CONTENT_LENGTH must be a positive integer') from None
if app.config['MAX_CONTENT_LENGTH'] <= 0:
    raise ValueError('MAX_CONTENT_LENGTH must be a positive integer')


@app.route('/')
def sappho_route():
    return render_template('sappho.html')


@app.route('/about')
def about_route():
    return render_template('about.html')


@app.route('/analyze-text', methods=['POST'])
def analyze():
    html = request.form.get('html', '')
    #analysis_start = time()
    text, tokens, metrics = analyze_text(html)
    #analysis_time = time() - analysis_start
    #Text.create(text=text, timestamp=datetime.now().replace(microsecond=0), **metrics)
    #Text.create(timestamp=datetime.now().replace(microsecond=0), analysis_time=analysis_time,
    #            character_count=metrics['character_count'], word_count=metrics['word_count'],
    #            sentence_count=metrics['sentence_count'])
    return jsonify({'text': text, 'tokens': tokens, 'metrics': metrics})





if __name__ == '__main__':
    app.run()
