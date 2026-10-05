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

ANTI_THINK_TEXT = "CRITICAL DIRECTIVE: DO NOT THINK OR OUTPUT ANY REASONING. START DIRECTLY WITH { AND OUTPUT ONLY RAW JSON.\n\n"
ANTI_THINK_SYS = "CRITICAL DIRECTIVE: DO NOT THINK OR OUTPUT ANY REASONING. START DIRECTLY WITH { AND OUTPUT ONLY RAW VALID JSON.\n\n"

NEW_PARSE_EVAL_RESPONSE_JOKES = """let rawResponse = $json.output || $json.text || $json.content || $json.response || $json;

let joke = {};
if (typeof rawResponse === 'string') {
  try {
    const cleanStr = rawResponse.replace(/```json/g, '').replace(/```/g, '').trim();
    joke = JSON.parse(cleanStr);
  } catch (e) {
    joke = {};
  }
} else if (typeof rawResponse === 'object' && rawResponse !== null) {
  joke = rawResponse.joke || (Array.isArray(rawResponse.jokes) ? rawResponse.jokes[0] : rawResponse);
}

// Recovery: If evaluator returned empty or invalid, pull first valid candidate from Agent
if (!joke || typeof joke !== 'object' || !joke.hook || joke.hook.toLowerCase().includes('no input')) {
  try {
    const agentNode = $('AI Dog Joke Agent').first().json;
    const agentOutput = agentNode.output || agentNode.text || agentNode.content || '';
    if (typeof agentOutput === 'string') {
      const cleanStr = agentOutput.replace(/```json/g, '').replace(/```/g, '').trim();
      const parsedAgent = JSON.parse(cleanStr);
      const candidates = parsedAgent.jokes || (Array.isArray(parsedAgent) ? parsedAgent : [parsedAgent]);
      if (Array.isArray(candidates) && candidates.length > 0 && candidates[0].hook) {
        joke = candidates[0];
      }
    }
  } catch (e) {}
}

const staticData = $getWorkflowStaticData('global');
if (!staticData.recentHistory) staticData.recentHistory = [];

// Diversified dog joke fallback pool (10 unique jokes, NO squirrel)
const fallbackPool = [
  { hook: "Treat jar opened", setup: "I heard it from outside", remate: "Fastest dog alive today", cta: "Follow for treats!" },
  { hook: "Mailman arrives again", setup: "Barking worked every time", remate: "He fled in fear", cta: "Defend your territory!" },
  { hook: "Vacuum woke up", setup: "The ancient roaring beast", remate: "Retreat under bed immediately", cta: "Share with pets!" },
  { hook: "Tennis ball lost", setup: "Rolled beneath the sofa", remate: "Mission impossible begins now", cta: "Help me find!" },
  { hook: "Fake ball throw", setup: "I saw your hand", remate: "Betrayal never forgotten human", cta: "Like if fooled!" },
  { hook: "Bath time announced", setup: "Suddenly I am deaf", remate: "Hiding in plain sight", cta: "Save all dogs!" },
  { hook: "Sofa cushion stolen", setup: "It belongs to me", remate: "Squatter rights applied here", cta: "Join our couch!" },
  { hook: "Doorbell fake sound", setup: "From television screen", remate: "Still barking just in case", cta: "Follow for chaos!" },
  { hook: "Car ride promise", setup: "Ended at the vet", remate: "The ultimate betrayal confirmed", cta: "Drop a comment!" },
  { hook: "Dinner late again", setup: "Starvation has clearly begun", remate: "Dramatic fainting on carpet", cta: "Feed your pup!" }
];

// Fallback if both agent and evaluator failed
if (!joke || typeof joke !== 'object' || !joke.hook || joke.hook.toLowerCase().includes('no input')) {
  const available = fallbackPool.filter(fb => {
    return !staticData.recentHistory.some(h => String(h).toLowerCase().includes(fb.hook.toLowerCase()));
  });
  const poolToUse = available.length > 0 ? available : fallbackPool;
  joke = poolToUse[Math.floor(Math.random() * poolToUse.length)];
}

if (!joke.cta || !joke.cta.trim()) { joke.cta = 'Share with floofs!'; }
const hook = joke.hook || '';
const setup = joke.setup || '';
const remate = joke.remate || '';
const cta = joke.cta || '';
const fullText = (hook + ' ' + setup + ' ' + remate + ' ' + cta).trim();

// Strictly enforce recording to recentHistory, with max length check to prevent corruption
if (fullText && fullText.length <= 120) {
  staticData.recentHistory.unshift(fullText);
  if (staticData.recentHistory.length > 10) {
    staticData.recentHistory = staticData.recentHistory.slice(0, 10);
  }
}

return [{ json: { joke: joke } }];"""

