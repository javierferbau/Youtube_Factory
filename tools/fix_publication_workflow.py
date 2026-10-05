#!/usr/bin/env python3
import urllib.request
import json
import sys

def get_n8n_api_key():
    import os
    key = os.getenv("N8N_API_KEY")
    if key:
        return key
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('N8N_API_KEY='):
                    return line.strip().split('=', 1)[1].strip(' "\'')
    return ""

API_KEY = get_n8n_api_key()
HEADERS = {
    'X-N8N-API-KEY': API_KEY,
    'Content-Type': 'application/json'
}

WF_ID = 'TxgttWgvz4Fpjn6K'
WF_URL = f'http://localhost:5678/api/v1/workflows/{WF_ID}'

NEW_BOT_RESPONSE_CODE = """const item = $input.first().json;
const raw = item.output || {};
let parsed = {};

if (typeof raw === 'string') {
  try {
    parsed = JSON.parse(raw.replace(/```json/g, '').replace(/```/g, '').trim());
  } catch (e) {
    // Attempt 1: Auto-repair missing commas before new properties
    try {
      const repaired = raw
        .replace(/```json/g, '')
        .replace(/```/g, '')
        .replace(/(["\\d\\]}])\\s*\\n\\s*"/g, '$1,\\n"')
        .trim();
      parsed = JSON.parse(repaired);
    } catch (e2) {
      parsed = {};
    }
  }
} else if (typeof raw === 'object' && raw !== null) {
  parsed = raw;
}

// Attempt 2: Fallback regex extraction if title or description is missing
if (typeof raw === 'string') {
  if (!parsed.title) {
    const titleMatch = raw.match(/"title"\\s*:\\s*"([^"\\\\]*(?:\\\\.[^"\\\\]*)*)"/);
    if (titleMatch) {
      try { parsed.title = JSON.parse(`"${titleMatch[1]}"`); } catch(e) { parsed.title = titleMatch[1]; }
    }
  }
  if (!parsed.description) {
    const descMatch = raw.match(/"description"\\s*:\\s*"([^"\\\\]*(?:\\\\.[^"\\\\]*)*)"/);
    if (descMatch) {
      try { parsed.description = JSON.parse(`"${descMatch[1]}"`); } catch(e) { parsed.description = descMatch[1]; }
    }
  }
  if (!parsed.user_tags && !parsed.tags) {
    const userTagsMatch = raw.match(/"user_tags"\\s*:\\s*"([^"]+)"/);
    if (userTagsMatch) parsed.user_tags = userTagsMatch[1];
    const tagsMatch = raw.match(/"tags"\\s*:\\s*\\[([\\s\\S]*?)\\]/);
    if (tagsMatch) {
      try { parsed.tags = JSON.parse(`[${tagsMatch[1]}]`); } catch(e) {}
    }
  }
}

// Guarantee user_tags is ALWAYS a primitive comma-separated string
let user_tags = '';
if (Array.isArray(parsed.user_tags)) {
  user_tags = parsed.user_tags.join(',');
} else if (typeof parsed.user_tags === 'string') {
  user_tags = parsed.user_tags;
} else if (Array.isArray(parsed.tags)) {
  user_tags = parsed.tags.map(t => String(t).replace(/\\s+/g, '')).join(',');
}

let tags = [];
if (Array.isArray(parsed.tags)) {
  tags = parsed.tags;
} else if (typeof parsed.tags === 'string') {
  tags = parsed.tags.split(',').map(t => t.trim());
}

return [{
  json: {
    ...item,
    ...parsed,
    title: parsed.title || '',
    description: parsed.description || '',
    tags,
    user_tags: String(user_tags)
  }
}];"""

def update_workflow():
    req = urllib.request.Request(WF_URL, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        wf = json.loads(resp.read().decode('utf-8'))

    # Backup
    with open('/home/javierferb/n8n/workflow_TxgttWgvz4Fpjn6K.backup.json', 'w') as f:
        json.dump(wf, f, indent=2)
    print("Backup saved.")

    for n in wf.get('nodes', []):
        if n.get('name') == 'BOT response to JSON':
            n['parameters']['jsCode'] = NEW_BOT_RESPONSE_CODE
            print("Updated BOT response to JSON")
        elif n.get('name') == 'AI SCRIPTS Agent':
            txt = n.get('parameters', {}).get('text', '')
            if 'Ensure strictly valid JSON syntax' not in txt:
                n['parameters']['text'] = txt.replace(
                    "REMINDER: Output NOTHING outside the JSON curly braces { }.",
                    "REMINDER: Output NOTHING outside the JSON curly braces { }. Ensure strictly valid JSON syntax with commas separating all keys."
                )
            print("Updated AI SCRIPTS Agent")

    settings = {k: v for k, v in wf.get('settings', {}).items() if k != 'binaryMode'}
    payload = {
        'name': wf['name'],
        'nodes': wf['nodes'],
        'connections': wf['connections'],
        'settings': settings
    }

    req_put = urllib.request.Request(WF_URL, data=json.dumps(payload).encode('utf-8'), headers=HEADERS, method='PUT')
    with urllib.request.urlopen(req_put) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("PUT workflow successful. Version:", res.get('versionId'))

    # Reactivate workflow
    deact = urllib.request.Request(f'{WF_URL}/deactivate', headers=HEADERS, method='POST')
    try:
        with urllib.request.urlopen(deact) as resp:
            print("Deactivated.")
    except Exception as e:
        pass

    act = urllib.request.Request(f'{WF_URL}/activate', headers=HEADERS, method='POST')
    with urllib.request.urlopen(act) as resp:
        print("Reactivated successfully.")

if __name__ == '__main__':
    update_workflow()
