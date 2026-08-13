#!/usr/bin/env python3
"""
Script de importação do WhatsApp para Segunda Mente V4.0

Uso:
    python importar_whatsapp.py "Conversa do WhatsApp com +55 42 9121-7776.txt"

Ele lê o arquivo exportado do WhatsApp, extrai links e notas de texto,
e envia cada um para a API do Segunda Mente para processamento automático.
"""

import re
import sys
import time
import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

# ============================================
# CONFIGURAÇÃO — ajuste a URL do seu app aqui
# ============================================
API_BASE = "https://segunda-mente-dusky.vercel.app"

# Intervalo entre capturas (segundos) — evitar rate limit
DELAY_BETWEEN_CAPTURES = 3

# Pular links destes domínios (não são conteúdo útil)
SKIP_DOMAINS = [
    "forms.office.com",
    "q.passkit.net",
    "sat.sef.sc.gov.br",
    "webservices.unetvale.com.br",
    "eproc.jfsc.jus.br",
]


def parse_whatsapp_export(filepath):
    """Lê o arquivo de exportação do WhatsApp e extrai mensagens."""
    messages = []
    current_msg = None

    # Padrão: DD/MM/YYYY HH:MM - Remetente: Mensagem
    pattern = re.compile(
        r'^(\d{2}/\d{2}/\d{4}) (\d{2}:\d{2}) - ([^:]+): (.+)$'
    )

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            match = pattern.match(line)
            if match:
                # Salvar mensagem anterior se existir
                if current_msg:
                    messages.append(current_msg)

                date_str, time_str, sender, text = match.groups()
                try:
                    dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M")
                except ValueError:
                    dt = None

                current_msg = {
                    "date": dt,
                    "date_str": f"{date_str} {time_str}",
                    "sender": sender.strip(),
                    "text": text.strip(),
                }
            elif current_msg:
                # Continuação da mensagem anterior (multi-linha)
                current_msg["text"] += "\n" + line

    # Última mensagem
    if current_msg:
        messages.append(current_msg)

    return messages


def classify_message(msg):
    """Classifica a mensagem: link, texto, mídia, ou ignorar."""
    text = msg["text"]

    # Ignorar mensagens de sistema
    if text.startswith("As mensagens que você envia"):
        return "skip", None

    # Ignorar mídia oculta
    if text == "<Mídia oculta>":
        return "skip", None

    # Ignorar arquivos anexados (imagens, vídeos, etc.)
    if "(arquivo anexado)" in text:
        return "skip", None

    # Extrair URLs
    urls = re.findall(r'https?://[^\s]+', text)

    if urls:
        # Limpar URLs (remover pontuação final)
        clean_urls = [re.sub(r'[,;)>]+$', '', u) for u in urls]

        # Se a mensagem é basicamente só um link
        text_without_urls = text
        for u in urls:
            text_without_urls = text_without_urls.replace(u, "").strip()

        if not text_without_urls:
            return "link", {"url": clean_urls[0]}
        else:
            # Link com nota
            return "link_with_note", {
                "url": clean_urls[0],
                "note": text_without_urls
            }

    # Texto puro (nota, ideia, lembrete)
    if len(text) > 5:  # Ignorar mensagens muito curtas
        return "text", {"text": text}

    return "skip", None


def should_skip_url(url):
    """Verifica se o link deve ser pulado."""
    for domain in SKIP_DOMAINS:
        if domain in url:
            return True
    return False


def capture_link(url, note=None):
    """Envia um link para a API de captura."""
    payload = {"url": url}
    if note:
        payload["note"] = note

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        f"{API_BASE}/api/capture/link",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            return True, result
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return False, f"HTTP {e.code}: {body}"
    except Exception as e:
        return False, str(e)


def capture_text(text):
    """Envia um texto para a API de captura."""
    payload = {"text": text}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        f"{API_BASE}/api/capture/text",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            return True, result
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return False, f"HTTP {e.code}: {body}"
    except Exception as e:
        return False, str(e)