NEW_PARSE_EVAL_RESPONSE_CTA = """let rawResponse = $json.output || $json.text || $json.content || $json.response || $json;

let joke = {};
if (typeof rawResponse === 'string') {
  try {
    const cleanStr = rawResponse.replace(/```json/g, '').replace(/```/g, '').trim();
    joke = JSON.parse(cleanStr);
  } catch (e) {
    joke = {};
  }
} else if (typeof rawResponse === 'object' && rawResponse !== null) {
  joke = rawResponse.joke || (Array.isArray(rawResponse.jokes) ? rawResponse.jokes[0] : rawResponse);
}

function isForbidden(j) {
  if (!j || typeof j !== 'object') return true;
  const str = ((j.hook || '') + ' ' + (j.setup || '') + ' ' + (j.remate || '')).toLowerCase();
  return /\\b(mic|microphone|micrófono|audio mic)\\b/i.test(str);
}

// Recovery: If evaluator returned empty, invalid or forbidden mic, pull first clean candidate from Agent
if (!joke || typeof joke !== 'object' || !joke.hook || joke.hook.toLowerCase().includes('no input') || isForbidden(joke)) {
  try {
    const agentNode = $('AI Dog CTA Agent').first().json;
    const agentOutput = agentNode.output || agentNode.text || agentNode.content || '';
    if (typeof agentOutput === 'string') {
      const cleanStr = agentOutput.replace(/```json/g, '').replace(/```/g, '').trim();
      const parsedAgent = JSON.parse(cleanStr);
      const candidates = parsedAgent.jokes || (Array.isArray(parsedAgent) ? parsedAgent : [parsedAgent]);
      if (Array.isArray(candidates)) {
        for (const cand of candidates) {
          if (cand && cand.hook && !isForbidden(cand)) {
            joke = cand;
            break;
          }
        }
      }
    }
  } catch (e) {}
}

const staticData = $getWorkflowStaticData('global');
if (!staticData.recentHistory) staticData.recentHistory = [];

const ctaFallbackPool = [
  { hook: "Action cam test", setup: "Mounted on my harness", remate: "Pure canine perspective recorded", cta: "Link in bio!" },
  { hook: "Gear review today", setup: "Toughest leash ever tested", remate: "Survived five mud puddles", cta: "Check the link!" },
  { hook: "Harness check done", setup: "Super comfy daily fit", remate: "Ready for wild adventures", cta: "Link in bio!" },
  { hook: "My favorite toy", setup: "Indestructible rubber squeaker toy", remate: "Human finally found one", cta: "Get yours now!" },
  { hook: "GPS dog collar", setup: "Tracks my tactical zooms", remate: "Never get lost again", cta: "Link in bio!" }
];

// Default clean fallback
if (!joke || typeof joke !== 'object' || !joke.hook || joke.hook.toLowerCase().includes('no input') || isForbidden(joke)) {
  const available = ctaFallbackPool.filter(fb => {
    return !staticData.recentHistory.some(h => String(h).toLowerCase().includes(fb.hook.toLowerCase()));
  });
  const poolToUse = available.length > 0 ? available : ctaFallbackPool;
  joke = poolToUse[Math.floor(Math.random() * poolToUse.length)];
}

if (!joke.cta || !joke.cta.trim()) { joke.cta = 'Link in bio!'; }
const hook = joke.hook || '';
const setup = joke.setup || '';
const remate = joke.remate || '';
const cta = joke.cta || '';
const fullText = (hook + ' ' + setup + ' ' + remate + ' ' + cta).trim();

if (fullText && fullText.length <= 120) {
  staticData.recentHistory.unshift(fullText);
  if (staticData.recentHistory.length > 10) {
    staticData.recentHistory = staticData.recentHistory.slice(0, 10);
  }
}

return [{ json: { joke: joke } }];"""

