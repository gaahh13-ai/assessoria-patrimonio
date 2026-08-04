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
    return _load("pesquisas.json", {"institutos": []})


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


# ---------- Painel de Pesquisas (gráficos de linha) ----------
POLL_COR = {"lula": "#e0564f", "flavio": "#4a90e2", "caiado": "#d6a53c",
            "zema": "#9a7fb0", "renan": "#57a785", "daciolo": "#c98bbe",
            "branco": "#cdd2dc", "indeciso": "#82828f", "neutro": "#8a8a96"}


def render_polls(pesquisas):
    insts = pesquisas.get("institutos", [])
    if not insts:
        return ""  # painel oculto enquanto não houver pesquisa curada
    inst0 = insts[0]
    footL = f'Fonte: <strong>{_e(inst0.get("nome",""))}</strong> &middot; intenção de voto (%)'
    data_json = json.dumps({"institutos": insts}, ensure_ascii=False)
    return (
        '      <div class="sec-title">Pesquisas Eleitorais <span class="poll-badge">Eleições 2026</span></div>\n'
        '      <div class="pcard" id="pollCard">\n'
        '        <div class="pctrl">\n'
        '          <div class="pinst">\n'
        '            <div class="pinst-btn" id="instBtn"><span class="dot"></span>'
        f'<span id="instNome">{_e(inst0.get("nome",""))}</span>'
        f'<span class="cv" id="instCampo">{_e(inst0.get("campo",""))}</span><span class="car">▼</span></div>\n'
        '            <div class="pinst-menu hidden" id="instMenu"></div>\n'
        '          </div>\n'
        '          <div class="ptabs" id="pollTabs">\n'
        '            <button class="ptab on" data-v="primeiro">1º turno</button>\n'
        '            <button class="ptab" data-v="segundo">2º turno</button>\n'
        '            <button class="ptab" data-v="rejeicao">Rejeição</button>\n'
        '          </div>\n'
        '        </div>\n'
        '        <div class="phead2"><div class="pscn" id="scnTitle">Intenção de voto &middot; 1º turno</div>'
        '<div class="pmeta" id="scnMeta"></div></div>\n'
        '        <div id="pollView"></div>\n'
        f'        <div class="pfoot"><span id="pollFootL">{footL}</span><span id="pollFootR"></span></div>\n'
        '      </div>\n'
        f'      <script type="application/json" id="pollData">{data_json}</script>\n'
    )


