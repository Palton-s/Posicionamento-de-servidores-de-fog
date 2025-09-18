def extrai_latencias_capacidades(dados):
    n_nodes = len(dados.get_performance_matrix())
    latencias = []
    capacidades = []
    for i in range(n_nodes):
        latencias.append([])
        capacidades.append([])
        for j in range(n_nodes):
            latencias[i].append(dados.get_performance_matrix()[i, j]["AggInfo"]["AvgDelay"])
            capacidades[i].append(dados.get_traffic_matrix()[i, j]["AggInfo"]["AvgBw"])
    for i in range(n_nodes):
        latencias[i][i] = 5*0.025 # 10ms
        capacidades[i][i] = 1000000
    return latencias, capacidades
