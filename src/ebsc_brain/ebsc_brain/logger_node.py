import rclpy
from rclpy.node import Node
import json
import os
from datetime import datetime
import numpy as np
import atexit
from collections import defaultdict
from ebsc_interfaces.msg import SemanticFact, MetricsEvent, ReputationUpdate

class LoggerNode(Node):
    def __init__(self):
        super().__init__('ebsc_logger_node')

        self.declare_parameter('total_uavs', 10)
        self.declare_parameter('num_byzantine', 3)
        self.total_uavs = self.get_parameter('total_uavs').get_parameter_value().integer_value
        self.num_byzantine = self.get_parameter('num_byzantine').get_parameter_value().integer_value

        self.start_time_ros = self.get_clock().now()
        self.start_time_wall = datetime.now()
        
        # Initialize all indicator storage
        self.consensus_results = []
        self.reputation_history = []
        self.message_counts = defaultdict(int)
        self.total_bytes = 0
        self.log_saved = False
        
        self.proposal_stats = {
            'total_proposals': 0,
            'accepted_proposals': 0,
            'rejected_proposals': 0,
            'honest_proposals': 0,
            'honest_accepted': 0,
            'honest_rejected': 0,
            'byzantine_proposals': 0,
            'byzantine_accepted': 0,
            'byzantine_rejected': 0,
            'by_proposer': defaultdict(lambda: {'total': 0, 'accepted': 0, 'rejected': 0})
        }

        log_dir = os.path.expanduser("~/ebsc_experiment_data")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = self.start_time_wall.strftime('%Y%m%d_%H%M%S')
        self.log_file = os.path.join(log_dir, f'ebsc_metrics_{timestamp}.json')
        self.get_logger().info(f"Logger initialized. Metrics will be saved to: {self.log_file}")

        # Subscribe to all the necessary data sources
        self.create_subscription(SemanticFact, '/ebsc/certificate', self.certificate_callback, 10)
        self.create_subscription(MetricsEvent, '/ebsc/metrics_events', self.metrics_event_callback, 100)
        self.create_subscription(ReputationUpdate, '/ebsc/reputation', self.reputation_callback, 10)

        atexit.register(self.save_log)

    def certificate_callback(self, msg: SemanticFact):
        """Processing received consensus certificates"""
        if msg.target_uuid in [r['target_uuid'] for r in self.consensus_results]: 
            return
        
        proposer_id = int(msg.original_bep.header.frame_id)
        is_byzantine = (proposer_id < self.num_byzantine)
        
        self.proposal_stats['total_proposals'] += 1
        if msg.accepted:
            self.proposal_stats['accepted_proposals'] += 1
        else:
            self.proposal_stats['rejected_proposals'] += 1
        
        # Statistics by node type
        if is_byzantine:
            self.proposal_stats['byzantine_proposals'] += 1
            if msg.accepted:
                self.proposal_stats['byzantine_accepted'] += 1
            else:
                self.proposal_stats['byzantine_rejected'] += 1
        else:
            self.proposal_stats['honest_proposals'] += 1
            if msg.accepted:
                self.proposal_stats['honest_accepted'] += 1
            else:
                self.proposal_stats['honest_rejected'] += 1
        
        # Statistics by specific node
        self.proposal_stats['by_proposer'][proposer_id]['total'] += 1
        if msg.accepted:
            self.proposal_stats['by_proposer'][proposer_id]['accepted'] += 1
        else:
            self.proposal_stats['by_proposer'][proposer_id]['rejected'] += 1
        
        self.get_logger().info(
            f"Logging consensus for '{msg.object_class}' ({msg.target_uuid[:8]}), "
            f"result: {'ACCEPTED' if msg.accepted else 'REJECTED'}, "
            f"proposer: UAV {proposer_id} ({'Byzantine' if is_byzantine else 'Honest'})"
        )
        
        ground_truth = self.get_ground_truth(msg.object_class)
        self.consensus_results.append({
            'timestamp_ros': self.get_clock().now().nanoseconds / 1e9,
            'target_uuid': msg.target_uuid,
            'decided_class': msg.object_class,
            'decided_location': {'x': msg.location.x, 'y': msg.location.y, 'z': msg.location.z},
            'ground_truth': ground_truth,
            'accuracy': self.calculate_accuracy(msg, ground_truth) if ground_truth else None,
            'convergence_time': msg.convergence_time,
            'num_supporters': len(msg.supporting_uavs),
            'supporters': sorted(list(msg.supporting_uavs)),
            'accepted': msg.accepted,
            'proposer_id': proposer_id,  
            'proposer_type': 'byzantine' if is_byzantine else 'honest'
        })

    def metrics_event_callback(self, msg: MetricsEvent):
        """Record message events"""
        self.message_counts[msg.event_type] += 1
        self.total_bytes += msg.size_bytes

    def reputation_callback(self, msg: ReputationUpdate):
        """Record reputation snapshot"""
        snapshot = {
            'timestamp': self.get_clock().now().nanoseconds / 1e9,
            'reputations': {uav_id: rep for uav_id, rep in zip(msg.uav_ids, msg.reputations)}
        }
        self.reputation_history.append(snapshot)

    def get_ground_truth(self, object_class: str):
        """Get the ground truth of the target"""
        ground_truths = {
            'tank': {'class': 'tank', 'location': {'x': 15.0, 'y': 15.0, 'z': 0.5}},
            'truck': {'class': 'truck', 'location': {'x': -10.0, 'y': 8.0, 'z': 0.75}},
            'supply': {'class': 'supply', 'location': {'x': 5.0, 'y': -8.0, 'z': 0.5}},
            'radar': {'class': 'radar', 'location': {'x': -12.0, 'y': -10.0, 'z': 1.0}},
            'infantry': {'class': 'infantry', 'location': {'x': 0.0, 'y': 12.0, 'z': 0.3}}
        }
        return ground_truths.get(object_class)

    def calculate_accuracy(self, decided_fact, ground_truth):
        """Calculate effectiveness indicators"""
        loc_error = np.sqrt(
            (decided_fact.location.x - ground_truth['location']['x'])**2 +
            (decided_fact.location.y - ground_truth['location']['y'])**2
        )
        class_correct = decided_fact.object_class == ground_truth['class']
        loc_correct = loc_error < 2.5
        return {
            'class_accuracy': 1.0 if class_correct else 0.0,
            'location_error': float(loc_error),
            'overall': 1.0 if (class_correct and loc_correct) else 0.0
        }

    def save_log(self):
        """Save final log"""
        if self.log_saved: 
            return
        self.log_saved = True
        self.get_logger().info("Saving final metrics...")

        experiment_duration = (self.get_clock().now() - self.start_time_ros).nanoseconds / 1e9
        summary = self.generate_summary(experiment_duration)
        
        data = {
            "metadata": {
                "experiment_start": self.start_time_wall.isoformat(),
                "experiment_duration": experiment_duration,
                "saved_at": datetime.now().isoformat(),
                "total_uavs": self.total_uavs,
                "num_byzantine": self.num_byzantine
            },
            "consensus_results": self.consensus_results,
            "reputation_history": self.reputation_history,
            "message_counts": dict(self.message_counts),
            "total_bytes": self.total_bytes,
            "proposal_stats": self._serialize_proposal_stats(),  
            "summary": summary
        }

        with open(self.log_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.get_logger().info(f"Metrics successfully saved to {self.log_file}")
        self.print_summary_report(data)

    def _serialize_proposal_stats(self):

        stats = dict(self.proposal_stats)
        stats['by_proposer'] = {
            int(k): dict(v) for k, v in self.proposal_stats['by_proposer'].items()
        }
        return stats

    def generate_summary(self, total_time):
        """Generate experimental summary statistics"""
        summary = {}
        
        # The accepted consensus is selected for validity calculation.
        accepted_results = [r for r in self.consensus_results if r.get('accepted', False)]

        # 1. Validity metrics (based only on accepted_results)
        if accepted_results:
            accuracies = [r['accuracy']['overall'] for r in accepted_results if r.get('accuracy')]
            class_accuracies = [r['accuracy']['class_accuracy'] for r in accepted_results if r.get('accuracy')]
            location_errors = [r['accuracy']['location_error'] for r in accepted_results if r.get('accuracy')]
            
            summary['consensus_accuracy'] = {
                "overall_accuracy_avg": float(np.mean(accuracies)) if accuracies else 0,
                "class_accuracy_avg": float(np.mean(class_accuracies)) if class_accuracies else 0,
                "location_error_avg": float(np.mean(location_errors)) if location_errors else 0,
            }
        
        # 2. Performance metrics (based on all consensus)
        total_consensuses = len(self.consensus_results)
        summary['performance'] = {
            "total_consensuses": total_consensuses,
            "total_accepted": len(accepted_results),
            "total_rejected": total_consensuses - len(accepted_results),
            "throughput_cps": total_consensuses / total_time if total_time > 0 else 0
        }
        
        if self.consensus_results:
            convergence_times = [r['convergence_time'] for r in self.consensus_results]
            summary['performance']['latency'] = {
                "average": float(np.mean(convergence_times)),
                "min": float(np.min(convergence_times)),
                "max": float(np.max(convergence_times)),
                "std": float(np.std(convergence_times))
            }

        # 3. Expenditure Indicators
        summary['overhead'] = {
            "total_messages": sum(self.message_counts.values()),
            "total_bytes": self.total_bytes,
            "avg_msg_per_consensus": sum(self.message_counts.values()) / total_consensuses if total_consensuses > 0 else 0,
            "avg_bytes_per_consensus": self.total_bytes / total_consensuses if total_consensuses > 0 else 0,
            "message_breakdown": dict(self.message_counts)
        }
        
        # Proposal acceptance rate index
        stats = self.proposal_stats
        summary['proposal_acceptance'] = {
            "overall_acceptance_rate": stats['accepted_proposals'] / stats['total_proposals'] if stats['total_proposals'] > 0 else 0,
            "overall_rejection_rate": stats['rejected_proposals'] / stats['total_proposals'] if stats['total_proposals'] > 0 else 0,
            "honest_acceptance_rate": stats['honest_accepted'] / stats['honest_proposals'] if stats['honest_proposals'] > 0 else 0,
            "honest_rejection_rate": stats['honest_rejected'] / stats['honest_proposals'] if stats['honest_proposals'] > 0 else 0,
            "byzantine_acceptance_rate": stats['byzantine_accepted'] / stats['byzantine_proposals'] if stats['byzantine_proposals'] > 0 else 0,
            "byzantine_rejection_rate": stats['byzantine_rejected'] / stats['byzantine_proposals'] if stats['byzantine_proposals'] > 0 else 0,
            "total_proposals": stats['total_proposals'],
            "honest_proposals": stats['honest_proposals'],
            "byzantine_proposals": stats['byzantine_proposals']
        }
        
        # 5. Fault tolerance index
        if self.reputation_history:
            last_rep_snapshot = self.reputation_history[-1]['reputations']
            honest_reps = [rep for uid, rep in last_rep_snapshot.items() if uid >= self.num_byzantine]
            byzantine_reps = [rep for uid, rep in last_rep_snapshot.items() if uid < self.num_byzantine]
            summary['fault_tolerance'] = {
                "final_avg_honest_rep": float(np.mean(honest_reps)) if honest_reps else 0,
                "final_avg_byzantine_rep": float(np.mean(byzantine_reps)) if byzantine_reps else 0,
                "reputation_gap": (float(np.mean(honest_reps)) if honest_reps else 0) - (float(np.mean(byzantine_reps)) if byzantine_reps else 0)
            }
        
        return summary

    def print_summary_report(self, data):
        """Print terminal summary report"""
        summary = data.get('summary', {})
        print("\n\n" + "="*60)
        print(" EBSC Protocol Experiment Final Report ")
        print("="*60)

        if not summary or not summary.get('performance', {}).get('total_consensuses'):
            print("\n⚠️  No consensus results were recorded during the experiment.\n")
        else:
            acc = summary.get('consensus_accuracy', {})
            perf = summary.get('performance', {})
            lat = perf.get('latency', {})
            ovr = summary.get('overhead', {})
            ft = summary.get('fault_tolerance', {})
            pa = summary.get('proposal_acceptance', {})  

            print("\n[ 1. effectiveness indicators ]")
            print(f"  - Overall validity (Proposal accepted): {acc.get('overall_accuracy_avg', 0) * 100:.2f}%")
            print(f"  - Category accuracy : {acc.get('class_accuracy_avg', 0) * 100:.2f}%")
            print(f"  - Average position error: {acc.get('location_error_avg', 0):.3f} m")

            print("\n[ 2. Performance indicators ]")
            print(f"  - Total number of consensuses: {perf.get('total_consensuses', 0)}")
            print(f"  - Accepted consensus: {perf.get('total_accepted', 0)}")
            print(f"  - Consensus of Rejection: {perf.get('total_rejected', 0)}")
            print(f"  - System throughput: {perf.get('throughput_cps', 0):.2f} consensus/sec")
            print(f"  - Average delay: {lat.get('average', 0):.4f} s (min: {lat.get('min', 0):.4f}, max: {lat.get('max', 0):.4f})")

            print("\n[ 3. Expenditure Indicators ]")
            print(f"  - Total number of messages: {ovr.get('total_messages', 0)}")
            print(f"  - Total traffic: {ovr.get('total_bytes', 0) / 1024:.2f} KB")
            print(f"  - Average number of consensus messages per consensus: {ovr.get('avg_msg_per_consensus', 0):.1f}")
            
            
            print("\n[ 4. Proposal acceptance rate ]")
            print(f"  - Total number of proposals: {pa.get('total_proposals', 0)} (Honest: {pa.get('honest_proposals', 0)}, Byzantium: {pa.get('byzantine_proposals', 0)})")
            print(f"  - Overall acceptance rate: {pa.get('overall_acceptance_rate', 0) * 100:.2f}%")
            print(f"  - Honest node proposal acceptance rate: {pa.get('honest_acceptance_rate', 0) * 100:.2f}%")
            print(f"  - Byzantine node proposal acceptance rate: {pa.get('byzantine_acceptance_rate', 0) * 100:.2f}%")
            print(f"  - Byzantine node proposal rejection rate: {pa.get('byzantine_rejection_rate', 0) * 100:.2f}%")
            
            print("\n[ 5. Fault tolerance indicators ]")
            print(f"  - Ultimate Honest Node Average Reputation: {ft.get('final_avg_honest_rep', 0):.3f}")
            print(f"  - Final Byzantine node average reputation: {ft.get('final_avg_byzantine_rep', 0):.3f}")
            print(f"  - Ultimate credibility gap: {ft.get('reputation_gap', 0):.3f}")

        print("="*60)
        print(f"\n✅ Detailed logs have been saved to: {self.log_file}\n")


def main(args=None):
    rclpy.init(args=args)
    logger_node = LoggerNode()
    try:
        rclpy.spin(logger_node)
    except KeyboardInterrupt:
        logger_node.get_logger().info("Logger node interrupted by user.")
    finally:
        if rclpy.ok():
            logger_node.save_log()
            logger_node.destroy_node()

if __name__ == '__main__':
    main()