# -*- coding: utf-8 -*-
"""Renderiza os painéis dinâmicos (Focus, Copom, IPCA, Pesquisas) a partir dos
arquivos em dados/*.json e pesquisas.json. Usado tanto pelo gerador quanto pela
atualização pontual das 9:30. Mantém o mesmo HTML/estilo do template."""
import os, json, html

DADOS_DIR = "dados"
ARROW = {"up": "▲", "dn": "▼", "eq": "■"}


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def load_focus():
    return _load(os.path.join(DADOS_DIR, "focus.json"),
                 {"atualizado": "", "anos": ["", "", ""], "linhas": []})


def load_copom():
    return _load(os.path.join(DADOS_DIR, "copom.json"), {"proxima": "", "reunioes": []})


def load_ipca():
    return _load(os.path.join(DADOS_DIR, "ipca.json"), {"acum12m": "", "meses": []})


def load_pesquisas():
    return _load("pesquisas.json", {"cenarios": []})


def _e(s):
    return html.escape(str(s), quote=True)


# ---------- Boletim Focus (barra lateral) ----------
def render_focus_block(focus):
    anos = (focus.get("anos") or ["", "", ""])[:3]
    while len(anos) < 3:
        anos.append("")
    head = "".join(f"<span>{_e(a)}</span>" for a in anos)
    rows = []
    for ln in focus.get("linhas", []):
        vals = ln.get("vals", [])[:3]
        vhtml = ""
        for v in vals:
            arw = ARROW.get(v.get("t", "eq"), "■")
            vhtml += f'<span>{_e(v.get("v",""))}<i class="{_e(v.get("t","eq"))}">{arw}</i></span>'
        while vhtml.count("<span>") < 3:
            vhtml += '<span>—</span>'
        rows.append(
            f'        <div class="foc-row"><span class="foc-lbl">{_e(ln.get("lbl",""))} '
            f'<em>{_e(ln.get("sub",""))}</em></span>{vhtml}</div>'
        )
    upd = _e(focus.get("atualizado", ""))
    return (
        "<!--FOCUS:START-->\n"
        f'      <div class="sec-title sub">Boletim Focus <span class="foc-upd">{upd}</span></div>\n'
        '      <div class="focus">\n'
        f'        <div class="foc-head"><span>Projeção do mercado</span>{head}</div>\n'
        + "\n".join(rows) + "\n"
        '        <div class="foc-foot">▲▼ = variação vs. semana anterior · fonte: Banco Central.</div>\n'
        '      </div>\n'
        "<!--FOCUS:END-->"
    )


# ---------- Modal Copom (Selic) ----------
def render_copom_modal(copom):
    rows = []
    for r in copom.get("reunioes", [])[:4]:
        tipo = r.get("tipo", "hold")
        cls = {"up": "up", "down": "dn", "dn": "dn", "hold": "hold"}.get(tipo, "hold")
        rows.append(
            f'      <div class="dtr"><span>{_e(r.get("data",""))}</span>'
            f'<span class="{cls}">{_e(r.get("decisao",""))}</span>'
            f'<span>{_e(r.get("selic",""))}</span></div>'
        )
    return (
        '<div class="dov" id="copomOv" aria-hidden="true">\n'
        '  <div class="dmodal" role="dialog" aria-label="Histórico do Copom">\n'
        '    <button class="dclose" data-close aria-label="Fechar">&times;</button>\n'
        '    <div class="dhead"><div class="dtag">Selic &middot; Copom</div><h3>Últimas decisões</h3></div>\n'
        f'    <div class="dnext"><span>Próxima reunião</span><b>{_e(copom.get("proxima",""))}</b></div>\n'
        '    <div class="dtable">\n'
        '      <div class="dth"><span>Reunião</span><span>Decisão</span><span>Selic</span></div>\n'
        + "\n".join(rows) + "\n"
        '    </div>\n'
        '    <div class="dfoot">pb = pontos-base. Fonte: Banco Central (Copom).</div>\n'
        '  </div>\n'
        '</div>'
    )


