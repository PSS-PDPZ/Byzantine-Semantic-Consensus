import matplotlib.pyplot as plt
import numpy as np

# === 1. Nature 顶刊级全局风格设置 ===
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['font.size'] = 12
plt.rcParams['axes.linewidth'] = 1.0  # 全局边框线宽 1.0
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.3
plt.rcParams['grid.linestyle'] = '--'
plt.rcParams['figure.dpi'] = 300

def plot_scalability_final_black_spines():
    # === 2. 数据准备 ===
    N = np.array([4, 8, 12, 16])
    
    # EBSC 真实数据
    ebsc_latency = np.array([0.0039, 0.0064, 0.0093, 0.42])
    ebsc_throughput_tpm = np.array([3.154, 6.062, 8.29, 9.12]) * 60
    ebsc_msg_count = np.array([4.92, 9.00, 13.24, 18.8])
    
    # EBSC 真实传输量 (KB/Consensus)
    total_kb = np.array([465.49, 1355.77, 2521.32, 3741.8])
    total_consensus = np.array([3.154, 6.062, 8.29, 9.12]) * 180
    ebsc_data_transfer = total_kb / total_consensus 

    # PBFT 理论数据
    pbft_latency = 0.015 * (N**2) + 0.02
    pbft_throughput_tpm = (1 / pbft_latency) * 60 * 0.8
    pbft_msg_count = 0.5 * (N**2)

    # === 3. 创建画布 ===
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5))
    
    # 配色
    c_ebsc = '#00A087'  # Teal
    c_pbft = '#3C5488'  # Dark Blue
    c_data = '#E64B35'  # Red (Data Transfer)

    # ==========================================
    # 子图 (a): Latency
    # ==========================================
    ax1.plot(N, pbft_latency, 'o--', color=c_pbft, lw=2, label='PBFT')
    ax1.plot(N, ebsc_latency, 's-', color=c_ebsc, lw=2.5, markersize=8, label='EBSC')
    ax1.fill_between(N, ebsc_latency, pbft_latency, color=c_pbft, alpha=0.1)
    ax1.set_xlabel('Number of Nodes', fontweight='bold')
    ax1.set_ylabel('Latency (s)', fontweight='bold')
    ax1.set_title('(a) Consensus Latency', fontweight='bold', y=-0.2)
    ax1.set_xticks(N)
    #ax1.legend(frameon=False)
    ax1.legend(frameon=True, facecolor='white')
    
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    # ==========================================
    # 子图 (b): Throughput
    # ==========================================
    width = 1.2
    ax2.bar(N - width/2, ebsc_throughput_tpm, width, color=c_ebsc, label='EBSC')
    ax2.bar(N + width/2, pbft_throughput_tpm, width, color=c_pbft, alpha=0.8, label='PBFT')
    ax2.set_xlabel('Number of Nodes', fontweight='bold',fontsize=12)
    ax2.set_ylabel('Throughput (TPM)', fontweight='bold',fontsize=14)
    ax2.set_title('(b) System Throughput', fontweight='bold', y=-0.2)
    ax2.set_xticks(N)
    #ax2.legend(frameon=False)
    ax2.legend(frameon=True, facecolor='white')

    
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    # ==========================================
    # 子图 (c): Overhead (修正：黑色边框)
    # ==========================================
    # 左轴: 消息数
    l1, = ax3.plot(N, pbft_msg_count, 'o--', color=c_pbft, lw=2, label='PBFT Msgs')
    l2, = ax3.plot(N, ebsc_msg_count, 's-', color=c_ebsc, lw=2.5, markersize=8, label='EBSC Msgs')
    ax3.set_xlabel('Number of Nodes', fontweight='bold')
    # Y轴标题保留颜色，方便区分
    ax3.set_ylabel('Avg Messages per Consensus', fontweight='bold', color=c_pbft)
    ax3.tick_params(axis='y', labelcolor=c_pbft)
    ax3.set_xticks(N)
    
    # 右轴: 数据传输量
    ax3_r = ax3.twinx()
    l3, = ax3_r.plot(N, ebsc_data_transfer, 'D:', color=c_data, lw=2.5, markersize=7, 
                     label='EBSC Data Transfer')
    
    ax3_r.set_ylabel('Avg Data Transfer (KB)', fontweight='bold', color=c_data)
    ax3_r.tick_params(axis='y', labelcolor=c_data)
    ax3_r.set_ylim(0, 4.5)

    # --- 关键修正：边框设置 ---
    # 1. 移除顶部
    ax3.spines['top'].set_visible(False)
    ax3_r.spines['top'].set_visible(False)
    
    # 2. 确保右边框可见，但设为【黑色】且不加粗
    ax3_r.spines['right'].set_visible(True)
    ax3_r.spines['right'].set_color('black') 
    # ax3_r.spines['right'].set_linewidth(1.0) # 默认就是1.0，与全局一致

    # 3. 左边框也保持默认黑色
    ax3.spines['left'].set_color('black')

    # 合并图例
    lines = [l1, l2, l3]
    labels = [l.get_label() for l in lines]
    #ax3.legend(lines, labels, frameon=False, loc='upper left', fontsize=10)
    ax3.legend(lines, labels, frameon=True, facecolor='white', loc='upper left', fontsize=10)

    
    ax3.set_title('(c) Communication Overhead', fontweight='bold', y=-0.2)

    # === 保存 ===
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.2, wspace=0.3)
    
    plt.savefig('Figure_6_2_Scalability.pdf', bbox_inches='tight')
    plt.savefig('Figure_6_2_Scalability.png', dpi=600, bbox_inches='tight')
    print("✅ Figure 6.2 已生成")

if __name__ == "__main__":
    plot_scalability_final_black_spines()