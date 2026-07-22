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
Modelo configurável via CLAUDE_MODEL (padrão: claude-sonnet-5).
"""

import os
import re
import sys
import json
import html
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
TEMPLATE_PATH = "morning-call.template.html"
OUTPUT_PATH = "morning-call.html"

TZ = ZoneInfo("America/Sao_Paulo")
DIAS = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
        "Sexta-feira", "Sábado", "Domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def data_extenso(dt):
    return f"{DIAS[dt.weekday()]}, {dt.day} de {MESES[dt.month - 1]} de {dt.year}"


def build_prompt(hoje):
    return f"""Hoje é {data_extenso(hoje)} (horário de Brasília), por volta das 6h da manhã.
Você vai montar o "Morning Call" diário de mercado da assessoria de patrimônio de Gabriel Barbosa.

Como é de manhã cedo, os dados de mercado devem ser do FECHAMENTO DO ÚLTIMO PREGÃO
(o dia útil anterior na B3 e em Wall Street). Se hoje for segunda-feira, o último pregão foi na sexta.

PESQUISE NA WEB (use a ferramenta de busca) e confirme cada dado numa fonte confiável
(Money Times, InfoMoney, B3, Investing, CNBC, Yahoo Finance). NUNCA invente números ou links.

Colete:
- Painel (fechamento do último pregão): Ibovespa (pontos e variação %), Dólar USD/BRL (cotação e %),
  Juros Futuros/DI (direção da curva; cite a Selic vigente), Petróleo Brent, S&P 500, Nasdaq, Dow Jones, Stoxx 600.
- As 5 maiores altas e as maiores baixas do Ibovespa (ticker, nome curto, variação %). Se quase tudo subiu/caiu,
  liste o que houver e explique numa nota.
- 5 notícias de "Mercado & Economia" e 5 de "Política & Internacional", cada uma com um bom RESUMO autoral
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
    {{"lbl": "Juros Futuros (DI)", "val": "Curva ▼", "chg": "Selic 14,25%", "bar": "acc", "cls": "up"}},
    {{"lbl": "Brent (set)", "val": "US$ 76,01", "chg": "▼ −0,38%", "bar": "down", "cls": "down"}},
    {{"lbl": "S&P 500", "val": "7.575,39", "chg": "▲ +0,42%", "bar": "up", "cls": "up"}},
    {{"lbl": "Nasdaq", "val": "26.281,11", "chg": "▲ +0,29%", "bar": "up", "cls": "up"}},
    {{"lbl": "Dow Jones", "val": "52.637,01", "chg": "▲ +0,29%", "bar": "up", "cls": "up"}},
    {{"lbl": "Stoxx 600", "val": "641,10", "chg": "▲ +0,04%", "bar": "up", "cls": "up"}}
  ],
  "altas": [{{"tk": "CMIN3", "nm": "CSN Mineração", "pc": "+8,28%"}}],
  "baixas": [{{"tk": "PRIO3", "nm": "PRIO", "pc": "−0,29%"}}],
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
Retorne SOMENTE o bloco <json>...</json>, nada além disso."""


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


def esc(s):
    return html.escape(str(s), quote=True)


def render_panel(items):
    out = []
    for it in items:
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
        out.append(
            f'        <div class="row"><div><div class="tk">{esc(it["tk"])}</div>'
            f'<div class="nm">{esc(it["nm"])}</div></div>'
            f'<div class="pc {cls}">{esc(it["pc"])}</div></div>'
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


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ERRO: ANTHROPIC_API_KEY não definida.")

    hoje = datetime.now(TZ)
    # dias úteis apenas (segurança extra caso rode fora do cron)
    if hoje.weekday() >= 5:
        print("Fim de semana — nada a gerar.")
        return

    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        template = f.read()

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 10}],
        messages=[{"role": "user", "content": build_prompt(hoje)}],
    )

    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    print(f"Resposta do modelo: {len(text)} caracteres de texto.")
    data = extract_json(text)

    # validações mínimas
    assert data.get("painel") and len(data["painel"]) >= 6, "painel incompleto"
    assert data.get("noticias_eco") and data.get("noticias_pol"), "notícias faltando"

    summary_html = "\n".join(f"    <p>{p}</p>" for p in data["resumo"])

    out = template
    out = out.replace("{{DATE}}", esc(data["date"]))
    out = out.replace("{{SUBTITLE}}", esc(data.get("subtitle", "")))
    out = out.replace("{{SUMMARY}}", summary_html)
    out = out.replace("{{NEWS_ECO}}", render_news(data["noticias_eco"]))
    out = out.replace("{{NEWS_POL}}", render_news(data["noticias_pol"]))
    out = out.replace("{{PANEL}}", render_panel(data["painel"]))
    out = out.replace("{{GAINS}}", render_rows(data.get("altas", []), "up"))
    out = out.replace("{{LOSSES}}", render_losses(data.get("baixas", []), data.get("baixas_nota", "")))
    out = out.replace("{{AGENDA}}", render_agenda(data.get("agenda", [])))
    out = out.replace("{{FOOTER_DATE}}", esc(data.get("footer_date", data["date"])))

    if "{{" in out:
        sys.exit("ERRO: sobraram marcadores não preenchidos no template.")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"OK: {OUTPUT_PATH} gerado para {data['date']}.")


if __name__ == "__main__":
    main()
