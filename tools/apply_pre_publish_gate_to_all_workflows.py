#!/usr/bin/env python3
"""
apply_pre_publish_gate_to_all_workflows.py
Inyecta el Pre-Publish Sanity Gate en los 12 workflows de producción de afiliados de n8n:
- En 'YT Preparar Payload Upload' (Horizontal)
- En 'Short 7. Preparar Payload Short Upload' (Short)

Si detecta inconsistencias semánticas por nicho o ausencia del archivo de vídeo,
lanza una excepción en el Code node, impidiendo la subida errónea a YouTube.
"""

import sys
import json
import urllib.request
import urllib.error

N8N_URL = "http://localhost:5678/api/v1"
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

AFFILIATE_WORKFLOWS = [
    ("WfAmazonRank001", "Cocina TOP", "cocina"),
    ("jYb2Pd8Jv2qOQqm5", "Cocina VS", "cocina"),
    ("MRJe3wXfPBSxXnvM", "Limpieza TOP", "limpieza"),
    ("mgV05WYtjtGHbS9u", "Limpieza VS", "limpieza"),
    ("tV9dc1F8tlxxjMUI", "Librería TOP", "libreria"),
    ("MxntmV6OMInrwhBc", "Librería VS", "libreria"),
    ("WU9Q9SxUdvR5kltl", "Zapatería TOP", "zapateria"),
    ("TY375mNkv5eejIQi", "Zapatería VS", "zapateria"),
    ("npnTZS8LUXJ4MsHf", "Barbería TOP", "barberia"),
    ("xOKGFm4CUSnDj77n", "Barbería VS", "barberia"),
    ("h2pK2nvTEu9z4757", "Taller TOP", "taller"),
    ("a0aGJENiz1HIEN9M", "Taller VS", "taller"),
]

