#!/usr/bin/env python3
"""
fix_ollama_metadata_nodes.py
Corrige los nodos de metadatos en n8n para asegurar que:
1. YT Preparar Input Ollama lea la descripción REAL generada por generate_youtube_metadata.py (con enlaces de afiliado y timestamps exactos).
2. YT Parsear Metadatos rechace cualquier alucinación de Ollama que contenga '[LINKS DE AFILIADO]' o '[Producto]' y restaure la descripción real.
3. YT Preparar Payload Upload verifique que la descripción final contenga los links de afiliado reales y timestamps.
"""

import urllib.request
import json

headers = {
    'X-N8N-API-KEY': 'YOUR_N8N_API_KEY_PLACEHOLDER',
    'Content-Type': 'application/json'
}

prep_input_code = """let projectDir = '';
try {
    projectDir = $('1b. Parsear Scraper').first().json.project_dir || $('0b. Parsear Temática').first().json.project_dir || '';
} catch (e1) {}

let containerDir = (projectDir || '').replace('/home/javierferb/ia-lab-files', '/files');
let fs = require('fs');
let metaFile = containerDir + '/youtube_metadata.json';

let realTitle = '';
let realDesc = '';

if (fs.existsSync(metaFile)) {
    try {
        let meta = JSON.parse(fs.readFileSync(metaFile, 'utf-8'));
        realTitle = meta.youtube_title || meta.title || '';
        realDesc = meta.youtube_description || meta.description || '';
    } catch(e2) {}
}

if (!realDesc) {
    let txtFile = containerDir + '/youtube_metadata.txt';
    if (fs.existsSync(txtFile)) {
        try {
            realDesc = fs.readFileSync(txtFile, 'utf-8');
        } catch(e3) {}
    }
}

let q = '';
try {
    q = $('0b. Parsear Temática').first().json.search_query || $('1b. Parsear Scraper').first().json.query || '';
} catch (e4) {}

let prods = [];
let dataJsonPath = containerDir + '/data.json';
if (fs.existsSync(dataJsonPath)) {
    try {
        let dataObj = JSON.parse(fs.readFileSync(dataJsonPath, 'utf-8'));
        prods = dataObj.products || [];
        if (!q) q = dataObj.query || '';
    } catch(e5) {}
}

let channelNiche = '';
let channelName = '';
try {
    channelName = $('Configuración Parámetros').first().json.channel_name || '';
    channelNiche = $('Configuración Parámetros').first().json.channel_niche || '';
} catch(e6) {}

if (!q) q = channelNiche || 'PRODUCTOS DESTACADOS';

let productNames = prods.map(p => p.title || '').filter(t => t.length > 0);
let productPrices = prods.map(p => p.price || '').filter(t => t.length > 0);

return [{
    json: {
        query: q,
        current_title: realTitle || ('TOP MEJORES ' + q.toUpperCase() + ' EN AMAZON 2026 🏆'),
        current_description: realDesc,
        products: prods,
        product_names: productNames,
        product_prices: productPrices,
        channel_name: channelName,
        channel_niche: channelNiche,
        project_dir: projectDir
    }
}];"""

parse_meta_code = """function parseAiJson(val) {
    if (!val) return {};
    if (typeof val === 'object') return val;
    let s = String(val).trim();
    s = s.replace(/^```(?:json)?\\s*/i, '').replace(/\\s*```$/g, '').trim();
    try {
        return JSON.parse(s);
    } catch (e) {
        let match = s.match(/(\\{[\\s\\S]*\\})/);
        if (match) {
            try { return JSON.parse(match[1]); } catch (e2) {}
        }
    }
    return {};
}

let stdoutStr = $json.stdout || '';
let parsedMeta = parseAiJson(stdoutStr);

if (parsedMeta.output) {
    let inner = parseAiJson(parsedMeta.output);
    if (inner && typeof inner === 'object') {
        parsedMeta = Object.assign({}, parsedMeta, inner);
    }
}

let prepInput = {};
try {
    prepInput = $('YT Preparar Input Ollama').item.json;
} catch(e1) {}

let title = parsedMeta.title || parsedMeta.youtube_title || prepInput.current_title || 'TOP MEJORES PRODUCTOS DE AMAZON 2026';
title = title.replace(/_/g, ' ').replace(/\\s+/g, ' ').trim();

let description = parsedMeta.description || parsedMeta.youtube_description || prepInput.current_description || '';

// Si Ollama alucinó texto marcador como [LINKS DE AFILIADO] o [Producto], restaurar la descripción real estructurada
if (description.includes('[LINKS DE AFILIADO]') || description.includes('[Producto]') || !description.includes('http')) {
    if (prepInput.current_description && prepInput.current_description.includes('http')) {
        description = prepInput.current_description;
    }
}

description = description.replace(/_/g, ' ').trim();

return [{
    json: {
        title: title,
        description: description,
        project_dir: prepInput.project_dir || $('0b. Parsear Temática').first().json.project_dir
    }
}];"""

