# Experimento de Variação de Latência

## Descrição
O arquivo `exp_latencia.py` contém um experimento que varia os requisitos de latência de 10ms a 200ms (incrementos de 10ms) e mede o número de servidores fog necessários para cada método.

## Como executar

### Executar standalone:
```bash
python exp_latencia.py
```

### Importar em outro script:
```python
import exp_latencia

# Executar o experimento
results = exp_latencia.run_latency_experiment()
```

## Saída
- **Gráfico PDF**: `result_pdf/latency_variation_experiment.pdf`
- **Console**: Progress durante execução
- **Plot interativo**: Mostrado na tela

## Estrutura do Gráfico
- **3 subplots**: Um para cada topologia (nsfnetbw, geant2bw, synth50bw)
- **5 curvas por subplot**: 4 heurísticas + OR-Tools
- **Eixo X**: Requisito de latência (10-200ms)
- **Eixo Y**: Número de servidores fog

## Cores dos Métodos
- **Excentricidade_Lat_max**: Vermelho
- **Excentricidade_Cap_Min**: Azul
- **Conectividade_Lat_Max**: Verde
- **Conectividade_Cap_Min**: Laranja
- **OR-Tools**: Preto

## Configurações
- **Range de latência**: 10ms a 200ms (incrementos de 10ms)
- **Capacidade fixa**: 0.1 Mbps
- **Amostras por topologia**: 5 (para eficiência)
- **Alpha OR-Tools**: 0.5 (solução balanceada)

# Experimentos de Otimização de Fog Placement

Este projeto realiza experimentos de otimização de posicionamento de fog nodes em diferentes topologias de rede, utilizando metaheurísticas e OR-Tools. Os resultados incluem gráficos e tabelas comparativas de desempenho.

## 1. Instalação das Dependências

Recomenda-se o uso de Python 3.11 ou superior.

Instale as dependências principais via pip:

```bash
pip install numpy matplotlib scipy pandas ortools networkx
```

## 2. Download dos Datasets

Os datasets utilizados estão disponíveis em:  
https://knowledgedefinednetworking.org/

Baixe os arquivos das topologias (ex: `nsfnetbw`, `geant2bw`, `synth50bw`) e coloque-os nas respectivas pastas do projeto:

```
/nsfnetbw/
/geant2bw/
/synth50bw/
```

## 3. Execução dos Experimentos

Para rodar os experimentos principais e gerar gráficos/tabelas, execute:

```bash
python experimento_principal.py
```

Para experimentos de variação de latência, execute:

```bash
python exp_latencia.py
```

Os resultados em PDF serão salvos na pasta `result_pdf/`.

## 4. Reprodutibilidade

Todos os experimentos utilizam seeds fixas para garantir que os resultados possam ser reproduzidos por qualquer pessoa, em qualquer ambiente.

## 5. Visualização dos Resultados

Os gráficos e tabelas gerados estarão disponíveis em arquivos PDF na pasta `result_pdf/`.  
Os logs e médias de desempenho são exibidos no terminal durante a execução.

---

Se precisar de instruções específicas para Windows ou outro sistema, posso detalhar!