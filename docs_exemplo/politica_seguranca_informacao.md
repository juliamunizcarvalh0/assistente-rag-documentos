# Política de Segurança da Informação — Aurora Pagamentos

*Documento fictício criado para demonstração. Versão 2.0, aprovada pelo Comitê de Segurança em janeiro de 2026.*

## 1. Objetivo e abrangência

Esta política define as regras para proteger as informações da Aurora Pagamentos e de seus clientes. Ela vale para todos os colaboradores, estagiários, prestadores de serviço e parceiros que tenham acesso aos sistemas da empresa. O descumprimento pode resultar em medidas disciplinares, incluindo desligamento.

## 2. Classificação da informação

Toda informação deve ser classificada em um dos quatro níveis:

- **Pública:** pode ser divulgada externamente, como o conteúdo do site e comunicados à imprensa.
- **Interna:** uso restrito aos colaboradores, como este manual e comunicados internos.
- **Confidencial:** acesso limitado a quem precisa, como contratos, dados financeiros e planos estratégicos.
- **Restrita:** o nível mais alto, que inclui dados pessoais de clientes, dados de cartão e chaves criptográficas.

Informações restritas nunca podem ser enviadas por e-mail, compartilhadas em ferramentas de chat ou armazenadas em dispositivos pessoais.

## 3. Senhas e autenticação

As senhas devem ter no mínimo 14 caracteres e não podem ser reutilizadas entre sistemas. O uso do gerenciador de senhas corporativo é obrigatório. Não é exigida troca periódica de senha, mas a troca é obrigatória imediatamente em caso de suspeita de vazamento.

A autenticação em dois fatores (MFA) é obrigatória em todos os sistemas corporativos. Para sistemas que acessam dados restritos, o segundo fator deve ser uma chave física de segurança; códigos por SMS não são aceitos.

## 4. Dispositivos e acesso remoto

Somente notebooks fornecidos pela empresa podem acessar sistemas internos. Os equipamentos têm disco criptografado e bloqueio automático de tela após 5 minutos de inatividade. Fora do escritório, o acesso deve ser feito pela VPN corporativa. É proibido usar redes Wi-Fi públicas sem a VPN ativa.

Pendrives e outros dispositivos de armazenamento removível ficam bloqueados por padrão. Exceções precisam de aprovação do time de Segurança e valem por no máximo 7 dias.

## 5. Controle de acesso

Os acessos seguem o princípio do menor privilégio: cada pessoa recebe apenas as permissões necessárias para sua função. As permissões são revisadas pelos gestores a cada trimestre. Acessos administrativos a ambientes de produção são temporários, concedidos por no máximo 8 horas e registrados para auditoria.

## 6. Proteção de dados pessoais (LGPD)

A Aurora trata dados pessoais de acordo com a Lei Geral de Proteção de Dados (Lei nº 13.709/2018). Os dados de clientes devem ser usados apenas para a finalidade informada no momento da coleta. Ambientes de teste e desenvolvimento devem usar dados anonimizados ou sintéticos, nunca dados reais de clientes.

Pedidos de titulares, como acesso, correção ou exclusão de dados, são encaminhados ao Encarregado de Dados (DPO) pelo e-mail privacidade@aurora.exemplo e devem ser respondidos em até 15 dias.

## 7. Incidentes de segurança

Qualquer suspeita de incidente, como um e-mail de phishing, perda de notebook ou acesso indevido, deve ser comunicada ao time de Segurança em até 1 hora, pelo canal #seguranca-incidentes ou pelo ramal 4040. Não tente investigar ou resolver o incidente por conta própria e não apague evidências.

Incidentes que envolvam dados pessoais e possam causar risco relevante aos titulares são comunicados à ANPD e aos titulares afetados em até 3 dias úteis, conforme a regulamentação.

## 8. Treinamento

Todos os colaboradores devem concluir o treinamento de segurança da informação em até 15 dias após a admissão e refazê-lo anualmente. O time de Segurança realiza simulações de phishing mensais; quem clicar em três simulações em um ano deve fazer um treinamento de reforço.
