# Decisoes de Arquitetura (ADR)

Registro das decisoes importantes tomadas no projeto e o **porque** de
cada uma. O objetivo e preservar o raciocinio para quem (humano ou IA)
retomar o projeto sem o contexto da conversa original.

Formato: cada decisao tem Contexto (o problema), Decisao (o que foi
escolhido) e Consequencias (o que isso implica, inclusive trade-offs).

Data de origem: 2026-07-07.

---

## ADR-01: Motor de classificacao trocavel (padrao de contrato)

**Contexto.** A classificacao depende de um modelo de visao. Modelos
evoluem rapido e podemos querer trocar o CLIP por outro (API de visao,
modelo novo) sem reescrever o app.

**Decisao.** Definir a interface abstrata `TaggerEngine`
(`core/engines/base.py`). Todo motor a implementa; o resto do app **so**
conhece esse contrato. A escolha do motor concreto acontece no
`registry.py`, por nome, vindo da config ou da UI.

**Consequencias.**
- Trocar de motor = mudar uma linha (`DEFAULT_ENGINE`) ou o dropdown.
- Motor novo = um arquivo em `engines/` + uma linha no `registry`.
- Exige disciplina: nenhuma parte do app pode importar `CLIPEngine`
  diretamente -- sempre via `get_engine()`.
- Permite um `FakeEngine` para testar toda a logica sem carregar modelo.

---

## ADR-02: Scores normalizados em 0.0-1.0 no contrato

**Contexto.** O usuario calibra um "limiar" de confianca. Se cada motor
devolvesse scores em escalas diferentes, o limiar calibrado para o CLIP
nao valeria para outro motor.

**Decisao.** O contrato obriga todo motor a devolver score em 0.0-1.0.
No CLIP, a similaridade de cosseno (-1..1) e mapeada para 0..1.

**Consequencias.**
- O limiar e portavel entre motores.
- Cada implementacao nova e responsavel por normalizar sua saida.
- O 0.0-1.0 do CLIP nao e uma "probabilidade" real, e uma similaridade
  reescalada -- bom para ordenar/cortar, nao para interpretar como %.

---

## ADR-03: CLIP local como primeiro motor (offline)

**Contexto.** Precisavamos de um motor que aceitasse tags livres definidas
pelo usuario, sem treino, e de preferencia sem custo/nuvem.

**Decisao.** Usar CLIP (`open_clip_torch`, variante `ViT-B-32`/`openai`)
rodando local. Tags viram texto; comparamos embedding da imagem com o de
cada tag.

**Consequencias.**
- Roda offline, de graca, com tags arbitrarias (zero-shot).
- Custo: baixar o modelo (~centenas de MB) e ter torch instalado.
- `ViT-B-32` e o ponto de partida (rapido); da para trocar por variante
  maior/mais precisa depois -- e so outra config do mesmo motor.

---

## ADR-04: Multi-tag -> copiar (nao mover) para as pastas

**Contexto.** Uma foto pode pertencer a varias tags (ex.: pessoas +
comida). Mover para uma unica pasta seria incompativel com multi-tag.

**Decisao.** Organizar por **copia**: a foto aparece na pasta de cada tag
aplicada; o original nunca e movido nem apagado. Modo `hardlink`
opcional para nao duplicar bytes (so no mesmo volume).

**Consequencias.**
- Multi-tag funciona naturalmente.
- Copia gasta disco; hardlink resolve mas so dentro do mesmo disco (cai
  para copia entre volumes, tratado no `organizer.py`).
- Operacao idempotente: destino ja existente nao e recopiado.

---

## ADR-05: Keywords com merge -- NUNCA sobrescrever (requisito central)

**Contexto.** Fotos ja podem ter tags/metadados de organizacoes
anteriores. O usuario exigiu que essas nao sejam perdidas.

**Decisao.** `metadata.py` sempre le as keywords atuais, faz uniao com as
novas e regrava. Nunca remove. Grava em `XMP-dc:Subject` e
`IPTC:Keywords` (campos reconhecidos por Lightroom, digiKam, Explorer).
Usa ExifTool por baixo, que preserva o resto do arquivo. Ha ainda o modo
opcional `skip_already_tagged` (pular fotos que ja tem keywords).

**Consequencias.**
- Requisito central garantido: metadados existentes preservados.
- Depende do binario ExifTool instalado no sistema (nao e pip puro).
- Se a uniao nao acrescenta nada, o arquivo nao e reescrito (evita
  regravacao a toa).

---

## ADR-06: Rotulos PT-BR mapeados para tags internas em ingles

**Contexto.** O CLIP compara muito melhor com texto em ingles, mas o
usuario e a interface sao em portugues.

**Decisao.** `tags.json` mapeia rotulo PT-BR -> tag interna em ingles. O
motor recebe o ingles; a UI, os nomes de pasta e as keywords usam o
rotulo PT-BR (via `Config.label_for`).

**Consequencias.**
- Melhor acuracia do CLIP sem expor ingles ao usuario.
- Uma camada de traducao a manter no `tags.json`.
- Alternativa futura: CLIP multilingue dispensaria o mapa (ver ADR em
  aberto).

---

## ADR-07: Logica separada da interface

**Contexto.** Queremos CLI (para validar rapido) e app grafico, sem
duplicar logica.

**Decisao.** Toda a orquestracao vive em `core/pipeline.py`
(classificar, aplicar). `cli.py` e `app.py` (Gradio) sao apenas cascas
que chamam o pipeline.

**Consequencias.**
- Uma unica fonte de verdade para o fluxo.
- Facil adicionar outra interface no futuro.
- O pipeline nao conhece o motor concreto (usa o contrato, ADR-01).

---

## ADR-08: Interface desktop com Gradio + fluxo de revisao

**Contexto.** O usuario quis um app com interface, e ter controle antes
de tocar nos arquivos.

**Decisao.** Gradio (janela local, um comando). Fluxo em 4 passos:
selecionar pasta+tags -> classificar -> revisar sugestoes -> aplicar. A
aplicacao (copia + gravacao) so ocorre apos revisao.

**Consequencias.**
- Rapido de montar, tudo em Python.
- O `app.py` atual e um esqueleto funcional; a edicao tag-a-tag no grid
  ainda sera refinada.

---

## Decisoes em aberto (ainda nao fechadas)

- **RAW/HEIC**: fora do MVP; exigem tratamento especial de metadados.
- **CLIP multilingue**: avaliar variante que entende PT direto e talvez
  aposentar o mapa de rotulos.
- **Edicao no grid da UI**: permitir marcar/desmarcar tags por foto antes
  de aplicar (hoje o corte e so pelo limiar).
- **Backup automatico**: considerar snapshot antes da primeira aplicacao
  real sobre o acervo.

---

## Como manter este arquivo

Ao tomar uma decisao de arquitetura relevante, adicione um novo ADR
(nao reescreva os antigos). Se uma decisao for revertida, adicione um ADR
novo que a substitui e marque o antigo como "Substituido por ADR-XX".
