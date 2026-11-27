# Telas e protótipos documentais

Abra [`telas.html`](telas.html) no navegador. São wireframes estáticos baseados nas rotas reais,
sem login, dados pessoais ou conexão à API. Documentam hierarquia e fluxos; não substituem o
frontend executável nem constituem prova de validação visual da implementação final.

| Tela | Código | Fluxo |
|---|---|---|
| Totem | `frontend/app/totem` | Categoria → emissão → código |
| Painel | `frontend/app/panel` | Chamada atual → guichê → últimas cinco; áudio após interação |
| Atendimento | `frontend/app/(attendant)` | Guichê → chamar → iniciar → finalizar ou repetir/ausência |
| Gestão | `frontend/app/(manager)` | Indicadores, relatórios, usuários, guichês e auditoria |

A previsão de próximas senhas é uma exceção à página 5 do PDF, aceita pelo solicitante;
não há confirmação documental de autorização do professor para essa exceção.
