<p align="center"><img src="tizen/icon.png" width="120" alt="Tela Livre"></p>

<h1 align="center">Tela Livre</h1>

<p align="center"><b>Uma tela inicial sem anúncios para TVs Samsung, com instalador de dois cliques no Windows.</b></p>

<p align="center"><img src="assets/preview.webp" width="880" alt="Navegando pelo Tela Livre: fileira de apps, destaque com botão Assistir, abas, gaveta com entradas e clima, e o modo noite"></p>
<p align="center"><sub>Navegando pela tela com o controle. Os destaques mostram as capas reais dos filmes e séries em alta; aqui as imagens são de exemplo.</sub></p>

A tela inicial das TVs Samsung vem cheia de vitrine que você não pediu. O Tela Livre é um app que vira a sua tela de
entrada: seus apps numa fileira, clima da sua cidade, relógio e, se quiser, os filmes e séries em alta só dos apps que
você já tem. Creme de dia, grafite quente de noite, seguindo o pôr do sol de verdade.

Nada na TV é apagado ou alterado. Ele entra como um app comum, e com uma opção da própria TV ela já liga direto nele.
Não curtiu? Exclui o app e está tudo como antes.

## Funciona em

TVs Samsung de **2016 a 2022**. Para saber o ano, olhe a letra logo depois das polegadas no modelo:

| Letra | K | M | N | R | T | A | B |
|---|---|---|---|---|---|---|---|
| Ano | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 |

Exemplo: UN65**T**U8000 é de 2020. TVs de 2023 em diante pedem um certificado da conta Samsung, que o instalador ainda
não faz.

## Você vai precisar

- Um PC com Windows ou um Mac na mesma rede Wi-Fi da TV (só para instalar)
- [Python 3](https://www.python.org/downloads/): na instalação, marque **Add Python to PATH**

## Instalação

**1. Descubra o IP do seu PC.** Windows + R, digite `cmd`, Enter, depois `ipconfig`. Anote o "Endereço IPv4" do
adaptador que tem "Gateway Padrão" preenchido (algo como 192.168.0.15). Ignore os de VMware e VPN.

**2. Ligue o modo desenvolvedor na TV.**
- Abra **Apps** e digite **1 2 3 4 5** no controle
- Não abriu? Use o teclado numérico do app **SmartThings** no celular, ou um teclado USB na TV
- Ligue **Developer mode**, coloque o IP do PC em **Host PC IP** e dê OK
- Reinicie a TV tirando da tomada por uns 5 segundos

**3. Descubra o IP da TV.** Configurações > Geral > Rede > Status da rede > Configurações de IP.

**4. Baixe o Tela Livre.** Botão verde **Code > Download ZIP**, e descompacte.

**5. Dois cliques em `instalar.bat`.** Se o Windows avisar, **Mais informações > Executar assim mesmo**. Ele pede o IP
da TV, pede para você criar uma senha (guarde: as atualizações usam a mesma) e manda o app para a TV.

**No Mac:** no lugar do `instalar.bat`, dê dois cliques em `instalar.command`. Na primeira vez o macOS bloqueia:
clique com o botão direito > **Abrir** > **Abrir**. Para o IP do Mac, veja Ajustes do Sistema > Wi-Fi > Detalhes.

**6. Ligar direto no Tela Livre.** Nas configurações da TV, em Opções da Tela Inicial, ligue **Autorun Last App**.

## Sua cidade e os filmes em alta (opcional)

Sem configurar nada, a cidade vem do fuso horário da TV. Para escolher a sua e ter os destaques, copie
`config.example.properties` para `config.properties`, preencha a cidade e uma chave gratuita do
[TMDB](https://www.themoviedb.org/settings/api), e rode `instalar.bat` de novo.

## Abrir direto um app (opcional)

Para a TV ligar direto no YouTube (ou outro app), coloque `startup_app=youtube` no `config.properties` e rode
`instalar.bat` de novo. Ao apertar Voltar no YouTube, a tela do Tela Livre aparece normalmente.

## Para remover

Na TV: Apps > Configurações > Tela Livre > Excluir.

## Como funciona

- `web/`: a tela inicial, em HTML, CSS e JavaScript leves para rodar até nos navegadores antigos das TVs
- `tizen/build.py` monta o app, `tizen/sign.py` assina sem precisar do Tizen Studio, `tizen/install.py` manda para a TV pelo Wi-Fi
- Dados: TMDB (destaques), Open-Meteo (clima e pôr do sol)

## Créditos

O Tela Livre nasceu do [Free My TV](https://github.com/simbasjungles/free-my-tv), projeto de código aberto (licença
MIT) que faz a tela inicial do Google TV e tem uma versão web para LG e Samsung. Daqui saíram a base do app web e o
envio para a TV. O Tela Livre foca só em Samsung e traz o visual novo, a fonte serifada, o assinador próprio, o
instalador de dois cliques e a documentação em português.

Feito por [Helio Arreche](https://github.com/ArrecheNeto), com o Claude. Fontes: Inter e Source Serif 4 (SIL OFL).
Ícones: Material Symbols (Apache 2.0). Este produto usa a API do TMDB, mas não é endossado nem certificado pelo TMDB.
Não é afiliado à Samsung.

## Licença

[MIT](LICENSE).
