# Posicionamento de Servidores de Fog

Este projeto realiza estudos e simulações sobre o posicionamento de servidores de fog computing, considerando diferentes cenários de conectividade, latência e capacidade de rede. O objetivo é analisar estratégias de otimização para aplicações como IoT industrial, jogos online, streaming 4K e videoconferência.

## Estrutura do Projeto

- `analise_convergencia_erro.py`: Analisa a convergência e o erro dos algoritmos de otimização.
- `analise_latencia_vs_capacidade_rede.py`: Estudo da relação entre latência e capacidade da rede.
- `aux_functions.py`: Funções auxiliares utilizadas nos experimentos e análises.
- `datanetAPI.py`: Interface para integração com a API de dados de rede.
- `exp_conectividade_cap_min.py`: Experimentos de conectividade com capacidade mínima.
- `exp_conectividade_lat_max.py`: Experimentos de conectividade com latência máxima.
- `exp_excentricidade_cap_max_v2.py`: Experimentos de excentricidade com capacidade máxima (versão 2).
- `exp_excentricidade_lat_min.py`: Experimentos de excentricidade com latência mínima.
- `ortool_l.py`: Algoritmos de otimização baseados em OR-Tools.
- `teste_otimização_l3.py`: Testes de otimização utilizando o modelo L3.
- `jaja.sql`: Script SQL para manipulação de dados relacionados aos experimentos.
- `result_pdf/`: Pasta com resultados dos experimentos em formato PDF, separados por cenário e parâmetros.

## Como Executar

1. Instale as dependências necessárias (ex: OR-Tools, pandas, numpy).
2. Execute os scripts de experimentos conforme o cenário desejado.
3. Os resultados serão gerados na pasta `result_pdf/`.

## Exemplos de Aplicação
- IoT Industrial
- Jogos Online
- Streaming 4K
- Videoconferência HD

## Contato
Autor: Palton-s

---

Este projeto é acadêmico e pode ser adaptado para diferentes cenários de fog computing e otimização de redes.