prep_payload_code = """let projectDir = '';
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

// 1. Intentar desde nodo 'YT Parsear Metadatos'
try {
    let parsedNode = $('YT Parsear Metadatos').first().json;
    if (parsedNode.title) title = parsedNode.title;
    if (parsedNode.description) description = parsedNode.description;
} catch(eNode) {}

// 2. Intentar desde nodo 'YT Preparar Input Ollama'
if (!title || !description || description.includes('[LINKS DE AFILIADO]') || description.includes('[Producto]')) {
    try {
        let ollamaInput = $('YT Preparar Input Ollama').first().json;
        if (!title && ollamaInput.current_title) title = ollamaInput.current_title;
        if (ollamaInput.current_description && ollamaInput.current_description.includes('http')) {
            description = ollamaInput.current_description;
        }
    } catch(eOllama) {}
}

// 3. Intentar desde youtube_metadata.json en disco
let metaFile = containerDir + '/youtube_metadata.json';
if ((!title || !description || description.includes('[LINKS DE AFILIADO]') || description.includes('[Producto]') || !tags_str) && fs.existsSync(metaFile)) {
    try {
        let meta = JSON.parse(fs.readFileSync(metaFile, 'utf-8'));
        if (!title) title = meta.youtube_title || meta.title || '';
        if (meta.youtube_description && meta.youtube_description.includes('http')) {
            description = meta.youtube_description;
        }
        if (!tags_str) tags_str = meta.tags_str || (meta.tags ? meta.tags.join(',') : '');
    } catch(eFile) {}
}

// 4. Intentar desde youtube_metadata.txt en disco si la descripción sigue sin ser válida
let txtFile = containerDir + '/youtube_metadata.txt';
if ((!description || description.includes('[LINKS DE AFILIADO]') || description.includes('[Producto]') || !description.includes('http')) && fs.existsSync(txtFile)) {
    try {
        let txtContent = fs.readFileSync(txtFile, 'utf-8');
        if (txtContent.includes('DESCRIPCIÓN DE YOUTUBE')) {
            description = txtContent.split('DESCRIPCIÓN DE YOUTUBE')[1].replace(/═+/g, '').trim();
        } else if (txtContent.includes('DESCRIPCIÓN:')) {
            description = txtContent.split('DESCRIPCIÓN:')[1].trim();
        } else {
            description = txtContent.trim();
        }
    } catch(eTxt) {}
}

// 5. Fallback tags_str desde nodo de etiquetas o input
if (!tags_str) {
    try {
        let tagsNode = $('YT Generador de Tags SEO').first().json;
        if (tagsNode.stdout) {
            let tObj = JSON.parse(tagsNode.stdout);
            tags_str = tObj.tags_str || '';
        }
    } catch(eT) {}
}

// 6. Generación de título de respaldo
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

workflows_to_update = ['WfAmazonRank001', 'jYb2Pd8Jv2qOQqm5', 'mgV05WYtjtGHbS9u', 'MxntmV6OMInrwhBc', 'tV9dc1F8tlxxjMUI', 'WU9Q9SxUdvR5kltl', 'TY375mNkv5eejIQi', 'MRJe3wXfPBSxXnvM']

for wfid in workflows_to_update:
    url = f'http://localhost:5678/api/v1/workflows/{wfid}'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            wf = json.loads(resp.read().decode('utf-8'))
        
        updated = False
        for node in wf['nodes']:
            if node['name'] == 'YT Preparar Input Ollama':
                node['parameters']['jsCode'] = prep_input_code
                updated = True
            elif node['name'] == 'YT Parsear Metadatos':
                node['parameters']['jsCode'] = parse_meta_code
                updated = True
            elif node['name'] == 'YT Preparar Payload Upload':
                node['parameters']['jsCode'] = prep_payload_code
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
                print(f'Workflow {wfid} ({wf.get("name")}) updated successfully.')
    except Exception as e:
        print(f'Error updating {wfid}: {e}')
