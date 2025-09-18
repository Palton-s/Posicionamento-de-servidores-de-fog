import sys, os
# Ensure parent directory is on path to import datanetAPI and shared modules if needed
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

import numpy as np
import matplotlib.pyplot as plt
import random
import datanetAPI
import aux_functions as aux
import exp_excentricidade_lat_min
from scipy.stats import sem, t

# Configurações do experimento
TOPOLOGY_PATHS = ['./nsfnetbw/', './geant2bw/', './synth50bw/']
TOPOLOGY_NAMES = ['NSFNET', 'GEANT2', 'SYNTH50']
N_TOTAL_EXPERIMENTS = 400
SAMPLE_SIZES = list(range(1, 380, 10))  # De 1 até 500, de 10 em 10
CONFIDENCE_LEVEL = 0.90

# Configurações da aplicação IoT Industrial
APP_CONFIG = {
    "nome": "IoT Industrial",
    "latencia": 15,  # ms
    "capacidade": 0.1  # Mbps
}

# Parâmetros da rede
L_cloud_fog = 100000
C_cloud_fog = 25
escala_latencia = 0.025/2

print(f"=== Análise de Convergência do Erro - {APP_CONFIG['nome']} ===")
print(f"Topologias: {', '.join(TOPOLOGY_NAMES)}")
print(f"Total de experimentos por topologia: {N_TOTAL_EXPERIMENTS}")
print(f"Intervalo de confiança: {CONFIDENCE_LEVEL*100}%")
print()

# Verificar se todos os diretórios de topologia existem
print("Verificando diretórios das topologias:")
for topology_path, topology_name in zip(TOPOLOGY_PATHS, TOPOLOGY_NAMES):
    full_path = os.path.join(PARENT_DIR, topology_path)
    exists = os.path.exists(full_path)
    print(f"  {topology_name}: {full_path} -> {'EXISTE' if exists else 'NÃO EXISTE'}")
    if exists:
        files = os.listdir(full_path)
        print(f"    Arquivos encontrados: {len(files)} arquivos")
print()

# Dicionário para armazenar resultados de todas as topologias
all_topology_results = {}

