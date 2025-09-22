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
import os
import csv
import exp_excentricidade_lat_min
import exp_excentricidade_cap_max_v2
import exp_conectividade_lat_max
import exp_conectividade_cap_min

# Configurar seed para reprodutibilidade dos experimentos
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)
# Configurar variáveis de ambiente para determinismo em solvers
os.environ['PYTHONHASHSEED'] = str(RANDOM_SEED)
print(f"Seed configurado para: {RANDOM_SEED}")

# Função para re-aplicar seeds antes de cada execução crítica
def reset_seeds():
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

# 1. Define Application Requirements
requisitos = {
    "iot_industrial": {
        "nome": "IoT Industrial",
        "latencia": 15,
        "capacidade": 0.1
    },
    "streaming_4k": {
        "nome": "Streaming de Vídeo 4K",
        "latencia": 70,
        "capacidade": 3.2
    },
    "jogos_online": {
        "nome": "Jogos Online (Cloud Gaming)",
        "latencia": 20,
        "capacidade": 4
    },
    "videoconferencia_hd": {
        "nome": "Videoconferência (HD)",
        "latencia": 100,
        "capacidade": 1.5
    }
}

ortool_app_key = "iot_industrial"

# 2. Define Experiment Solvers and their Names
experimentos_solvers = {
    "Excentricidade_Lat_max": exp_excentricidade_lat_min.solver,
    "Excentricidade_Cap_Min": exp_excentricidade_cap_max_v2.solver,
    "Conectividade_Lat_Max": exp_conectividade_lat_max.solver,
    "Conectividade_Cap_Min": exp_conectividade_cap_min.solver
}

# 3. Define Topologies (Dataset Paths) relative to parent folder
topologias_paths = ['./nsfnetbw/', './geant2bw/', './synth50bw/']

# Initialize timing dictionaries by topology
heuristic_timing = {}
ortools_timing = {}
for topology_path in topologias_paths:
    topology_name = topology_path.strip('./').replace('/', '')
    heuristic_timing[topology_name] = {name: [] for name in experimentos_solvers.keys()}
    ortools_timing[topology_name] = []

# 4. Experiment Parameters
n_simulacoes_por_config = 1
L_cloud_fog = 100000
C_cloud_fog = 25
n_pontos_ortool = 1
alphas = np.linspace(0, 1, n_pontos_ortool)

escala_latencia = 0.025/2

print("--- Pré-carregando todas as amostras de dados ---")
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
        for k in range(n_simulacoes_por_config):
            try:
                dados_sample = next(it_topo)
                lat, cap = aux.extrai_latencias_capacidades(dados_sample)
                samples["lat"].append(lat)
                samples["cap"].append(cap)
                samples["dados"].append(dados_sample)
            except StopIteration:
                if k == 0:
                    print(f"    ERRO: Nenhuma amostra de dados encontrada em {topology_path}.")
                else:
                    print(f"    Aviso: Apenas {k} amostras de dados encontradas (solicitado {n_simulacoes_por_config}).")
                break
        if samples["lat"]:
            samples["n_nodes"] = len(samples["lat"][0])
            samples["actual_samples"] = len(samples["lat"])
            topology_samples[topology_path] = samples
            print(f"    Carregadas {samples['actual_samples']} amostras para {topology_path}")
        else:
            topology_samples[topology_path] = None
    except Exception as e:
        print(f"  ERRO CRÍTICO ao carregar dados para {topology_path}: {e}")
        topology_samples[topology_path] = None

results_list = []
csv_headers = ["Experiment_Name", "Requirement_Name", "Topology_Name", "Avg_Fogs", "Avg_Latency_ms"]

all_results_raw = {}

