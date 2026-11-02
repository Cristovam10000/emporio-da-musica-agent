# Store policy knowledge (Empório da Música)

This file holds the store's policy manual, split into sections that the `get_store_policy` tool looks up by key.
The policy text is a verbatim Portuguese transcription of `data/políticas_da_loja.pdf` (PDF contradictions kept as-is); the "Interpretation notes" subsections are ours.

## contato_endereco
<!-- source: PDF cover (address/phone/e-mail lines), 1.2 -->
**Capa**

Rua 14 de Maio, 3200 — Centro Campo Grande – MS – CEP 79202-333

(67) 3341-4444 — contato@emporiodamusica.com.br

**1.2 Dados da Empresa**

| Campo | Informação |
|---|---|
| Razão Social | Empório da Música Instrumentos Musicais Ltda. |
| Nome Fantasia | Empório da Música |
| CNPJ | 12.345.678/0001-90 |
| Endereço | Rua 14 de Maio, 3200 — Centro, Campo Grande - MS, 79202-333 |
| Telefone / WhatsApp | (67) 3341-4444 |
| E-mail | contato@empóriodamusica.com.br |
| Fundação | 2008 |

### Interpretation notes
- Use (67) 3341-4444 as the store phone/WhatsApp; the PDF also lists (67) 3321-4500 in section 7 - flagged for the store to confirm (P1).
- Use the e-mail without accent, contato@emporiodamusica.com.br (as on the cover); the table in 1.2 shows contato@empóriodamusica.com.br - flagged for the store to confirm (P2).

## horario
<!-- source: PDF 2 -->
**2. Horário de Funcionamento**

O atendimento presencial na loja segue os horários abaixo. O atendimento via WhatsApp segue o mesmo horário, com respostas automáticas fora do expediente.

| Dia | Horário |
|---|---|
| Segunda a Sexta-feira | 09:00 às 18:00 |
| Sábado | 09:00 às 13:00 |
| Domingo e Feriados | Fechado |

Em datas especiais (Black Friday, Aniversário da Loja, Natal), o horário pode ser estendido. Alterações serão comunicadas com antecedência nas redes sociais e no atendimento via WhatsApp.

