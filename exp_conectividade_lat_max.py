import datanetAPI
import networkx as nx
import random
import numpy as np

"""# Fixando a seed para garantir a reprodutibilidade
random.seed(42)
np.random.seed(42)

# Dataset de teste
datasets = './nsfnetbw/'

# Inicializando o leitor de dados
reader = datanetAPI.DatanetAPI(datasets)
it = iter(reader)
dados = next(it)

# Define os requisitos de latência
L_max = 0.2
L_cloud_fog = 1"""
#(latencias, capacidades, L_max, C_min, L_cloud_fog, C_cloud_fog, cloud_position):
def solver(latencias, capacidades, L_max, C_min, L_cloud_fog, C_cloud_fog, cloud_position, dados):
    
    uni = 0.025/2
    L_max = uni*L_max # 10ms (tempo real) 80ms (jogos) 200ms (IoT)
    L_cloud_fog = uni*L_cloud_fog # 200ms
    
    
    n_nodes = len(latencias)

    # Define os nós de fog
    fogs = [0 for _ in range(n_nodes)]
    # Define o nó da cloud
    node = cloud_position
    # Coloca o nó da cloud como um nó de fog
    fogs[node] = 1

    # Define a matriz de atendimento
    y = []
    for i in range(n_nodes):
        y.append([])
        latencies_fogs = {k: latencias[i][k] for k in range(n_nodes) if fogs[k] == 1}
        min_lat_node = min(latencies_fogs, key=latencies_fogs.get)
        for j in range(n_nodes):
            y[i].append(1 if min_lat_node == j else 0)

    requisitos_atendidos = [0 for _ in range(n_nodes)]
    # Calcula o grau dos nós (número de conexões)
    nos_mais_conectados = dict(nx.degree(dados.topology_object))
    nos_mais_conectados.pop(node, None)
    
    def desempate(nos):
        # Ordena os nós primeiro pelo grau (decrescente) e depois pela latência (decrescente)
        ordenacao = sorted(nos, key=lambda x: (nos[x], latencias[x][node]), reverse=True)
        return ordenacao

    # Enquanto houver nós não atendidos
    while sum(requisitos_atendidos) < n_nodes:
        
        # Para cada nó, captura a latência entre ele e o nó que o atende
        for i in range(n_nodes):
            if fogs[i] == 1:
                lat = latencias[i][node]
                cap = capacidades[i][node]
                if lat < L_cloud_fog and cap > C_cloud_fog:
                    requisitos_atendidos[i] = 1
                else:
                    requisitos_atendidos[i] = 0
            else:
                lat = latencias[i][y[i].index(1)]
                cap = capacidades[i][y[i].index(1)]
                if lat < L_max and cap > C_min:
                    requisitos_atendidos[i] = 1
                else:
                    requisitos_atendidos[i] = 0
        # se sum(requisitos_atendidos) == n_nodes, então todos os nós foram atendidos
        if sum(requisitos_atendidos) == n_nodes:
            break
        if sum(fogs) >= n_nodes:
            # calcula a latência média da rede
            total_latencia = 0
            for i in range(n_nodes):
                for j in range(n_nodes):
                    total_latencia += latencias[i][j] * y[i][j]
            media_latencia = total_latencia / n_nodes
            return n_nodes, fogs, media_latencia
        
        
        # Pega a key do nó mais conectado com critério de desempate
        no_fog = desempate(nos_mais_conectados)[0]
        # Coloca a fog nesse nó
        fogs[no_fog] = 1
        # Remove o nó da lista de possíveis nós de fog
        nos_mais_conectados.pop(no_fog)
        
        # Recalcula a matriz de atendimento y com base nos fogs atuais (reatribui ao fog mais próximo)
        y = []
        for i in range(n_nodes):
            y.append([])
            latencies_fogs = {k: latencias[i][k] for k in range(n_nodes) if fogs[k] == 1}
            min_lat_node = min(latencies_fogs, key=latencies_fogs.get)
            for j in range(n_nodes):
                y[i].append(1 if min_lat_node == j else 0)
    
    # coloca 1 na posição do nó da cloud
    fogs[node] = 1
    
    # calcula a latência média da rede
    total_latencia = 0
    for i in range(n_nodes):
        for j in range(n_nodes):
            total_latencia += latencias[i][j] * y[i][j]
    media_latencia = total_latencia / n_nodes
    
    return sum(fogs) -1, fogs, media_latencia