for exp_name, solver_func in experimentos_solvers.items():
    print(f"--- Running Experiment Type: {exp_name} ---")
    for topology_path in topologias_paths:
        print(f"  --- Topology: {topology_path} ---")
        samples = topology_samples.get(topology_path)
        if not samples:
            print(f"    Pulando topologia {topology_path} devido a erro no carregamento de dados.")
            continue
        try:
            sim_latenciass = samples["lat"]
            sim_capacidadess = samples["cap"]
            sim_dadozes = samples["dados"]
            current_n_nodes = samples["n_nodes"]
            actual_samples_loaded = samples["actual_samples"]

            for req_key, req_config in requisitos.items():
                req_name = req_config["nome"]
                L_max = req_config["latencia"]
                C_min = req_config["capacidade"]
                print(f"    --- Requirement: {req_name} (L_max={L_max}ms, C_min={C_min}Mbps) ---")

                total_fogs_for_avg = 0
                total_latency_for_avg = 0
                successful_runs_this_config = 0

                if req_name not in all_results_raw:
                    all_results_raw[req_name] = {}
                if topology_path not in all_results_raw[req_name]:
                    all_results_raw[req_name][topology_path] = {}
                if exp_name not in all_results_raw[req_name][topology_path]:
                    all_results_raw[req_name][topology_path][exp_name] = {"fogs": [], "latency": []}
                for i in range(actual_samples_loaded):
                    reset_seeds()  # Re-aplicar seeds antes de cada execução
                    cloud_position = random.randint(0, current_n_nodes - 1)
                    current_latencias = sim_latenciass[i]
                    current_capacidades = sim_capacidadess[i]
                    solver_args = [current_latencias, current_capacidades, L_max, C_min, L_cloud_fog, C_cloud_fog, cloud_position]
                    if "Conectividade" in exp_name:
                        if i < len(sim_dadozes):
                            solver_args.append(sim_dadozes[i])
                        else:
                            print(f"      ERROR: Missing 'dados' object for connectivity solver, sample {i}. Skipping this run.")
                            continue
                    try:
                        # Time the heuristic solver execution
                        start_time = time.time()
                        resultado_solver = solver_func(*solver_args)
                        end_time = time.time()
                        execution_time = end_time - start_time
                        topology_name = topology_path.strip('./').replace('/', '')
                        heuristic_timing[topology_name][exp_name].append(execution_time)
                        
                        num_fogs_in_run = sum(resultado_solver[1])
                        latency_in_run = resultado_solver[2]
                        total_fogs_for_avg += num_fogs_in_run
                        total_latency_for_avg += latency_in_run
                        successful_runs_this_config += 1
                        all_results_raw[req_name][topology_path][exp_name]["fogs"].append(num_fogs_in_run)
                        all_results_raw[req_name][topology_path][exp_name]["latency"].append(latency_in_run / escala_latencia)
                    except IndexError:
                        print(f"      ERROR: Solver {exp_name} for {req_name} on {topology_path}, sample {i} returned unexpected result format.")
                    except Exception as e:
                        print(f"      ERROR running solver {exp_name} for {req_name} on {topology_path}, sample {i}: {e}")

                if successful_runs_this_config > 0:
                    avg_fogs = total_fogs_for_avg / successful_runs_this_config
                    avg_latency = total_latency_for_avg / successful_runs_this_config
                else:
                    avg_fogs = float('nan')
                    avg_latency = float('nan')
                    print(f"      WARNING: No successful runs for {exp_name}, {req_name} on {topology_path}.")

                results_list.append({
                    "Experiment_Name": exp_name,
                    "Requirement_Name": req_name,
                    "Topology_Name": topology_path,
                    "Avg_Fogs": f"{avg_fogs:.2f}" if not np.isnan(avg_fogs) else "NaN",
                    "Avg_Latency_ms": f"{(avg_latency/escala_latencia):.2f}" if not np.isnan(avg_latency) else "NaN"
                })
                print(f"      Avg Fogs: {avg_fogs:.2f}, Avg Latency: {avg_latency:.2f} ms (over {successful_runs_this_config} runs)")
        except Exception as e:
            print(f"  CRITICAL ERROR processing topology {topology_path}: {e}")
            continue

dados_reorganizados = {}
for item in results_list:
    aplicacao = item["Requirement_Name"]
    experimento = item["Experiment_Name"]
    topologia = item["Topology_Name"]

    if aplicacao not in dados_reorganizados:
        dados_reorganizados[aplicacao] = {}
    if topologia not in dados_reorganizados[aplicacao]:
        dados_reorganizados[aplicacao][topologia] = {}
    
    dados_reorganizados[aplicacao][topologia][experimento] = {
        "avg_fogs": item["Avg_Fogs"],
        "avg_latency_ms": item["Avg_Latency_ms"]
    }