### Interpretation notes
- Holidays are computed in code (national + Mato Grosso do Sul holidays, plus Aug 26, Campo Grande's anniversary); the code cannot know movable municipal holidays or optional days off, so do not state a holiday status that was not given to you (P9).
- Whether the store is open now, and when it reopens, is computed in code and injected into the system prompt each turn; outside business hours, state the reopening time from that status and never work it out yourself (P10).

## pagamento_parcelamento
<!-- source: PDF 3, 3.1 -->
**3. Formas de Pagamento**

Aceitamos as seguintes formas de pagamento para compras presenciais e online:

| Forma | Condições | Observações |
|---|---|---|
| PIX | Pagamento à vista | 5% de desconto sobre o preço de tabela |
| Cartão de Débito | Pagamento à vista | Todas as bandeiras aceitas |
| Cartão de Crédito | Até 12x sem juros | Parcela mínima de R$ 100,00 |
| Boleto Bancário | Pagamento à vista | Compensação em até 3 dias úteis |

**3.1 Regras de Parcelamento**

- Parcelamento em até 3x: sem juros, sem valor mínimo de parcela (exceto abaixo de R$ 50,00).
- Parcelamento de 4x a 6x: sem juros, parcela mínima de R$ 80,00.
- Parcelamento de 7x a 12x: sem juros, parcela mínima de R$ 100,00.
- Combinação de formas de pagamento: permitida (ex.: PIX + cartão) para compras acima de R$ 2.000,00.

### Interpretation notes
- Follow the tiered rules in 3.1 over the "parcela mínima de R$ 100,00" in the payment table, because 3.1 is more specific; installment amounts are computed in code, so quote them as returned by the tools (P3).
- For 1-3 installments, treat the minimum installment as R$ 50,00 (our reading of "sem valor mínimo de parcela (exceto abaixo de R$ 50,00)") (P3).

## trocas_devolucoes
<!-- source: PDF 4, 4.1, 4.2, 4.3, 4.4 -->
**4. Política de Trocas e Devoluções**

A Empório da Música segue as diretrizes do Código de Defesa do Consumidor (Lei nº 8.078/90) e oferece condições claras para trocas e devoluções.

**4.1 Direito de Arrependimento (Compras Online)**

- O cliente pode solicitar a devolução em até 7 (sete) dias corridos após o recebimento do produto, sem necessidade de justificativa.
- O produto deve estar em sua embalagem original, sem sinais de uso, com todos os acessórios e manuais.
- O reembolso será realizado na mesma forma de pagamento original em até 10 dias úteis.
- O frete de devolução é por conta da loja em caso de arrependimento.

**4.2 Trocas por Defeito**

- Produtos com defeito de fabricação podem ser trocados em até 30 (trinta) dias corridos após a compra.
- Após os 30 dias, o cliente deve acionar a garantia diretamente com o fabricante. A Empório da Música pode intermediar o processo mediante solicitação.
- Danos causados por mau uso, quedas, exposição a umidade excessiva ou modificações não autorizadas não são cobertos.

**4.3 Trocas por Preferência**

- Trocas por preferência (cor, modelo, tamanho) são permitidas em até 7 dias, mediante disponibilidade do produto desejado.
- O produto deve estar em perfeito estado e na embalagem original.
- Diferenças de valor serão cobradas ou reembolsadas conforme o caso.

**4.4 Itens Não Elegíveis para Troca**

- Instrumentos com personalização ou ajustes sob encomenda (setup, regulagem especial).
- Produtos adquiridos em promoções de liquidação com aviso explícito de "venda final".
- Boquilhas de instrumentos de sopro, por questões de higiene.

### Interpretation notes
- Before giving return/exchange guidance, ask for what is missing: order number, contact, date the customer received the item, and the reason (P5).
- The 7-day right of withdrawal (4.1) applies to online purchases. Assume orders found in the system are online purchases; if the customer says they bought in the physical store, the customer's statement prevails (P5).
- Never use `estimated_delivery` as proof of receipt; count the days from the received-on date the customer gives. Phrase guidance conditionally ("pelo que você me contou, ...") and never say a return is approved (P5).
- Explain both the 30-day defect exchange (counted from the purchase, 4.2) and the 90-day legal warranty (counted from receipt, section 8.1) only when the customer reports a defect (P4).
- Treat the 7 days for exchange by preference (4.3) as counted from receipt, since the PDF does not say from when (P6).

## frete_entrega
<!-- source: PDF 5.1, 5.2, 5.3 -->
**5. Política de Frete e Entregas**

**5.1 Entregas na Região Metropolitana de Campo Grande**

- Frete grátis para pedidos acima de R$ 500,00.
- Para pedidos abaixo de R$ 500,00, taxa fixa de R$ 35,00.
- Prazo de entrega: 1 a 3 dias úteis.
- Entrega realizada por motoboy próprio. O cliente será contactado por telefone antes da entrega.

**5.2 Entregas para Outras Cidades**

Utilizamos os serviços dos Correios (PAC e SEDEX) e da transportadora Jadlog para envios fora da região metropolitana de Campo Grande.

| Modalidade | Prazo Estimado | Rastreamento | Seguro |
|---|---|---|---|
| PAC (Correios) | 5 a 12 dias úteis | Sim | Incluído |
| SEDEX (Correios) | 2 a 5 dias úteis | Sim | Incluído |
| Jadlog (.package) | 3 a 8 dias úteis | Sim | Incluído |

O valor do frete é calculado automaticamente com base no CEP de destino, peso e dimensões do produto. Instrumentos de grande porte (baterias acústicas, pianos digitais, contrabaixos) podem exigir frete especial com cotação individual.

Todos os envios incluem seguro contra extravios e danos durante o transporte. Em caso de avaria, o cliente deve recusar o recebimento e entrar em contato imediatamente com a loja.

**5.3 Código de Rastreamento**

O código de rastreamento é enviado automaticamente por e-mail e WhatsApp assim que o pedido é despachado. O formato padrão é BR seguido de 9 caracteres alfanuméricos e BR (exemplo: BR4K7M2X9P1BR). O rastreamento pode ser consultado diretamente no site dos Correios ou da Jadlog.

### Interpretation notes
- Do not calculate shipping for other cities: it depends on CEP, weight and dimensions, which the assistant does not have. Share the delivery-time table and offer the team for a quote. Inside the Campo Grande metro area, the free-shipping above R$ 500,00 / R$ 35,00 rule can be stated as written (2.3).

## promocoes
<!-- source: PDF 6, 6.1, 6.2 -->
**6. Promoções e Descontos**

**6.1 Tipos de Promoção**

A Empório da Música realiza promoções periódicas ao longo do ano. As principais campanhas incluem:

- Aniversário da Loja (Agosto): descontos de 10% a 25% em itens selecionados.
- Black Friday (Novembro): descontos de 15% a 30% em todo o catálogo.
- Volta às Aulas (Fevereiro): descontos especiais em instrumentos para estudantes.
- Queima de Estoque: promoções pontuais para renovação de catálogo.
- Semana do Músico: promoções na semana do Dia do Músico (22 de novembro).

**6.2 Regras de Promoções**

**Cumulatividade:** promoções não são cumulativas. O desconto de PIX (5%) não se aplica sobre preços já promocionais.

**Estoque:** promoções estão sujeitas à disponibilidade de estoque. Produtos esgotados durante a promoção não geram direito a rain check (reserva de preço).

**Comunicação:** preços promocionais devem sempre ser apresentados junto ao preço original e o percentual de desconto, para total transparência ao cliente.

### Interpretation notes
- Whether a product is on sale comes only from the product tools (promotions active in the system). Never infer a discount from the calendar (e.g. "it is November, so Black Friday applies" or the Semana do Músico): if the customer asks about a campaign and the product has no active promotion, say it is not active at the moment and give the current price (D8).

## garantia
<!-- source: PDF 8, 8.1, 8.2, 8.3 -->
**8. Garantia**

**8.1 Garantia Legal**

Conforme o Código de Defesa do Consumidor, todos os produtos possuem garantia legal de 90 (noventa) dias contra defeitos de fabricação, contados a partir da data de recebimento pelo cliente.

**8.2 Garantia do Fabricante**

Além da garantia legal, a maioria dos fabricantes oferece garantia própria que pode variar de 6 meses a 2 anos. Os prazos e condições específicos estão detalhados no certificado de garantia que acompanha cada produto.

**8.3 O que Não Cobre a Garantia**

- Desgaste natural de peças (trastes, cordas, feltros, palhetas de sopro).
- Danos por mau uso, queda, exposição a condições climáticas extremas.
- Modificações ou reparos realizados por terceiros não autorizados.
- Danos estéticos que não afetem a funcionalidade do instrumento.

### Interpretation notes
- Mention the warranty only when the customer reports a defect; then explain both the 30-day defect exchange (counted from the purchase, section 4.2) and the 90-day legal warranty (counted from receipt, 8.1) (P4).

## privacidade
<!-- source: PDF 9 -->
**9. Privacidade e Proteção de Dados**

A Empório da Música está em conformidade com a Lei Geral de Proteção de Dados (LGPD — Lei nº 13.709/2018). Os dados pessoais coletados durante o atendimento (nome, telefone, e-mail, endereço) são utilizados exclusivamente para:

- Processamento e entrega de pedidos.
- Comunicação sobre status de pedidos e rastreamento.
- Envio de promoções e novidades (mediante consentimento explícito do cliente).
- Cumprimento de obrigações legais e fiscais.

Dados de clientes não são compartilhados com terceiros para fins de marketing. O cliente pode solicitar a exclusão de seus dados a qualquer momento entrando em contato pelo WhatsApp ou e-mail.

## sobre_loja
<!-- source: PDF cover (title, slogan, version, internal-use lines), 1, 1.1, 10, closing footer -->
**Capa**

EMPÓRIO DA MÚSICA

Sua música começa aqui.

MANUAL DE POLÍTICAS E PROCEDIMENTOS

Atendimento ao Cliente

Versão 2.1 — Junho de 2025

Documento interno — Uso restrito da equipe de atendimento

**1. Sobre a Empório da Música**

A Empório da Música é uma loja especializada em instrumentos musicais, fundada em 2008 em Campo Grande, Mato Grosso do Sul. Com mais de 15 anos de atuação no mercado, somos referência regional na venda de instrumentos para músicos iniciantes, intermediários e profissionais. Nosso catálogo abrange mais de 300 instrumentos de marcas nacionais e internacionais, incluindo guitarras, baixos, violões, baterias, teclados, instrumentos de sopro, cordas orquestrais e ukuleles. Trabalhamos exclusivamente com instrumentos musicais — não comercializamos acessórios como cordas, palhetas, cabos, cases, pedais ou amplificadores.

**1.1 Missão**

Democratizar o acesso a instrumentos musicais de qualidade na região Centro-Oeste, oferecendo atendimento especializado e preços competitivos, contribuindo para o desenvolvimento cultural e musical da comunidade.

**10. Disposições Finais**

Este manual é um documento interno da Empório da Música e deve ser utilizado como referência por todos os membros da equipe de atendimento, incluindo o assistente virtual. As políticas descritas neste documento estão sujeitas a atualizações periódicas. Em caso de dúvidas sobre a aplicação de qualquer política, o atendente deve consultar a gerência antes de fornecer informações ao cliente. O objetivo é sempre garantir transparência, precisão e a melhor experiência possível para o cliente.

Empório da Música — Sua música começa aqui.

Última atualização: Junho de 2025 — Versão 2.1

### Interpretation notes
- The "300+ instruments" claim includes wind and orchestral strings, but the data has only 65 products and empty categories (6/7/8). Only state what is in the data, e.g. "no momento não temos [sax] no sistema", and offer to forward the request to the team to check on ordering (P7).

## atendimento_regras
<!-- source: PDF 7, 7.1, 7.2, 7.3 -->
**7. Atendimento via WhatsApp**

O canal de WhatsApp (67) 3321-4500 é o principal meio de atendimento remoto da Empório da Música. O atendimento pode ser realizado por atendentes humanos ou pelo assistente virtual.

**7.1 Diretrizes de Atendimento**

**Tom de voz:** informal mas profissional. O cliente deve se sentir acolhido, como se estivesse conversando com um amigo que entende de música. Evitar linguagem excessivamente formal ou robotizada.

**Tempo de resposta:** máximo de 5 minutos durante o horário de funcionamento. Fora do expediente, o assistente virtual deve informar o horário de retorno.

**Informações precisas:** nunca fornecer informações sobre preços, estoque ou prazos sem consultar o sistema. Informações incorretas geram frustração e podem configurar propaganda enganosa.

**Escopo:** o atendente deve informar que a loja trabalha exclusivamente com instrumentos musicais. Pedidos de acessórios (cordas, cabos, palhetas, pedais, amplificadores, cases) devem ser educadamente redirecionados. Sugerir lojas parceiras quando possível.

**7.2 Fluxo de Atendimento Padrão**

1. Saudação: cumprimentar o cliente pelo nome (se disponível) e perguntar como pode ajudar.
2. Entendimento: identificar a necessidade do cliente (busca de produto, dúvida, rastreamento, reclamação).
3. Consulta: buscar no sistema as informações relevantes (produto, estoque, promoção, pedido).
4. Resposta: apresentar as opções de forma clara e objetiva, com preços e condições.
5. Fechamento: confirmar se o cliente precisa de mais alguma coisa e encerrar com cordialidade.

**7.3 Situações Especiais**

**Produto fora de estoque:** informar que o produto está temporariamente indisponível e sugerir alternativas semelhantes que estejam disponíveis. Nunca confirmar disponibilidade sem verificar o estoque atual.

**Produto descontinuado:** informar que o produto não faz mais parte do catálogo e oferecer modelos equivalentes ou sucessores.

**Promoção expirada:** caso o cliente pergunte sobre uma promoção, verificar se ela encontra-se ativa no sistema. Se a promoção estiver vencida, informar com transparência e apresentar o preço atual. Nunca prometer um desconto que não está mais vigente.

**Reclamação:** ouvir o cliente com empatia, registrar a reclamação e encaminhar para o responsável. Prazo de retorno: 24 horas úteis.

### Interpretation notes
- This section goes to the system prompt, not to the tool. The WhatsApp (67) 3321-4500 here conflicts with (67) 3341-4444 elsewhere; use 3341-4444 and flag for the store to confirm (P1).
- Never invent partner stores for "Sugerir lojas parceiras": the PDF gives no list, so say the team can point the customer to one (P8).
- Outside business hours, give the return time from the store status injected each turn (P10).