GATE_SNIPPET_HORIZ = """
// ============================================================================
// 🛡️ PRE-PUBLISH SANITY GATE (COMPROBACIÓN PREVENTIVA DE PUBLICACIÓN HORIZONTAL)
// ============================================================================
if (containerDir && fs.existsSync(containerDir)) {
    let gateErrors = [];
    const NICHE_BANNED = {
        'taller': ['barbacoa', 'parrilla', 'bbq', 'pelo', 'cabello', 'afeitad', 'afeitadora', 'cortapelo', 'depilad', 'barba', 'dientes', 'dental', 'cocina', 'vajilla', 'sarten', 'sartén', 'olla', 'aspirador', 'colchon', 'mascota', 'fregadero', 'inodoro', 'champú'],
        'barberia': ['madera', 'taller', 'taladro', 'sierra', 'bricolaje', 'jardin', 'cesped', 'cocina', 'sarten', 'freidora', 'aspirador', 'fregona', 'limpieza', 'coche'],
        'cocina': ['taladro', 'sierra', 'amoladora', 'taller', 'pelo', 'afeitad', 'zapato', 'zapatilla', 'aspiradora', 'fregona', 'soldador'],
        'limpieza': ['sarten', 'sartén', 'olla', 'cocina', 'taladro', 'sierra', 'zapato', 'zapatilla', 'libro', 'novela', 'barberia', 'afeitadora'],
        'zapateria': ['aspiradora', 'freidora', 'sartén', 'taladro', 'sierra', 'libro', 'novela', 'afeitadora'],
        'libreria': ['aspiradora', 'freidora', 'taladro', 'zapato', 'afeitadora', 'sarten', 'bateria de cocina']
    };

    let dirLow = containerDir.toLowerCase();
    let niche = 'general';
    if (dirLow.includes('taller') || dirLow.includes('bricolaje')) niche = 'taller';
    else if (dirLow.includes('barber') || dirLow.includes('afeitad')) niche = 'barberia';
    else if (dirLow.includes('cocina')) niche = 'cocina';
    else if (dirLow.includes('limpiez')) niche = 'limpieza';
    else if (dirLow.includes('zapat') || dirLow.includes('calzad')) niche = 'zapateria';
    else if (dirLow.includes('librer') || dirLow.includes('libro')) niche = 'libreria';

    let bannedList = NICHE_BANNED[niche] || [];

    // 1. Validación Semántica de Productos desde data.json
    let dataJsonPath = containerDir + '/data.json';
    if (fs.existsSync(dataJsonPath)) {
        try {
            let dRaw = JSON.parse(fs.readFileSync(dataJsonPath, 'utf8'));
            let qLow = (dRaw.query || '').toLowerCase();
            let prods = dRaw.products || [];
            if (!prods.length && dRaw.product_a && dRaw.product_b) {
                prods = [dRaw.product_a, dRaw.product_b];
            }
            for (let idx = 0; idx < prods.length; idx++) {
                let pTitle = (prods[idx].title || '').toLowerCase();
                for (let b of bannedList) {
                    let re = new RegExp('\\\\b' + b + '\\\\b', 'i');
                    if (re.test(pTitle) && !qLow.includes(b)) {
                        gateErrors.push(`[HORIZONTAL] Producto #${idx + 1} ajeno al nicho ${niche}: término prohibido '${b}' en '${prods[idx].title.substring(0, 45)}...'`);
                    }
                }
            }
        } catch (eData) {
            gateErrors.push(`Error analizando data.json: ${eData.message}`);
        }
    } else {
        gateErrors.push('data.json no existe en el directorio del proyecto.');
    }

    // 2. Validación de Vídeo Horizontal Renderizado
    let horizFiles = ['/RENDER_FINAL_AMAZON.mp4', '/RENDER_FINAL_NAS.mp4'];
    let videoFound = false;
    for (let hf of horizFiles) {
        let vPath = containerDir + hf;
        if (fs.existsSync(vPath)) {
            let stat = fs.statSync(vPath);
            if (stat.size > 1000000) {
                videoFound = true;
                break;
            }
        }
    }
    if (!videoFound) {
        gateErrors.push('[HORIZONTAL] Vídeo renderizado horizontal ausente o corrupto (< 1MB).');
    }

    // 3. Validación de Miniatura (solo si ya existe en disco)
    let thumbPath = containerDir + '/thumbnail.jpg';
    if (fs.existsSync(thumbPath)) {
        let tStat = fs.statSync(thumbPath);
        if (tStat.size < 30000) {
            gateErrors.push(`[MINIATURA] thumbnail.jpg demasiado ligera (${tStat.size} bytes).`);
        }
    }

    if (gateErrors.length > 0) {
        throw new Error('[PRE-PUBLISH GATE BLOQUEADO - HORIZONTAL] ' + gateErrors.join(' | '));
    }
}
"""

