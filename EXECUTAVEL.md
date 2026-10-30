# AliceMind para Windows

## Criar o executável

Requisitos: Windows, Python 3.14 e conexão à internet para instalar dependências.

Para iniciar a criação com duplo clique, abra `build_exe.cmd`. Alternativamente, no PowerShell, na pasta do projeto:

```powershell
.\build_exe.ps1
```

O programa será criado em `dist\AliceMind\AliceMind.exe`. O conteúdo completo da pasta `dist\AliceMind` é necessário; copie ou distribua a pasta inteira, não apenas o `.exe`.

Ao abrir o executável, o AliceMind inicia seu servidor apenas em `127.0.0.1`, abre a página no navegador padrão e deixa uma janela de controle minimizada na barra de tarefas. Para parar o servidor, use **Encerrar AliceMind** na barra lateral do app, **Encerrar AliceMind** na janela de controle ou feche a janela de controle.

As conversas e os dados da Central do Agente ficam em `%LOCALAPPDATA%\Omni\memory`. Esse local foi mantido para preservar os dados existentes. A chave do OmniRoute pode ser definida na variável de ambiente `OMNI_API_KEY`; configure `OMNI_API_URL` se o endpoint não for o padrão. A busca web requer `TAVILY_API_KEY`. Não inclua chaves no executável nem no repositório.

O executável não inclui o OmniRoute/modelo de IA nem uma chave de busca. Esses serviços precisam estar acessíveis e configurados separadamente.

## Recursos do aplicativo

- Pesquise conversas anteriores por título ou conteúdo e exporte o chat atual em Markdown ou texto.
- Use atalhos de prompt editáveis para explicações, revisão, análise de código, planejamento e entrevistas; salve e remova seus próprios favoritos localmente.
- Anexe arquivos diretamente na caixa de mensagem do chat ou indexe documentos na Central do Agente. São aceitos arquivos de texto e código (incluindo Python `.py` e SQL `.sql`), PDF, DOCX, XLSX e PPTX, com limite de 10 MB por arquivo. Imagens PNG, JPG, GIF e WebP podem ser analisadas por modelos OmniRoute com suporte a visão; executáveis e arquivos compactados não são interpretados.
- Compare dois arquivos de texto ou PDF e veja as linhas adicionadas e removidas.
- Crie tarefas locais com prazo e prioridade; edite esses campos e o status depois.
- Consulte fontes web recentes salvas localmente. Apenas links HTTP/HTTPS válidos são guardados.
- Otimize o currículo em linguagem direta e baixe o resultado em PDF ou texto. O PDF usa um layout profissional simples; confira nomes, datas e demais informações antes de compartilhar.

## Execução autônoma sob autorização

Na Central do agente, descreva o pedido, selecione as ações permitidas e clique em **Autorizar e executar pedido**. O AliceMind planeja e executa até 12 etapas por pedido. O plano, o andamento e os resultados ficam visíveis durante a sessão.

As ferramentas são limitadas a pesquisar documentos já indexados, pesquisar na web, criar ou atualizar tarefas locais, redigir textos, criar arquivos dentro da pasta de projeto autorizada e executar verificações Python/testes ou o build fixo do executável. No `.exe`, essa pasta começa em `%LOCALAPPDATA%\Omni\workspace`; você pode informar outra pasta de projeto na Central do agente. No modo fonte, o padrão é a pasta do projeto atual. Não há execução de comandos arbitrários, exclusão de arquivos, envio de mensagens/candidaturas, publicação, compras ou acesso a contas.

Cada consulta web exige confirmação antes de ser enviada ao Tavily. Substituir um arquivo existente mostra uma comparação e pede confirmação; gerar o executável também pede confirmação antes de substituir os artefatos de build. Arquivos de credenciais, configurações ocultas e pastas de dados/build ficam protegidos contra edição direta pelo agente. O pedido e o plano são enviados ao endpoint OmniRoute configurado; documentos locais não são enviados automaticamente. Se uma etapa falhar, as etapas anteriores concluídas não são desfeitas.

O andamento de uma tarefa autônoma fica salvo localmente e pode ser retomado pela Central do agente após reabrir o programa. Se o aplicativo fechou durante uma etapa, confira primeiro os efeitos locais: ao retomar, essa etapa pode ser repetida. Tarefas em andamento não são executadas em segundo plano enquanto o programa está fechado.

Os dados locais, inclusive conversas, fontes, perfil, tarefas e checkpoints, ficam em `%LOCALAPPDATA%\Omni\memory`, sem criptografia. Não salve senhas ou informações altamente sensíveis.
