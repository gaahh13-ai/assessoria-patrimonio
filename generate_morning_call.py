#!/usr/bin/env python3
"""
Gera o morning-call.html da assessoria de Gabriel Barbosa.

Fluxo:
  1. Usa a API da Anthropic (com a ferramenta de busca na web) para pesquisar
     o fechamento do último pregão e as principais notícias do dia.
  2. Recebe os dados em JSON estruturado.
  3. Preenche o template (morning-call.template.html), travando o design.
  4. Grava morning-call.html (o commit/push é feito pelo workflow do GitHub Actions).

Requer a variável de ambiente ANTHROPIC_API_KEY.
Modelo configurável via CLAUDE_MODEL (padrão: claude-haiku-4-5-20251001).
"""

import os
import re
import sys
import json
import html
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic

import paineis  # renderiza os painéis dinâmicos (Focus, Copom, IPCA, Pesquisas)

MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
TEMPLATE_PATH = "morning-call.template.html"
OUTPUT_PATH = "index.html"

TZ = ZoneInfo("America/Sao_Paulo")
DIAS = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
        "Sexta-feira", "Sábado", "Domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


DIAS_CURTO = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
HIST_DIR = "historico"
HIST_JSON = "historico.json"


def data_extenso(dt):
    return f"{DIAS[dt.weekday()]}, {dt.day} de {MESES[dt.month - 1]} de {dt.year}"


def arquivar(out_html, dt):
    """Salva um snapshot do dia em historico/AAAA-MM-DD.html e atualiza o índice historico.json."""
    iso = dt.strftime("%Y-%m-%d")
    os.makedirs(HIST_DIR, exist_ok=True)
    with open(os.path.join(HIST_DIR, f"{iso}.html"), "w", encoding="utf-8") as f:
        f.write(out_html)

    entries = []
    if os.path.exists(HIST_JSON):
        try:
            with open(HIST_JSON, encoding="utf-8") as f:
                entries = json.load(f)
        except Exception:
            entries = []

    entries = [e for e in entries if e.get("iso") != iso]
    entries.insert(0, {
        "iso": iso,
        "label": f"{dt.day:02d}/{dt.month:02d}/{dt.year}",
        "dia": DIAS_CURTO[dt.weekday()],
    })
    entries.sort(key=lambda e: e.get("iso", ""), reverse=True)
    entries = entries[:5]  # mantém apenas os 5 dias mais recentes

    with open(HIST_JSON, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False)
    print(f"Arquivado: {HIST_DIR}/{iso}.html ({len(entries)} edições no índice).")

    # Retenção: remove do disco os snapshots que saíram do índice de 5 dias.
    manter = {e.get("iso") for e in entries}
    for nome in os.listdir(HIST_DIR):
        if nome.endswith(".html") and nome[:-5] not in manter:
            try:
                os.remove(os.path.join(HIST_DIR, nome))
                print(f"Removido do histórico (retenção 5 dias): {nome}")
            except OSError:
                pass