# ---------- CSS e JS (injetados uma vez) ----------
def css_block():
    return r"""
/* ===== Painéis dinâmicos (Pesquisas / Focus / modais) ===== */
.poll-badge{font-family:'Poppins';font-weight:600;font-size:9px;letter-spacing:.5px;color:#141414;background:var(--gold);padding:3px 9px;border-radius:20px;margin-left:auto;text-transform:none}
.pcard{background:var(--ink2);border:1px solid rgba(255,255,255,.07);border-left:3px solid var(--gold);border-radius:0 16px 16px 0;padding:18px 22px 16px;margin-bottom:8px}
.pctrl{display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:6px}
.pinst{position:relative}
.pinst-btn{display:flex;align-items:center;gap:10px;background:var(--ink);border:1px solid rgba(255,255,255,.12);border-radius:10px;padding:9px 14px;cursor:pointer;font-family:'Poppins';font-weight:600;font-size:13px;color:var(--white)}
.pinst-btn .dot{width:9px;height:9px;border-radius:50%;background:var(--gold)}
.pinst-btn .cv{font-family:'Barlow';font-weight:500;font-size:11px;color:var(--muted);margin-left:2px}
.pinst-btn .car{margin-left:6px;color:var(--muted);font-size:10px}
.pinst-menu{position:absolute;top:calc(100% + 6px);left:0;background:var(--ink);border:1px solid rgba(255,255,255,.14);border-radius:10px;padding:5px;min-width:220px;z-index:20;box-shadow:0 12px 30px rgba(0,0,0,.5)}
.pinst-menu.hidden{display:none}
.pinst-opt{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:9px 11px;border-radius:7px;cursor:pointer;font-family:'Poppins';font-weight:600;font-size:12.5px}
.pinst-opt:hover{background:rgba(255,255,255,.06)}
.pinst-opt.on{background:rgba(201,169,74,.14);color:var(--gold)}
.pinst-opt small{font-family:'Barlow';font-weight:500;font-size:10.5px;color:var(--muted)}
.ptabs{display:inline-flex;background:var(--ink);border:1px solid rgba(255,255,255,.10);border-radius:11px;padding:4px;gap:3px}
.ptab{border:0;background:transparent;color:var(--muted);font-family:'Poppins';font-weight:700;font-size:12.5px;padding:8px 16px;border-radius:8px;cursor:pointer;letter-spacing:.2px;transition:all .15s}
.ptab:hover{color:var(--white)}
.ptab.on{background:linear-gradient(180deg,var(--gold),#b8983c);color:#161616;box-shadow:0 3px 10px rgba(201,169,74,.25)}
.phead2{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:6px;margin:14px 0 2px}
.pscn{font-family:'Poppins';font-weight:700;font-size:15px;color:var(--white)}
.pscn small{font-family:'Barlow';font-weight:500;font-size:12px;color:var(--muted);margin-left:6px}
.pmeta{font-size:11px;color:var(--muted)}
.bars{margin-top:12px}
.brow{display:grid;grid-template-columns:168px 1fr 44px;gap:12px;align-items:center;margin:9px 0}
.bnm{font-family:'Poppins';font-size:12.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bnm small{font-family:'Barlow';font-weight:500;color:var(--muted);font-size:10.5px;margin-left:4px}
.btrack{height:15px;background:rgba(255,255,255,.055);border-radius:7px;overflow:hidden}
.bfill{display:block;height:100%;border-radius:7px}
.bpct{font-family:'Poppins';font-weight:700;font-size:13px;text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.brow.sec .bnm,.brow.sec .bpct{color:var(--muted)}
.brow.cmp{grid-template-columns:168px 1fr 60px}
.conf{margin-top:14px}
.conf-main{display:flex;gap:14px;margin-bottom:14px}
.conf-box{flex:1;background:var(--ink);border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:14px 16px}
.conf-box .cn{font-family:'Poppins';font-weight:600;font-size:13px;display:flex;align-items:center;gap:8px}
.conf-box .cn i{width:11px;height:11px;border-radius:50%}
.conf-box .cp{font-family:'Poppins';font-weight:800;font-size:30px;margin-top:6px;font-variant-numeric:tabular-nums}
.conf-sub{font-family:'Poppins';font-size:11px;font-weight:600;letter-spacing:.4px;text-transform:uppercase;color:var(--muted);margin:4px 0 8px}
.pfoot{margin-top:14px;padding-top:11px;border-top:1px solid rgba(255,255,255,.07);font-size:10.5px;color:var(--muted);display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}
.pcard svg{width:100%;height:auto;display:block;margin-top:6px}
.lbl-x{font-family:'Barlow';font-size:11px;fill:var(--muted);font-weight:500}
.lbl-y{font-family:'Barlow';font-size:10.5px;fill:#6a6a76}
.val{font-family:'Poppins';font-size:12px;font-weight:700;font-variant-numeric:tabular-nums}
.endlbl{font-family:'Poppins';font-size:12px;font-weight:700}
.plegend{display:flex;gap:16px;flex-wrap:wrap;margin:10px 0 0}
.lg{display:flex;align-items:center;gap:7px;font-size:12px;font-weight:600;font-family:'Poppins'}
.lg i{width:12px;height:12px;border-radius:4px;display:inline-block}
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
(function(){
  var el=document.getElementById('pollData'); if(!el) return;
  var DADOS; try{ DADOS=JSON.parse(el.textContent); }catch(e){ return; }
  var INST=DADOS.institutos||[]; if(!INST.length) return;
  var COR={lula:"#e0564f",flavio:"#4a90e2",caiado:"#d6a53c",zema:"#9a7fb0",renan:"#57a785",daciolo:"#c98bbe",branco:"#cdd2dc",indeciso:"#82828f",neutro:"#8a8a96"};
  var st={inst:0,view:"primeiro"};
  function line(seg){
    var x0=46,x1=740,mT=24,mB=360,n=seg.meses.length;
    var mx=0; seg.series.forEach(function(se){se.vals.forEach(function(v){if(v>mx)mx=v;});});
    var yMax=Math.max(10,Math.ceil((mx+4)/10)*10);
    var xAt=function(i){return n===1?(x0+x1)/2:x0+i*(x1-x0)/(n-1);};
    var yAt=function(v){return mB-(v/yMax)*(mB-mT);};
    var s="";
    for(var g=0;g<=yMax;g+=10){var yy=yAt(g);
      s+='<line x1="'+x0+'" y1="'+yy+'" x2="'+x1+'" y2="'+yy+'" stroke="rgba(255,255,255,.06)"/>';
      s+='<text class="lbl-y" x="'+(x0-10)+'" y="'+(yy+3.5)+'" text-anchor="end">'+g+'</text>';}
    seg.meses.forEach(function(m,i){s+='<text class="lbl-x" x="'+xAt(i)+'" y="'+(mB+22)+'" text-anchor="middle">'+m+'</text>';});
    seg.series.forEach(function(se){ if(n>1){var pts=se.vals.map(function(v,i){return xAt(i)+','+yAt(v);}).join(' ');
      s+='<polyline points="'+pts+'" fill="none" stroke="'+COR[se.tipo]+'" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>';}});
    var lu=null,fl=null; seg.series.forEach(function(se){if(se.tipo==='lula')lu=se; if(se.tipo==='flavio')fl=se;});
    seg.series.forEach(function(se){
      var proto=(se.tipo==='lula'||se.tipo==='flavio');
      se.vals.forEach(function(v,i){
        var x=xAt(i),y=yAt(v);
        s+='<circle cx="'+x+'" cy="'+y+'" r="4.4" fill="#1c1c22"/><circle cx="'+x+'" cy="'+y+'" r="3" fill="'+COR[se.tipo]+'"/>';
        var show=false, off=-11;
        if(proto){ show=true;
          if(se.tipo==='lula'&&fl) off=(v>=fl.vals[i]?-11:15);
          else if(se.tipo==='flavio'&&lu) off=(v>lu.vals[i]?-11:15);
        } else { show=(i===0||i===se.vals.length-1); off=-11; }
        if(show) s+='<text class="val" x="'+x+'" y="'+(y+off)+'" text-anchor="middle" fill="'+COR[se.tipo]+'">'+v+'</text>';
      });
      var li=se.vals.length-1, ex=(n===1?(x0+x1)/2:x1), ly=yAt(se.vals[li]);
      s+='<text class="endlbl" x="'+(ex+10)+'" y="'+(ly+4)+'" fill="'+COR[se.tipo]+'">'+se.nome.replace(/ \\(.*\\)/,'')+'</text>';
    });
    var leg=seg.series.map(function(se){return '<span class="lg"><i style="background:'+COR[se.tipo]+'"></i>'+se.nome+'</span>';}).join('');
    return '<svg viewBox="0 0 900 400" role="img" aria-label="Evolucao da pesquisa">'+s+'</svg><div class="plegend">'+leg+'</div>';
  }
  function render(){
    var it=INST[st.inst];
    document.getElementById('instNome').textContent=it.nome;
    document.getElementById('instCampo').textContent=it.campo;
    document.querySelectorAll('#pollTabs .ptab').forEach(function(t){t.classList.toggle('on',t.getAttribute('data-v')===st.view);});
    var titles={primeiro:"Intenção de voto \\u00b7 1º turno",segundo:"Intenção de voto \\u00b7 2º turno",rejeicao:"Rejeição \\u00b7 não votaria de jeito nenhum"};
    document.getElementById('scnTitle').textContent=titles[st.view];
    var seg=it[st.view];
    document.getElementById('scnMeta').textContent=(seg.nota||"")+" \\u00b7 "+it.nome;
    document.getElementById('pollView').innerHTML=line(seg);
    document.getElementById('pollFootL').innerHTML='Fonte: <strong style="color:var(--white)">'+it.nome+'</strong> \\u00b7 intenção de voto (%)';
    document.getElementById('pollFootR').textContent=seg.meses.length+' pesquisa(s) \\u00b7 série mensal';
    var menu=document.getElementById('instMenu');
    menu.innerHTML=INST.map(function(x,i){return '<div class="pinst-opt'+(i===st.inst?' on':'')+'" data-i="'+i+'">'+x.nome+'<small>'+x.campo+'</small></div>';}).join('');
    menu.querySelectorAll('.pinst-opt').forEach(function(o){o.addEventListener('click',function(){st.inst=+o.getAttribute('data-i');menu.classList.add('hidden');render();});});
  }
  document.getElementById('pollTabs').addEventListener('click',function(e){var b=e.target.closest('.ptab');if(!b)return;st.view=b.getAttribute('data-v');render();});
  var ib=document.getElementById('instBtn');
  ib.addEventListener('click',function(e){e.stopPropagation();document.getElementById('instMenu').classList.toggle('hidden');});
  document.addEventListener('click',function(e){var m=document.getElementById('instMenu');if(m&&!m.classList.contains('hidden')&&!e.target.closest('.pinst'))m.classList.add('hidden');});
  render();
})();
</script>"""
