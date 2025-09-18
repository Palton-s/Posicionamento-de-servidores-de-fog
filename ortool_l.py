from ortools.linear_solver import pywraplp
import random


def solveProblem(latencias, capacidades,L_max, C_min, L_cloud_fog, C_cloud_fog, cloud, alpha=1.0):
    solver = pywraplp.Solver('Simple_lp_program', pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING)
    #solver.EnableOutput()  # Habilita a saída de log do solver


    uni = 0.025/2
    #uni = 1
    
    L_max = uni*L_max # 10ms (tempo real) 80ms (jogos) 200ms (IoT)
    L_cloud_fog = uni*L_cloud_fog # 200ms
    C_min = C_min
    C_cloud_fog = C_cloud_fog

    # sorteia um nó para ser o cloud
    #cloud = random.randint(0, len(latencias)-1)

    N = len(latencias)

    # define as variaveis de decisao

    # y representa se um nó i é servido por um nó j
    y = []
    for i in range(N):
        y.append([])
        for j in range(N):
            y[i].append(solver.BoolVar("y_"+str(i)+"_"+str(j)))

    # x representa se um nó i é um servidor
    x = []
    for i in range(N):
        x.append(solver.BoolVar("x_"+str(i)))
        

    # define as restricoes

    # cada nó deve ser servido por um servidor
    for i in range(N):
        ct = solver.Constraint(1, 1)
        for j in range(N):
            ct.SetCoefficient(y[i][j], 1)
            
    # se um nó é servido por outro, então o nó que serve deve ser um servidor
    for i in range(N):
        for j in range(N):
            ct = solver.Constraint(-solver.infinity(), 0)
            ct.SetCoefficient(y[i][j], 1)
            ct.SetCoefficient(x[j], -1)

    # se o nó é um servidor ele deve ser servidor por ele mesmo
    # x[i] - y[i][i] = 0 para todo i pertencente a n
    for i in range(N):
        ct = solver.Constraint(0, 0)
        ct.SetCoefficient(x[i], 1)
        ct.SetCoefficient(y[i][i], -1)

    # a latencia de um nó i para um nó j deve ser menor que L_max
    """for i in range(N):
        for j in range(N):
            ct = solver.Constraint(-solver.infinity(), L_max)
            ct.SetCoefficient(y[i][j], float(latencias[i][j]))"""

    # a capacidade de um nó i para um nó j deve ser maior que C_min
    for i in range(N):
        for j in range(N):
            ct = solver.Constraint(-solver.infinity(), float(capacidades[i][j]))
            ct.SetCoefficient(y[i][j], C_min)
            


    # a latência entre um nó de serivdor e o cloud deve ser menor que L_cloud_fog
    for i in range(N):
        ct = solver.Constraint(-solver.infinity(), L_cloud_fog)
        ct.SetCoefficient(x[i], float(latencias[cloud][i]))
        
    # a capacidade entre um nó de servidor e o cloud deve ser maior que C_min
    for i in range(N):
        ct = solver.Constraint(-solver.infinity(), float(capacidades[cloud][i]))
        ct.SetCoefficient(x[i], C_cloud_fog)
            
    # x[cloud] = 1
    ct = solver.Constraint(1, 1)
    ct.SetCoefficient(x[cloud], 1)

        
    # define a funcao objetivo
    # define a função objetivo com dois critérios: número de fogs e latência média

    objective = solver.Objective()
    max_latencia = max(max(latencias[i]) for i in range(N))  # Máxima latência entre os nós
    for i in range(N):
        objective.SetCoefficient(x[i], (1-alpha)/N)  # Minimiza número de fog nodes
        for j in range(N):
            objective.SetCoefficient(y[i][j], alpha * float(latencias[i][j])/(max_latencia*N))  # Minimiza latência média

    objective.SetMinimization()


    # resolve o problema
    solver.Solve()
    
    # resgata a solução para x[]
    X_solution = []
    for i in range(N):
        X_solution.append(int(x[i].solution_value()))
    # se i for igual ao cloud coloca o valor 2
    X_solution[cloud] = 2
    
    # calcula a latência média da rede com base na solução encontrada
    total_latencia = 0
    total_atendidos = 0
    for i in range(N):
        for j in range(N):
            if y[i][j].solution_value() > 0.5:
                total_latencia += float(latencias[i][j])
                total_atendidos += 1
    latencia_media = total_latencia / total_atendidos if total_atendidos > 0 else 0
            
    # se a latência média for 0, então não tem solução e então coloca L_cloud_fog
    if latencia_media == 0:
        latencia_media = L_cloud_fog
        #print("Solução não encontrada, latência média é 0")
        

    # imprime o resultado
    return  solver.Objective().Value() -1, X_solution, latencia_media