NEW_PARSE_EVAL_RESPONSE_CTA1 = """let rawResponse = $json.output || $json.text || $json.content || $json.response || $json;

let joke = {};
if (typeof rawResponse === 'string') {
  try {
    const cleanStr = rawResponse.replace(/```json/g, '').replace(/```/g, '').trim();
    joke = JSON.parse(cleanStr);
  } catch (e) {
    joke = {};
  }
} else if (typeof rawResponse === 'object' && rawResponse !== null) {
  joke = rawResponse.joke || (Array.isArray(rawResponse.jokes) ? rawResponse.jokes[0] : rawResponse);
}

// Recovery: If evaluator returned empty or invalid, pull first valid candidate from Agent
if (!joke || typeof joke !== 'object' || !joke.hook || joke.hook.toLowerCase().includes('no input')) {
  try {
    const agentNode = $('AI Dog Comments percutor').first().json;
    const agentOutput = agentNode.output || agentNode.text || agentNode.content || '';
    if (typeof agentOutput === 'string') {
      const cleanStr = agentOutput.replace(/```json/g, '').replace(/```/g, '').trim();
      const parsedAgent = JSON.parse(cleanStr);
      const candidates = parsedAgent.jokes || (Array.isArray(parsedAgent) ? parsedAgent : [parsedAgent]);
      if (Array.isArray(candidates) && candidates.length > 0 && candidates[0].hook) {
        joke = candidates[0];
      }
    }
  } catch (e) {}
}

const staticData = $getWorkflowStaticData('global');
if (!staticData.recentHistory) staticData.recentHistory = [];

const commentsFallbackPool = [
  { hook: "What about yours?", setup: "Does your dog do this?", remate: "Tell me in comments", cta: "Comment below!" },
  { hook: "Be honest humans", setup: "Who actually rules household?", remate: "I already know answer", cta: "Drop your thoughts!" },
  { hook: "Your dog reaction?", setup: "When treat bag rustles?", remate: "Instant teleportation mode on", cta: "Share your stories!" },
  { hook: "Rate this chaos", setup: "Scale from one ten", remate: "I gave myself eleven", cta: "Vote down below!" },
  { hook: "Who is guiltier?", setup: "Me or the cat?", remate: "Evidence was totally planted", cta: "Comment your verdict!" }
];

// Modality-specific default fallback if both agent and evaluator failed
if (!joke || typeof joke !== 'object' || !joke.hook || joke.hook.toLowerCase().includes('no input')) {
  const available = commentsFallbackPool.filter(fb => {
    return !staticData.recentHistory.some(h => String(h).toLowerCase().includes(fb.hook.toLowerCase()));
  });
  const poolToUse = available.length > 0 ? available : commentsFallbackPool;
  joke = poolToUse[Math.floor(Math.random() * poolToUse.length)];
}

if (!joke.cta || !joke.cta.trim()) { joke.cta = 'Comment below!'; }
const hook = joke.hook || '';
const setup = joke.setup || '';
const remate = joke.remate || '';
const cta = joke.cta || '';
const fullText = (hook + ' ' + setup + ' ' + remate + ' ' + cta).trim();

if (fullText && fullText.length <= 120) {
  staticData.recentHistory.unshift(fullText);
  if (staticData.recentHistory.length > 10) {
    staticData.recentHistory = staticData.recentHistory.slice(0, 10);
  }
}

return [{ json: { joke: joke } }];"""

NEW_NOMBRE_JOKES = """const staticData = $getWorkflowStaticData('global');
let recentHistory = staticData.recentHistory || [];

// Filter out any corrupted, excessively long or monologue items
recentHistory = recentHistory.filter(h => typeof h === 'string' && h.length <= 120 && !h.toLowerCase().includes('sorry') && !h.toLowerCase().includes('wait no') && !h.toLowerCase().includes('thinking'));
staticData.recentHistory = recentHistory.slice(0, 5);

const newline = String.fromCharCode(10);
const historyText = staticData.recentHistory.length > 0
  ? 'FORBIDDEN PREVIOUS SCRIPTS (DO NOT REPEAT OR COPY ANY OF THESE):' + newline + '- ' + staticData.recentHistory.join(newline + '- ')
  : 'No previous scripts recorded yet.';

$input.all().forEach(item => {
  item.json.dogName = 'Draco';
  item.json.historyText = historyText;
  item.json.input = 'Write 5 original dog jokes in English.';
  item.json.chatInput = 'Write 5 original dog jokes in English.';
});
return $input.all();"""

