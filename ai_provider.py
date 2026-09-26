import os, json, requests

def load_config():
    with open('ai_config.json') as f:
        return json.load(f)

def detect_provider(key):
    """Figures out the provider purely from the key's shape."""
    if key.startswith('AIza'):
        return 'gemini'
    if key.startswith('gsk_'):
        return 'groq'
    if key.startswith('sk-or-v1'):
        return 'openrouter'
    if key.startswith('sk-'):
        return 'deepseek_or_openai'   # resolved by trying endpoints
    return None

def ask_ai(prompt, max_tokens=400):
    cfg = load_config()
    key = os.environ.get(cfg['api_key_env'], '')
    if not key:
        return "(No AI_API_KEY secret set)"

    provider = detect_provider(key)
    model = cfg['models'].get(provider, '') if provider in cfg['models'] else None

    try:
        if provider == 'gemini':
            url = cfg['endpoints']['gemini'].format(model=model, key=key)
            r = requests.post(url, json={
                'contents': [{'parts': [{'text': prompt}]}],
                'generationConfig': {'temperature': 0.3, 'maxOutputTokens': max_tokens}
            }, timeout=60)
            r.raise_for_status()
            return r.json()['candidates'][0]['content']['parts'][0]['text']

        # all others share the OpenAI-compatible format
        candidates = ([('deepseek', cfg['endpoints']['deepseek']),
                       ('openai', cfg['endpoints']['openai'])]
                      if provider == 'deepseek_or_openai'
                      else [(provider, cfg['endpoints'][provider])])

        for name, url in candidates:
            try:
                headers = {'Authorization': f'Bearer {key}',
                           'Content-Type': 'application/json'}
                if name == 'openrouter':
                    headers['HTTP-Referer'] = 'https://github.com'
                    headers['X-Title'] = 'OxAlpha Trade Agent'
                r = requests.post(url, headers=headers, json={
                    'model': cfg['models'][name],
                    'temperature': 0.3,
                    'max_tokens': max_tokens,
                    'messages': [{'role': 'user', 'content': prompt}]
                }, timeout=60)
                r.raise_for_status()
                return r.json()['choices'][0]['message']['content']
            except Exception:
                continue   # try next candidate endpoint

        return "(AI request failed on all endpoints)"
    except Exception as e:
        return f"(AI error: {e})"