# Loop através de todas as topologias
for topo_idx, (topology_path, topology_name) in enumerate(zip(TOPOLOGY_PATHS, TOPOLOGY_NAMES)):
    print(f"\n{'='*60}")
    print(f"PROCESSANDO TOPOLOGIA: {topology_name}")
    print(f"{'='*60}")
    
    # 1. Carregar dados da topologia
    print("Carregando dados da topologia...")
    print(f"Caminho completo: {os.path.join(PARENT_DIR, topology_path)}")
    
    try:
        reader = datanetAPI.DatanetAPI(os.path.join(PARENT_DIR, topology_path), [])
        it_topo = iter(reader)
        
        # Coletar todas as amostras necessárias
        latencias_samples = []
        capacidades_samples = []
        
        for k in range(N_TOTAL_EXPERIMENTS):
            try:
                dados_sample = next(it_topo)
                lat, cap = aux.extrai_latencias_capacidades(dados_sample)
                latencias_samples.append(lat)
                capacidades_samples.append(cap)
            except StopIteration:
                print(f"Aviso: Apenas {k} amostras encontradas (solicitado {N_TOTAL_EXPERIMENTS})")
                break
        
        n_samples_loaded = len(latencias_samples)
        if n_samples_loaded == 0:
            print(f"ERRO: Nenhuma amostra carregada para {topology_name}")
            continue
        
        n_nodes = len(latencias_samples[0])
        print(f"Carregadas {n_samples_loaded} amostras")
        print(f"Número de nós: {n_nodes}")
        
    except Exception as e:
        print(f"ERRO ao carregar dados para {topology_name}: {e}")
        print(f"Verificando se o diretório existe: {os.path.exists(os.path.join(PARENT_DIR, topology_path))}")
        continue

    # 2. Executar todos os experimentos da metaheurística
    print(f"\nExecutando experimentos com metaheurística Excentricidade (Latência mínima)...")

    L_max = APP_CONFIG["latencia"]
    C_min = APP_CONFIG["capacidade"]

    results_fogs = []
    results_latency = []

    for i in range(n_samples_loaded):
        if (i + 1) % 50 == 0 or (i + 1) == n_samples_loaded:
            print(f"  Progresso: {i + 1}/{n_samples_loaded}")
        
        # Configurar experimento
        cloud_position = random.randint(0, n_nodes - 1)
        current_latencias = latencias_samples[i]
        current_capacidades = capacidades_samples[i]
        
        try:
            # Executar metaheurística
            resultado = exp_excentricidade_lat_min.solver(
                current_latencias, 
                current_capacidades, 
                L_max, 
                C_min, 
                L_cloud_fog, 
                C_cloud_fog, 
                cloud_position
            )
            
            num_fogs = sum(resultado[1])
            avg_latency = resultado[2]
            
            results_fogs.append(num_fogs)
            results_latency.append(avg_latency / escala_latencia)
            
        except Exception as e:
            print(f"  ERRO no experimento {i}: {e}")
            continue

    print(f"Experimentos concluídos: {len(results_fogs)}")

    # 3. Calcular erro para diferentes tamanhos de amostra
    print(f"\nCalculando intervalos de confiança ({CONFIDENCE_LEVEL*100}%) para diferentes tamanhos de amostra...")

    sample_sizes_actual = []
    errors_fogs = []
    errors_latency = []
    percent_errors_fogs = []
    percent_errors_latency = []
    means_fogs = []
    means_latency = []

    for sample_size in SAMPLE_SIZES:
        if sample_size > len(results_fogs):
            continue
        
        # Usar as primeiras 'sample_size' amostras
        sample_fogs = np.array(results_fogs[:sample_size])
        sample_latency = np.array(results_latency[:sample_size])
        
        # Calcular estatísticas
        mean_fogs = np.mean(sample_fogs)
        mean_latency = np.mean(sample_latency)
        
        # Calcular intervalo de confiança
        n = len(sample_fogs)
        alpha = 1 - CONFIDENCE_LEVEL
        t_critical = t.ppf(1 - alpha/2, n - 1)
        
        # Erro padrão
        se_fogs = sem(sample_fogs)
        se_latency = sem(sample_latency)
        
        # Margem de erro (metade da largura do intervalo de confiança)
        error_fogs = se_fogs * t_critical
        error_latency = se_latency * t_critical
        
        # Calcular erro percentual em relação à média
        percent_error_fogs = (error_fogs / mean_fogs * 100) if mean_fogs > 0 else 0
        percent_error_latency = (error_latency / mean_latency * 100) if mean_latency > 0 else 0
        
        sample_sizes_actual.append(sample_size)
        errors_fogs.append(error_fogs)
        errors_latency.append(error_latency)
        percent_errors_fogs.append(percent_error_fogs)
        percent_errors_latency.append(percent_error_latency)
        means_fogs.append(mean_fogs)
        means_latency.append(mean_latency)

    # Armazenar resultados desta topologia
    all_topology_results[topology_name] = {
        'sample_sizes': sample_sizes_actual.copy(),
        'errors_fogs': errors_fogs.copy(),
        'errors_latency': errors_latency.copy(),
        'percent_errors_fogs': percent_errors_fogs.copy(),
        'percent_errors_latency': percent_errors_latency.copy(),
        'means_fogs': means_fogs.copy(),
        'means_latency': means_latency.copy(),
        'n_experiments': len(results_fogs)
    }
    
    print(f"Primeiros 10 pontos para {topology_name}:")
    for i in range(min(10, len(sample_sizes_actual))):
        n = sample_sizes_actual[i]
        err_f = errors_fogs[i]
        err_l = errors_latency[i]
        percent_err_f = percent_errors_fogs[i]
        percent_err_l = percent_errors_latency[i]
        mean_f = means_fogs[i]
        mean_l = means_latency[i]
        print(f"  n={n:3d}: Fogs = {mean_f:.2f} ± {err_f:.3f} ({percent_err_f:.1f}%), Latência = {mean_l:.2f} ± {err_l:.3f} ms ({percent_err_l:.1f}%)")

# 4. Plotar gráficos comparativos
print("\nGerando gráficos comparativos...")

# Cores e estilos para cada topologia
colors = ['blue', 'red', 'green']
markers = ['o', 's', '^']
linestyles = ['-', '--', '-.']

# Gráfico 1: Erro no número de fogs
fig1, ax1 = plt.subplots(1, 1, figsize=(10, 6))

