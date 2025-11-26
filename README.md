This repository contains the official ROS 2 implementation for the paper:
**"EBSC: Forging Trustworthy Collective Perception in UAV Swarms with Evidence-based Byzantine Semantic Consensus"**

## 🛠 Environment
*   **OS:** Ubuntu 22.04 LTS
*   **ROS 2:** Humble Hawksbill
*   **Simulator:** Gazebo Classic 11
*   **Dependencies:** `numpy`, `torch`, `torchvision`, `pandas`, `matplotlib`

## 🚀 Installation

1.  **Setup Workspace:**
    ```bash
    mkdir -p ~/ebsc_ws/src
    cd ~/ebsc_ws/src
    # Clone this repository here
    git clone <Phttps://github.com/PSS-PDPZ/byzantine-semantic-consensus> .
    ```

2.  **Build:**
    ```bash
    cd ~/ebsc_ws
    colcon build --symlink-install
    source install/setup.bash
    ```

3.  **Setup Gazebo Models:**
    ```bash
    # Copy drone models to Gazebo directory
    cp -r src/ebsc_simulation/models/* ~/.gazebo/models/
    ```

## 🏃‍♂️ How to Run

**Launch the experiment (12 UAVs, 3 Byzantine nodes):**
```bash
ros2 launch ebsc_launcher start_ebsc_experiment.launch.py