def build_prompt(hoje):
    return f"""Hoje é {data_extenso(hoje)} (horário de Brasília), por volta das 6h da manhã.
Você vai montar o "Morning Call" diário de mercado da assessoria de investimentos de Gabriel Barbosa.

Como é de manhã cedo, os dados de mercado devem ser do FECHAMENTO DO ÚLTIMO PREGÃO
(o dia útil anterior na B3 e em Wall Street). Se hoje for segunda-feira, o último pregão foi na sexta.

PESQUISE NA WEB (use a ferramenta de busca) e confirme cada dado numa fonte confiável
(Money Times, InfoMoney, B3, Investing, CNBC, Yahoo Finance). NUNCA invente números ou links.
SEJA EFICIENTE NAS BUSCAS: faça até 8 buscas, bem direcionadas. Reserve buscas para:
1-2 do fechamento do pregão e índices, 1-2 para as maiores altas/baixas com a cotação das ações, e 2-3 para as notícias.
Reaproveite o que já encontrou; não repita buscas. Você PRECISA entregar 4 notícias de Mercado/Economia e 4 de Política.

Use SEMPRE os dados do FECHAMENTO DO ÚLTIMO PREGÃO (dia útil anterior).

Colete:
- Painel (fechamento do último pregão), com pontuação/cotação E variação % de CADA um destes SEIS índices:
  Ibovespa, Dólar USD/BRL, Petróleo Brent, S&P 500, Nasdaq e Dow Jones. NÃO inclua bolsas europeias
  (nada de STOXX 600), nem Selic nem DI no painel. Se, mesmo após buscar, você NÃO encontrar o valor real
  de algum índice, OMITA esse índice da lista — JAMAIS escreva "n/d" no painel.
- Destaques de juros e inflação: Selic vigente (ex.: "14,25% a.a."); IPCA acumulado em 12 meses (ex.: "+5,23%");
  IPCA do último mês já publicado, com o nome do mês (ex.: "Junho: +0,16%").
- As 5 a 6 MAIORES ALTAS e as 5 a 6 MAIORES BAIXAS do Ibovespa. Para CADA ação é OBRIGATÓRIO:
  ticker, nome curto, variação % real E a cotação de fechamento em reais (ex.: "R$ 5,23"). A cotação costuma
  vir ENTRE PARÊNTESES ao lado da variação (ex.: "MGLU3 ... 7,76% (R$ 4,86)"). Se você NÃO tiver a cotação
  em R$ de uma ação, NÃO a inclua. NUNCA use "n/d". Preciso de pelo menos 3 altas e 3 baixas COM cotação.
- 4 notícias de "Mercado & Economia" e 4 de "Política & Internacional", cada uma com um bom RESUMO autoral
  (2 a 4 frases, escrito por você, sem copiar o texto da fonte), o veículo e a URL REAL da matéria (verifique cada link).
- Agenda econômica da semana (4 a 6 itens) com dia e evento; marque o item mais importante com "hl": true.

Responda APENAS com um objeto JSON válido entre as marcas <json> e </json>, no formato exato:

<json>
{{
  "date": "{data_extenso(hoje)}",
  "subtitle": "Abertura da semana · fechamento de sexta (10/07)",
  "resumo": ["primeiro parágrafo do panorama", "segundo parágrafo"],
  "painel": [
    {{"lbl": "Ibovespa", "val": "177.866", "chg": "▲ +2,97%", "bar": "up", "cls": "up"}},
    {{"lbl": "Dólar (USD/BRL)", "val": "R$ 5,1084", "chg": "▼ −0,28%", "bar": "up", "cls": "up"}},
    {{"lbl": "Brent (set)", "val": "US$ 76,01", "chg": "▼ −0,38%", "bar": "down", "cls": "down"}},
    {{"lbl": "S&P 500", "val": "7.575,39", "chg": "▲ +0,42%", "bar": "up", "cls": "up"}},
    {{"lbl": "Nasdaq", "val": "26.281,11", "chg": "▲ +0,29%", "bar": "up", "cls": "up"}},
    {{"lbl": "Dow Jones", "val": "52.637,01", "chg": "▲ +0,29%", "bar": "up", "cls": "up"}}
  ],
  "selic": "14,25% a.a.",
  "ipca_12m": "+5,23%",
  "ipca_mes": "Junho: +0,16%",
  "altas": [{{"tk": "CMIN3", "nm": "CSN Mineração", "pc": "+8,28%", "preco": "R$ 5,23"}}],
  "baixas": [{{"tk": "PRIO3", "nm": "PRIO", "pc": "−0,29%", "preco": "R$ 55,45"}}],
  "baixas_nota": "Opcional: nota curta se o pregão foi de alta/queda generalizada. Use string vazia se não precisar.",
  "noticias_eco": [
    {{"tag": "Mercado", "tag_class": "mkt", "titulo": "...", "resumo": "...", "fonte": "Money Times", "url": "https://..."}}
  ],
  "noticias_pol": [
    {{"tag": "Internacional", "tag_class": "pol", "titulo": "...", "resumo": "...", "fonte": "Money Times", "url": "https://..."}}
  ],
  "agenda": [
    {{"day": "SEG 13", "ev": "<b>Boletim Focus</b> (BC)", "hl": false}},
    {{"day": "RADAR", "ev": "<b>Copom em 4-5/08:</b> mercado precifica corte da Selic.", "hl": true}}
  ],
  "footer_date": "{hoje.day} de {MESES[hoje.month - 1]} de {hoje.year}"
}}
</json>

Regras: variação positiva usa seta ▲ e "cls": "up"; negativa usa ▼ e "cls": "down".
Para o card de juros/DI, "bar" pode ser "acc" (cor de destaque). Use o sinal de menos tipográfico "−" (U+2212).
Formato numérico brasileiro (milhar com ".", decimal com ","). O campo "subtitle" deve refletir o dia real
(ex.: "Fechamento do pregão de ontem (DD/MM)"). Em "ev" da agenda pode usar <b>...</b>. Não use aspas triplas.

IMPORTANTÍSSIMO — FORMATO DA RESPOSTA:
- Responda EXCLUSIVAMENTE com o bloco <json>...</json>. NUNCA escreva explicações, comentários ou qualquer
  texto em prosa — nem antes, nem depois, nem para avisar que faltou algum dado.
- Se não encontrar algum dado, preencha o campo com o melhor valor disponível ou "n/d" e SIGA em frente.
- O painel deve trazer os seis índices (Ibovespa, Dólar, Brent, S&P 500, Nasdaq, Dow Jones), sem bolsas
  europeias. Se não encontrar o valor real de algum, OMITA aquele índice — nunca escreva "n/d".
- Para os juros, se não achar a taxa exata, use "Selic 14,25%".
- Você DEVE concluir a tarefa e devolver o JSON. Se uma busca falhar, tente outra abordagem; JAMAIS responda que "não conseguiu".
- Comece a resposta com <json>{{ e termine com }}</json>. Retorne SEMPRE o JSON completo, com todos os campos."""