GATE_SNIPPET_SHORT_HEAD = """let projectDir = '';
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

// ============================================================================
// 🛡️ PRE-PUBLISH SANITY GATE (COMPROBACIÓN PREVENTIVA DE PUBLICACIÓN SHORT)
// ============================================================================
if (containerDir && fs.existsSync(containerDir)) {
    let gateErrors = [];
    const NICHE_BANNED = {
        'taller': ['barbacoa', 'parrilla', 'bbq', 'pelo', 'cabello', 'afeitad', 'afeitadora', 'cortapelo', 'depilad', 'barba', 'dientes', 'dental', 'cocina', 'vajilla', 'sarten', 'sartén', 'olla', 'aspirador', 'colchon', 'mascota', 'fregadero', 'inodoro', 'champú'],
        'barberia': ['madera', 'taller', 'taladro', 'sierra', 'bricolaje', 'jardin', 'cesped', 'cocina', 'sarten', 'freidora', 'aspirador', 'fregona', 'limpieza', 'coche'],
        'cocina': ['taladro', 'sierra', 'amoladora', 'taller', 'pelo', 'afeitad', 'zapato', 'zapatilla', 'aspiradora', 'fregona', 'soldador'],
        'limpieza': ['sarten', 'sartén', 'olla', 'cocina', 'taladro', 'sierra', 'zapato', 'zapatilla', 'libro', 'novela', 'barberia', 'afeitadora'],
        'zapateria': ['aspiradora', 'freidora', 'sartén', 'taladro', 'sierra', 'libro', 'novela', 'afeitadora'],
        'libreria': ['aspiradora', 'freidora', 'taladro', 'zapato', 'afeitadora', 'sarten', 'bateria de cocina']
    };

    let dirLow = containerDir.toLowerCase();
    let niche = 'general';
    if (dirLow.includes('taller') || dirLow.includes('bricolaje')) niche = 'taller';
    else if (dirLow.includes('barber') || dirLow.includes('afeitad')) niche = 'barberia';
    else if (dirLow.includes('cocina')) niche = 'cocina';
    else if (dirLow.includes('limpiez')) niche = 'limpieza';
    else if (dirLow.includes('zapat') || dirLow.includes('calzad')) niche = 'zapateria';
    else if (dirLow.includes('librer') || dirLow.includes('libro')) niche = 'libreria';

    let bannedList = NICHE_BANNED[niche] || [];

    // 1. Validación de Guion del Short (short_script.json)
    let sScriptPath = containerDir + '/short_script.json';
    let qLow = '';
    if (fs.existsSync(sScriptPath)) {
        try {
            let sData = JSON.parse(fs.readFileSync(sScriptPath, 'utf8'));
            qLow = (sData.query || '').toLowerCase();
            let sText = ((sData.hook || '') + ' ' + (sData.product || '') + ' ' + qLow).toLowerCase();
            for (let b of bannedList) {
                let re = new RegExp('\\\\b' + b + '\\\\b', 'i');
                if (re.test(sText) && !qLow.includes(b)) {
                    gateErrors.push(`[SHORT] Guion del Short contiene término ajeno al nicho ${niche}: '${b}'`);
                }
            }
        } catch (eS) {
            gateErrors.push(`Error analizando short_script.json: ${eS.message}`);
        }
    }

    // 2. Validación de Productos en data.json (producto que nutre el Short)
    let dataJsonPath = containerDir + '/data.json';
    if (fs.existsSync(dataJsonPath)) {
        try {
            let dRaw = JSON.parse(fs.readFileSync(dataJsonPath, 'utf8'));
            if (!qLow) qLow = (dRaw.query || '').toLowerCase();
            let topProd = null;
            if (dRaw.products && dRaw.products.length > 0) topProd = dRaw.products[0];
            else if (dRaw.product_a) topProd = dRaw.product_a;

            if (topProd) {
                let pTitle = (topProd.title || '').toLowerCase();
                for (let b of bannedList) {
                    let re = new RegExp('\\\\b' + b + '\\\\b', 'i');
                    if (re.test(pTitle) && !qLow.includes(b)) {
                        gateErrors.push(`[SHORT] Producto Top usado en Short ajeno al nicho ${niche}: '${b}' en '${(topProd.title || '').substring(0, 45)}...'`);
                    }
                }
            }
        } catch (eD) {}
    }

    // 3. Validación de Vídeo Short Renderizado
    let shortFiles = ['/RENDER_FINAL_SHORT_VERTICAL.mp4', '/short_video.mp4'];
    let shortFound = false;
    for (let sf of shortFiles) {
        let vPath = containerDir + sf;
        if (fs.existsSync(vPath)) {
            let stat = fs.statSync(vPath);
            if (stat.size > 500000) {
                shortFound = true;
                break;
            }
        }
    }
    if (!shortFound) {
        gateErrors.push('[SHORT] Vídeo vertical renderizado ausente o corrupto (< 500KB).');
    }

    if (gateErrors.length > 0) {
        throw new Error('[PRE-PUBLISH GATE BLOQUEADO - SHORT] ' + gateErrors.join(' | '));
    }
}
"""

def update_node_code(nodes, node_name, modify_fn):
    for node in nodes:
        if node.get("name") == node_name:
            cur_code = node.get("parameters", {}).get("jsCode", "")
            new_code = modify_fn(cur_code)
            node["parameters"]["jsCode"] = new_code
            return True
    return False

