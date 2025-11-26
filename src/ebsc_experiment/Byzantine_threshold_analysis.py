import matplotlib.pyplot as plt
import numpy as np

# === 1. Nature 顶刊级全局风格设置 ===
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['font.size'] = 12          
plt.rcParams['axes.linewidth'] = 1.0    
plt.rcParams['xtick.major.width'] = 1.0
plt.rcParams['ytick.major.width'] = 1.0
plt.rcParams['axes.grid'] = True        
plt.rcParams['grid.alpha'] = 0.3        
plt.rcParams['grid.linestyle'] = '--'   
plt.rcParams['figure.dpi'] = 300        

def plot_nature_style_threshold_analysis_final():
    """
    生成 Figure 6-3: 拜占庭比例临界点分析 (含区域背景，无多余注释)
    """
    # === 2. 数据准备 ===
    f_counts = np.array([1, 2, 3, 4, 5, 6, 7, 8])
    
    # 子图 (a) 数据
    ebsc_acc = np.array([100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0])
    pbft_acc = np.array([100.0, 100.0, 100.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    # 子图 (b) 数据
    honest_rep = np.array([1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000])
    byz_rep = np.array([0.110, 0.105, 0.107, 0.100, 0.104, 0.107, 0.113, 0.111])

    # === 3. 配色 ===
    color_ebsc = '#00A087'  # Teal
    color_pbft = '#3C5488'  # Dark Blue
    color_bad  = '#E64B35'  # Red

    # 创建画布
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5)) 

    # ==========================================
    # === 4. 绘制子图 (a): 含 Zone 背景 ===
    # ==========================================
    
    # --- 关键修改：添加区域背景 ---
    # Standard BFT Zone 
    zone1 = ax1.axvspan(0.0, 4.0, color='green', alpha=0.08, label='Standard BFT Zone')
    # EBSC Extended Zone 
    zone2 = ax1.axvspan(4.0, 8.5, color='orange', alpha=0.15, label='EBSC Extended Zone')

    # 绘制线条
    line_pbft = ax1.plot(f_counts, pbft_acc, color=color_pbft, linestyle='--', linewidth=2, 
             marker='x', markersize=8, label='PBFT', zorder=3)[0]
    line_ebsc = ax1.plot(f_counts, ebsc_acc, color=color_ebsc, linestyle='-', linewidth=2.5, 
             marker='o', markersize=8, label='EBSC', zorder=4)[0]

    # BFT 边界线
    ax1.axvline(x=4, color='red', linestyle='--', linewidth=1.5, alpha=0.8)
    ax1.text(4.1, 50, 'BFT Failure Bound (f ≥ 4)', rotation=0, verticalalignment='center', 
             fontsize=10, color='red', fontweight='bold')

    # 轴设置
    ax1.set_ylabel('Honest Proposal Acceptance (%)', fontweight='bold', fontsize=14)
    ax1.set_xlabel('Number of Byzantine Nodes', fontweight='bold', fontsize=12)
    ax1.set_ylim(-5, 110)
    ax1.set_xticks(f_counts)
    
    # 子图标题放在底部
    ax1.set_title('(a) Liveness Boundary Extension', fontweight='bold', fontsize=14, y=-0.2)
    
    # 图例 - 包含区域背景和线条
    ax1.legend([line_pbft, line_ebsc, zone1, zone2], 
               ['PBFT', 'EBSC', 'Standard BFT Zone', 'EBSC Extended Zone'],
               loc='upper left', bbox_to_anchor=(0.54, 0.9), frameon=True, fontsize=11)

    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    # ==========================================
    # === 5. 绘制子图 (b): 信誉稳定性 ===
    # ==========================================
    
    ax2.plot(f_counts, honest_rep, color=color_ebsc, linestyle='-', linewidth=2.5, 
             marker='s', markersize=7, label='Honest Nodes', zorder=4)
    ax2.plot(f_counts, byz_rep, color=color_bad, linestyle='-', linewidth=2.5, 
             marker='D', markersize=7, label='Byzantine Nodes', zorder=4)

    ax2.fill_between(f_counts, honest_rep, byz_rep, color='gray', alpha=0.15, label='Trust Gap')

    ax2.set_ylabel('Reputation Score', fontweight='bold', fontsize=14)
    ax2.set_xlabel('Number of Byzantine Nodes', fontweight='bold', fontsize=12)
    ax2.set_ylim(0, 1.1)
    ax2.set_xticks(f_counts)
    
    # 子图标题放在底部
    ax2.set_title('(b) Reputation System Stability', fontweight='bold', fontsize=14, y=-0.2)

    ax2.legend(loc='upper left', bbox_to_anchor=(0.605, 0.9), frameon=True, fontsize=11)

    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    
    # === 6. 保存 ===
    plt.tight_layout()
    plt.subplots_adjust(wspace=0.25, bottom=0.20)
    
    plt.savefig('Figure_6_3_Threshold.pdf', format='pdf', bbox_inches='tight')
    plt.savefig('Figure_6_3_Threshold.png', dpi=600, bbox_inches='tight')

    print("✅ 图表已生成")

if __name__ == "__main__":
    plot_nature_style_threshold_analysis_final()