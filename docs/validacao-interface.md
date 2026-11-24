# Validação da interface — 23/11/2026

Verificação guiada no navegador contra o projeto Docker isolado de revisão, com dados fictícios,
frontend em `http://localhost:18080` e API em `http://localhost:15000`. O controle de expediente foi
desativado somente nesse ambiente para a demonstração fora do horário; os testes do backend validam
o expediente habilitado. Não se trata de uma suíte E2E automatizada versionada.

## Fluxos observados

| Fluxo | Resultado observado |
|---|---|
| Totem: emissão prioritária | `SP002` emitida, comprovante com código completo e retorno automático à seleção |
| Totem: tela pequena (459 × 539) | Cabeçalho separado das opções; rolagem permitiu alcançar as três categorias e emitir `SG002` |
| Login do gestor | Acesso à gestão, indicadores e conexão em tempo real |
| Gestão | Listas de usuários e guichês, relatório diário, filtro por categoria e trilha de auditoria carregados |
| Login do atendente | Exibido somente o guichê autorizado; abertura do guichê 02 pela interface |
| Chamada e repetição | `SE001` apareceu no painel sem recarregar; repetição mudou o rótulo para “Última chamada” |
| Ausência | Indisponível antes da segunda chamada; registrada após a repetição e exibida no relatório filtrado |
| Atendimento | `SP002` chamada, iniciada e finalizada pela interface; cronômetro visível e duração final de 31 segundos |
| Áudio | Clique liberou “Som ativado”; nenhuma mensagem de erro no console durante as chamadas. O solicitante confirmou que ouviu o sinal e a voz |

## Regressões visuais verificadas antes e depois

- Painel em 1280 × 720: a fonte calculada pela janela deixava `SE001` com largura de texto de 507 px
  em apenas 438 px disponíveis, exibindo reticências. Após medir a largura útil do cartão, a mesma
  verificação passou: 335 px de texto em 335 px do elemento; `SP002` também passou com 359 px.
- Totem em 459 × 539: o primeiro botão começava em y=11, sobrepondo o nome do laboratório, cujo limite
  inferior era y=44,5. Após a correção, o botão começou em y=229, abaixo do nome (y=43), e a rolagem
  permitiu alcançar a terceira opção sem esconder o cabeçalho.
- Cabeçalho do painel na mesma tela pequena: antes, o conteúdo exigia 706 px em uma tela de 459 px.
  Após empilhar o cabeçalho no breakpoint de telefone, a largura total passou a 459 px, sem excesso
  horizontal. O código `SG001` ficou inteiro: 291 px no telefone e 354 px no desktop.

Para repetir, prepare contas de demonstração seguindo o README, abra totem/painel/equipe em abas
separadas, habilite o som no painel e percorra os fluxos acima. No painel, confira visualmente o código
completo e verifique que `scrollWidth <= clientWidth + 1` no elemento do código. Em tela pequena,
confira a separação do cabeçalho e o acesso por rolagem às três opções do totem.

Os resultados não substituem a conferência dos PDFs oficiais. Antes da apresentação, repita o teste
de áudio no equipamento da sala, pois volume, saída de som e motor de voz dependem do dispositivo.
