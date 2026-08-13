#!/usr/bin/env python3
"""
Reclassifica todos os conteúdos do Segunda Mente com o novo prompt.
Roda no seu computador, chamando a API em lotes.
"""

import json
import time
import urllib.request
import urllib.error

API_BASE = "https://segunda-mente-dusky.vercel.app"
BATCH_SIZE = 5
DELAY_BETWEEN_BATCHES = 2


def api_call(method, path, data=None):
    url = f"{API_BASE}{path}"
    body = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return True, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode()[:200]}"
    except Exception as e:
        return False, str(e)


def get_all_content_ids():
    """Busca todos os IDs de conteúdos processados."""
    ids = []
    offset = 0
    limit = 50
    while True:
        ok, data = api_call("GET", f"/api/contents?limit={limit}&offset={offset}&status=processed")
        if not ok:
            print(f"Erro ao buscar conteúdos: {data}")
            break
        items = data if isinstance(data, list) else data.get("results", data.get("contents", []))
        if not items:
            break
        for item in items:
            ids.append(item["id"])
        if len(items) < limit:
            break
        offset += limit
        time.sleep(0.5)
    return ids


def reclassify_one(content_id):
    """Reclassifica um conteúdo específico."""
    ok, result = api_call("POST", f"/api/reclassify/{content_id}")
    return ok, result


def process_pending():
    """Processa conteúdos pendentes."""
    ok, result = api_call("POST", "/api/process/pending")
    return ok, result


def main():
    print(f"\n{'='*60}")
    print(f"  SEGUNDA MENTE V4.0 — Reclassificação em Massa")
    print(f"{'='*60}")

    # Primeiro, tentar processar pendentes
    print("\n📋 Processando conteúdos pendentes...")
    ok, result = process_pending()
    if ok:
        print(f"   ✅ {result}")
    else:
        print(f"   ⚠️ {result}")

    # Buscar todos os IDs
    print("\n🔍 Buscando todos os conteúdos processados...")
    ids = get_all_content_ids()
    print(f"   Encontrados: {len(ids)} conteúdos para reclassificar")

    if not ids:
        # Tentar buscar sem filtro de status
        print("   Tentando sem filtro de status...")
        ok, data = api_call("GET", "/api/contents?limit=50&offset=0")
        if ok:
            items = data if isinstance(data, list) else data.get("results", data.get("contents", []))
            ids = [item["id"] for item in items]
            print(f"   Encontrados: {len(ids)} conteúdos")

    if not ids:
        print("   ❌ Nenhum conteúdo encontrado. Verifique a API.")
        return

    estimated_time = (len(ids) * DELAY_BETWEEN_BATCHES) // 60
    estimated_cost = len(ids) * 0.001  # gpt-4o-mini é barato

    print(f"\n⏱️  Tempo estimado: ~{estimated_time} minutos")
    print(f"💰 Custo estimado: ~${estimated_cost:.2f} USD")

    response = input("\nDeseja reclassificar todos? (s/n): ").strip().lower()
    if response != 's':
        print("Cancelado.")
        return

    # Reclassificar um por um
    success = 0
    errors = 0
    error_list = []

    print(f"\n🔄 Reclassificando {len(ids)} conteúdos...\n")

    for i, content_id in enumerate(ids, 1):
        pct = (i / len(ids)) * 100
        print(f"  [{i}/{len(ids)}] ({pct:.0f}%) {content_id[:12]}...", end=" ", flush=True)

        ok, result = reclassify_one(content_id)
        if ok:
            # Mostrar nova categoria se disponível
            new_cat = ""
            if isinstance(result, dict):
                new_cat = result.get("category", result.get("new_category", ""))
            print(f"✅ {new_cat}")
            success += 1
        else:
            print(f"❌ {str(result)[:50]}")
            errors += 1
            error_list.append({"id": content_id, "error": str(result)})

        time.sleep(DELAY_BETWEEN_BATCHES)

    # Relatório
    print(f"\n{'='*60}")
    print(f"  RECLASSIFICAÇÃO CONCLUÍDA")
    print(f"{'='*60}")
    print(f"  ✅ Sucesso: {success}")
    print(f"  ❌ Erros: {errors}")

    if error_list:
        with open("reclassify_errors.json", "w") as f:
            json.dump(error_list, f, indent=2)
        print(f"  📄 Erros salvos em reclassify_errors.json")

    # Stats finais
    print(f"\n📊 Verificando resultado...")
    ok, stats = api_call("GET", "/api/stats")
    if ok:
        print(f"\n  Categorias atualizadas:")
        for cat, count in stats.get("by_category", {}).items():
            print(f"    {cat}: {count}")
        print(f"\n  Top tags:")
        for tag in stats.get("top_tags", [])[:10]:
            print(f"    #{tag['name']}: {tag['count']}")

    print(f"\n🧠 Abra o app para ver os resultados!")


if __name__ == "__main__":
    main()
