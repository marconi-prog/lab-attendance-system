# Conclusão acadêmica — plano de implementação

**Objetivo:** alinhar o projeto ao PDF da atividade (10 páginas) e publicar via dev → main.

**Arquitetura:** preservar Flask/MySQL e Expo Web. ADMIN mantém compatibilidade de API e passa
a acumular as operações de atendimento, limitadas aos guichês autorizados. Um índice único sobre
um campo calculado limita a um gestor ativo; migration recusa dados conflitantes sem alterá-los.

**Restrições:** preservar contas, licença, autoria e alterações existentes; não mover tag publicada;
nome, Expo e previsões no painel aceitos pelo solicitante. Datas sob responsabilidade do solicitante.
PDF principal ainda não localizado: não inventar interpretação de 5% nem alteração de horários.

- [x] Confirmar equipe e colaboradores por API autenticada; registrar limites administrativos.
- [x] Implementar gestor/atendente e unicidade com testes de regressão e migration não destrutiva.
- [x] Atualizar Python para 3.14, validar dependências e execução real no Docker; configurar CI (execução remota ainda a conferir).
- [x] Produzir artefatos de branding, MER, UML, mockups e requisitos com base no código.
- [x] Atualizar matriz de conformidade e checklist com evidências e exceções autorizadas.
- [x] Validar em bancos descartáveis (292 testes), testar frontend e Docker, revisar diff e segurança.
- [ ] Fazer commits na dev, publicar PR, integrar main e registrar referência final sem mover tag.

**Foco da revisão:** concorrência na criação de gestor; contas antigas com conflito; acesso indevido
a guichês; migração preservando dados; operação das duas áreas pelo gestor; falhas de rede e áudio.

Execução autorizada diretamente pelo solicitante. Claude Code implementa perfis/testes;
Codex organiza infraestrutura, artefatos, revisão, validação e publicação.
