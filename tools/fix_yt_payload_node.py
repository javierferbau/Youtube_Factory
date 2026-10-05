#!/usr/bin/env python3
import urllib.request
import json

headers = {
    'X-N8N-API-KEY': 'YOUR_N8N_API_KEY_PLACEHOLDER',
    'Content-Type': 'application/json'
}

js_code = """let projectDir = '';
try {
    projectDir = $('1b. Parsear Scraper').first().json.project_dir;
} catch (e1) {}

if (!projectDir) {
    try {
        projectDir = $('0b. Parsear Temática').first().json.project_dir;
    } catch (e2) {}
}

if (!projectDir) {
    try {
        projectDir = $input.first().json.project_dir;
    } catch (e3) {}
}

let containerDir = (projectDir || '').replace('/home/javierferb/ia-lab-files', '/files');
let fs = require('fs');

let title = '';
let description = '';
let tags_str = '';

// 1. Try reading from upstream node 'YT Parsear Metadatos'
try {
    let parsedNode = $('YT Parsear Metadatos').first().json;
    if (parsedNode.title) title = parsedNode.title;
    if (parsedNode.description) description = parsedNode.description;
} catch(eNode) {}

// 2. Try reading from node 'YT Preparar Input Ollama'
if (!title || !description) {
    try {
        let ollamaInput = $('YT Preparar Input Ollama').first().json;
        if (!title && ollamaInput.current_title) title = ollamaInput.current_title;
        if (!description && ollamaInput.current_description) description = ollamaInput.current_description;
    } catch(eOllama) {}
}

// 3. Try reading youtube_metadata.json from disk
let metaFile = containerDir + '/youtube_metadata.json';
if ((!title || !description || !tags_str) && fs.existsSync(metaFile)) {
    try {
        let meta = JSON.parse(fs.readFileSync(metaFile, 'utf-8'));
        if (!title) title = meta.youtube_title || meta.title || '';
        if (!description) description = meta.youtube_description || meta.description || '';
        if (!tags_str) tags_str = meta.tags_str || (meta.tags ? meta.tags.join(',') : '');
    } catch(eFile) {}
}

// 4. Try reading youtube_metadata.txt from disk if description is still missing
let txtFile = containerDir + '/youtube_metadata.txt';
if (!description && fs.existsSync(txtFile)) {
    try {
        let txtContent = fs.readFileSync(txtFile, 'utf-8');
        if (txtContent.includes('DESCRIPCIÓN DE YOUTUBE')) {
            description = txtContent.split('DESCRIPCIÓN DE YOUTUBE')[1].replace(/═+/g, '').trim();
        } else {
            description = txtContent.trim();
        }
    } catch(eTxt) {}
}

// 5. Fallback tags_str from node 'YT Generador de Tags SEO' or input
if (!tags_str) {
    try {
        let tagsNode = $('YT Generador de Tags SEO').first().json;
        if (tagsNode.stdout) {
            let tObj = JSON.parse(tagsNode.stdout);
            tags_str = tObj.tags_str || '';
        }
    } catch(eT) {}
}

// 6. Fallback title generation if still empty or invalid
if (!title || title.endsWith('...') || title.length < 15 || title.includes('_')) {
    try {
        let scraper = $('1b. Parsear Scraper').first().json || {};
        let productA = scraper.product_a || {};
        let productB = scraper.product_b || {};
        let brandA = (productA.brand || '').toUpperCase().trim();
        let brandB = (productB.brand || '').toUpperCase().trim();
        let q = (scraper.query || (scraper.search_query || '')).replace(/_/g, ' ').trim();
        if (brandA && brandB && brandA !== brandB) {
            title = brandA + ' vs ' + brandB + (q ? ' | ' + q.charAt(0).toUpperCase() + q.slice(1) : '') + ' ¿Cuál Elegir?';
        } else if (q) {
            title = 'TOP COMPARATIVA | ' + q.charAt(0).toUpperCase() + q.slice(1) + ' 2026 ⚔️';
        }
    } catch(e5) {}
}
if (!title || title.length < 10) {
    title = 'Comparativa de Productos 2026 ⚔️';
}

title = title.replace(/_/g, ' ').replace(/\\s+/g, ' ').trim();
if (title.length > 95) {
    title = title.substring(0, 92).trim();
}

if (description) {
    description = description.replace(/_/g, ' ').trim();
}

const items = $input.all();
const outItems = [];
for (let item of items) {
    let newItem = {
        json: {
            ...item.json,
            title: title,
            description: description,
            tags_str: tags_str
        }
    };
    if (item.binary) newItem.binary = item.binary;
    outItems.push(newItem);
}
return outItems;"""

for wfid in ['WfAmazonRank001', 'jYb2Pd8Jv2qOQqm5']:
    url = f'http://localhost:5678/api/v1/workflows/{wfid}'
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        wf = json.loads(resp.read().decode('utf-8'))
    
    updated = False
    for node in wf['nodes']:
        if node['name'] == 'YT Preparar Payload Upload':
            node['parameters']['jsCode'] = js_code
            updated = True
    
    if updated:
        allowed = {'executionOrder', 'timezone', 'saveDataErrorExecution', 'saveDataSuccessExecution', 'saveExecutionProgress', 'callerPolicy'}
        clean_settings = {k: v for k, v in wf.get('settings', {}).items() if k in allowed}
        payload = {
            'name': wf['name'],
            'nodes': wf['nodes'],
            'connections': wf['connections'],
            'settings': clean_settings
        }
        put_req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='PUT')
        with urllib.request.urlopen(put_req) as p_resp:
            print(f'Workflow {wfid} updated successfully.')
