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

# Configurações do experimento
TOPOLOGY_PATH = './nsfnetbw/'
N_EXPERIMENTS = 500
TOPOLOGY_NAME = 'nsfnetbw'

# Configurações da aplicação IoT Industrial
IOT_CONFIG = {
        "nome": "Videoconferência (HD)",
        "latencia": 25,
        "capacidade": 50
    }

# Parâmetros da rede
L_cloud_fog = 25
C_cloud_fog = 50
escala_latencia = 0.025/2

print(f"=== Análise Latência Média vs Número de fogs - {IOT_CONFIG['nome']} ===")
print(f"Topologia: {TOPOLOGY_NAME}")
print(f"Número de experimentos: {N_EXPERIMENTS}")
print(f"Metaheurística: Excentricidade (Latência mínima)")
print(f"Requisitos IoT: Latência ≤ {IOT_CONFIG['latencia']} ms, Capacidade ≥ {IOT_CONFIG['capacidade']} Mbps")
print()

# 1. Carregar dados da topologia
print("Carregando dados da topologia...")
try:
    reader = datanetAPI.DatanetAPI(os.path.join(PARENT_DIR, TOPOLOGY_PATH), [])
    it_topo = iter(reader)
    
    # Coletar todas as amostras necessárias
    samples_data = []
    
    for k in range(N_EXPERIMENTS):
        try:
            dados_sample = next(it_topo)
            lat, cap = aux.extrai_latencias_capacidades(dados_sample)
            samples_data.append({
                'latencias': lat,
                'capacidades': cap,
                'dados': dados_sample
            })
        except StopIteration:
            print(f"Aviso: Apenas {k} amostras encontradas (solicitado {N_EXPERIMENTS})")
            break
    
    n_samples_loaded = len(samples_data)
    if n_samples_loaded == 0:
        raise Exception("Nenhuma amostra carregada")
    
    n_nodes = len(samples_data[0]['latencias'])
    print(f"Carregadas {n_samples_loaded} amostras")
    print(f"Número de nós: {n_nodes}")
    
except Exception as e:
    print(f"ERRO ao carregar dados: {e}")
    exit(1)

# 2. Executar experimentos e coletar dados da rede
print(f"\nExecutando {n_samples_loaded} experimentos...")

L_max = IOT_CONFIG["latencia"]
C_min = IOT_CONFIG["capacidade"]

# Listas para armazenar resultados
solution_avg_latencies = []  # Latência média efetiva da solução (L_ij × Y_ij)
network_avg_capacities = []  # Capacidade média da rede (entre todos os nós)
num_fogs_list = []

for i in range(n_samples_loaded):
    if (i + 1) % 50 == 0 or (i + 1) == n_samples_loaded:
        print(f"  Progresso: {i + 1}/{n_samples_loaded}")
    
    # Configurar experimento
    #cloud_position = random.randint(0, n_nodes - 1)
    cloud_position = 0
    current_latencias = samples_data[i]['latencias']
    current_capacidades = samples_data[i]['capacidades']
    
    # Calcular capacidade média da rede (matriz completa)
    capacidades_array = np.array(current_capacidades)
    
    # Capacidade média entre todos os pares de nós
    network_avg_cap = np.mean(capacidades_array)
    
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
        solution_avg_latency = resultado[2]  # Esta é a latência média efetiva (L_ij × Y_ij)
        avg_l_r = solution_avg_latency / escala_latencia
        if avg_l_r > IOT_CONFIG['latencia']:
            print("    Solução não atende requisitos, pulando...")
        
        # Armazenar dados da solução
        solution_avg_latencies.append(solution_avg_latency / escala_latencia)
        network_avg_capacities.append(network_avg_cap)
        num_fogs_list.append(num_fogs)
        
    except Exception as e:
        print(f"  ERRO no experimento {i}: {e}")
        continue

print(f"Experimentos concluídos: {len(solution_avg_latencies)}")

# 3. Estatísticas dos dados coletados
if len(solution_avg_latencies) > 0:
    print(f"\n=== ESTATÍSTICAS DA SOLUÇÃO ===")
    print(f"Latência média da solução (L_ij × Y_ij):")
    print(f"  Mínima: {min(solution_avg_latencies):.2f} ms")
    print(f"  Máxima: {max(solution_avg_latencies):.2f} ms")
    print(f"  Média: {np.mean(solution_avg_latencies):.2f} ms")
    print(f"  Desvio padrão: {np.std(solution_avg_latencies):.2f} ms")
    
    print(f"Capacidade média da rede:")
    print(f"  Mínima: {min(network_avg_capacities):.2f} Mbps")
    print(f"  Máxima: {max(network_avg_capacities):.2f} Mbps")
    print(f"  Média: {np.mean(network_avg_capacities):.2f} Mbps")
    print(f"  Desvio padrão: {np.std(network_avg_capacities):.2f} Mbps")
    
    print(f"Número de fogs:")
    print(f"  Mínimo: {min(num_fogs_list)}")
    print(f"  Máximo: {max(num_fogs_list)}")
    print(f"  Média: {np.mean(num_fogs_list):.2f}")

# 4. Plotar gráfico
print("\nGerando gráfico...")

fig, ax = plt.subplots(1, 1, figsize=(12, 8))

# Scatter plot dos experimentos - Latência média efetiva vs Número de fogs
scatter = ax.scatter(solution_avg_latencies, num_fogs_list, 
                    c=network_avg_capacities, cmap='viridis', alpha=0.7, s=50, 
                    edgecolors='black', linewidth=0.5)

