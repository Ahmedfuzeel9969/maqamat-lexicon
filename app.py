import os
import re
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
import pytesseract

app = Flask(__name__)
CORS(app)

# ونڈوز کو ٹیسیریکٹ سافٹ ویئر کا اصل راستہ بتانا (خرابی دور کرنے کے لیے)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# اے آئی (Gemini) کی چابی اگر آپ کے پاس ہو، ورنہ یہ متبادل کے ساتھ چلے گا
os.environ["GEMINI_API_KEY"] = "YOUR_GEMINI_API_KEY_HERE"

def add_arabic_diacritics(text):
    try:
        url = "https://mishkal.herokuapp.com/api/diacritize"
        response = requests.post(url, json={"text": text}, timeout=10)
        if response.status_code == 200:
            return response.json().get("result", text)
    except Exception:
        pass
    return text

def get_arabic_root(word):
    if not word: return ""
    clean_for_root = re.sub(r'[\u064B-\u0652\u0640]', '', word)
    if clean_for_root.startswith("ال"): clean_for_root = clean_for_root[2:]
    if clean_for_root.startswith(("فال", "بال", "وال", "كال")): clean_for_root = clean_for_root[3:]
    elif clean_for_root.startswith(("لل", "بال")): clean_for_root = clean_for_root[2:]
    
    root = clean_for_root
    if root.startswith(("ب", "و", "ف", "ل")) and len(root) > 3: root = root[1:]
    if len(root) > 3 and root.startswith(("ي", "ت", "ن", "أ")): root = root[1:]
    
    suffixes = ["ون", "ين", "ات", "تما", "هما", "كم", "هم", "نا", "تم", "تا", "ة", "ه", "ا"]
    for suf in suffixes:
        if root.endswith(suf) and len(root) > 3:
            root = root[:-len(suf)]
            break
    return root if len(root) >= 2 else clean_for_root

def ask_ai_dictionary(word, context_text, mode="restricted"):
    try:
        client = genai.Client()
        if mode == "restricted":
            prompt = f"""
            تم ایک متبحر عربی لغت نویس اور علامہ حریری کے اسلوب کے ماہر ہو۔ 
            تمہیں صرف اور صرف نیچے دیے گئے متن (Context) کی حدود میں رہ کر لفظ "{word}" کی علمی، لغوی اور اصطلاحی تشریح کرنی ہے۔
            ضابطہ: اگر یہ لفظ اس متن میں موجود نہ ہو یا اس کا لغوی حل اس متن سے واضح نہ ہو رہا ہو، تو باہر سے کوئی کہانی نہ بناؤ، بلکہ صاف اردو میں لکھ دو کہ "یہ لفظ فراہم کردہ متن کی حدود میں نہیں ملا"۔
            فراہم کردہ متن:
            \"\"\"{context_text}\"\"\"
            جواب صرف اردو زبان میں، علمی اور جامع ہونا چاہیے، جس میں مادہ اور نحوی/صرفی فائدہ مذکور ہو۔
            """
        else:
            prompt = f"""
            تم ایک مائہ ناز عربی لغت نگار ہو۔ لفظ "{word}" کی مقاماتِ حریری کے ادبی اسلوب کے پیشِ نظر مکمل لغوی، صرفی، اور نحوی تحقیق پیش کرو۔
            اس کا اصل مادہ، باب، اور مقامات میں اس کے مروجہ ادبی معنی واضح کرو۔ جواب علمی اردو میں ہو۔
            """
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text
    except Exception:
        return "⚠️ اے آئی کنکشن یا API KEY پائتھن میں موجود نہیں ہے۔ لغت کا متبادل نظام فعال ہے۔"

@app.route('/api/process-text', methods=['POST'])
def process_text():
    try:
        data = request.json or {}
        raw_text = data.get("text", "")
        ai_mode = data.get("ai_mode", "restricted")
        
        if not raw_text.strip(): 
            return jsonify({"error": "متن خالی ہے"}), 400
            
        vocalized_text = add_arabic_diacritics(raw_text)
        lines = vocalized_text.split('\n')
        global_words = []
        punctuation = re.compile(r'[۔،؟؛؛۔_()\[\]{}""\'\'‘’“”«»!@#$%^&*+=~\-|,.<>:\/]')
        
        for line in lines:
            trimmed = line.strip()
            if not trimmed: continue
            words = trimmed.split()
            for w in words:
                clean_w = punctuation.sub('', w).strip()
                if len(clean_w) > 1:
                    global_words.append({"original": w, "clean": clean_w})
                    
        root_index = {}
        index_list = []
        for idx, item in enumerate(global_words):
            root_word = get_arabic_root(item["clean"])
            if root_word not in root_index:
                root_index[root_word] = {"original_words": set(), "ai_explanation": ""}
            
            root_index[root_word]["original_words"].add(item["original"])
            if not root_index[root_word]["ai_explanation"]:
                root_index[root_word]["ai_explanation"] = ask_ai_dictionary(item["clean"], raw_text, ai_mode)
            
            start = max(0, idx - 4)
            end = min(len(global_words), idx + 5)
            snippet = ["__START_HIGHLIGHT__" + global_words[i]['original'] + "__END_HIGHLIGHT__" if i == idx else global_words[i]['original'] for i in range(start, end)]
            
            index_list.append({
                "clean_word": item["original"],
                "root_key": root_word,
                "context": "... " + " ".join(snippet) + " ..."
            })
            
        sorted_roots = sorted(root_index.keys())
        sorted_index_list = sorted(index_list, key=lambda x: x["root_key"])
        
        final_lexicon = {}
        for r in sorted_roots:
            final_lexicon[r] = {
                "words": list(root_index[r]["original_words"]),
                "ai_notes": root_index[r]["ai_explanation"]
            }
        return jsonify({
            "lexicon": final_lexicon,
            "index": sorted_index_list
        })
    except Exception as e:
        return jsonify({"error": f"سسٹم میں خرابی: {str(e)}"}), 500

if __name__ == '__main__':
    print("🤖 اسمارٹ اے آئی لغت ساز (محصور و عام موڈ) پورٹ 5000 پر فعال ہے...")
    app.run(port=5000, debug=True)