# ---------- Modal IPCA ----------
def render_ipca_modal(ipca):
    rows = []
    for m in ipca.get("meses", [])[:12]:
        cls = "dn" if m.get("tipo") == "dn" else ""
        rows.append(
            f'      <div class="dtr"><span>{_e(m.get("mes",""))}</span>'
            f'<span class="{cls}">{_e(m.get("no_mes",""))}</span>'
            f'<span>{_e(m.get("acum",""))}</span></div>'
        )
    return (
        '<div class="dov" id="ipcaOv" aria-hidden="true">\n'
        '  <div class="dmodal" role="dialog" aria-label="IPCA últimos 12 meses">\n'
        '    <button class="dclose" data-close aria-label="Fechar">&times;</button>\n'
        '    <div class="dhead"><div class="dtag">IPCA &middot; IBGE</div><h3>Últimos 12 meses</h3></div>\n'
        f'    <div class="dnext"><span>Acumulado 12 meses</span><b>{_e(ipca.get("acum12m",""))}</b></div>\n'
        '    <div class="dtable ipca">\n'
        '      <div class="dth"><span>Mês</span><span>No mês</span><span>Acum. 12m</span></div>\n'
        + "\n".join(rows) + "\n"
        '    </div>\n'
        '    <div class="dfoot">Fonte: IBGE.</div>\n'
        '  </div>\n'
        '</div>'
    )


# ---------- Painel de Pesquisas (coluna principal) ----------
def render_polls(pesquisas):
    cens = pesquisas.get("cenarios", [])
    if not cens:
        return ""  # painel oculto quando não há pesquisa curada
    blocks = []
    for c in cens:
        linhas = []
        for it in c.get("itens", []):
            sec = " sec" if it.get("sec") else ""
            try:
                w = float(str(it.get("pct", "0")).replace("%", "").replace(",", "."))
            except Exception:
                w = 0
            linhas.append(
                f'        <div class="poll-row{sec}"><span class="poll-nm">{_e(it.get("nome",""))}</span>'
                f'<div class="poll-bar"><span style="width:{w:.0f}%"></span></div>'
                f'<span class="poll-pct">{_e(it.get("pct",""))}</span></div>'
            )
        blocks.append(
            '      <div class="poll-wrap">\n'
            '        <div class="poll-head">\n'
            f'          <div class="poll-scn">{_e(c.get("cenario",""))}</div>\n'
            f'          <div class="poll-meta">{_e(c.get("meta",""))}</div>\n'
            '        </div>\n'
            + "\n".join(linhas) + "\n"
            + (f'        <div class="poll-foot">{_e(c.get("nota",""))}</div>\n' if c.get("nota") else "")
            + '      </div>'
        )
    return (
        '      <div class="sec-title">Pesquisas Eleitorais <span class="poll-badge">Eleições 2026</span></div>\n'
        + "\n".join(blocks) + "\n"
    )