for idx, (topo_name, topo_data) in enumerate(all_topology_results.items()):
    ax1.plot(topo_data['sample_sizes'], topo_data['errors_fogs'], 
             color=colors[idx], marker=markers[idx], linestyle=linestyles[idx],
             linewidth=2, markersize=4, label=topo_name, alpha=0.8)

ax1.set_xlabel('Experimentos', fontsize=14)
ax1.set_ylabel('Margem de Erro (Número de Fogs)', fontsize=14)
#ax1.set_title('Convergência do Erro - Número de Fogs\n(Intervalo de Confiança 90%)', fontsize=14)
ax1.grid(True, alpha=0.3)
ax1.legend(fontsize=12)
ax1.tick_params(axis='both', which='major', labelsize=12)

plt.tight_layout()

# Salvar gráfico de fogs
output_file_fogs = f'./result_pdf/convergencia_erro_fogs_{APP_CONFIG["nome"].replace(" ", "_").lower()}_todas_topologias.pdf'
os.makedirs('./result_pdf', exist_ok=True)
plt.savefig(output_file_fogs, bbox_inches='tight', format='pdf')
print(f"Gráfico de fogs salvo em: {output_file_fogs}")

# Gráfico 2: Erro na latência média
fig2, ax2 = plt.subplots(1, 1, figsize=(10, 6))

for idx, (topo_name, topo_data) in enumerate(all_topology_results.items()):
    ax2.plot(topo_data['sample_sizes'], topo_data['errors_latency'], 
             color=colors[idx], marker=markers[idx], linestyle=linestyles[idx],
             linewidth=2, markersize=4, label=topo_name, alpha=0.8)

ax2.set_xlabel('Experimentos', fontsize=14)
ax2.set_ylabel('Margem de Erro (ms)', fontsize=14)
#ax2.set_title('Convergência do Erro - Latência Média\n(Intervalo de Confiança 90%)', fontsize=14)
ax2.grid(True, alpha=0.3)
ax2.legend(fontsize=12)
ax2.tick_params(axis='both', which='major', labelsize=12)

plt.tight_layout()

# Salvar gráfico de latência
output_file_latency = f'./result_pdf/convergencia_erro_latencia_{APP_CONFIG["nome"].replace(" ", "_").lower()}_todas_topologias.pdf'
plt.savefig(output_file_latency, bbox_inches='tight', format='pdf')
print(f"Gráfico de latência salvo em: {output_file_latency}")

# Gráfico 3: Erro percentual no número de fogs
fig3, ax3 = plt.subplots(1, 1, figsize=(10, 6))

for idx, (topo_name, topo_data) in enumerate(all_topology_results.items()):
    ax3.plot(topo_data['sample_sizes'], topo_data['percent_errors_fogs'], 
             color=colors[idx], marker=markers[idx], linestyle=linestyles[idx],
             linewidth=2, markersize=4, label=topo_name, alpha=0.8)

ax3.set_xlabel('Experimentos', fontsize=14)
ax3.set_ylabel('Erro Percentual (%)', fontsize=14)
ax3.grid(True, alpha=0.3)
ax3.legend(fontsize=12)
ax3.tick_params(axis='both', which='major', labelsize=12)

plt.tight_layout()

# Salvar gráfico de fogs percentual
output_file_fogs_percent = f'./result_pdf/convergencia_erro_fogs_percentual_{APP_CONFIG["nome"].replace(" ", "_").lower()}_todas_topologias.pdf'
plt.savefig(output_file_fogs_percent, bbox_inches='tight', format='pdf')
print(f"Gráfico de fogs (percentual) salvo em: {output_file_fogs_percent}")

# Gráfico 4: Erro percentual na latência média
fig4, ax4 = plt.subplots(1, 1, figsize=(10, 6))

for idx, (topo_name, topo_data) in enumerate(all_topology_results.items()):
    ax4.plot(topo_data['sample_sizes'], topo_data['percent_errors_latency'], 
             color=colors[idx], marker=markers[idx], linestyle=linestyles[idx],
             linewidth=2, markersize=4, label=topo_name, alpha=0.8)

ax4.set_xlabel('Experimentos', fontsize=14)
ax4.set_ylabel('Erro Percentual (%)', fontsize=14)
ax4.grid(True, alpha=0.3)
ax4.legend(fontsize=12)
ax4.tick_params(axis='both', which='major', labelsize=12)