resultado_aplicacoes_dict = dados_reorganizados
pontos = resultado_aplicacoes_dict

for req_key_loop, ortool_app_config in requisitos.items():
    ortool_app_name_for_pontos = ortool_app_config["nome"]
    print(f"\n==== Executando OR-Tools para requisito: {ortool_app_name_for_pontos} ====")

    # Coletar tipos de experimentos heurísticos disponíveis para este requisito
    all_heuristic_exp_types = set()
    if ortool_app_name_for_pontos in pontos:
        for topo_name in pontos[ortool_app_name_for_pontos]:
            if isinstance(pontos[ortool_app_name_for_pontos][topo_name], dict):
                for exp_name in pontos[ortool_app_name_for_pontos][topo_name].keys():
                    all_heuristic_exp_types.add(exp_name)
    sorted_heuristic_exp_types = sorted(list(all_heuristic_exp_types))

    default_markers = ['s', '^', 'D', 'P', 'o', '*', 'X', 'v', '<', '>']
    cmap_colors = plt.cm.get_cmap('Set1', len(sorted_heuristic_exp_types) if sorted_heuristic_exp_types else 1)

    marker_map = {exp_name: default_markers[i % len(default_markers)] for i, exp_name in enumerate(sorted_heuristic_exp_types)}
    color_map = {exp_name: cmap_colors(i) for i, exp_name in enumerate(sorted_heuristic_exp_types)}

    # Portuguese labels for metaheuristics
    portuguese_labels = {
        "Excentricidade_Lat_max": "Excentricidade (Baseada em Latência)",
        "Excentricidade_Cap_Min": "Excentricidade (Baseada em Capacidade)",
        "Conectividade_Lat_Max": "Conectividade (Baseada em Latência)",
        "Conectividade_Cap_Min": "Conectividade (Baseada em Capacidade)",
    }

    fig, axs = plt.subplots(1, len(topologias_paths), figsize=(21, 7), sharey=False)
    if len(topologias_paths) == 1:
        axs = np.array([axs])

    for idx, dataset_path_str in enumerate(topologias_paths):
        print(f"\nProcessing dataset: {dataset_path_str} for OR-Tools with {ortool_app_name_for_pontos}...")
        current_ax = axs[idx]
        samples = topology_samples.get(dataset_path_str)
        if not samples:
            print(f"  Pulando plot para {dataset_path_str} devido a erro no carregamento de dados.")
            dataset_title = os.path.basename(os.path.normpath(dataset_path_str)).upper()
            current_ax.set_title(f"{dataset_title}\n(Erro de Carregamento de Dados)")
            current_ax.text(0.5, 0.5, 'Erro de Carregamento de Dados', horizontalalignment='center', verticalalignment='center', transform=current_ax.transAxes)
            continue
        n_nodes = samples["n_nodes"]
        latenciass_exp_ortool = samples["lat"]
        capacidadess_exp_ortool = samples["cap"]
        # Use only the first 5% of the samples used by the metaheuristics (at least 1)
        n_metaheuristica_samples = samples["actual_samples"]
        n_experimentos_ortool = max(1, n_metaheuristica_samples // 20)
        if n_experimentos_ortool < n_metaheuristica_samples:
            print(f"  OR-Tools: usando apenas 5% dos dados: {n_experimentos_ortool} de {n_metaheuristica_samples} amostras (primeiras)")
        else:
            print(f"  OR-Tools: total de amostras disponível é pequeno; usando {n_experimentos_ortool} amostra(s)")
        L_max = ortool_app_config["latencia"]
        C_min = ortool_app_config["capacidade"]
        plot_n_fogs_ortool = []
        plot_latencia_media_ortool = []
        progress_count = 0
        for alpha in alphas:
            reset_seeds()  # Re-aplicar seeds antes de cada execução do OR-Tools
            cloud_position = random.randint(0, n_nodes-1)
            fogs_sum_for_alpha = 0
            lat_sum_for_alpha = 0
            # Iterate only over the first 5% of samples
            for i in range(n_experimentos_ortool):
                # Time the OR-Tools solver execution
                start_time = time.time()
                otimo = ortool_l.solveProblem(latenciass_exp_ortool[i], capacidadess_exp_ortool[i], L_max, C_min, L_cloud_fog, C_cloud_fog, cloud_position, alpha)
                end_time = time.time()
                execution_time = end_time - start_time
                topology_name = dataset_path_str.strip('./').replace('/', '')
                ortools_timing[topology_name].append(execution_time)
                
                if otimo and len(otimo) >= 3:
                    fogs_sum_for_alpha += sum(otimo[1]) - 1
                    lat_sum_for_alpha += otimo[2]
            avg_fogs_ortool = fogs_sum_for_alpha / n_experimentos_ortool if n_experimentos_ortool > 0 else 0
            avg_lat_ortool = lat_sum_for_alpha / n_experimentos_ortool if n_experimentos_ortool > 0 else 0
            
            plot_n_fogs_ortool.append(avg_fogs_ortool)
            plot_latencia_media_ortool.append(avg_lat_ortool / (escala_latencia))
            
            progress_count += 1
            if progress_count % 20 == 0 or progress_count == len(alphas):
                print(f"  OR-Tool ({ortool_app_name_for_pontos}) on {dataset_path_str}, Alpha Progress: {progress_count}/{len(alphas)}")
        
        current_ax.scatter(
            plot_latencia_media_ortool, plot_n_fogs_ortool,
            marker='.', color='blue', alpha=0.8, s=30, zorder=1, label='Ótimo'
        )

        if ortool_app_name_for_pontos in pontos and \
           dataset_path_str in pontos[ortool_app_name_for_pontos] and \
           isinstance(pontos[ortool_app_name_for_pontos][dataset_path_str], dict):

            experiments_data = pontos[ortool_app_name_for_pontos][dataset_path_str]
            for exp_name, exp_results in experiments_data.items():
                try:
                    raw = all_results_raw.get(ortool_app_name_for_pontos, {}).get(dataset_path_str, {}).get(exp_name, None)
                    marker_style = marker_map.get(exp_name, 'o')
                    point_color = color_map.get(exp_name, 'black')
                    if raw and len(raw["fogs"]) > 1 and len(raw["latency"]) > 1:
                        fogs_arr = np.array(raw["fogs"])
                        lat_arr = np.array(raw["latency"])
                        n = len(fogs_arr)
                        mean_fogs = np.mean(fogs_arr)
                        mean_lat = np.mean(lat_arr)
                        conf = 0.95
                        h_fogs = sem(fogs_arr) * t.ppf((1 + conf) / 2., n-1)
                        h_lat = sem(lat_arr) * t.ppf((1 + conf) / 2., n-1)
                        current_ax.errorbar(
                            mean_lat, mean_fogs,
                            xerr=h_lat, yerr=h_fogs,
                            fmt=marker_style,
                            color=point_color,
                            markeredgecolor='black',
                            markersize=10,
                            elinewidth=2,
                            capsize=6,
                            zorder=2,
                            label=portuguese_labels.get(exp_name, exp_name)
                        )
                    elif raw and len(raw["fogs"]) == 1 and len(raw["latency"]) == 1:
                        current_ax.scatter(
                            raw["latency"][0], raw["fogs"][0],
                            marker=marker_style,
                            s=80,
                            edgecolor='black',
                            color=point_color,
                            zorder=2
                        )
                    else:
                        fogs = float(exp_results['avg_fogs'])
                        latency = float(exp_results['avg_latency_ms'])
                        current_ax.scatter(
                            latency, fogs,
                            marker=marker_style,
                            s=80,
                            edgecolor='black',
                            color=point_color,
                            zorder=2
                        )
                except (ValueError, KeyError, TypeError) as e:
                    print(f"  Skipping point for {ortool_app_name_for_pontos}, {exp_name} in {dataset_path_str} due to data issue: {e}")
        else:
            print(f"  No heuristic data in 'pontos' for {ortool_app_name_for_pontos} in {dataset_path_str}")

        # Axis labels and title per subplot
        current_ax.set_xlabel('Latência média (ms)', fontsize=14)
        current_ax.set_ylabel('Número de fogs', fontsize=14)
        dataset_name_for_title = os.path.basename(os.path.normpath(dataset_path_str)).upper()
        # Remove title from top of subplot
        current_ax.grid(True)
        current_ax.set_ylim(0, n_nodes + 1 if n_nodes > 0 else 10)
        current_ax.set_xlim(left=0)
        current_ax.set_ylim(bottom=0)
        
        # Increase tick label font size
        current_ax.tick_params(axis='both', which='major', labelsize=12)
        
        # Add subplot label (a), (b), (c) with topology name at the bottom
        subplot_letters = ['a)', 'b)', 'c)']
        if idx < len(subplot_letters):
            label_text = f"{subplot_letters[idx]} {dataset_name_for_title}"
            current_ax.text(0.5, -0.15, label_text, 
                          horizontalalignment='center', 
                          verticalalignment='top',
                          transform=current_ax.transAxes,
                          fontsize=24)

    # Montar legenda
    legend_elements = []
    legend_elements.append(plt.Line2D([0], [0], marker='.', color='w', 
                                       label='Ótimo',
                                       markerfacecolor='blue', markersize=10, alpha=0.8))
    for exp_name in sorted_heuristic_exp_types:
        marker_style = marker_map.get(exp_name, 'x')
        point_color = color_map.get(exp_name, 'black')
        legend_elements.append(plt.Line2D([0], [0], marker=marker_style, color='w', label=portuguese_labels.get(exp_name, exp_name),
                                          markerfacecolor=point_color, markeredgecolor='black', markersize=9))

    if legend_elements:
        fig.legend(handles=legend_elements, loc='upper center', 
                   ncol=min(5, len(legend_elements)), 
                   bbox_to_anchor=(0.5, 1.04), 
                   fontsize=12)

    # Salvar PDF por requisito
    result_pdf_dir = './result_pdf'
    if not os.path.exists(result_pdf_dir):
        os.makedirs(result_pdf_dir)

    filename_pdf = f"{result_pdf_dir}/{req_key_loop}_lat{ortool_app_config['latencia']}_cap{ortool_app_config['capacidade']}_sim{n_simulacoes_por_config}_ort{n_pontos_ortool}.pdf"

    plt.tight_layout(rect=[0, 0.08, 1, 1.0])
    plt.savefig(filename_pdf, bbox_inches='tight', format='pdf')
    #plt.show()

# Print timing summary as a table with confidence intervals
print("\nTempo médio de execução por topologia (segundos) ± Intervalo de Confiança (90%):")
print("="*120)

# Get topology names
topology_names = [path.strip('./').replace('/', '') for path in topologias_paths]

# Print header
header = f"{'Método':<25}"
for topo_name in topology_names:
    header += f"{topo_name:>30}"
print(header)
print("-" * len(header))

# Print heuristic times with confidence intervals
for method_name in experimentos_solvers.keys():
    row = f"{method_name:<25}"
    for topo_name in topology_names:
        times = heuristic_timing[topo_name][method_name]
        if times and len(times) > 1:
            avg_time = np.mean(times)
            n = len(times)
            # Calculate 90% confidence interval
            confidence = 0.90
            h = sem(times) * t.ppf((1 + confidence) / 2., n-1)
            row += f"{avg_time:>12.6f} ± {h:>8.6f}"
        elif times and len(times) == 1:
            avg_time = times[0]
            row += f"{avg_time:>12.6f} ± {'N/A':>8}"
        else:
            row += f"{'N/A':>30}"
    print(row)

# Print OR-Tools times with confidence intervals
row = f"{'OR-Tools':<25}"
for topo_name in topology_names:
    times = ortools_timing[topo_name]
    if times and len(times) > 1:
        avg_time = np.mean(times)
        n = len(times)
        # Calculate 90% confidence interval
        confidence = 0.90
        h = sem(times) * t.ppf((1 + confidence) / 2., n-1)
        row += f"{avg_time:>12.6f} ± {h:>8.6f}"
    elif times and len(times) == 1:
        avg_time = times[0]
        row += f"{avg_time:>12.6f} ± {'N/A':>8}"
    else:
        row += f"{'N/A':>30}"
print(row)

print("="*120)