# ---------- CSS e JS (injetados uma vez) ----------
def css_block():
    return r"""
/* ===== Painéis dinâmicos (Pesquisas / Focus / modais) ===== */
.poll-badge{font-family:'Poppins';font-weight:600;font-size:9px;letter-spacing:.5px;color:#141414;background:var(--gold);padding:3px 9px;border-radius:20px;margin-left:auto;text-transform:none}
.poll-wrap{background:var(--ink2);border:1px solid rgba(255,255,255,.07);border-left:3px solid var(--gold);border-radius:0 14px 14px 0;padding:16px 18px 14px;margin-bottom:16px}
.poll-head{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:6px;margin-bottom:14px}
.poll-scn{font-family:'Poppins';font-weight:700;font-size:14px;color:var(--white)}
.poll-meta{font-size:11px;color:var(--muted)}
.poll-row{display:grid;grid-template-columns:130px 1fr 44px;gap:12px;align-items:center;margin:10px 0}
.poll-nm{font-family:'Poppins';font-size:12.5px;font-weight:600}
.poll-bar{height:13px;background:rgba(255,255,255,.06);border-radius:7px;overflow:hidden}
.poll-bar span{display:block;height:100%;background:linear-gradient(90deg,var(--acc),#2fae94);border-radius:7px}
.poll-pct{font-family:'Poppins';font-weight:700;font-size:13px;text-align:right;font-variant-numeric:tabular-nums}
.poll-row.sec .poll-bar span{background:rgba(255,255,255,.20)}
.poll-row.sec .poll-nm,.poll-row.sec .poll-pct{color:var(--muted)}
.poll-foot{margin-top:13px;padding-top:11px;border-top:1px solid rgba(255,255,255,.07);font-size:10.5px;color:var(--muted)}
.poll-wrap+.poll-wrap{margin-top:-4px}
.foc-upd{font-family:'Barlow';font-weight:500;font-size:9px;letter-spacing:.3px;color:var(--muted);text-transform:none;background:rgba(255,255,255,.06);padding:3px 8px;border-radius:20px;margin-left:auto}
.focus{background:var(--ink2);border:1px solid rgba(255,255,255,.07);border-radius:13px;padding:4px 2px;margin-bottom:12px}
.foc-head{display:grid;grid-template-columns:1fr 46px 46px 46px;gap:3px;padding:10px 12px 6px;font-family:'Poppins';font-size:9.5px;font-weight:600;letter-spacing:.3px;text-transform:uppercase;color:var(--muted)}
.foc-head span:not(:first-child){text-align:right}
.foc-row{display:grid;grid-template-columns:1fr 46px 46px 46px;gap:3px;align-items:center;padding:9px 12px;border-top:1px solid rgba(255,255,255,.06);font-family:'Poppins';font-size:12px;font-weight:700;font-variant-numeric:tabular-nums}
.foc-row .foc-lbl{font-weight:600;font-size:12.5px}
.foc-row .foc-lbl em{display:block;font-family:'Barlow';font-style:normal;font-weight:400;font-size:10px;color:var(--muted);margin-top:1px}
.foc-row span:not(:first-child){text-align:right}
.foc-row i{font-style:normal;font-size:8px;margin-left:3px}
.foc-row i.up{color:#e0a94a}.foc-row i.dn{color:#6fb2ff}.foc-row i.eq{color:var(--muted);font-size:7px}
.foc-foot{padding:9px 12px 7px;font-size:9.5px;color:var(--muted);line-height:1.4}
.mbox.clk{cursor:pointer;transition:border-color .15s,transform .08s}
.mbox.clk:hover{border-color:rgba(201,169,74,.5)}
.mbox.clk:active{transform:scale(.985)}
.mbox .tap{font-size:9px;color:var(--gold);opacity:.9;margin-top:6px;letter-spacing:.2px;font-weight:600}
.dov{position:fixed;inset:0;background:rgba(6,6,10,.55);backdrop-filter:blur(2px);display:none;align-items:center;justify-content:center;z-index:120;padding:20px}
.dov.on{display:flex}
.dmodal{background:var(--ink2);border:1px solid rgba(255,255,255,.1);border-top:3px solid var(--gold);border-radius:16px;max-width:440px;width:100%;max-height:84vh;overflow:auto;padding:20px 22px 16px;position:relative;box-shadow:0 24px 64px rgba(0,0,0,.55);animation:dpop .18s ease}
@keyframes dpop{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.dclose{position:absolute;top:10px;right:14px;background:transparent;border:none;color:var(--muted);font-size:24px;line-height:1;cursor:pointer}
.dtag{font-family:'Poppins';font-size:10px;font-weight:600;letter-spacing:1px;color:var(--gold);text-transform:uppercase}
.dhead h3{font-family:'Poppins';font-weight:700;font-size:18px;margin:3px 0 14px}
.dnext{display:flex;justify-content:space-between;align-items:center;background:linear-gradient(180deg,rgba(201,169,74,.14),rgba(201,169,74,.04));border:1px solid rgba(201,169,74,.4);border-radius:11px;padding:11px 14px;margin-bottom:14px}
.dnext span{font-size:10.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.dnext b{font-family:'Poppins';font-size:15px;color:var(--gold)}
.dtable{border:1px solid rgba(255,255,255,.07);border-radius:11px;overflow:hidden}
.dth{display:grid;grid-template-columns:1.15fr 1fr .82fr;gap:6px;padding:9px 14px;font-family:'Poppins';font-size:9.5px;font-weight:600;letter-spacing:.4px;text-transform:uppercase;color:var(--muted);background:rgba(255,255,255,.03)}
.dtr{display:grid;grid-template-columns:1.15fr 1fr .82fr;gap:6px;padding:11px 14px;border-top:1px solid rgba(255,255,255,.06);font-family:'Poppins';font-size:13px;font-weight:600;font-variant-numeric:tabular-nums;align-items:center}
.dth span:not(:first-child),.dtr span:not(:first-child){text-align:right}
.dtr .up{color:#f28b82}.dtr .dn{color:var(--up)}.dtr .hold{color:var(--muted)}
.dtable.ipca .dth,.dtable.ipca .dtr{grid-template-columns:1fr .9fr .9fr}
.dfoot{padding:11px 2px 0;font-size:10px;color:var(--muted)}
"""


def js_block():
    return """<script>
(function(){
  function op(id){var o=document.getElementById(id);if(o){o.classList.add('on');document.body.style.overflow='hidden';}}
  function cl(){document.querySelectorAll('.dov.on').forEach(function(o){o.classList.remove('on');});document.body.style.overflow='';}
  var s=document.getElementById('cardSelic');if(s)s.addEventListener('click',function(){op('copomOv');});
  var i=document.getElementById('cardIpca');if(i)i.addEventListener('click',function(){op('ipcaOv');});
  document.querySelectorAll('.dov').forEach(function(o){o.addEventListener('click',function(ev){if(ev.target===o)cl();});});
  document.querySelectorAll('[data-close]').forEach(function(b){b.addEventListener('click',cl);});
  document.addEventListener('keydown',function(ev){if(ev.key==='Escape')cl();});
})();
</script>"""