def main():
    if len(sys.argv) < 2:
        print("Uso: python importar_whatsapp.py <arquivo_whatsapp.txt>")
        sys.exit(1)

    filepath = sys.argv[1]
    print(f"\n{'='*60}")
    print(f"  SEGUNDA MENTE V4.0 — Importador do WhatsApp")
    print(f"{'='*60}")
    print(f"\nLendo arquivo: {filepath}")

    # Parsear mensagens
    messages = parse_whatsapp_export(filepath)
    print(f"Total de mensagens encontradas: {len(messages)}")

    # Classificar
    links = []
    texts = []
    skipped = 0

    for msg in messages:
        msg_type, data = classify_message(msg)
        if msg_type == "link":
            if not should_skip_url(data["url"]):
                links.append({**data, "date": msg["date_str"]})
        elif msg_type == "link_with_note":
            if not should_skip_url(data["url"]):
                links.append({**data, "date": msg["date_str"]})
        elif msg_type == "text":
            texts.append({**data, "date": msg["date_str"]})
        else:
            skipped += 1

    # Remover links duplicados (manter o primeiro)
    seen_urls = set()
    unique_links = []
    for link in links:
        if link["url"] not in seen_urls:
            seen_urls.add(link["url"])
            unique_links.append(link)
    links = unique_links

    print(f"\n📊 Resumo:")
    print(f"   🔗 Links únicos para importar: {len(links)}")
    print(f"   📝 Notas de texto: {len(texts)}")
    print(f"   ⏭️  Ignorados (mídia/sistema): {skipped}")

    total = len(links) + len(texts)
    estimated_time = total * DELAY_BETWEEN_CAPTURES
    estimated_cost = total * 0.002

    print(f"\n⏱️  Tempo estimado: ~{estimated_time // 60} minutos")
    print(f"💰 Custo estimado OpenAI: ~${estimated_cost:.2f} USD")
    print(f"\n{'='*60}")

    response = input("\nDeseja continuar? (s/n): ").strip().lower()
    if response != 's':
        print("Importação cancelada.")
        sys.exit(0)

    # Importar links
    success_count = 0
    error_count = 0
    errors = []

    print(f"\n🔗 Importando {len(links)} links...\n")
    for i, link in enumerate(links, 1):
        url = link["url"]
        note = link.get("note")
        date = link["date"]

        # Progresso
        pct = (i / len(links)) * 100
        print(f"  [{i}/{len(links)}] ({pct:.0f}%) {url[:60]}...", end=" ", flush=True)

        ok, result = capture_link(url, note)
        if ok:
            print("✅")
            success_count += 1
        else:
            print(f"❌ {result[:50]}")
            error_count += 1
            errors.append({"url": url, "error": str(result)})

        time.sleep(DELAY_BETWEEN_CAPTURES)

    # Importar textos
    print(f"\n📝 Importando {len(texts)} notas de texto...\n")
    for i, note in enumerate(texts, 1):
        text = note["text"]
        preview = text[:50].replace("\n", " ")

        pct = (i / len(texts)) * 100
        print(f"  [{i}/{len(texts)}] ({pct:.0f}%) {preview}...", end=" ", flush=True)

        ok, result = capture_text(text)
        if ok:
            print("✅")
            success_count += 1
        else:
            print(f"❌ {result[:50]}")
            error_count += 1
            errors.append({"text": preview, "error": str(result)})

        time.sleep(DELAY_BETWEEN_CAPTURES)

    # Relatório final
    print(f"\n{'='*60}")
    print(f"  IMPORTAÇÃO CONCLUÍDA")
    print(f"{'='*60}")
    print(f"  ✅ Sucesso: {success_count}")
    print(f"  ❌ Erros: {error_count}")
    print(f"  📊 Total processado: {success_count + error_count}")

    if errors:
        print(f"\n  Erros salvos em: import_errors.json")
        with open("import_errors.json", "w", encoding="utf-8") as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)

    print(f"\n🧠 Abra segunda-mente-dusky.vercel.app para ver seus conteúdos!")
    print()


if __name__ == "__main__":
    main()