def _try_load(candidate):
    candidate = candidate.strip()
    candidate = re.sub(r"^```(?:json)?", "", candidate).strip()
    candidate = re.sub(r"```$", "", candidate).strip()
    try:
        return json.loads(candidate)
    except Exception:
        # remove vírgulas sobrando antes de } ou ]
        fixed = re.sub(r",(\s*[}\]])", r"\1", candidate)
        return json.loads(fixed)


def extract_json(text):
    """Extrai o objeto JSON da resposta do modelo, tentando várias estratégias."""
    candidates = []
    m = re.search(r"<json>(.*?)</json>", text, re.DOTALL)
    if m:
        candidates.append(m.group(1))
    for fm in re.finditer(r"```(?:json)?\s*(.*?)```", text, re.DOTALL):
        candidates.append(fm.group(1))
    if "{" in text and "}" in text:
        candidates.append(text[text.index("{"): text.rindex("}") + 1])
    candidates.append(text)
    for c in candidates:
        try:
            return _try_load(c)
        except Exception:
            continue
    raise ValueError("Não consegui extrair JSON da resposta do modelo. Início da resposta:\n" + text[:1000])


def repair_to_json(client, text):
    """Passo de reparo barato (sem busca): converte a resposta do modelo em JSON válido."""
    prompt = (
        "O texto a seguir contém dados de mercado e notícias, possivelmente em prosa. "
        "Converta em UM ÚNICO objeto JSON válido do Morning Call, com as chaves: date, subtitle, "
        "resumo (lista de 2 strings), painel (lista de {lbl,val,chg,bar,cls}), selic, ipca_12m, ipca_mes, "
        "altas (lista {tk,nm,pc,preco}), baixas (lista {tk,nm,pc,preco}), baixas_nota, noticias_eco e noticias_pol (listas de "
        "{tag,tag_class,titulo,resumo,fonte,url}), agenda (lista {day,ev,hl}) e footer_date. "
        "Use os dados presentes no texto; se algo faltar, use \"n/d\" ou omita itens da lista. "
        "Responda SOMENTE com o JSON entre <json> e </json>, sem nenhum texto extra.\n\nTEXTO:\n" + text
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
    )
    rtext = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    return extract_json(rtext)


def esc(s):
    return html.escape(str(s), quote=True)


def _val_ok(v):
    """True se o valor é numérico de verdade (não vazio, não 'n/d')."""
    v = str(v).strip().lower()
    return bool(v) and v != "n/d" and bool(re.search(r"\d", v))


def render_panel(items):
    out = []
    for it in items:
        if not _val_ok(it.get("val", "")):
            continue  # nunca renderiza card 'n/d'/vazio no painel
        bar = {"up": "bar-up", "down": "bar-down", "acc": "bar-acc"}.get(it.get("bar", "up"), "bar-up")
        cls = "down" if it.get("cls") == "down" else "up"
        out.append(
            f'        <div class="cmini"><div class="bar {bar}"></div>'
            f'<div class="lbl">{esc(it["lbl"])}</div>'
            f'<div class="val">{esc(it["val"])}</div>'
            f'<div class="chg {cls}">{esc(it["chg"])}</div></div>'
        )
    return "\n".join(out)


def render_rows(items, cls):
    out = []
    for it in items:
        preco = it.get("preco", "")
        preco_html = f'<div class="prc">{esc(preco)}</div>' if preco and preco != "n/d" else ""
        out.append(
            f'        <div class="row"><div><div class="tk">{esc(it["tk"])}</div>'
            f'<div class="nm">{esc(it["nm"])}</div></div>'
            f'<div class="rt"><div class="pc {cls}">{esc(it["pc"])}</div>{preco_html}</div></div>'
        )
    return "\n".join(out)


def render_news(items):
    out = []
    for it in items:
        tag_class = it.get("tag_class", "mkt")
        if tag_class not in ("mkt", "eco", "pol"):
            tag_class = "mkt"
        url = it["url"]
        if not str(url).startswith("http"):
            continue
        out.append(
            f'        <a class="item" href="{esc(url)}" target="_blank" rel="noopener">\n'
            f'          <div class="it-tag {tag_class}">{esc(it["tag"])}</div>\n'
            f'          <div class="it-title">{esc(it["titulo"])}</div>\n'
            f'          <div class="it-sum">{esc(it["resumo"])}</div>\n'
            f'          <div class="it-src">{esc(it["fonte"])} <span class="arrow">↗</span></div>\n'
            f'        </a>'
        )
    return "\n\n".join(out)


def render_agenda(items):
    out = []
    for it in items:
        hl = " hl" if it.get("hl") else ""
        out.append(
            f'        <div class="ar{hl}"><span class="day">{esc(it["day"])}</span>'
            f'<div class="ev">{it["ev"]}</div></div>'
        )
    return "\n".join(out)


def render_losses(items, nota):
    body = render_rows(items, "down")
    if nota:
        body += f'\n        <div class="pnote">{esc(nota)}</div>'
    return body


