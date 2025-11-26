import matplotlib.pyplot as plt
import numpy as np

# === 1. Nature 顶刊级全局风格设置 ===
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['font.size'] = 12          # 字体大小
plt.rcParams['axes.linewidth'] = 1.0    # 边框线宽
plt.rcParams['xtick.major.width'] = 1.0
plt.rcParams['ytick.major.width'] = 1.0
plt.rcParams['axes.grid'] = True        
plt.rcParams['grid.alpha'] = 0.3        
plt.rcParams['grid.linestyle'] = '--'   # 虚线网格
plt.rcParams['figure.dpi'] = 300        # 高DPI

def plot_nature_style_clean_v4():
    """
    生成 Figure 6.1: 攻击鲁棒性评估 (最终定稿版：N/A 标签)
    """
    # === 2. 数据准备 ===
    methods = ['EBSC', 'PBFT', 'SMV', 'WAF']
    accuracy = [100.0, 62.5, 48.2, 51.3] 
    rejection = [98, 85.0, 10.0, 0.0]

    # === 3. Nature (NPG) 配色 ===
    colors = [
        '#00A087',  # EBSC: Teal
        '#3C5488',  # PBFT: Dark Blue
        '#F39B7F',  # SMV:  Salmon
        '#8491B4'   # WAF:  Blue Grey
    ]

    # 纹理
    patterns = ['', '///', '...', '\\\\\\']

    # 创建画布
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5)) 
    
    # === 4. 绘制子图 (a): 准确率 ===
    bars1 = ax1.bar(methods, accuracy, color=colors, edgecolor='black', 
                   linewidth=0.8, width=0.65, alpha=0.9, zorder=3) 
    
    for bar, pat in zip(bars1, patterns):
        bar.set_hatch(pat)

    ax1.set_ylabel('Consensus Validity (%)', fontweight='bold', fontsize=14)
    ax1.set_xlabel('(a) Overall Validity Comparison', fontweight='bold', fontsize=14, labelpad=12)
    ax1.set_ylim(0, 110)
    ax1.tick_params(axis='both', labelsize=12) 

    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    # === 5. 绘制子图 (b): 拒绝率 ===
    bars2 = ax2.bar(methods, rejection, color=colors, edgecolor='black', 
                   linewidth=0.8, width=0.65, alpha=0.9, zorder=3)
    
    for bar, pat in zip(bars2, patterns):
        bar.set_hatch(pat)

    ax2.set_ylabel('Byzantine Rejection Rate (%)', fontweight='bold', fontsize=14)
    ax2.set_xlabel('(b) Malicious Proposal Rejection', fontweight='bold', fontsize=14, labelpad=12)
    ax2.set_ylim(0, 110)
    ax2.tick_params(axis='both', labelsize=12)

    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    # === 特别处理：给 WAF 添加 "N/A" 标签 ===
    # x坐标为3 (WAF的索引), y坐标设为 2 (稍微抬高一点避免重叠)
    # 字体颜色用深灰色，保持专业感
    ax2.text(3, 2, 'N/A', ha='center', va='bottom', fontsize=11, fontweight='bold', color='#333333')

    # === 6. 保存 ===
    plt.tight_layout()
    plt.subplots_adjust(wspace=0.25, bottom=0.20)
    
    plt.savefig('Figure_6_1_Robustness.pdf', format='pdf', bbox_inches='tight')
    plt.savefig('Figure_6_1_Robustness.png', dpi=600, bbox_inches='tight')

    print("✅ 图表已生成 :")
    print("   - Figure_6_1_Robustness.pdf")
    print("   - Figure_6_1_Robustness.png")

if __name__ == "__main__":
    plot_nature_style_clean_v4()