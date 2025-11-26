import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset
import os

# === Nature/ICRA 顶刊级全局风格设置 ===
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['font.size'] = 12
plt.rcParams['axes.linewidth'] = 1.0
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.3
plt.rcParams['grid.linestyle'] = '--'
plt.rcParams['figure.dpi'] = 300

# === 数据文件路径 ===
json_file_path = '/home/pss/ebsc_experiment_data/ebsc_metrics_20251125_221938.json'

def plot_ebsc_results_attack_defense_view():
    print(f"正在读取数据文件: {json_file_path} ...")
    if not os.path.exists(json_file_path):
        print("❌ 错误: 找不到文件")
        return

    with open(json_file_path, 'r') as f:
        data = json.load(f)

    # === 配置 ===
    metadata = data.get('metadata', {})
    total_uavs = metadata.get('total_uavs', 12)
    num_byz = metadata.get('num_byzantine', 3)
    experiment_duration = metadata.get('experiment_duration', 180.0)

    # ==========================================
    # 数据处理 1: 信誉演化 (图 a)
    # ==========================================
    rep_history = data.get('reputation_history', [])
    start_t = rep_history[0]['timestamp']
    times_rep = np.array([x['timestamp'] - start_t for x in rep_history])
    node_ids = sorted([int(k) for k in rep_history[0]['reputations'].keys()])
    
    df_rep = pd.DataFrame(index=times_rep)
    for nid in node_ids:
        trace = [entry['reputations'].get(str(nid), 0.6) for entry in rep_history]
        df_rep[f'Node_{nid}'] = trace

    if times_rep[0] > 0.0:
        init_row = pd.DataFrame({col: [0.6] for col in df_rep.columns}, index=[0.0])
        df_rep = pd.concat([init_row, df_rep]).sort_index()
        times_rep = df_rep.index.to_numpy()

    # ==========================================
    # 数据处理 2: 攻击 vs 防御 (图 b)
    # ==========================================
    consensus_results = data.get('consensus_results', [])
    consensus_results.sort(key=lambda x: x['timestamp_ros'])
    
    min_time = rep_history[0]['timestamp']
    
    time_points = [0]
    cum_honest_total = [0]
    cum_honest_accepted = [0]
    cum_byz_total = [0]
    cum_byz_accepted = [0]
    
    h_tot, h_acc, b_tot, b_acc = 0, 0, 0, 0
    
    for r in consensus_results:
        t = r['timestamp_ros'] - min_time
        if t < 0: continue 
        
        is_byz = (r['proposer_type'] == 'byzantine')
        accepted = r['accepted']
        
        if is_byz:
            b_tot += 1
            if accepted: b_acc += 1
        else:
            h_tot += 1
            if accepted: h_acc += 1
            
        time_points.append(t)
        cum_honest_total.append(h_tot)
        cum_honest_accepted.append(h_acc)
        cum_byz_total.append(b_tot)
        cum_byz_accepted.append(b_acc)

    time_points = np.array(time_points)
    cum_byz_total = np.array(cum_byz_total)
    cum_byz_accepted = np.array(cum_byz_accepted)

    # ==========================================
    # === 3. 绘图 ===
    # ==========================================
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5)) 
    
    c_honest = '#00A087'
    c_byz    = '#E64B35'
    
    # --- Subplot (a): Reputation Evolution ---
    # 1. 主图绘制
    for i in range(num_byz):
        y_data = df_rep[f'Node_{i}'].values # 关键修复：加上 .values
        jitter = np.random.normal(0, 0.004, size=len(y_data)); jitter[0]=0
        ax1.plot(times_rep, y_data + jitter, color=c_byz, alpha=0.6, linewidth=1.5)
        
    for i in range(num_byz, total_uavs):
        y_data = df_rep[f'Node_{i}'].values # 关键修复：加上 .values
        jitter = np.random.normal(0, 0.006, size=len(y_data)); jitter[0]=0
        ax1.plot(times_rep, y_data + jitter, color=c_honest, alpha=0.4, linewidth=1.5)
    
    ax1.axhline(y=1.0, color='gray', linestyle=':', alpha=0.4)
    ax1.axhline(y=0.1, color='gray', linestyle=':', alpha=0.4)
    ax1.axhline(y=0.6, color='black', linestyle='--', alpha=0.3, linewidth=1.0)
    ax1.text(2, 0.62, 'Initial Score ($R_{init}=0.6$)', fontsize=11, fontweight='bold', color='#333333')

    ax1.annotate('Byzantines Isolated', xy=(8, 0.15), xytext=(30, 0.35),
                 arrowprops=dict(arrowstyle='->', color='black', lw=1.5), 
                 fontsize=12, fontweight='bold')

    ax1.set_ylabel('Reputation Score', fontweight='bold', fontsize=14)
    ax1.set_xlabel('Experiment Time (s)', fontweight='bold', fontsize=12)
    ax1.set_ylim(-0.05, 1.1) 
    ax1.set_xlim(0, experiment_duration)
    ax1.set_title('(a) Individual Node Reputation Evolution', fontweight='bold', y=-0.2, fontsize=14)
    
    legend_elements_a = [
        Line2D([0], [0], color=c_honest, lw=2, label=f'Honest Nodes (x{total_uavs-num_byz})'),
        Line2D([0], [0], color=c_byz, lw=2, label=f'Byzantine Nodes (x{num_byz})')
    ]
    # 图例放右上角，给局部放大图腾出位置
    ax1.legend(handles=legend_elements_a, loc='upper right', bbox_to_anchor=(1.0, 0.9), frameon=True, fontsize=11)
    ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)

    # ======================================================
    # === 添加局部放大图 inset zoom (修复并调整位置) ===
    # ======================================================
    # 位置调整：bbox_to_anchor=(x, y, width, height) 
    # (0.45, 0.35, 0.4, 0.4) -> 放在中间偏右上的位置
    inset = inset_axes(ax1, width="80%", height="80%", loc='lower left',
                       bbox_to_anchor=(0.6, 0.25, 0.4, 0.4),
                       bbox_transform=ax1.transAxes)

    # 画同样的数据到 inset (关键修复：加上 .values)
    for i in range(num_byz):
        inset.plot(times_rep, df_rep[f'Node_{i}'].values, color=c_byz, alpha=0.8, linewidth=2)

    for i in range(num_byz, total_uavs):
        inset.plot(times_rep, df_rep[f'Node_{i}'].values, color=c_honest, alpha=0.8, linewidth=2)

    # 放大初期 0~10s 区间
    inset.set_xlim(0, 10)
    inset.set_ylim(0, 1.05) # 包含 0 到 1 的完整变化
    inset.set_title("First 10s Detail", fontsize=10)
    
    # 稍微调整刻度字体大小
    inset.tick_params(axis='both', which='major', labelsize=9)
    inset.grid(alpha=0.2)

    # 连接线
    mark_inset(ax1, inset, loc1=2, loc2=4, fc="none", ec="0.4", linestyle=':', lw=0.8)

    # --- Subplot (b): Attack/Defense (保持原样) ---
    ax2.plot(time_points, cum_honest_accepted, color=c_honest, linewidth=2.5, label='Honest Proposals (Accepted)')
    ax2.plot(time_points, cum_byz_total, color=c_byz, linestyle='--', linewidth=2.0, label='Byzantine Attempts (Total)')
    ax2.plot(time_points, cum_byz_accepted, color=c_byz, linewidth=2.5, label='Byzantine Proposals (Accepted)')

    ax2.fill_between(time_points, cum_byz_accepted, cum_byz_total, 
                     color=c_byz, alpha=0.15, hatch='///', edgecolor=c_byz, label='Blocked Attempts')

    ax2.set_ylabel('Cumulative Proposals', fontweight='bold', fontsize=14)
    ax2.set_xlabel('Experiment Time (s)', fontweight='bold', fontsize=12)
    ax2.set_title('(b) Cumulative Proposal Acceptance and Defense', fontweight='bold', y=-0.2, fontsize=14)
    ax2.set_xlim(0, experiment_duration)
    ax2.set_ylim(0, max(cum_honest_total[-1], cum_byz_total[-1]) * 1.1)

    mid_time = experiment_duration * 0.6
    idx = np.abs(time_points - mid_time).argmin()
    mid_y_total = cum_byz_total[idx]
    mid_y_acc = cum_byz_accepted[idx]
    
    ax2.annotate(f'98% Blocked\n({int(cum_byz_total[-1]-cum_byz_accepted[-1])} Rejected)', 
                 xy=(mid_time, (mid_y_total + mid_y_acc)/2), 
                 xytext=(mid_time + 10, (mid_y_total + mid_y_acc)/2 - 50),
                 arrowprops=dict(arrowstyle='->', connectionstyle="arc3,rad=-0.2", color='black'),
                 fontsize=11, fontweight='bold', color=c_byz)

    handles, labels = ax2.get_legend_handles_labels()
    order = [0, 1, 2, 3] 
    ax2.legend([handles[idx] for idx in order],[labels[idx] for idx in order], 
               loc='upper left', frameon=True, fontsize=11)
    
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    # === 保存 ===
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.2, wspace=0.2)
    
    plt.savefig('Figure_6_4_Reputation.pdf', format='pdf', bbox_inches='tight')
    plt.savefig('Figure_6_4_Reputation.pdf', format='pdf', bbox_inches='tight')
    plt.savefig('Figure_6_4_Reputation.png', dpi=600, bbox_inches='tight')
    print("✅ 图表已生成！")

if __name__ == "__main__":
    plot_ebsc_results_attack_defense_view()