def brapi_precos(tickers):
    """Cotações de fechamento das ações via brapi.dev (JSON estável).
    Retorna {TICKER: 'R$ x,xx'}. Usa BRAPI_TOKEN se existir (opcional). Nunca levanta exceção.

    O plano gratuito da brapi aceita apenas UM ativo por requisição (uma lista
    com vários tickers retorna HTTP 400), então consultamos um a um."""
    import urllib.request
    import time
    out = {}
    if not tickers:
        return out
    token = os.environ.get("BRAPI_TOKEN", "").strip()
    falhas = 0
    for tk in tickers:
        try:
            url = "https://brapi.dev/api/quote/" + tk
            if token:
                url += "?token=" + token
            req = urllib.request.Request(url, headers={"User-Agent": "morning-call-bot"})
            with urllib.request.urlopen(req, timeout=20) as r:
                payload = json.loads(r.read().decode("utf-8"))
            for it in payload.get("results", []):
                sym = (it.get("symbol") or "").upper()
                preco = it.get("regularMarketPrice")
                if preco is None:
                    preco = it.get("regularMarketPreviousClose")
                if sym and preco is not None:
                    out[sym] = "R$ " + f"{float(preco):.2f}".replace(".", ",")
        except Exception as e:
            falhas += 1
            if falhas <= 2:
                print(f"brapi ({tk}) indisponível: {str(e)[:120]}")
        time.sleep(0.2)  # cortesia com a API
    return out


def brapi_cotacoes(tickers):
    """Como brapi_precos, mas devolve preço E variação % de cada ação:
    {TICKER: {"preco": "R$ x,xx", "pc": "+x,xx%"}}. Nunca levanta exceção."""
    import urllib.request
    import time
    out = {}
    if not tickers:
        return out
    token = os.environ.get("BRAPI_TOKEN", "").strip()
    falhas = 0
    for tk in tickers:
        try:
            url = "https://brapi.dev/api/quote/" + tk
            if token:
                url += "?token=" + token
            req = urllib.request.Request(url, headers={"User-Agent": "morning-call-bot"})
            with urllib.request.urlopen(req, timeout=20) as r:
                payload = json.loads(r.read().decode("utf-8"))
            for it in payload.get("results", []):
                sym = (it.get("symbol") or "").upper()
                if not sym:
                    continue
                info = {}
                preco = it.get("regularMarketPrice")
                if preco is None:
                    preco = it.get("regularMarketPreviousClose")
                if preco is not None:
                    info["preco"] = "R$ " + f"{float(preco):.2f}".replace(".", ",")
                chg = it.get("regularMarketChangePercent")
                if chg is not None:
                    sinal = "+" if float(chg) >= 0 else "−"
                    info["pc"] = sinal + f"{abs(float(chg)):.2f}".replace(".", ",") + "%"
                if info:
                    out[sym] = info
        except Exception as e:
            falhas += 1
            if falhas <= 2:
                print(f"brapi ({tk}) indisponível: {str(e)[:120]}")
        time.sleep(0.2)
    return out


# Índices que o painel deve conter (grupos de palavras-chave para casar o rótulo).
PAINEL_CORE = [["ibov"], ["usd/brl", "dólar", "dolar"], ["s&p"], ["nasdaq"], ["dow"]]


def limpar_painel(data):
    """Remove do painel qualquer índice sem valor real (evita cards 'n/d')."""
    data["painel"] = [it for it in (data.get("painel") or []) if _val_ok(it.get("val", ""))]
    return data


def _pc_valido(it):
    return bool(re.search(r"\d", str(it.get("pc", "")))) and str(it.get("pc", "")).strip().lower() != "n/d"


def _pc_num(pc):
    """Converte '+1,08%' / '−2,34%' em float (+1.08 / -2.34). None se não der."""
    s = str(pc).replace("%", "").replace("+", "").strip()
    s = s.replace("−", "-").replace("–", "-").replace("—", "-")
    s = s.replace(".", "").replace(",", ".")  # formato BR: vírgula decimal
    try:
        return float(s)
    except Exception:
        return None


def preparar_movers(data):
    """Monta as 3 maiores altas e as 3 maiores baixas de forma consistente:
    pega preço e variação na brapi (fonte estável; usa o modelo na falta), descarta
    quem ficar sem preço, RE-CLASSIFICA pelo sinal real (positivo=alta, negativo=baixa)
    e ORDENA (altas do maior para o menor; baixas da maior queda para a menor)."""
    cand = [it for it in (data.get("altas") or []) + (data.get("baixas") or []) if _pc_valido(it)]
    tickers = []
    for it in cand:
        tk = (it.get("tk") or "").strip().upper()
        if tk and tk not in tickers:
            tickers.append(tk)
    cot = brapi_cotacoes(tickers[:20])

    enr, vistos = [], set()
    for it in cand:
        tk = (it.get("tk") or "").strip().upper()
        if not tk or tk in vistos:
            continue
        c = cot.get(tk, {})
        preco = c.get("preco") or (it.get("preco") or "").strip()
        pc = c.get("pc") or it.get("pc")
        n = _pc_num(pc)
        if not preco or preco == "n/d" or n is None or n == 0:
            continue  # sem preço/variação confiável, ou variação zero
        vistos.add(tk)
        it2 = dict(it)
        it2["preco"] = preco
        it2["pc"] = pc
        it2["_n"] = n
        enr.append(it2)

    altas = sorted([x for x in enr if x["_n"] > 0], key=lambda x: -x["_n"])[:3]
    baixas = sorted([x for x in enr if x["_n"] < 0], key=lambda x: x["_n"])[:3]
    for x in altas + baixas:
        x.pop("_n", None)
    data["altas"] = altas
    data["baixas"] = baixas
    print(f"movers: {len(altas)} altas / {len(baixas)} baixas com preço "
          f"(brapi {len(cot)}/{len(tickers)}).")
    return data