# Linha vertical para requisito de latência
ax.axvline(x=IOT_CONFIG['latencia'], color='red', linestyle='--', linewidth=2, 
           label=f'Requisito latência = {IOT_CONFIG["latencia"]} ms')

# Configurações do gráfico
ax.set_xlabel('Latência média da solução (ms)', fontsize=14)
ax.set_ylabel('Número de fogs', fontsize=14)
#ax.set_title(f'Latência Média Efetiva vs Número de Fogs - {TOPOLOGY_NAME}\n'
#             f'Metaheurística: Excentricidade (Latência), {len(solution_avg_latencies)} experimentos', 
#             fontsize=16)
ax.grid(True, alpha=0.3)
ax.tick_params(axis='both', which='major', labelsize=12)

# Colorbar para capacidade média da rede
cbar = plt.colorbar(scatter, ax=ax)
cbar.set_label('Capacidade média da rede (Mbps)', fontsize=12)
cbar.ax.tick_params(labelsize=10)

# Adicionar linha horizontal na colorbar marcando o requisito de capacidade
cbar_min, cbar_max = scatter.get_clim()
if IOT_CONFIG['capacidade'] >= cbar_min and IOT_CONFIG['capacidade'] <= cbar_max:
    # Adicionar linha horizontal no colorbar
    cbar.ax.axhline(y=IOT_CONFIG['capacidade'], color='red', linestyle='--', linewidth=2)
    # Adicionar texto indicativo
    cbar.ax.text(0.5, IOT_CONFIG['capacidade'], f'{IOT_CONFIG["capacidade"]} Mbps', 
                transform=cbar.ax.get_yaxis_transform(), 
                verticalalignment='center', horizontalalignment='left',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8),
                fontsize=10, color='red', fontweight='bold')

# Região de requisito de latência atendido
x_min, x_max = ax.get_xlim()
y_min, y_max = ax.get_ylim()

# Destacar região que atende o requisito de latência (latência ≤ 15 ms)
if IOT_CONFIG['latencia'] < x_max:
    ax.fill_betweenx([y_min, y_max], x_min, IOT_CONFIG['latencia'], 
                     alpha=0.2, color='green', 
                     label='Região de latência viável')

# Posicionar legenda no canto superior esquerdo
ax.legend(fontsize=12, loc='upper left')

plt.tight_layout()

# 5. Salvar gráfico
output_file = f'./result_pdf/latencia_vs_numero_fogs_{IOT_CONFIG["nome"].replace(" ", "_").lower()}_{TOPOLOGY_NAME.lower()}.pdf'
os.makedirs('./result_pdf', exist_ok=True)
plt.savefig(output_file, bbox_inches='tight', format='pdf', dpi=300)
print(f"Gráfico salvo em: {output_file}")

# 6. Análise de requisitos atendidos
experiments_meeting_latency = sum(1 for lat in solution_avg_latencies if lat <= IOT_CONFIG['latencia'])
experiments_meeting_capacity = sum(1 for cap in network_avg_capacities if cap >= IOT_CONFIG['capacidade'])
experiments_meeting_both = sum(1 for lat, cap in zip(solution_avg_latencies, network_avg_capacities) 
                              if lat <= IOT_CONFIG['latencia'] and cap >= IOT_CONFIG['capacidade'])

print(f"\n=== ANÁLISE DE REQUISITOS IoT ===")
print(f"Experimentos que atendem requisito de latência (≤ {IOT_CONFIG['latencia']} ms): {experiments_meeting_latency}/{len(solution_avg_latencies)} ({100*experiments_meeting_latency/len(solution_avg_latencies):.1f}%)")
print(f"Experimentos que atendem requisito de capacidade (≥ {IOT_CONFIG['capacidade']} Mbps): {experiments_meeting_capacity}/{len(network_avg_capacities)} ({100*experiments_meeting_capacity/len(network_avg_capacities):.1f}%)")
print(f"Experimentos que atendem AMBOS os requisitos: {experiments_meeting_both}/{len(solution_avg_latencies)} ({100*experiments_meeting_both/len(solution_avg_latencies):.1f}%)")

# 7. Correlação entre latência efetiva da solução e número de fogs
correlation = np.corrcoef(solution_avg_latencies, num_fogs_list)[0, 1]
print(f"\nCorrelação entre latência efetiva da solução e número de fogs: {correlation:.3f}")

if abs(correlation) > 0.7:
    correlation_strength = "forte"
elif abs(correlation) > 0.3:
    correlation_strength = "moderada"
else:
    correlation_strength = "fraca"

correlation_direction = "positiva" if correlation > 0 else "negativa"
print(f"Correlação {correlation_strength} {correlation_direction}")

# 8. Análise adicional entre latência efetiva e capacidade da rede
correlation_lat_cap = np.corrcoef(solution_avg_latencies, network_avg_capacities)[0, 1]
print(f"Correlação entre latência efetiva e capacidade da rede: {correlation_lat_cap:.3f}")

plt.show()

print(f"\n=== RESUMO ===")
print(f"Topologia: {TOPOLOGY_NAME}")
print(f"Experimentos realizados: {len(solution_avg_latencies)}")
print(f"Requisitos IoT: Latência ≤ {IOT_CONFIG['latencia']} ms, Capacidade ≥ {IOT_CONFIG['capacidade']} Mbps")
print(f"Taxa de sucesso (ambos requisitos): {100*experiments_meeting_both/len(solution_avg_latencies):.1f}%")
print(f"Gráfico salvo: {output_file}")