#!/usr/bin/env python3
import json
import os
import sys
import tempfile
from n8n_helper import _request, update_workflow

WORKFLOWS = [
    ("Cocina Top", "WfAmazonRank001"),
    ("Cocina VS", "jYb2Pd8Jv2qOQqm5"),
    ("Limpieza Top", "MRJe3wXfPBSxXnvM"),
    ("Limpieza VS", "mgV05WYtjtGHbS9u"),
    ("Librería Top", "tV9dc1F8tlxxjMUI"),
    ("Librería VS", "MxntmV6OMInrwhBc"),
    ("Zapatería Top", "WU9Q9SxUdvR5kltl"),
    ("Zapatería VS", "TY375mNkv5eejIQi")
]

def patch_workflow_sales(label, wfid):
    wf = _request(f"/workflows/{wfid}")
    if not wf:
        print(f"[{label}] Error: No se pudo obtener workflow {wfid}")
        return False

    nodes = {n.get("name"): n for n in wf.get("nodes", [])}
    conns = wf.get("connections", {})

    # 1. Patch YT Preparar Payload Upload to read and propagate pinned_comment
    payload_node = nodes.get("YT Preparar Payload Upload")
    if payload_node:
        js = payload_node.get("parameters", {}).get("jsCode", "")
        if "pinned_comment = meta.pinned_comment" not in js:
            js = js.replace("let tags_str = '';", "let tags_str = '';\nlet pinned_comment = '';")
            js = js.replace("if (!tags_str) tags_str = meta.tags_str || (meta.tags ? meta.tags.join(',') : '');",
                            "if (!tags_str) tags_str = meta.tags_str || (meta.tags ? meta.tags.join(',') : '');\n        if (meta.pinned_comment) pinned_comment = meta.pinned_comment;")
        if "pinned_comment: pinned_comment" not in js:
            js = js.replace("tags_str: tags_str", "tags_str: tags_str,\n            pinned_comment: pinned_comment")
        payload_node["parameters"]["jsCode"] = js
        print(f"  [{label}] Actualizado YT Preparar Payload Upload con pinned_comment")

    # 2. Patch Short 5. Parsear Metadatos Short
    short5_node = nodes.get("Short 5. Parsear Metadatos Short")
    if short5_node:
        s5_js = short5_node.get("parameters", {}).get("jsCode", "")
        if "pinned_comment" not in s5_js:
            s5_js = s5_js.replace("tags_str: (data.tags || ['Shorts', 'amazon']).join(','),",
                                  "tags_str: (data.tags || ['Shorts', 'amazon']).join(','),\n        pinned_comment: data.pinned_comment || '',")
            short5_node["parameters"]["jsCode"] = s5_js
            print(f"  [{label}] Actualizado Short 5 con pinned_comment")

    # 3. Patch Short 7. Preparar Payload Short Upload
    short_payload_node = nodes.get("Short 7. Preparar Payload Short Upload")
    if short_payload_node:
        s_js = short_payload_node.get("parameters", {}).get("jsCode", "")
        if "pinned_comment" not in s_js:
            s_js = s_js.replace("tags_str: meta.tags_str || 'Shorts,amazon'",
                                "tags_str: meta.tags_str || 'Shorts,amazon',\n            pinned_comment: meta.pinned_comment || ''")
            s_js = s_js.replace("tags_str: meta.tags_str || 'Shorts,comparativa,amazon,vs'",
                                "tags_str: meta.tags_str || 'Shorts,comparativa,amazon,vs',\n            pinned_comment: meta.pinned_comment || ''")
            short_payload_node["parameters"]["jsCode"] = s_js
            print(f"  [{label}] Actualizado Short 7 con pinned_comment")

    # Get YouTube OAuth credential from YT Upload YouTube
    yt_upload_node = nodes.get("YT Upload YouTube")
    yt_creds = yt_upload_node.get("credentials") if yt_upload_node else {}

    # 4. Patch / Add YT Publicar Comentario Fijado node (Long video)
    pinned_node_name = "YT Publicar Comentario Fijado"
    yt_json_body = '={{ { "snippet": { "videoId": $(\'YT Upload YouTube\').first().json.id || $(\'YT Upload YouTube\').first().json.uploadId, "topLevelComment": { "snippet": { "textOriginal": $(\'YT Preparar Payload Upload\').first().json.pinned_comment || $json.pinned_comment || \'\' } } } } }}'
    
    if pinned_node_name in nodes:
        # Update existing parameters to specifyBody: "json" and jsonBody
        p_node = nodes[pinned_node_name]
        p_node["parameters"]["specifyBody"] = "json"
        p_node["parameters"]["jsonBody"] = yt_json_body
        p_node["parameters"].pop("body", None)
        print(f"  [{label}] Configuración corregida en '{pinned_node_name}' (specifyBody=json, jsonBody)")
    elif yt_creds:
        thumb_pos = nodes.get("YT Subir Miniatura YouTube", {}).get("position", [5760, -224])
        comment_pos = [thumb_pos[0] + 110, thumb_pos[1]]
        pinned_node = {
            "parameters": {
                "method": "POST",
                "url": "https://www.googleapis.com/youtube/v3/commentThreads?part=snippet",
                "authentication": "predefinedCredentialType",
                "nodeCredentialType": "youTubeOAuth2Api",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {
                            "name": "Content-Type",
                            "value": "application/json"
                        }
                    ]
                },
                "sendBody": True,
                "contentType": "json",
                "specifyBody": "json",
                "jsonBody": yt_json_body,
                "options": {}
            },
            "id": f"yt-pinned-{wfid[:8]}",
            "name": pinned_node_name,
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": comment_pos,
            "credentials": yt_creds,
            "onError": "continueRegularOutput"
        }
        wf["nodes"].append(pinned_node)
        nodes[pinned_node_name] = pinned_node
        conns["YT Subir Miniatura YouTube"] = {"main": [[{"node": pinned_node_name, "type": "main", "index": 0}]]}
        conns[pinned_node_name] = {"main": [[{"node": "YT Preparar Texto Telegram", "type": "main", "index": 0}]]}
        print(f"  [{label}] Añadido y conectado nodo '{pinned_node_name}'")

    # 5. Patch / Add Short 8b. Comentario Fijado Short
    short_pinned_name = "Short 8b. Comentario Fijado Short"
    short_json_body = '={{ { "snippet": { "videoId": $(\'Short 8. Upload YouTube Short\').first().json.id || $(\'Short 8. Upload YouTube Short\').first().json.uploadId, "topLevelComment": { "snippet": { "textOriginal": $(\'Short 7. Preparar Payload Short Upload\').first().json.pinned_comment || \'\' } } } } }}'
    
    if short_pinned_name in nodes:
        s_p_node = nodes[short_pinned_name]
        s_p_node["parameters"]["specifyBody"] = "json"
        s_p_node["parameters"]["jsonBody"] = short_json_body
        s_p_node["parameters"].pop("body", None)
        print(f"  [{label}] Configuración corregida en '{short_pinned_name}' (specifyBody=json, jsonBody)")
    else:
        short_upload_node = nodes.get("Short 8. Upload YouTube Short")
        if short_upload_node and yt_creds:
            s_pos = short_upload_node.get("position", [3968, 48])
            s_comment_pos = [s_pos[0] + 110, s_pos[1]]
            s_pinned_node = {
                "parameters": {
                    "method": "POST",
                    "url": "https://www.googleapis.com/youtube/v3/commentThreads?part=snippet",
                    "authentication": "predefinedCredentialType",
                    "nodeCredentialType": "youTubeOAuth2Api",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [
                            {
                                "name": "Content-Type",
                                "value": "application/json"
                            }
                        ]
                    },
                    "sendBody": True,
                    "contentType": "json",
                    "specifyBody": "json",
                    "jsonBody": short_json_body,
                    "options": {}
                },
                "id": f"short-pinned-{wfid[:8]}",
                "name": short_pinned_name,
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": s_comment_pos,
                "credentials": yt_creds,
                "onError": "continueRegularOutput"
            }
            wf["nodes"].append(s_pinned_node)
            nodes[short_pinned_name] = s_pinned_node
            conns["Short 8. Upload YouTube Short"] = {"main": [[{"node": short_pinned_name, "type": "main", "index": 0}]]}
            conns[short_pinned_name] = {"main": [[{"node": "Short 9. Notificación Telegram Short", "type": "main", "index": 0}]]}
            print(f"  [{label}] Añadido y conectado nodo '{short_pinned_name}'")

    # Save update
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump(wf, tf, ensure_ascii=False, indent=2)
        tmp_name = tf.name

    try:
        update_workflow(wfid, tmp_name)
        print(f"[{label}] OK: Workflow {wfid} actualizado con éxito")
        return True
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)

def main():
    print("=== APLICANDO OPTIMIZACIÓN Y CORRECCIÓN DE COMENTARIOS EN TODOS LOS WORKFLOWS ===")
    for label, wfid in WORKFLOWS:
        patch_workflow_sales(label, wfid)

if __name__ == "__main__":
    main()
