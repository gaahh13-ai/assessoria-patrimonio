# Como adicionar uma nova pesquisa ao painel

O painel de "Pesquisas Eleitorais" do site é alimentado pelo arquivo **`pesquisas.json`**.
Cada instituto tem três visões — **1º turno**, **2º turno** e **rejeição** — e cada visão é um
gráfico de **linha (% × meses)**. Adicionar uma nova pesquisa = **acrescentar um novo mês (vértice)**
no fim de cada série.

## Modelo para me mandar (copie, preencha e envie)

Quando sair uma nova onda, é só me mandar algo assim que eu atualizo o `pesquisas.json`:

```
Instituto: Genial/Quaest   (ou BTG/Nexus)
Mês/rótulo: Ago/26
Campo (data): 07 a 10 de agosto de 2026

1º turno:
  Lula: 41
  Flávio Bolsonaro: 30
  Ronaldo Caiado: 5
  (demais nomes que quiser acompanhar)

2º turno (Lula × Flávio):
  Lula: 46
  Flávio Bolsonaro: 38
  (Branco/Nulo e Indecisos, se tiver)

Rejeição:
  Flávio Bolsonaro: 55
  Lula: 49
  Ronaldo Caiado: 33
  Romeu Zema: 30
```

Só precisa mandar os nomes que já acompanhamos (hoje mostramos 3–4 principais por gráfico).
Se faltar algum número numa onda, tudo bem — a série só não ganha ponto naquele nome.

## Estrutura do arquivo (referência técnica)

```json
{
  "institutos": [
    {
      "id": "quaest",
      "nome": "Genial/Quaest",
      "campo": "jul/26",
      "primeiro": {
        "nota": "1º turno",
        "meses": ["Fev/26", "Mar/26", "Jul/26"],
        "series": [
          {"nome": "Lula (PT)", "tipo": "lula", "vals": [41, 39, 40]},
          {"nome": "Flávio Bolsonaro (PL)", "tipo": "flavio", "vals": [32, 32, 28]}
        ]
      },
      "segundo":  { "nota": "...", "meses": [...], "series": [...] },
      "rejeicao": { "nota": "...", "meses": [...], "series": [...] }
    }
  ]
}
```

Regras ao adicionar um mês:
- Acrescente o novo rótulo em **`meses`** (ex.: `"Ago/26"`).
- Acrescente o novo valor no fim de **`vals`** de cada série (mesma ordem dos meses).
- `meses` e cada `vals` devem ter **o mesmo tamanho**.
- Atualize o campo **`campo`** do instituto para a onda mais recente (ex.: `"ago/26"`).

## Cores por nome (campo `tipo`)

Cada série tem um `tipo` que define a cor da linha (a cor segue a pessoa em todas as visões):

| tipo      | quem                  | cor        |
|-----------|-----------------------|------------|
| `lula`    | Lula                  | vermelho   |
| `flavio`  | Flávio Bolsonaro      | azul       |
| `caiado`  | Ronaldo Caiado        | âmbar      |
| `zema`    | Romeu Zema            | roxo       |
| `renan`   | Renan Santos          | verde      |
| `daciolo` | Cabo Daciolo          | rosa       |
| `branco`  | Branco/Nulo           | cinza claro|
| `indeciso`| Indecisos             | cinza      |

Para um nome novo que ainda não tem cor, me avisa que eu escolho uma e registro aqui.