def dados_validos(d, mode):
    """Validação por modo. main/market exigem painel-core completo + 3 altas e 3 baixas
    com preço. agenda exige a lista de agenda. main também exige as notícias."""
    if not d:
        return False
    if mode == "agenda":
        return len(d.get("agenda") or []) >= 3
    painel = [it for it in (d.get("painel") or []) if _val_ok(it.get("val", ""))]
    labels = " ".join((it.get("lbl", "") or "").lower() for it in painel)
    painel_ok = all(any(k in labels for k in grp) for grp in PAINEL_CORE)
    altas_ok = len([x for x in (d.get("altas") or []) if x.get("preco") and _pc_valido(x)]) >= 3
    baixas_ok = len([x for x in (d.get("baixas") or []) if x.get("preco") and _pc_valido(x)]) >= 3
    mercado_ok = painel_ok and altas_ok and baixas_ok
    if mode == "market":
        return mercado_ok
    return mercado_ok and bool(d.get("noticias_eco")) and bool(d.get("noticias_pol"))


# ===== Painéis dinâmicos: rolagem (IPCA/Copom) e Boletim Focus =====
def _save_dado(nome, obj):
    os.makedirs(paineis.DADOS_DIR, exist_ok=True)
    with open(os.path.join(paineis.DADOS_DIR, nome), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _ask_json(client, prompt, max_uses=4):
    """Pergunta curta com busca na web; devolve o JSON (ou levanta exceção)."""
    msgs = [{"role": "user", "content": prompt}]
    parts = []
    for _ in range(6):
        resp = client.messages.create(
            model=MODEL, max_tokens=1500,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": max_uses}],
            messages=msgs,
        )
        for b in resp.content:
            if getattr(b, "type", "") == "text":
                parts.append(b.text)
        if resp.stop_reason == "pause_turn":
            msgs.append({"role": "assistant", "content": resp.content})
            continue
        break
    return extract_json("".join(parts))


def atualizar_ipca(client):
    """Se saiu um IPCA mensal novo, adiciona o mês e descarta o mais antigo (12 meses)."""
    try:
        ipca = paineis.load_ipca()
        atual = (ipca.get("meses") or [{}])[0].get("mes", "")
        d = _ask_json(client,
            "Qual é o IPCA cheio (IBGE) mais recente já divulgado: variacao no mes e acumulado em 12 meses? "
            f"O mes mais recente que ja tenho registrado e '{atual}'. Responda SOMENTE com JSON entre <json></json>: "
            '{"novo": true, "mes": "mmm/aa", "no_mes": "+0,00%", "acum12m": "+0,00%"}. '
            "Use novo=true APENAS se houver um mes mais recente que o registrado; senao {\"novo\": false}. Formato brasileiro.")
        if not d or not d.get("novo"):
            return
        mes = (d.get("mes") or "").strip(); nm = (d.get("no_mes") or "").strip(); ac = (d.get("acum12m") or "").strip()
        if not (mes and nm and ac):
            return
        try:
            tp = "dn" if float(nm.replace("%", "").replace(",", ".").replace("+", "")) < 0 else "up"
        except Exception:
            tp = "up"
        meses = [m for m in ipca.get("meses", []) if m.get("mes") != mes]
        meses.insert(0, {"mes": mes, "no_mes": nm, "tipo": tp, "acum": ac})
        ipca["meses"] = meses[:12]; ipca["acum12m"] = ac
        _save_dado("ipca.json", ipca)
        print(f"IPCA: novo mes adicionado ({mes}).")
    except Exception as e:
        print(f"atualizar_ipca ignorado: {str(e)[:140]}")


def atualizar_copom(client):
    """Se houve nova decisão do Copom, adiciona e descarta a mais antiga (4 reuniões)."""
    try:
        copom = paineis.load_copom()
        atual = (copom.get("reunioes") or [{}])[0].get("data", "")
        d = _ask_json(client,
            "Houve uma decisao do Copom (Banco Central) MAIS RECENTE do que a reuniao "
            f"'{atual}'? Se sim, informe: data da reuniao, decisao (ex.: 'Mantida', '+25 pb', '-50 pb'), "
            "a Selic resultante e a data da PROXIMA reuniao. Responda SOMENTE com JSON entre <json></json>: "
            '{"novo": true, "data": "dd-dd mmm/aa", "decisao": "...", "tipo": "hold|up|down", "selic": "00,00%", "proxima": "dd-dd mmm aaaa"}. '
            "Se nao houver decisao nova, {\"novo\": false}.")
        if not d or not d.get("novo"):
            return
        data_r = (d.get("data") or "").strip()
        if not data_r:
            return
        r = {"data": data_r, "decisao": (d.get("decisao") or "").strip(),
             "tipo": (d.get("tipo") or "hold").strip(), "selic": (d.get("selic") or "").strip()}
        reun = [x for x in copom.get("reunioes", []) if x.get("data") != data_r]
        reun.insert(0, r); copom["reunioes"] = reun[:4]
        if d.get("proxima"):
            copom["proxima"] = str(d["proxima"]).strip()
        _save_dado("copom.json", copom)
        print(f"Copom: nova reuniao adicionada ({data_r}).")
    except Exception as e:
        print(f"atualizar_copom ignorado: {str(e)[:140]}")


def _anos_focus(hoje):
    y = hoje.year
    return [str(y), str(y + 1), str(y + 2)]


def atualizar_focus(client, hoje):
    """Busca o último Boletim Focus e recomputa a tabela (com setas vs. semana anterior)."""
    focus = paineis.load_focus()
    anos = _anos_focus(hoje)
    d = _ask_json(client,
        f"Traga as projecoes MEDIANAS do ultimo Boletim Focus (Banco Central) para {anos[0]}, {anos[1]} e {anos[2]}: "
        "IPCA (%), PIB (%), Selic no fim do ano (%) e Cambio R$/US$. Responda SOMENTE com JSON entre <json></json>: "
        '{"IPCA": ["0,00","0,00","0,00"], "PIB": ["0,00","0,00","0,00"], "Selic": ["0,00","0,00","0,00"], "Cambio": ["0,00","0,00","0,00"]} '
        "na ordem dos anos, numeros em formato brasileiro sem o simbolo de porcentagem.")
    if not d:
        raise ValueError("Focus sem dados")
    prev = {ln.get("lbl"): [v.get("v", "") for v in ln.get("vals", [])] for ln in focus.get("linhas", [])}
    conf = [("IPCA", "inflação", "%"), ("PIB", "crescimento", "%"), ("Selic", "fim do ano", "%"), ("Câmbio", "R$/US$", "")]
    km = {"IPCA": "IPCA", "PIB": "PIB", "Selic": "Selic", "Câmbio": "Cambio"}
    linhas = []
    for lbl, sub, suf in conf:
        arr = d.get(km[lbl]) or []
        vals = []
        for i in range(3):
            raw = str(arr[i]).replace("%", "").strip() if i < len(arr) else ""
            if not raw:
                vals.append({"v": "—", "t": "eq"}); continue
            v = raw + ("%" if suf == "%" else "")
            t = "eq"; pv = prev.get(lbl, [])
            try:
                if i < len(pv) and pv[i]:
                    a = float(raw.replace(",", ".")); b = float(str(pv[i]).replace("%", "").replace(",", "."))
                    t = "up" if a > b + 1e-9 else ("dn" if a < b - 1e-9 else "eq")
            except Exception:
                t = "eq"
            vals.append({"v": v, "t": t})
        linhas.append({"lbl": lbl, "sub": sub, "vals": vals})
    focus["anos"] = anos
    focus["linhas"] = linhas
    from datetime import timedelta
    _seg = hoje - timedelta(days=hoje.weekday())
    focus["atualizado"] = "seg " + _seg.strftime("%d/%m")
    _save_dado("focus.json", focus)
    return focus


def rodar_focus_only(hoje):
    """Atualização das 9:30: mexe SOMENTE no Boletim Focus (index + snapshot de hoje)."""
    client = anthropic.Anthropic()
    try:
        focus = atualizar_focus(client, hoje)
    except Exception as e:
        print(f"Focus nao atualizado ({str(e)[:140]}). Nada alterado.")
        return
    bloco = paineis.render_focus_block(focus)
    pat = re.compile(r"<!--FOCUS:START-->.*?<!--FOCUS:END-->", re.DOTALL)
    iso = hoje.strftime("%Y-%m-%d")
    alvos = [OUTPUT_PATH, os.path.join("historico", iso + ".html")]
    for path in alvos:
        try:
            s = open(path, encoding="utf-8").read()
        except FileNotFoundError:
            continue
        if "<!--FOCUS:START-->" in s:
            s = pat.sub(lambda m: bloco, s, count=1)
            with open(path, "w", encoding="utf-8") as f:
                f.write(s)
            print(f"Boletim Focus atualizado em {path}.")
        else:
            print(f"Marcadores de Focus nao encontrados em {path}.")


_MES_EXT = {"jan": "Janeiro", "fev": "Fevereiro", "mar": "Março", "abr": "Abril",
            "mai": "Maio", "jun": "Junho", "jul": "Julho", "ago": "Agosto",
            "set": "Setembro", "out": "Outubro", "nov": "Novembro", "dez": "Dezembro"}


def _cards_macro(data):
    """Selic e IPCA dos cards: usa o modelo se vier número real; senão cai para os
    dados mantidos em dados/*.json (nunca mostra 'n/d')."""
    def bom(v):
        v = str(v).strip()
        return v and v.lower() != "n/d" and "n/d" not in v.lower() and bool(re.search(r"\d", v))

    selic = str(data.get("selic", "")).strip()
    if not bom(selic):
        r = (paineis.load_copom().get("reunioes") or [{}])[0]
        selic = (r.get("selic", "").strip() + " a.a.") if r.get("selic") else "14,25% a.a."

    ip = paineis.load_ipca()
    ipca12 = str(data.get("ipca_12m", "")).strip()
    if not bom(ipca12):
        ipca12 = ip.get("acum12m", "") or "n/d"

    ipca_mes = str(data.get("ipca_mes", "")).strip()
    if not bom(ipca_mes):
        m = (ip.get("meses") or [{}])[0]
        abbr = (m.get("mes", "")[:3]).lower()
        nome = _MES_EXT.get(abbr, m.get("mes", ""))
        ipca_mes = f"{nome}: {m.get('no_mes','')}" if m.get("no_mes") else "n/d"
    return selic, ipca12, ipca_mes


def montar_pagina(template, data, hora):
    """Preenche o template completo (modo main). `hora` = HH:MM da rodada (carimbos)."""
    summary_html = "\n".join(f"    <p>{p}</p>" for p in data["resumo"])
    selic, ipca12, ipca_mes = _cards_macro(data)
    out = template
    out = out.replace("{{DATE}}", esc(data["date"]))
    out = out.replace("{{SUMMARY}}", summary_html)
    out = out.replace("{{NEWS_ECO}}", render_news(data["noticias_eco"]))
    out = out.replace("{{NEWS_POL}}", render_news(data["noticias_pol"]))
    out = out.replace("{{PANEL}}", render_panel(data["painel"]))
    out = out.replace("{{MERCADO_HORA}}", esc(hora))
    out = out.replace("{{SELIC}}", esc(selic))
    out = out.replace("{{IPCA_12M}}", esc(ipca12))
    out = out.replace("{{IPCA_MES}}", esc(ipca_mes))
    out = out.replace("{{GAINS}}", render_rows(data.get("altas", []), "up"))
    out = out.replace("{{LOSSES}}", render_losses(data.get("baixas", []), data.get("baixas_nota", "")))
    out = out.replace("{{DESTAQUES_HORA}}", esc(hora))
    out = out.replace("{{AGENDA}}", render_agenda(data.get("agenda", [])))
    out = out.replace("{{FOOTER_DATE}}", esc(data.get("footer_date", data["date"])))
    out = out.replace("{{POLLS}}", paineis.render_polls(paineis.load_pesquisas()))
    out = out.replace("{{FOCUS_BLOCK}}", paineis.render_focus_block(paineis.load_focus()))
    out = out.replace("{{MODAL_COPOM}}", paineis.render_copom_modal(paineis.load_copom()))
    out = out.replace("{{MODAL_IPCA}}", paineis.render_ipca_modal(paineis.load_ipca()))
    return out


def _extrai_bloco(template, tag):
    m = re.search(r"<!--%s:START-->.*?<!--%s:END-->" % (tag, tag), template, re.DOTALL)
    return m.group(0) if m else None


def _preenche_bloco(bloco, data, hora):
    """Preenche os placeholders que aparecem dentro dos blocos parciais."""
    b = bloco
    b = b.replace("{{PANEL}}", render_panel(data["painel"]))
    b = b.replace("{{MERCADO_HORA}}", esc(hora))
    b = b.replace("{{GAINS}}", render_rows(data.get("altas", []), "up"))
    b = b.replace("{{LOSSES}}", render_losses(data.get("baixas", []), data.get("baixas_nota", "")))
    b = b.replace("{{DESTAQUES_HORA}}", esc(hora))
    b = b.replace("{{AGENDA}}", render_agenda(data.get("agenda", [])))
    return b


def substituir_blocos(hoje, tags, template, data, hora):
    """Atualiza só os blocos indicados (por marcadores) no index e no snapshot de hoje."""
    novos = {}
    for tag in tags:
        tpl = _extrai_bloco(template, tag)
        if tpl:
            novos[tag] = _preenche_bloco(tpl, data, hora)
        else:
            print(f"Bloco {tag} nao existe no template.")
    iso = hoje.strftime("%Y-%m-%d")
    for path in [OUTPUT_PATH, os.path.join(HIST_DIR, iso + ".html")]:
        try:
            s = open(path, encoding="utf-8").read()
        except FileNotFoundError:
            continue
        feito = []
        for tag, novo in novos.items():
            pat = re.compile(r"<!--%s:START-->.*?<!--%s:END-->" % (tag, tag), re.DOTALL)
            if pat.search(s):
                s = pat.sub(lambda m: novo, s, count=1)
                feito.append(tag)
            else:
                print(f"Marcadores {tag} nao encontrados em {path}.")
        if feito:
            with open(path, "w", encoding="utf-8") as f:
                f.write(s)
            print(f"Blocos {feito} atualizados em {path}.")


def _copom_vencido(hoje):
    """True se hoje ja passou do ultimo dia da reuniao registrada como "proxima".
    A busca de Selic/Copom so roda um dia apos a reuniao prevista no site."""
    from datetime import date
    prox = (paineis.load_copom().get("proxima") or "").lower()
    meses = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
             "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}
    mes = next((n for ab, n in meses.items() if ab in prox), 0)
    anos = re.findall(r"20\d{2}", prox)
    dias = re.findall(r"\b(\d{1,2})\b", re.sub(r"20\d{2}", "", prox))
    if not (mes and anos and dias):
        return False
    try:
        fim = date(int(anos[0]), mes, max(int(d) for d in dias))
    except ValueError:
        return False
    return hoje.date() > fim


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ERRO: ANTHROPIC_API_KEY não definida.")

    hoje = datetime.now(TZ)

    # Modo de atualização:
    #   main   – 5:45, dias úteis (página completa: data, resumo, notícias + tudo)
    #   market – 13:00 e 18:30 (só Painel de Mercado + Destaques B3, com carimbo de horário)
    #   focus  – segunda 9:30 (só Boletim Focus)
    #   agenda – sexta 18:30 (só Agenda da Semana, referente à semana seguinte)
    # Compatível com o antigo FOCUS_ONLY.
    mode = os.environ.get("MODE", "").strip().lower()
    if not mode:
        mode = "focus" if os.environ.get("FOCUS_ONLY", "").strip().lower() == "true" else "main"

    if mode == "focus":
        print("Modo focus (Boletim Focus, segunda 9:30).")
        rodar_focus_only(hoje)
        return

    # dias úteis apenas (segurança extra caso rode fora do cron).
    # FORCE_RUN=true (disparo manual com "forçar") permite rodar no fim de semana.
    forcar = os.environ.get("FORCE_RUN", "").strip().lower() == "true"
    if hoje.weekday() >= 5 and not forcar:
        print("Fim de semana — nada a gerar.")
        return

    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        template = f.read()

    client = anthropic.Anthropic()
    prompt = build_prompt(hoje)

    def gerar_texto():
        """Uma rodada de geração com busca na web; trata turnos pausados (pause_turn)."""
        messages = [{"role": "user", "content": prompt}]
        parts = []
        sr = None
        for _ in range(8):
            resp = client.messages.create(
                model=MODEL,
                max_tokens=16000,
                tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}],
                messages=messages,
            )
            sr = resp.stop_reason
            for b in resp.content:
                if getattr(b, "type", "") == "text":
                    parts.append(b.text)
            if sr == "pause_turn":
                messages.append({"role": "assistant", "content": resp.content})
                continue
            break
        return "".join(parts), sr

    # Gera; a cada tentativa já enriquece movers (preço/variação via brapi) e limpa o
    # painel ANTES de validar, para exigir 3 altas + 3 baixas com preço e o painel-core
    # completo. Só publica dados que passam na validação do modo.
    data = None
    for tentativa in range(4):
        text, sr = gerar_texto()
        print(f"Tentativa {tentativa + 1}: {len(text)} caracteres (stop_reason={sr}).")
        d = None
        try:
            d = extract_json(text)
        except Exception as e:
            print(f"JSON não veio limpo ({str(e)[:100]}); acionando o passo de reparo...")
            try:
                d = repair_to_json(client, text)
            except Exception as e2:
                print(f"Reparo falhou: {str(e2)[:100]}")
                d = None
        if d and mode in ("main", "market"):
            limpar_painel(d)
            preparar_movers(d)
        if dados_validos(d, mode):
            data = d
            break
        print(f"Tentativa {tentativa + 1} incompleta para o modo '{mode}'; nova tentativa...")

    if not dados_validos(data, mode):
        sys.exit(f"Não consegui gerar dados completos ({mode}) após 4 tentativas. Página anterior mantida.")

    hora = hoje.strftime("%H:%M")

    # Modos parciais: atualizam só os blocos indicados no index + snapshot de hoje.
    if mode == "market":
        print(f"Modo market ({hora}): Painel de Mercado + Destaques B3.")
        substituir_blocos(hoje, ["MERCADO", "DESTAQUES"], template, data, hora)
        return
    if mode == "agenda":
        print(f"Modo agenda ({hora}): Agenda da Semana.")
        substituir_blocos(hoje, ["AGENDA"], template, data, hora)
        return

    # mode == main: página completa
    # Rolagem: se saiu IPCA mensal novo ou nova decisão do Copom, adiciona e descarta o mais antigo.
    if hoje.day == 13:
        atualizar_ipca(client)
    if _copom_vencido(hoje):
        atualizar_copom(client)

    if hoje.weekday() == 1:  # terca: atualiza o Boletim Focus (BC divulga na segunda)
        try:
            atualizar_focus(client, hoje)
        except Exception as e:
            print(f"Focus (terca) nao atualizado: {str(e)[:140]}")

    out = montar_pagina(template, data, hora)

    if "{{" in out:
        sys.exit("ERRO: sobraram marcadores não preenchidos no template.")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"OK: {OUTPUT_PATH} gerado para {data['date']}.")

    # Guarda a edição do dia para o histórico (dropdown "Histórico" na página).
    arquivar(out, hoje)


if __name__ == "__main__":
    main()
