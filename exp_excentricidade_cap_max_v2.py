import datanetAPI
import networkx as nx
import random
import numpy as np

# Configurar seed para garantir reprodutibilidade
random.seed(42)
np.random.seed(42)



def solver(latencias, capacidades, L_max, C_min, L_cloud_fog, C_cloud_fog, cloud_position):
    
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
        # Se o nó i é um fog, ele atende a si mesmo (autossuficiência)
        if fogs[i] == 1:
            for j in range(n_nodes):
                y[i].append(1 if i == j else 0)  # yii = 1, yij = 0 para j != i
        else:
            # Se não é fog, encontra o fog com maior capacidade para atendê-lo
            capacities_fogs = {k: capacidades[i][k] for k in range(n_nodes) if fogs[k] == 1}
            max_cap_node = max(capacities_fogs, key=capacities_fogs.get)
            for j in range(n_nodes):
                y[i].append(1 if max_cap_node == j else 0)

    # Seleciona todos os nós que possuem capacidade entre a cloud e o nó maior que C_cloud_fog
    # EXCLUINDO a cloud (node) da lista de candidatos
    possiveis_nos_de_fog = [i for i in range(n_nodes) if capacidades[i][node] > C_cloud_fog and i != node]

    requisitos_atendidos = [0 for _ in range(n_nodes)]
    latencia_atendida = ['' for _ in range(n_nodes)]

    # Seleciona o nó com a menor capacidade (ordem determinística)
    capacidades_nos_posssiveis_de_fog = {i: capacidades[i][node] for i in possiveis_nos_de_fog}
    # Não é necessário fazer pop(node, None) porque node já foi excluído acima
    
    # Converte para lista ordenada por chave para garantir determinismo
    nos_ordenados = sorted(capacidades_nos_posssiveis_de_fog.keys())

    # Enquanto houver nós não atendidos
    while sum(requisitos_atendidos) < n_nodes:
        

        # Para cada nó, captura a latência entre ele e o nó que o atende
        for i in range(n_nodes):
            if fogs[i] == 1:
                lat = latencias[i][node]
                cap = capacidades[i][node]
                if lat < L_cloud_fog and cap > C_cloud_fog:
                    requisitos_atendidos[i] = 1
                    latencia_atendida[i] = f"O nó de fog {i} é atendido pelo nó de cloud {node} com latência {lat}"
                else:
                    requisitos_atendidos[i] = 0
                    latencia_atendida[i] = f"O nó de fog {i} não é atendido pelo nó de cloud {node} com latência {lat}"
            else:
                lat = latencias[i][y[i].index(1)]
                cap = capacidades[i][y[i].index(1)]
                if lat < L_max and cap > C_min:
                    requisitos_atendidos[i] = 1
                    latencia_atendida[i] = f"O nó {i} é atendido pelo nó de fog {y[i].index(1)} com latência {lat}"
                else:
                    requisitos_atendidos[i] = 0
                    latencia_atendida[i] = f"O nó {i} não é atendido pelo nó de fog {y[i].index(1)} com latência {lat}"
                    
        if not capacidades_nos_posssiveis_de_fog:
            # calcula a latência média da rede
            total_latencia = 0
            for i in range(n_nodes):
                for j in range(n_nodes):
                    total_latencia += latencias[i][j] * y[i][j]
            media_latencia = total_latencia / n_nodes
            return n_nodes, fogs, media_latencia
        
        # se todos os requisitos foram atendidos, encessa o loop
        if sum(requisitos_atendidos) == n_nodes:
            break
        # caso contrário, adiciona um nó de fog e testa novamente
        
        # Pega a key do nó com a menor capacidade (determinístico)
        if capacidades_nos_posssiveis_de_fog:
            no_fog = min(capacidades_nos_posssiveis_de_fog.keys(), key=lambda k: (capacidades_nos_posssiveis_de_fog[k], k))
        else:
            # Se não há mais nós possíveis, pega o primeiro da lista ordenada
            no_fog = min(nos_ordenados) if nos_ordenados else node
        # Coloca a fog nesse nó
        fogs[no_fog] = 1
        # Remove o nó da lista de possíveis nós de fog
        capacidades_nos_posssiveis_de_fog.pop(no_fog)
        
        # Recalcula a matriz de atendimento y com base nos fogs atuais (autossuficiência)
        y = []
        for i in range(n_nodes):
            y.append([])
            # Se o nó i é um fog, ele atende a si mesmo (autossuficiência)
            if fogs[i] == 1:
                for j in range(n_nodes):
                    y[i].append(1 if i == j else 0)  # yii = 1, yij = 0 para j != i
            else:
                # Se não é fog, encontra o fog com maior capacidade para atendê-lo
                capacities_fogs = {k: capacidades[i][k] for k in range(n_nodes) if fogs[k] == 1}
                max_cap_node = max(capacities_fogs.keys(), key=lambda k: (capacities_fogs[k], -k)) if capacities_fogs else node
                for j in range(n_nodes):
                    y[i].append(1 if max_cap_node == j else 0)
        
        for chave in sorted(capacidades_nos_posssiveis_de_fog.keys()):  # Ordem determinística
            # pega a linha da matriz de latencias que corresponde ao nó
            linha = capacidades[chave]
            # multiplica a linha pelo vetor de fogs
            capacidades_ = np.array(linha) * np.array(fogs)
            # soma os valores do vetor
            capacidade_ecentricidade = sum(capacidades_)
            capacidades_nos_posssiveis_de_fog[chave] = capacidade_ecentricidade
        
        # Recalcula a matriz de atendimento y com base nos fogs atuais (reatribui ao fog com maior capacidade)
        y = []
        for i in range(n_nodes):
            y.append([])
            capacities_fogs = {k: capacidades[i][k] for k in range(n_nodes) if fogs[k] == 1}
            max_cap_node = max(capacities_fogs, key=capacities_fogs.get)
            for j in range(n_nodes):
                y[i].append(1 if max_cap_node == j else 0)
        
        
        
    # para cada elemento de fogs
    # coloca 2 na posição do elemento se for um nó de clouid
    fogs[cloud_position] = 1
    
    
    # calcula a latência média da rede
    total_latencia = 0
    for i in range(n_nodes):
        for j in range(n_nodes):
            total_latencia += latencias[i][j] * y[i][j]
    media_latencia = total_latencia / n_nodes
    
    return sum(fogs) -1, fogs, media_latencia
