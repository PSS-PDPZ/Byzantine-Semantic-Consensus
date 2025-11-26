import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
import numpy as np
import math
import time
import json
import random
from collections import defaultdict

from geometry_msgs.msg import Point, Pose
from std_msgs.msg import Header, String
from sensor_msgs.msg import Image as RosImage
from ebsc_interfaces.msg import Bep, SemanticFact, MetricsEvent, ReputationUpdate
from ebsc_interfaces.srv import VerifyProof

from .bft_consensus import BFTConsensus
from .perception_module import PerceptionModule

class EBSCAgent(Node):
    def __init__(self):
        super().__init__('ebsc_agent')

        self.declare_parameter('uav_id', 0)
        self.declare_parameter('uav_name', 'uav_0')
        self.declare_parameter('is_byzantine', False)
        # 节点数量和拜占庭节点数量的默认值
        self.declare_parameter('total_uavs', 10) 
        self.declare_parameter('num_byzantine', 3)  
        
        self.uav_id = self.get_parameter('uav_id').get_parameter_value().integer_value
        self.uav_name = self.get_parameter('uav_name').get_parameter_value().string_value
        self.is_byzantine = self.get_parameter('is_byzantine').get_parameter_value().bool_value
        # 节点数量和拜占庭节点的实际数量可以通过start_ebsc_experiment.launch.py文件得到
        self.total_uavs = self.get_parameter('total_uavs').get_parameter_value().integer_value
        self.num_byzantine = self.get_parameter('num_byzantine').get_parameter_value().integer_value  
        
        if self.is_byzantine:
            self.get_logger().warn(f"[{self.uav_name}] 🔥 *** I am a Byzantine node! ***")
        else:
            self.get_logger().info(f"[{self.uav_name}] ✅ Honest node initialized.")

        self.perception = PerceptionModule(self.get_logger())
        self.bft = BFTConsensus(self, self.uav_id, self.total_uavs)

        self.is_reputation_manager = (self.uav_id == 0)
        self.reputation_table = {i: 0.6 for i in range(self.total_uavs)}
        
        if self.is_reputation_manager:
            self.vote_ledger = defaultdict(dict)

        self.current_pose = Pose()
        self.patrol_angle = (self.uav_id / self.total_uavs) * 2.0 * math.pi
        self.patrol_radius = 15.0
        self.patrol_speed = 0.6
        self.patrol_height = 5.0
        self.start_time = time.time()
        self.targets_published = {}
        self._dummy_image = None
        self.known_targets = {
            'ebsc_target_tank': {'location': (15.0, 15.0, 0.5), 'class': 'tank'},
            'ebsc_target_truck': {'location': (-10.0, 8.0, 0.75), 'class': 'truck'},
            'ebsc_target_supply': {'location': (5.0, -8.0, 0.5), 'class': 'supply'},
            'ebsc_target_radar': {'location': (-12.0, -10.0, 1.0), 'class': 'radar'},
            'ebsc_target_infantry': {'location': (0.0, 12.0, 0.3), 'class': 'infantry'}
        }

        gossip_qos = QoSProfile(reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST, depth=self.total_uavs * 2)
        self.bep_subscription = self.create_subscription(Bep, '/ebsc/gossip', self.bft.handle_bep_proposal, gossip_qos)
        self.metrics_event_pub = self.create_publisher(MetricsEvent, '/ebsc/metrics_events', 100)
        self.reputation_pub = self.create_publisher(ReputationUpdate, '/ebsc/reputation', 10)
        self.reputation_sub = self.create_subscription(ReputationUpdate, '/ebsc/reputation', self.handle_reputation_update, 10)
        
        if self.is_reputation_manager:
            self.reputation_broadcast_timer = self.create_timer(1.0, self.broadcast_reputation)
            self.vote_sub_for_manager = self.create_subscription(String, '/ebsc/vote', self.handle_vote_for_manager, 100)

        self.patrol_timer = self.create_timer(0.2, self.simulate_patrol_and_perception)
        self.get_logger().info(f"[{self.uav_name}] EBSC Agent ready and patrolling.")

    def handle_vote_for_manager(self, msg: String):
        """信誉管理员记录所有投票"""
        if not self.is_reputation_manager: 
            return
        try:
            data = json.loads(msg.data)
            self.vote_ledger[data['proposal_hash']][int(data['voter_id'])] = data['vote']
        except Exception as e:
            self.get_logger().error(f"Reputation manager failed to record vote: {e}")

    def report_event(self, event_type: str, details: str = "", size_bytes: int = 0):
        msg = MetricsEvent()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = str(self.uav_id)
        msg.event_type = event_type
        msg.uav_id = self.uav_id
        msg.details = details
        msg.size_bytes = size_bytes
        self.metrics_event_pub.publish(msg)

    def handle_reputation_update(self, msg: ReputationUpdate):
        """非管理员节点接收信誉更新"""
        if self.is_reputation_manager: 
            return
        for uav_id, reputation in zip(msg.uav_ids, msg.reputations):
            self.reputation_table[uav_id] = reputation

    def broadcast_reputation(self):
        """定期广播信誉表"""
        if not self.is_reputation_manager: 
            return
        msg = ReputationUpdate()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = str(self.uav_id)
        msg.uav_ids = [int(k) for k in self.reputation_table.keys()]
        msg.reputations = list(self.reputation_table.values())
        self.reputation_pub.publish(msg)

    def update_reputation_after_vote(self, voter_id: int, vote_correct: bool):
        """
        更新单个节点的信誉 初始信誉0.6，最高1，最低0.1
        vote_correct: True表示行为正确（奖励），False表示行为错误（惩罚）
        """
        if not self.is_reputation_manager: 
            return
        
        current_rep = self.reputation_table.get(voter_id, 0.6)
        
        if vote_correct:
            # 正确行为: 小幅奖励
            new_rep = min(1.0, current_rep + 0.01)
        else:
            # 错误行为: 大幅惩罚
            new_rep = max(0.1, current_rep - 0.1)
        
        self.reputation_table[voter_id] = new_rep
        
        # 信誉变化会通过broadcast_reputation()自动广播给logger_node

    def simulate_patrol_and_perception(self):
        elapsed_time = time.time() - self.start_time
        current_angle = self.patrol_angle + self.patrol_speed * elapsed_time
        self.current_pose.position.x = self.patrol_radius * math.cos(current_angle)
        self.current_pose.position.y = self.patrol_radius * math.sin(current_angle)
        self.current_pose.position.z = self.patrol_height

        for target_name, target_info in self.known_targets.items():
            target_x, target_y, target_z = target_info['location']
            distance = math.sqrt(
                (self.current_pose.position.x - target_x)**2 + 
                (self.current_pose.position.y - target_y)**2 + 
                (self.current_pose.position.z - target_z)**2
            )

            if distance < 30.0:
                now = self.get_clock().now()
                last_time = self.targets_published.get(target_name)
                if last_time and (now - last_time).nanoseconds / 1e9 < 5.0: 
                    continue
                
                if random.random() < max(0.1, 1.0 - (distance / 30.0)):
                    self.get_logger().info(f"[{self.uav_name}] 👀 Perceived {target_name} at {distance:.1f}m")
                    self.targets_published[target_name] = now
                    target_pose = Pose()
                    target_pose.position.x = float(target_x)
                    target_pose.position.y = float(target_y)
                    target_pose.position.z = float(target_z)
                    self.trigger_perception(target_name, target_pose, target_info['class'])

    def trigger_perception(self, target_name: str, target_pose: Pose, target_class: str):
        """触发感知并创建提案"""
        original_class = target_class
        
        # 拜占庭节点的攻击行为  拜占庭节点的提案总是恶意的
        if self.is_byzantine:
            attack_type = np.random.choice(['class', 'location'], p=[0.6, 0.4])
            
            if attack_type == 'class':
                all_classes = list(set([info['class'] for info in self.known_targets.values()]))
                if target_class in all_classes: 
                    all_classes.remove(target_class)
                if all_classes:
                    target_class = np.random.choice(all_classes)
                    self.get_logger().warn(
                        f"[{self.uav_name}] 🔥 Attack: Falsifying class from "
                        f"'{original_class}' to '{target_class}'"
                    )
            elif attack_type == 'location':
                offset_x = np.random.uniform(-8, 8)
                offset_y = np.random.uniform(-8, 8)
                target_pose.position.x += offset_x
                target_pose.position.y += offset_y
                self.get_logger().warn(
                    f"[{self.uav_name}] 🔥 Attack: Falsifying location by "
                    f"({offset_x:.1f}, {offset_y:.1f})m"
                )

        # 创建BEP消息
        bep_msg = Bep()
        bep_msg.header = Header(stamp=self.get_clock().now().to_msg(), frame_id=str(self.uav_id))
        bep_msg.object_class = target_class
        bep_msg.confidence_score = np.random.uniform(0.85, 0.99)
        bep_msg.estimated_location = target_pose.position
        bep_msg.uav_pose_at_perception = self.current_pose
        
        # 创建加密证明
        claim = {
            "proposer_id": self.uav_id,
            "object_class": bep_msg.object_class,
            "location": {
                "x": round(bep_msg.estimated_location.x, 2),
                "y": round(bep_msg.estimated_location.y, 2),
                "z": round(bep_msg.estimated_location.z, 2)
            }
        }
        bep_msg.crypto_proof = json.dumps(claim, sort_keys=True)
        
        # 发起共识
        self.bft.propose_target(bep_msg)