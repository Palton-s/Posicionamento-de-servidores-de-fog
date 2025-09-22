import sys, os
import time
import ortool_l
import datanetAPI
import networkx as nx
import matplotlib.pyplot as plt
import random
import numpy as np
import aux_functions as aux
from scipy.stats import sem, t
import pandas as pd
import csv
import exp_excentricidade_lat_min
import exp_excentricidade_cap_max_v2
import exp_conectividade_lat_max
import exp_conectividade_cap_min

def run_latency_experiment(n_experiments=300):
    """
    Executa experimento de variação de requisitos de latência (10-200ms)
    para avaliar o número de servidores fog necessários por cada método.
    
    Args:
        n_experiments (int): Número de experimentos por método/topologia/latência
    """
    
    print("=" * 80)
    print("EXPERIMENTO DE VARIAÇÃO DE LATÊNCIA")
    print("=" * 80)
    print(f"Número de experimentos por configuração: {n_experiments}")
    
    # Configurações do experimento
    topologias_paths = ['./nsfnetbw/', './geant2bw/', './synth50bw/']
    latency_range = np.arange(10, 201, 5)  # 10ms a 200ms em passos de 10ms
    fixed_capacity = 0.1  # Capacidade fixa para isolar efeito da latência
    L_cloud_fog = 100000
    C_cloud_fog = 25
    
    # Definir métodos experimentais
    experimentos_solvers = {
        "Excentricidade_Lat_max": exp_excentricidade_lat_min.solver,
        "Excentricidade_Cap_Min": exp_excentricidade_cap_max_v2.solver,
        "Conectividade_Lat_Max": exp_conectividade_lat_max.solver,
        "Conectividade_Cap_Min": exp_conectividade_cap_min.solver
    }
    
    # Carregar dados das topologias
    print("Carregando dados das topologias...")
    topology_samples = {}
    for topology_path in topologias_paths:
        print(f"  Carregando de: {topology_path}")
        try:
            reader = datanetAPI.DatanetAPI(topology_path, [])
            it_topo = iter(reader)
            samples = {
                "lat": [],
                "cap": [],
                "dados": [],
                "n_nodes": 0,
                "actual_samples": 0
            }
            
            for sample_idx in range(n_experiments):  # Carregar amostras suficientes para os experimentos
                try:
                    dados_sample = next(it_topo)
                    lat, cap = aux.extrai_latencias_capacidades(dados_sample)
                    samples["lat"].append(lat)
                    samples["cap"].append(cap)
                    samples["dados"].append(dados_sample)
                    samples["actual_samples"] += 1
                except StopIteration:
                    if sample_idx == 0:
                        print(f"    ERRO: Nenhuma amostra encontrada em {topology_path}")
                    else:
                        print(f"    Aviso: Apenas {sample_idx} amostras encontradas")
                    break
            
            if samples["lat"]:
                samples["n_nodes"] = len(samples["lat"][0])
                topology_samples[topology_path] = samples
                print(f"    Carregadas {samples['actual_samples']} amostras com {samples['n_nodes']} nós")
            else:
                print(f"    ERRO: Nenhuma amostra válida carregada de {topology_path}")
                topology_samples[topology_path] = None
            
        except Exception as e:
            print(f"    ERRO ao carregar {topology_path}: {e}")
            topology_samples[topology_path] = None
    
    # Estrutura de resultados: {topology: {method: {'latencies': [], 'fog_counts': []}}}
    latency_results = {}
    for topology_path in topologias_paths:
        topology_name = topology_path.strip('./').replace('/', '')
        latency_results[topology_name] = {}
        for method_name in list(experimentos_solvers.keys()) + ['OR-Tools']:
            latency_results[topology_name][method_name] = {'latencies': [], 'fog_counts': []}
    
    # Executar experimento para cada topologia
    for topology_path in topologias_paths:
        topology_name = topology_path.strip('./').replace('/', '')
        print(f"\nProcessando topologia: {topology_name}")
        
        samples = topology_samples.get(topology_path)
        if not samples:
            print(f"  Pulando {topology_name} - dados não carregados")
            continue
        
        # Usar primeira amostra para consistência
        latenciass = samples["lat"][0]
        capacidadess = samples["cap"][0]
        dados = samples["dados"][0] if samples["dados"] else None
        n_nodes = samples["n_nodes"]
        
        # Testar cada requisito de latência
        for L_max in latency_range:
            print(f"  Testando L_max = {L_max}ms")
            
            # Testar cada método heurístico
            for method_name, solver_func in experimentos_solvers.items():
                fog_counts_for_latency = []
                
                # Executar múltiplos experimentos para esta configuração
                for exp_idx in range(min(n_experiments, samples["actual_samples"])):
                    latenciass = samples["lat"][exp_idx]
                    capacidadess = samples["cap"][exp_idx]
                    dados = samples["dados"][exp_idx] if samples["dados"] else None
                    
                    cloud_position = random.randint(0, samples["n_nodes"] - 1)
                    solver_args = [latenciass, capacidadess, L_max, fixed_capacity, 
                                 L_cloud_fog, C_cloud_fog, cloud_position]
                    
                    # Adicionar dados para métodos de conectividade
                    if "Conectividade" in method_name and dados is not None:
                        solver_args.append(dados)
                    elif "Conectividade" in method_name and dados is None:
                        # Pular métodos de conectividade se não há dados disponíveis
                        continue
                    
                    try:
                        resultado = solver_func(*solver_args)
                        fog_count = sum(resultado[1]) - 1  # Subtrair 1 para excluir cloud
                        fog_counts_for_latency.append(fog_count)
                    except Exception as e:
                        print(f"    Erro em {method_name}, exp {exp_idx}: {e}")
                
                # Calcular média dos fog counts para esta latência
                if fog_counts_for_latency:
                    avg_fog_count = np.mean(fog_counts_for_latency)
                    latency_results[topology_name][method_name]['latencies'].append(L_max)
                    latency_results[topology_name][method_name]['fog_counts'].append(avg_fog_count)
            
            # Testar OR-Tools
            fog_counts_ortools = []
            for exp_idx in range(min(n_experiments, samples["actual_samples"])):
                latenciass = samples["lat"][exp_idx]
                capacidadess = samples["cap"][exp_idx]
                cloud_position = random.randint(0, samples["n_nodes"] - 1)
                
                try:
                    # Usar alpha = 0.5 para OR-Tools (solução balanceada)
                    alpha = 0
                    otimo = ortool_l.solveProblem(latenciass, capacidadess, L_max, fixed_capacity, 
                                               L_cloud_fog, C_cloud_fog, cloud_position, alpha)
                    if otimo and len(otimo) >= 3:
                        fog_count = sum(otimo[1]) - 2  # Subtrair 2 para excluir cloud e fog
                        fog_counts_ortools.append(fog_count)
                except Exception as e:
                    print(f"    Erro em OR-Tools, exp {exp_idx}: {e}")
            
            # Calcular média dos fog counts OR-Tools para esta latência
            if fog_counts_ortools:
                avg_fog_count_ortools = np.mean(fog_counts_ortools)
                latency_results[topology_name]['OR-Tools']['latencies'].append(L_max)
                latency_results[topology_name]['OR-Tools']['fog_counts'].append(avg_fog_count_ortools)
    
    # Criar o gráfico
    print("\nCriando gráfico...")
    fig, axs = plt.subplots(1, 3, figsize=(18, 6))
    topology_names = [path.strip('./').replace('/', '') for path in topologias_paths]
    
    # Definir cores para cada método (incluindo OR-Tools)
    colors = {
        'Excentricidade_Lat_max': 'red',
        'Excentricidade_Cap_Min': 'blue', 
        'Conectividade_Lat_Max': 'green',
        'Conectividade_Cap_Min': 'orange',
        'OR-Tools': 'black'
    }
    
    # Nomes mais limpos para as legendas
    legend_names = {
        'Excentricidade_Lat_max': 'Exc. Lat. Max',
        'Excentricidade_Cap_Min': 'Exc. Cap. Min', 
        'Conectividade_Lat_Max': 'Con. Lat. Max',
        'Conectividade_Cap_Min': 'Con. Cap. Min',
        'OR-Tools': 'Ótimo'
    }
    
    # Plotar para cada topologia
    for idx, topology_name in enumerate(topology_names):
        ax = axs[idx]
        
        # Coletar todos os valores de fog counts para determinar escala do eixo Y
        all_fog_counts = []
        
        # Plotar cada método (heurísticas + OR-Tools)
        for method_name in list(experimentos_solvers.keys()) + ['OR-Tools']:
            data = latency_results[topology_name][method_name]
            if data['latencies'] and data['fog_counts']:
                ax.plot(data['latencies'], data['fog_counts'], 
                       color=colors[method_name], marker='o', linewidth=2, 
                       markersize=4, label=legend_names[method_name])
                all_fog_counts.extend(data['fog_counts'])
        
        ax.set_xlabel('Requisito de Latência (ms)', fontsize=12)
        if idx == 0:  # Apenas o primeiro subplot tem ylabel
            ax.set_ylabel('Número de Servidores Fog', fontsize=12)
        ax.set_title(f'{topology_name}', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(10, 200)
        
        # Definir escala do eixo Y baseada nos dados desta topologia
        if all_fog_counts:
            min_fogs = min(all_fog_counts)
            max_fogs = max(all_fog_counts)
            margin = (max_fogs - min_fogs) * 0.1  # 10% de margem
            ax.set_ylim(max(0, min_fogs - margin), max_fogs + margin)
        
        # Adicionar legenda individual para cada subplot
        ax.legend(loc='upper right', fontsize=9)
    
    plt.tight_layout()
    
    # Salvar o gráfico
    result_pdf_dir = './result_pdf'
    if not os.path.exists(result_pdf_dir):
        os.makedirs(result_pdf_dir)
    
    # Nome do arquivo com parâmetros do experimento
    min_lat = int(latency_range.min())
    max_lat = int(latency_range.max())
    step_lat = int(latency_range[1] - latency_range[0])
    capacity_str = str(fixed_capacity).replace('.', 'p')  # 0.1 -> 0p1
    
    latency_experiment_pdf = f"{result_pdf_dir}/latency_experiment_lat{min_lat}-{max_lat}step{step_lat}_cap{capacity_str}_n{n_experiments}.pdf"
    plt.savefig(latency_experiment_pdf, bbox_inches='tight', format='pdf')
    print(f"\nGráfico salvo em: {latency_experiment_pdf}")
    plt.show()
    
    print("=" * 80)
    print("EXPERIMENTO DE VARIAÇÃO DE LATÊNCIA CONCLUÍDO")
    print("=" * 80)
    
    return latency_results

if __name__ == "__main__":
    # Executar experimento se chamado diretamente com 300 experimentos por configuração
    results = run_latency_experiment(n_experiments=300)