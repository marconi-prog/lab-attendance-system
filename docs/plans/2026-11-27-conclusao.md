# Conclusão acadêmica — plano de implementação

**Objetivo:** alinhar o projeto ao PDF da atividade (10 páginas) e publicar via dev → main.

**Arquitetura:** preservar Flask/MySQL e Expo Web. ADMIN mantém compatibilidade de API e passa
a acumular as operações de atendimento, limitadas aos guichês autorizados. Um índice único sobre
um campo calculado limita a um gestor ativo; migration recusa dados conflitantes sem alterá-los.

**Restrições:** preservar contas, licença, autoria e alterações existentes; não mover tag publicada;
nome, Expo e previsões no painel aceitos pelo solicitante. Datas sob responsabilidade do solicitante.
Na preparação inicial o PDF principal não estava disponível. Posteriormente foram recebidos e
lidos a especificação e o edital: emissão/chamadas 07h–17h, simulação sintética de tempos/ausências,
campos de atendimento em branco para ausentes, casos de uso, API v1 e backup/restauração.
Validação complementar em `docs/validacao-especificacao.md`; não forçar descarte no atendimento real.

- [x] Confirmar equipe e colaboradores por API autenticada; registrar limites administrativos.
- [x] Implementar gestor/atendente e unicidade com testes de regressão e migration não destrutiva.
- [x] Atualizar Python para 3.14, validar dependências e execução real no Docker; configurar CI (execução remota ainda a conferir).
- [x] Produzir artefatos de branding, MER, UML, mockups e requisitos com base no código.
- [x] Atualizar matriz de conformidade e checklist com evidências e exceções autorizadas.
- [x] Validar em bancos descartáveis (292 testes), testar frontend e Docker, revisar diff e segurança.
- [x] Fazer commits na dev e preparar publicação via [PR #4](https://github.com/marconi-prog/lab-attendance-system/pull/4), fonte do estado da integração e checks; referência deste lote `v1.0.1-entrega`, preservando `v1.0-entrega`.

**Foco da revisão:** concorrência na criação de gestor; contas antigas com conflito; acesso indevido
a guichês; migração preservando dados; operação das duas áreas pelo gestor; falhas de rede e áudio.

Execução autorizada diretamente pelo solicitante. Claude Code implementa perfis/testes;
Codex organiza infraestrutura, artefatos, revisão, validação e publicação.
