import os, json, requests

def load_config():
    with open('ai_config.json') as f:
        return json.load(f)

def ask_ai(prompt, max_tokens=400):
    """Universal AI call. Reads ai_config.json each time — so you can
    switch provider/model/key without touching any code."""
    cfg = load_config()
    pname = cfg['provider']
    p = cfg['providers'][pname]
    key = os.environ.get(p['key_env'], '')
    if not key:
        return f"(No API key found for provider '{pname}' — set secret {p['key_env']})"

    try:
        if p['type'] == 'gemini':
            url = (f"{p['base_url']}/v1beta/models/{cfg['model']}:generateContent"
                   f"?key={key}")
            r = requests.post(url, json={
                'contents': [{'parts': [{'text': prompt}]}],
                'generationConfig': {'temperature': cfg.get('temperature', 0.3),
                                     'maxOutputTokens': max_tokens}
            }, timeout=60)
            r.raise_for_status()
            return r.json()['candidates'][0]['content']['parts'][0]['text']

        elif p['type'] == 'openai_compatible':
            headers = {'Authorization': f'Bearer {key}',
                       'Content-Type': 'application/json'}
            if pname == 'openrouter':
                headers['HTTP-Referer'] = 'https://github.com'
                headers['X-Title'] = 'OxAlpha Trade Agent'
            r = requests.post(p['base_url'], headers=headers, json={
                'model': cfg['model'],
                'temperature': cfg.get('temperature', 0.3),
                'max_tokens': max_tokens,
                'messages': [{'role': 'user', 'content': prompt}]
            }, timeout=60)
            r.raise_for_status()
            return r.json()['choices'][0]['message']['content']

        else:
            return f"(Unknown provider type: {p['type']})"
    except Exception as e:
        return f"(AI provider '{pname}' error: {e})"