NEW_NOMBRE_CTA = """const staticData = $getWorkflowStaticData('global');
let recentHistory = staticData.recentHistory || [];
recentHistory = recentHistory.filter(h => typeof h === 'string' && h.length <= 120 && !h.toLowerCase().includes('sorry') && !h.toLowerCase().includes('thinking'));
staticData.recentHistory = recentHistory.slice(0, 5);

const newline = String.fromCharCode(10);
const historyText = staticData.recentHistory.length > 0
  ? 'FORBIDDEN PREVIOUS SCRIPTS (DO NOT REPEAT OR COPY ANY OF THESE):' + newline + '- ' + staticData.recentHistory.join(newline + '- ')
  : 'No previous scripts recorded yet.';

$input.all().forEach(item => {
  item.json.dogName = 'Draco';
  item.json.historyText = historyText;
  item.json.input = 'Write 5 short dog-POV CTA scripts in English explicitly naming one of our 8 exact bio products: Camera that I use, Longboard 4x4, Lens protector, Selfie stick, Whistle balls Chuckit, Paws balsam, Non-stop Dogwear Touring Bungee, Non-stop Dogwear Line Harness. STRICT RULE: DO NOT mention any microphone or mic. We do not have a mic, only the camera with its built-in mic.';
  item.json.chatInput = 'Write 5 short dog-POV CTA scripts in English explicitly naming one of our 8 exact bio products: Camera that I use, Longboard 4x4, Lens protector, Selfie stick, Whistle balls Chuckit, Paws balsam, Non-stop Dogwear Touring Bungee, Non-stop Dogwear Line Harness. STRICT RULE: DO NOT mention any microphone or mic. We do not have a mic, only the camera with its built-in mic.';
});
return $input.all();"""

NEW_NOMBRE_COMMENTS = """const staticData = $getWorkflowStaticData('global');
let recentHistory = staticData.recentHistory || [];
recentHistory = recentHistory.filter(h => typeof h === 'string' && h.length <= 120 && !h.toLowerCase().includes('sorry') && !h.toLowerCase().includes('thinking'));
staticData.recentHistory = recentHistory.slice(0, 5);

const newline = String.fromCharCode(10);
const historyText = staticData.recentHistory.length > 0
  ? 'FORBIDDEN PREVIOUS SCRIPTS (DO NOT REPEAT OR COPY ANY OF THESE):' + newline + '- ' + staticData.recentHistory.join(newline + '- ')
  : 'No previous scripts recorded yet.';

$input.all().forEach(item => {
  item.json.dogName = 'Draco';
  item.json.historyText = historyText;
  item.json.input = 'Write 5 sarcastic dog-POV scripts in English asking viewers funny questions to comment about their own dogs.';
  item.json.chatInput = 'Write 5 sarcastic dog-POV scripts in English asking viewers funny questions to comment about their own dogs.';
});
return $input.all();"""

