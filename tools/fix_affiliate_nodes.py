#!/usr/bin/env python3
import tempfile
import os
import json
from n8n_helper import _request, update_workflow

VS_NODE_4_CMD = r'''=p_dir="{{ $('1b. Parsear Scraper').first().json.project_dir || $('0b. Parsear Temática').first().json.project_dir }}"
aff_tag="{{ $('Configuración Parámetros').first().json.affiliate_tag }}"
cat << 'EOF' | /home/javierferb/n8n/venv/bin/python3 /home/javierferb/n8n/tools/save_vs_script.py "$p_dir" --affiliate_tag "$aff_tag"
{{ JSON.stringify($json) }}
EOF'''

SAFE_CHAT_ID = r"={{ $('Configuración Parámetros1').first().json.telegram_chat_id }}"

# VS workflows
for wfid, name in [('jYb2Pd8Jv2qOQqm5', 'Cocina VS'), ('TY375mNkv5eejIQi', 'Zapatería VS'), ('mgV05WYtjtGHbS9u', 'Limpieza VS')]:
    wf = _request(f'/workflows/{wfid}')
    mod = False
    for n in wf.get('nodes', []):
        if n.get('name') == '4. Guardar Guion JSON':
            n['parameters']['command'] = VS_NODE_4_CMD
            mod = True
    if mod:
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as tf:
            json.dump(wf, tf)
            tmp = tf.name
        update_workflow(wfid, tmp)
        os.remove(tmp)
        print(f'Corrected node 4 in {name} ({wfid})')

# Top workflows error notification
for wfid, name in [('WU9Q9SxUdvR5kltl', 'Zapatería Top'), ('WfAmazonRank001', 'Cocina Top'), ('MRJe3wXfPBSxXnvM', 'Limpieza Top'), ('tV9dc1F8tlxxjMUI', 'Librería Top')]:
    wf = _request(f'/workflows/{wfid}')
    mod = False
    for n in wf.get('nodes', []):
        if n.get('name') == 'Notificar Telegram Éxito1':
            n['parameters']['chatId'] = SAFE_CHAT_ID
            mod = True
    if mod:
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as tf:
            json.dump(wf, tf)
            tmp = tf.name
        update_workflow(wfid, tmp)
        os.remove(tmp)
        print(f'Corrected error notifier chatId in {name} ({wfid})')

