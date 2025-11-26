import json
import time
from datetime import datetime
import numpy as np
import os

class MetricsCollector:
    """EBSC 实验指标收集器"""
    
    def __init__(self, node):
        self.node = node
        self.start_time = time.time()
        
        # 定义 ground truth
        self.ground_truths = {
            'ebsc_target_tank': {
                'class': 'tank',
                'location': {'x': 15.0, 'y': 15.0, 'z': 0.5}
            },
            'ebsc_target_truck': {
                'class': 'truck',
                'location': {'x': -10.0, 'y': 8.0, 'z': 0.75}
            },
            'ebsc_target_supply': {
                'class': 'supply',
                'location': {'x': 5.0, 'y': -8.0, 'z': 0.5}
            },
            'ebsc_target_radar': {
                'class': 'radar',
                'location': {'x': -12.0, 'y': -10.0, 'z': 1.0}
            },
            'ebsc_target_infantry': {
                'class': 'infantry',
                'location': {'x': 0.0, 'y': 12.0, 'z': 0.3}
            }
        }
        
        # 指标存储
        self.consensus_results = []
        self.reputation_history = []
        self.message_counts = {
            'bep': 0,
            'proposal': 0,
            'vote': 0,
            'certificate': 0
        }
        
        # 性能指标
        self.message_timestamps = []
        self.consensus_latencies = []
        
        # 创建日志目录
        log_dir = os.path.expanduser("~/ebsc_experiment_data")
        os.makedirs(log_dir, exist_ok=True)
        
        # 创建日志文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(log_dir, f"ebsc_metrics_{timestamp}.json")
        
        self.node.get_logger().info(f"📊 指标将保存到: {self.log_file}")
    
    def log_consensus(self, decided_fact, time_taken):
        """记录共识结果"""
        ground_truth = None
        for target_id, gt in self.ground_truths.items():
            if target_id in decided_fact.target_uuid:
                ground_truth = gt
                break
        
        if not ground_truth:
            self.node.get_logger().warn(
                f"未找到目标 {decided_fact.target_uuid} 的 ground truth")
            return
        
        self.consensus_latencies.append(float(time_taken))
        
        accuracy = self._calculate_accuracy(decided_fact, ground_truth)
        
        result = {
            'timestamp': time.time() - self.start_time,
            'target_id': decided_fact.target_uuid,
            'decided_class': decided_fact.object_class,
            'decided_location': {
                'x': float(decided_fact.location.x),
                'y': float(decided_fact.location.y),
                'z': float(decided_fact.location.z)
            },
            'ground_truth': ground_truth,
            'accuracy': accuracy,
            'convergence_time': float(time_taken),
            'num_supporters': len(decided_fact.supporting_uavs),
            'supporters': decided_fact.supporting_uavs
        }
        
        self.consensus_results.append(result)
        
        self.node.get_logger().info(
            f"📊 共识 #{len(self.consensus_results)}: "
            f"类别准确率={accuracy['class_accuracy']*100:.0f}%, "
            f"位置误差={accuracy['location_error']:.2f}m, "
            f"延迟={time_taken:.2f}s")
    
    def log_reputation_snapshot(self, reputation_table, byzantine_nodes):
        """记录信誉快照"""
        honest_reps = [
            rep for id, rep in reputation_table.items()
            if id not in byzantine_nodes
        ]
        byzantine_reps = [
            rep for id, rep in reputation_table.items()
            if id in byzantine_nodes
        ]
        
        snapshot = {
            'timestamp': time.time() - self.start_time,
            'honest_avg': float(np.mean(honest_reps)) if honest_reps else 0.0,
            'honest_min': float(np.min(honest_reps)) if honest_reps else 0.0,
            'honest_max': float(np.max(honest_reps)) if honest_reps else 0.0,
            'byzantine_avg': float(np.mean(byzantine_reps)) if byzantine_reps else 0.0,
            'byzantine_min': float(np.min(byzantine_reps)) if byzantine_reps else 0.0,
            'byzantine_max': float(np.max(byzantine_reps)) if byzantine_reps else 0.0,
            'reputation_gap': float(
                np.mean(honest_reps) - np.mean(byzantine_reps)
            ) if (honest_reps and byzantine_reps) else 0.0
        }
        
        self.reputation_history.append(snapshot)
    
    def increment_message_count(self, msg_type):
        """✅ 增加消息计数（由全局事件触发）"""
        if msg_type in self.message_counts:
            self.message_counts[msg_type] += 1
    
    def log_message_sent(self):
        """记录消息发送（已废弃，由report_event替代）"""
        self.message_timestamps.append(time.time())
    
    def _calculate_accuracy(self, decided_fact, ground_truth):
        """计算准确率指标"""
        class_correct = decided_fact.object_class == ground_truth['class']
        
        loc_error = np.sqrt(
            (decided_fact.location.x - ground_truth['location']['x'])**2 +
            (decided_fact.location.y - ground_truth['location']['y'])**2 +
            (decided_fact.location.z - ground_truth['location']['z'])**2
        )
        
        loc_correct = loc_error < 2.0
        
        return {
            'class_accuracy': 1.0 if class_correct else 0.0,
            'location_error': float(loc_error),
            'location_correct': 1.0 if loc_correct else 0.0,
            'overall': 1.0 if (class_correct and loc_correct) else 0.0
        }
    
    def save_metrics(self):
        """保存所有指标到 JSON 文件"""
        metrics = {
            'metadata': {
                'experiment_start': datetime.fromtimestamp(self.start_time).isoformat(),
                'experiment_duration': time.time() - self.start_time,
                'saved_at': datetime.now().isoformat()
            },
            'consensus_results': self.consensus_results,
            'reputation_history': self.reputation_history,
            'message_counts': self.message_counts,
            'summary': self._generate_summary()
        }
        
        with open(self.log_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        return self.log_file
    
    def _generate_summary(self):
        """✅ 生成实验摘要统计（修正吞吐量定义）"""
        if not self.consensus_results:
            return {
                'note': 'No consensus results yet',
                'total_messages': sum(self.message_counts.values())
            }
        
        class_accuracies = [r['accuracy']['class_accuracy'] for r in self.consensus_results]
        location_errors = [r['accuracy']['location_error'] for r in self.consensus_results]
        overall_accuracies = [r['accuracy']['overall'] for r in self.consensus_results]
        convergence_times = [r['convergence_time'] for r in self.consensus_results]
        
        if self.reputation_history:
            final_snapshot = self.reputation_history[-1]
            reputation_summary = {
                'final_honest_avg': final_snapshot['honest_avg'],
                'final_byzantine_avg': final_snapshot['byzantine_avg'],
                'final_reputation_gap': final_snapshot['reputation_gap']
            }
        else:
            reputation_summary = {}
        
        total_time = time.time() - self.start_time
        total_messages = sum(self.message_counts.values())
        total_consensuses = len(self.consensus_results)
        
        performance_metrics = {
            # ✅ 消息吞吐量（通信开销指标）
            'message_throughput': {
                'total_messages': total_messages,
                'experiment_duration_seconds': total_time,
                'messages_per_second': total_messages / total_time if total_time > 0 else 0,
                'messages_per_minute': (total_messages / total_time * 60) if total_time > 0 else 0
            },
            
            # ✅ 共识吞吐量（系统性能核心指标）
            'consensus_throughput': {
                'total_consensuses': total_consensuses,
                'experiment_duration_seconds': total_time,
                'consensuses_per_second': total_consensuses / total_time if total_time > 0 else 0,
                'consensuses_per_minute': (total_consensuses / total_time * 60) if total_time > 0 else 0
            },
            
            # 延迟指标
            'latency': {
                'consensus_latency_avg_seconds': float(np.mean(self.consensus_latencies)) if self.consensus_latencies else 0,
                'consensus_latency_min_seconds': float(np.min(self.consensus_latencies)) if self.consensus_latencies else 0,
                'consensus_latency_max_seconds': float(np.max(self.consensus_latencies)) if self.consensus_latencies else 0,
                'consensus_latency_std_seconds': float(np.std(self.consensus_latencies)) if self.consensus_latencies else 0
            }
        }
        
        summary = {
            'total_consensuses': len(self.consensus_results),
            'consensus_accuracy': {
                'class_accuracy_avg': float(np.mean(class_accuracies)),
                'location_error_avg': float(np.mean(location_errors)),
                'location_error_std': float(np.std(location_errors)),
                'overall_accuracy_avg': float(np.mean(overall_accuracies))
            },
            'convergence_time': {
                'average': float(np.mean(convergence_times)),
                'std': float(np.std(convergence_times)),
                'min': float(np.min(convergence_times)),
                'max': float(np.max(convergence_times))
            },
            'reputation_system': reputation_summary,
            'communication': {
                'total_messages': sum(self.message_counts.values()),
                'bep_messages': self.message_counts['bep'],
                'consensus_messages': (
                    self.message_counts['proposal'] +
                    self.message_counts['vote'] +
                    self.message_counts['certificate']
                )
            },
            'performance': performance_metrics,
            'experiment_duration_seconds': time.time() - self.start_time
        }
        
        return summary