plt.tight_layout()

# Salvar gráfico de latência percentual
output_file_latency_percent = f'./result_pdf/convergencia_erro_latencia_percentual_{APP_CONFIG["nome"].replace(" ", "_").lower()}_todas_topologias.pdf'
plt.savefig(output_file_latency_percent, bbox_inches='tight', format='pdf')
print(f"Gráfico de latência (percentual) salvo em: {output_file_latency_percent}")

# 5. Resumo dos resultados para todas as topologias
print(f"\n{'='*80}")
print(f"RESUMO DOS RESULTADOS - TODAS AS TOPOLOGIAS")
print(f"{'='*80}")
print(f"Aplicação: {APP_CONFIG['nome']}")
print(f"Metaheurística: Excentricidade (Latência mínima)")
print(f"Intervalo de confiança: {CONFIDENCE_LEVEL*100}%")
print()

for topo_name, topo_data in all_topology_results.items():
    print(f"\n--- {topo_name} ---")
    print(f"Experimentos realizados: {topo_data['n_experiments']}")
    
    sample_sizes = topo_data['sample_sizes']
    errors_fogs = topo_data['errors_fogs']
    errors_latency = topo_data['errors_latency']
    percent_errors_fogs = topo_data['percent_errors_fogs']
    percent_errors_latency = topo_data['percent_errors_latency']
    means_fogs = topo_data['means_fogs']
    means_latency = topo_data['means_latency']
    
    if len(sample_sizes) > 0:
        # Comparar primeiro vs último ponto
        inicial_err_fogs = errors_fogs[0]
        final_err_fogs = errors_fogs[-1]
        inicial_err_lat = errors_latency[0]
        final_err_lat = errors_latency[-1]
        
        inicial_percent_fogs = percent_errors_fogs[0]
        final_percent_fogs = percent_errors_fogs[-1]
        inicial_percent_lat = percent_errors_latency[0]
        final_percent_lat = percent_errors_latency[-1]
        
        reducao_fogs = inicial_err_fogs / final_err_fogs if final_err_fogs > 0 else float('inf')
        reducao_lat = inicial_err_lat / final_err_lat if final_err_lat > 0 else float('inf')
        
        print(f"Erro inicial (n={sample_sizes[0]}):")
        print(f"  Fogs: ±{inicial_err_fogs:.3f} ({inicial_percent_fogs:.1f}%), Latência: ±{inicial_err_lat:.3f} ms ({inicial_percent_lat:.1f}%)")
        print(f"Erro final (n={sample_sizes[-1]}):")
        print(f"  Fogs: ±{final_err_fogs:.3f} ({final_percent_fogs:.1f}%), Latência: ±{final_err_lat:.3f} ms ({final_percent_lat:.1f}%)")
        print(f"Redução do erro: Fogs {reducao_fogs:.1f}x, Latência {reducao_lat:.1f}x")
        print(f"Média final: {means_fogs[-1]:.2f} ± {final_err_fogs:.3f} fogs, {means_latency[-1]:.2f} ± {final_err_lat:.3f} ms")

# Comparação entre topologias
print(f"\n{'='*80}")
print("COMPARAÇÃO ENTRE TOPOLOGIAS (erro final)")
print(f"{'='*80}")
print("Topologia | Erro Fogs | Erro % Fogs | Erro Latência | Erro % Latência | Média Fogs | Média Latência")
print("----------|-----------|-------------|---------------|-----------------|------------|----------------")

for topo_name, topo_data in all_topology_results.items():
    if len(topo_data['errors_fogs']) > 0:
        final_err_fogs = topo_data['errors_fogs'][-1]
        final_err_lat = topo_data['errors_latency'][-1]
        final_percent_fogs = topo_data['percent_errors_fogs'][-1]
        final_percent_lat = topo_data['percent_errors_latency'][-1]
        final_mean_fogs = topo_data['means_fogs'][-1]
        final_mean_lat = topo_data['means_latency'][-1]
        
        print(f"{topo_name:9s} | {final_err_fogs:9.3f} | {final_percent_fogs:11.1f} | {final_err_lat:13.3f} | {final_percent_lat:15.1f} | {final_mean_fogs:10.2f} | {final_mean_lat:14.2f}")

plt.show()