def update_workflow():
    wf_url = 'http://localhost:5678/api/v1/workflows/Gk7AsGpOPt9LeArk'
    req = urllib.request.Request(wf_url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        wf = json.loads(resp.read().decode('utf-8'))

    nodes = wf.get('nodes', [])
    for n in nodes:
        name = n.get('name')
        if name == 'Parse Evaluation Response':
            n['parameters']['jsCode'] = NEW_PARSE_EVAL_RESPONSE_JOKES
            print("Updated Parse Evaluation Response")
        elif name == 'Parse Evaluation Response CTA':
            n['parameters']['jsCode'] = NEW_PARSE_EVAL_RESPONSE_CTA
            print("Updated Parse Evaluation Response CTA")
        elif name == 'Parse Evaluation Response CTA1':
            n['parameters']['jsCode'] = NEW_PARSE_EVAL_RESPONSE_CTA1
            print("Updated Parse Evaluation Response CTA1")
        elif name == '🐶 NOMBRE (Jokes)':
            n['parameters']['jsCode'] = NEW_NOMBRE_JOKES
            print("Updated 🐶 NOMBRE (Jokes)")
        elif name == '🐶 NOMBRE (CTA)':
            n['parameters']['jsCode'] = NEW_NOMBRE_CTA
            print("Updated 🐶 NOMBRE (CTA)")
        elif name == '🐶 NOMBRE (Comments)':
            n['parameters']['jsCode'] = NEW_NOMBRE_COMMENTS
            print("Updated 🐶 NOMBRE (Comments)")
        elif name in ['AI Dog Joke Agent', 'AI Dog CTA Agent', 'AI Dog Comments percutor']:
            # Inject anti-thinking directive
            txt = n.get('parameters', {}).get('text', '')
            if 'CRITICAL DIRECTIVE' not in txt:
                if txt.startswith('='):
                    n['parameters']['text'] = '=\nCRITICAL DIRECTIVE: DO NOT THINK OR OUTPUT ANY REASONING. START DIRECTLY WITH { AND OUTPUT ONLY RAW JSON.\n\n' + txt[1:]
                else:
                    n['parameters']['text'] = ANTI_THINK_TEXT + txt
            sys_msg = n.get('parameters', {}).get('options', {}).get('systemMessage', '')
            if 'CRITICAL DIRECTIVE' not in sys_msg:
                if sys_msg.startswith('='):
                    n['parameters']['options']['systemMessage'] = '=\nCRITICAL DIRECTIVE: DO NOT THINK OR OUTPUT ANY REASONING. START DIRECTLY WITH { AND OUTPUT ONLY RAW VALID JSON.\n\n' + sys_msg[1:]
                else:
                    n['parameters']['options']['systemMessage'] = ANTI_THINK_SYS + sys_msg
            print(f"Updated {name}")
        elif name in ['AI Dog Joke Evaluator', 'AI Dog CTA Evaluator', 'AI Dog Comments percutor Evaluator1']:
            txt = n.get('parameters', {}).get('text', '')
            if 'CRITICAL DIRECTIVE' not in txt:
                if txt.startswith('='):
                    n['parameters']['text'] = '=\nCRITICAL DIRECTIVE: DO NOT THINK OR OUTPUT ANY REASONING. START DIRECTLY WITH { AND OUTPUT ONLY RAW JSON.\n\n' + txt[1:]
                else:
                    n['parameters']['text'] = ANTI_THINK_TEXT + txt
            sys_msg = n.get('parameters', {}).get('options', {}).get('systemMessage', '')
            if 'CRITICAL DIRECTIVE' not in sys_msg:
                if sys_msg.startswith('='):
                    n['parameters']['options']['systemMessage'] = '=\nCRITICAL DIRECTIVE: DO NOT THINK OR OUTPUT ANY REASONING. START DIRECTLY WITH { AND OUTPUT ONLY RAW VALID JSON.\n\n' + sys_msg[1:]
                else:
                    n['parameters']['options']['systemMessage'] = ANTI_THINK_SYS + sys_msg
            print(f"Updated {name}")

    # Clean staticData
    if 'staticData' in wf and 'global' in wf['staticData']:
        wf['staticData']['global']['recentHistory'] = [
            "Socks vanished. Innocent face deployed. Evidence under rug. Follow Draco!",
            "Doorbell rang. Full tactical alert. Just delivery guy. Like for bravery!",
            "Puddle jumped. Mud bath achieved. Human in tears. Share with dogs!",
            "Dinner delayed. Stared at clock. Dramatic sigh released. Comment below!",
            "Treat bag opened. Three rooms away. Immediate teleportation. Link in bio!"
        ]

    # Save via PUT
    put_data = {
        'name': wf['name'],
        'nodes': wf['nodes'],
        'connections': wf['connections'],
        'settings': {k: v for k, v in wf.get('settings', {}).items() if k != 'binaryMode'},
        'staticData': wf.get('staticData', {})
    }
    req_put = urllib.request.Request(wf_url, data=json.dumps(put_data).encode('utf-8'), headers=HEADERS, method='PUT')
    with urllib.request.urlopen(req_put) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("PUT workflow successful. Version:", res.get('versionId'))

    # Reactivate workflow to force n8n reload
    print("Reactivating workflow...")
    deact = urllib.request.Request(f'{wf_url}/deactivate', headers=HEADERS, method='POST')
    try:
        with urllib.request.urlopen(deact) as resp:
            print("Deactivated.")
    except Exception as e:
        print("Deactivation note:", e)

    act = urllib.request.Request(f'{wf_url}/activate', headers=HEADERS, method='POST')
    with urllib.request.urlopen(act) as resp:
        print("Reactivated successfully.")

if __name__ == '__main__':
    update_workflow()