def inject_horiz_gate(code):
    marker = "// 🛡️ PRE-PUBLISH SANITY GATE (COMPROBACIÓN PREVENTIVA DE PUBLICACIÓN HORIZONTAL)"
    if marker in code:
        parts = code.split(marker)
        pre = parts[0].rsplit("// ============================================================================", 1)[0]
        # Buscar el cierre del gate
        end_marker = "throw new Error('[PRE-PUBLISH GATE BLOQUEADO - HORIZONTAL] ' + gateErrors.join(' | '));\n    }\n}"
        if end_marker in parts[1]:
            post = parts[1].split(end_marker, 1)[1]
            return pre.strip() + "\n" + GATE_SNIPPET_HORIZ.strip() + "\n" + post.strip()
    
    target = "let fs = require('fs');"
    if target in code:
        idx = code.find(target) + len(target)
        return code[:idx] + "\n\n" + GATE_SNIPPET_HORIZ.strip() + "\n\n" + code[idx:].lstrip()
    else:
        return GATE_SNIPPET_HORIZ.strip() + "\n\n" + code

def inject_short_gate(code):
    marker = "// 🛡️ PRE-PUBLISH SANITY GATE (COMPROBACIÓN PREVENTIVA DE PUBLICACIÓN SHORT)"
    if marker in code:
        parts = code.split(marker)
        end_marker = "throw new Error('[PRE-PUBLISH GATE BLOQUEADO - SHORT] ' + gateErrors.join(' | '));\n    }\n}"
        if end_marker in parts[1]:
            post = parts[1].split(end_marker, 1)[1]
            return GATE_SNIPPET_SHORT_HEAD.strip() + "\n\n" + post.strip()
    
    return GATE_SNIPPET_SHORT_HEAD.strip() + "\n\n" + code.strip()

def process_workflow(wfid, wfname, apply_changes=True):
    headers = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}
    url = f"{N8N_URL}/workflows/{wfid}"
    
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"❌ Error obteniendo workflow {wfid} ({wfname}): {e}")
        return False

    nodes = data.get("nodes", [])
    
    h_ok = update_node_code(nodes, "YT Preparar Payload Upload", inject_horiz_gate)
    s_ok = update_node_code(nodes, "Short 7. Preparar Payload Short Upload", inject_short_gate)

    if not apply_changes:
        print(f"ℹ️ [DRY RUN] {wfname} ({wfid}): Horiz={h_ok}, Short={s_ok}")
        return True

    raw_settings = data.get("settings", {})
    allowed_keys = {'executionOrder', 'timezone', 'saveDataErrorExecution', 'saveDataSuccessExecution', 'saveExecutionProgress', 'callerPolicy'}
    clean_settings = {k: v for k, v in raw_settings.items() if k in allowed_keys}
    payload = {
        "name": data.get("name"),
        "nodes": nodes,
        "connections": data.get("connections"),
        "settings": clean_settings
    }

    body = json.dumps(payload).encode("utf-8")
    put_req = urllib.request.Request(url, data=body, headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(put_req) as resp:
            print(f"✅ {wfname:20} ({wfid}) -> Pre-Publish Sanity Gate ACTUALIZADO con éxito.")
            return True
    except urllib.error.HTTPError as e:
        print(f"❌ Error actualizando workflow {wfid} ({wfname}): {e.code} - {e.read().decode('utf-8')}")
        return False

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    print(f"=== ACTUALIZANDO PRE-PUBLISH SANITY GATE EN 12 WORKFLOWS (Dry-run: {dry_run}) ===")
    success_count = 0
    for wfid, wfname, niche in AFFILIATE_WORKFLOWS:
        if process_workflow(wfid, wfname, apply_changes=(not dry_run)):
            success_count += 1
    print(f"\nResultado final: {success_count}/{len(AFFILIATE_WORKFLOWS)} workflows actualizados.")
