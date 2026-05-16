import os
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    # یہ لائن انٹرنیٹ پر انڈیکس فائل کو سکرین پر دکھائے گی
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Index file not found or error: {str(e)}"

@app.route('/api/process-text', \
           methods=['POST'])
def process_text():
    # یہاں موبائل سے آنے والی ریکویسٹ کو پڑھا جا رہا ہے
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'عبارت موصول نہیں ہوئی'}), 400
    
    user_text = data['text']
    
    # لغت میں تلاش کا لاجک (یہاں آپ اپنی ضرورت کے مطابق لغت کا ڈیٹا بڑھا سکتے ہیں)
    result_message = f"آپ نے تلاش کیا: {user_text}\n\n[یہاں لغت کے معنی اور مقامات کی تشریح ظاہر ہوگی۔ آپ کا آن لائن سسٹم اب بالکل تیار ہے!]"
    
    return jsonify({'result': result_message})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
