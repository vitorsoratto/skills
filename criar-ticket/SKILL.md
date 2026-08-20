---
name: criar-ticket
description: Entrevista objetiva que transforma uma solicitação de suporte em um ticket claro, pronto para copiar no ClickUp.
disable-model-invocation: true
---

Run a `/criar-ticket` session.

## Purpose

Use the existing grilling flow to clarify a feature or bug without changing its decision-making sequence: ask in rounds, where each round contains only questions whose prerequisites are already settled. Do not write files or create ClickUp tickets.

The result is a concise, copy-ready ticket for technical support to create in ClickUp.

## Conversation rules

- Before asking, use the conversation, attached material, repository, and available tools to resolve what can be known.
- Ask only for information necessary to define the reported feature or bug. Do not branch into implementation, adjacent products, or hypothetical scope.
- Ask at most three questions per round. Each question MUST be short, concrete, and use plain language suitable for technical support staff who are not specialists.
- Prefer a direct choice or a request for a single fact. Avoid compound, abstract, or deep technical questions.
- Do not repeat answered questions or ask for information already available from the investigation.
- When an important answer cannot be found, ask one clear question for the responsible technical person instead of guessing.
- Stop once the ticket can state the requested outcome and objective acceptance criteria. Do not keep grilling for completeness alone.

## Final output

Return only this ticket structure in Portuguese:

```text
Título
[ação ou problema em uma frase]

Contexto
[o que acontece hoje, quem é afetado e o limite confirmado do pedido]

Resultado esperado
[comportamento observável depois da atividade]

Critérios de aceite
- [critério objetivo e verificável]
- [critério objetivo e verificável]

Pergunta para o responsável técnico
[incluir somente se alguma informação essencial continuar pendente]
```
