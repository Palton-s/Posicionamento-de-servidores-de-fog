import datanetAPI
import networkx as nx
import random
import numpy as np



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
        latencies_fogs = {k: latencias[i][k] for k in range(n_nodes) if fogs[k] == 1}
        min_lat_node = min(latencies_fogs, key=latencies_fogs.get)
        for j in range(n_nodes):
            y[i].append(1 if min_lat_node == j else 0)

    # Seleciona todos os nós que possuem latência entre a cloud e o nó menor que L_cloud_fog
    possiveis_nos_de_fog = [i for i in range(n_nodes) if latencias[i][node] < L_cloud_fog]

    requisitos_atendidos = [0 for _ in range(n_nodes)]
    latencia_atendida = ['' for _ in range(n_nodes)]

    # Seleciona o nó com a maior latência
    latencias_nos_posssiveis_de_fog = {i: latencias[i][node] for i in possiveis_nos_de_fog}
    latencias_nos_posssiveis_de_fog.pop(node, None)

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
                    
        if not latencias_nos_posssiveis_de_fog: # se não houver mais nós possíveis de fog, retorna o número de nós e os nós de fog
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
        
        
        
        # Pega a key do nó com a maior latência
        no_fog = max(latencias_nos_posssiveis_de_fog, key=latencias_nos_posssiveis_de_fog.get)
        # Coloca a fog nesse nó
        fogs[no_fog] = 1
        # Remove o nó da lista de possíveis nós de fog
        latencias_nos_posssiveis_de_fog.pop(no_fog)
        
        # pega as chaves do arrat fogs em que o valor é 1
        fogs_values = [i for i in range(n_nodes) if fogs[i] == 1]
        

        for chave, valor in latencias_nos_posssiveis_de_fog.items():
            # pega a linha da matriz de latencias que corresponde ao nó
            linha = latencias[chave]
            # multiplica a linha pelo vetor de fogs
            latencias_ = np.array(linha) * np.array(fogs)
            # soma os valores do vetor
            latencia_ecentricidade = sum(latencias_)
            latencias_nos_posssiveis_de_fog[chave] = latencia_ecentricidade
        
        # Recalcula a matriz de atendimento y com base nos fogs atuais (reatribui ao fog mais próximo)
        y = []
        for i in range(n_nodes):
            y.append([])
            latencies_fogs = {k: latencias[i][k] for k in range(n_nodes) if fogs[k] == 1}
            # segurança: se não houver fog (não deve ocorrer), mantém cloud como destino
            min_lat_node = min(latencies_fogs, key=latencies_fogs.get)
            for j in range(n_nodes):
                y[i].append(1 if min_lat_node == j else 0)
            
        
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
