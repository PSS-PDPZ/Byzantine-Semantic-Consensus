#ebsc_project_ws/src/ebsc_brain/ebsc_brain/bft_consensus.py:
import rclpy
from rclpy.task import Future
from rclpy.serialization import serialize_message
import time
import math
import json
import hashlib
from enum import Enum
import numpy as np  

from ebsc_interfaces.msg import Bep, SemanticFact
from std_msgs.msg import String
from ebsc_interfaces.srv import VerifyProof

class ConsensusPhase(Enum): 
    IDLE = 0
    VOTING = 1
    DECIDED = 2

class ConsensusResult(Enum): 
    PENDING = 0
    ACCEPTED = 1
    REJECTED = 2

class BFTConsensus:
    def __init__(self, node: 'EBSCAgent', uav_id: int, total_uavs: int):
        self.node = node
        self.uav_id = uav_id
        self.total_uavs = total_uavs
        self.min_reputation_ratio = 2.0 / 3.0
        
        self.my_proposals = {}
        self.received_proposals = {}
        self.decided_targets = {}
        self.proposal_timeout = 30.0
        
        # ROS 通信接口
        self.bep_pub = self.node.create_publisher(Bep, '/ebsc/gossip', 10)
        self.vote_pub = self.node.create_publisher(String, '/ebsc/vote', 10)
        self.certificate_pub = self.node.create_publisher(SemanticFact, '/ebsc/certificate', 10)
        self.vote_sub = self.node.create_subscription(String, '/ebsc/vote', self.handle_vote, 10)
        self.certificate_sub = self.node.create_subscription(
            SemanticFact, '/ebsc/certificate', self.handle_certificate, 10
        )
        
        # Truth Oracle 客户端
        self.proof_client = self.node.create_client(VerifyProof, 'verify_proof')
        if not self.proof_client.wait_for_service(timeout_sec=5.0):
            self.node.get_logger().error("Truth Oracle service not available! Consensus will fail.")
        
        # 约束条件
        self.known_target_bounds = {
            'x_min': -20.0, 'x_max': 20.0, 
            'y_min': -20.0, 'y_max': 20.0, 
            'z_min': 0.0, 'z_max': 5.0
        }
        self.known_classes = ['tank', 'truck', 'supply', 'radar', 'infantry']
        
        # 超时检查
        self.timeout_timer = self.node.create_timer(1.0, self.check_timeouts)
        
        self.node.get_logger().info(f"[BFT Module] Initialized for UAV {self.uav_id}.")

    def _hash_bep(self, bep_msg: Bep) -> str:
        """生成提案的唯一哈希值"""
        bep_data = {
            'proposer': bep_msg.header.frame_id,
            'class': bep_msg.object_class,
            'location': (
                round(bep_msg.estimated_location.x, 1),
                round(bep_msg.estimated_location.y, 1)
            ),
            'timestamp_sec': bep_msg.header.stamp.sec
        }
        return hashlib.sha256(json.dumps(bep_data, sort_keys=True).encode()).hexdigest()[:16]

    def propose_target(self, bep_msg: Bep):
        """发起新提案"""
        proposal_hash = self._hash_bep(bep_msg)
        
        if proposal_hash in self.my_proposals and \
           self.my_proposals[proposal_hash]['phase'] == ConsensusPhase.VOTING:
            return
        
        # 提案者自己投YES票
        self.my_proposals[proposal_hash] = {
            'bep': bep_msg,
            'votes': {self.uav_id: ('YES', self.node.reputation_table.get(self.uav_id, 1.0))},
            'phase': ConsensusPhase.VOTING,
            'start_time': time.time()
        }
        
        self.bep_pub.publish(bep_msg)
        self.node.get_logger().info(f"🚀 Proposal {proposal_hash} broadcasted (self-voted YES).")
        
        msg_size = len(serialize_message(bep_msg))
        self.node.report_event('bep_propose', bep_msg.object_class, size_bytes=msg_size)

    def handle_bep_proposal(self, bep_msg: Bep):
        """处理收到的提案"""
        proposer_id = int(bep_msg.header.frame_id)
        
        if proposer_id == self.uav_id:
            return
        
        proposal_hash = self._hash_bep(bep_msg)
        
        if proposal_hash in self.received_proposals:
            return
        
        self.received_proposals[proposal_hash] = bep_msg
        self.node.get_logger().info(f"📩 Received proposal {proposal_hash} from UAV {proposer_id}.")
        
        self._validate_and_vote(bep_msg, proposer_id, proposal_hash)

    def _validate_and_vote(self, bep_msg: Bep, proposer_id: int, proposal_hash: str):
        """验证提案并投票"""
        # 步骤1: 基本合理性检查
        if not self._check_target_sanity(bep_msg):
            self.node.get_logger().warn(f"Proposal {proposal_hash} failed sanity check. Voting NO.")
            self._send_vote(proposal_hash, proposer_id, 'NO')
            return
        
        # 步骤2: 异步调用Truth Oracle验证
        request = VerifyProof.Request()
        request.bep_proposal = bep_msg
        future = self.proof_client.call_async(request)
        future.add_done_callback(
            lambda f: self.verification_done_callback(f, proposal_hash, proposer_id)
        )

    def verification_done_callback(self, future: Future, proposal_hash: str, proposer_id: int):
        """Oracle验证完成的回调"""
        try:
            response = future.result()
            oracle_vote = 'YES' if response.is_valid else 'NO'
            
            # ============ 拜占庭投票攻击 ============
            #拜占庭节点有50%的时间诚实投票、40%反转投票、10%沉默不投  模拟了智能对手试图维持一定信誉以延长攻击时间的场景
            if self.node.is_byzantine:
                attack_strategy = np.random.choice(
                    ['honest', 'flip', 'silent'],
                    p=[0.5, 0.4, 0.1] 
                )
                if attack_strategy == 'flip':
                    # 反转投票: YES→NO, NO→YES
                    vote = 'NO' if oracle_vote == 'YES' else 'YES'
                    self.node.get_logger().warn(
                        f"🔥 Byzantine voting attack: flipping {oracle_vote} → {vote}"
                    )
                elif attack_strategy == 'silent':
                    # 沉默攻击: 不投票
                    self.node.get_logger().warn(
                        f"🔥 Byzantine voting attack: silent (not voting)"
                    )
                    return  # 直接返回，不发送投票
                else:
                    # 诚实投票
                    vote = oracle_vote
            else:
                vote = oracle_vote
            # ==========================================
            
            self.node.get_logger().info(
                f"Oracle {'✅ verified' if response.is_valid else '❌ rejected'} "
                f"proposal {proposal_hash}. Voting {vote}."
            )
            self._send_vote(proposal_hash, proposer_id, vote)
            
        except Exception as e:
            self.node.get_logger().error(f"Truth Oracle service call failed for {proposal_hash}: {e}")
            self._send_vote(proposal_hash, proposer_id, 'NO')

    def _send_vote(self, proposal_hash: str, proposer_id: int, vote: str):
        """发送投票"""
        vote_msg = String()
        vote_data = {
            'proposal_hash': proposal_hash,
            'proposer_id': proposer_id,
            'voter_id': self.uav_id,
            'vote': vote,
            'reputation': self.node.reputation_table.get(self.uav_id, 1.0)
        }
        vote_msg.data = json.dumps(vote_data)
        self.vote_pub.publish(vote_msg)
        
        msg_size = len(vote_msg.data.encode('utf-8'))
        self.node.report_event('vote', vote, size_bytes=msg_size)

    def handle_vote(self, msg: String):
        """处理收到的投票"""
        try:
            data = json.loads(msg.data)
            proposal_hash = data['proposal_hash']
            voter_id = int(data['voter_id'])
            
            if proposal_hash not in self.my_proposals:
                return
            
            proposal_info = self.my_proposals[proposal_hash]
            
            if proposal_info['phase'] == ConsensusPhase.DECIDED:
                return
            
            if voter_id in proposal_info['votes']:
                return
            
            proposal_info['votes'][voter_id] = (data['vote'], data['reputation'])
            
            consensus_result = self._check_votes_threshold(proposal_info)
            
            if consensus_result != ConsensusResult.PENDING:
                self._create_and_broadcast_certificate(proposal_hash, proposal_info, consensus_result)
                
        except Exception as e:
            self.node.get_logger().error(f"Error handling vote: {e}", exc_info=True)

    def _check_votes_threshold(self, proposal_info: dict) -> ConsensusResult:
        """检查投票是否达到阈值"""
        reputation_table = self.node.reputation_table
        total_reputation = sum(reputation_table.values())
        
        if total_reputation == 0:
            return ConsensusResult.PENDING
        
        # 统计YES和NO的加权票数
        weighted_yes = sum(
            reputation_table.get(voter_id, 0.0) 
            for voter_id, (vote, _) in proposal_info['votes'].items() 
            if vote == 'YES'
        )
        weighted_no = sum(
            reputation_table.get(voter_id, 0.0) 
            for voter_id, (vote, _) in proposal_info['votes'].items() 
            if vote == 'NO'
        )
        
        yes_ratio = weighted_yes / total_reputation
        no_ratio = weighted_no / total_reputation
        
        self.node.get_logger().info(
            f"📊 Vote stats for {self._hash_bep(proposal_info['bep'])}: "
            f"YES weight = {weighted_yes:.2f} ({yes_ratio:.1%}), "
            f"NO weight = {weighted_no:.2f} ({no_ratio:.1%})"
        )
        
        if yes_ratio >= self.min_reputation_ratio:
            return ConsensusResult.ACCEPTED
        if no_ratio >= self.min_reputation_ratio:
            return ConsensusResult.REJECTED
        
        return ConsensusResult.PENDING

    def _create_and_broadcast_certificate(self, proposal_hash: str, proposal_info: dict, result: ConsensusResult):
        """创建并广播证书"""
        proposal_info['phase'] = ConsensusPhase.DECIDED
        bep = proposal_info['bep']
        
        fact = SemanticFact()
        fact.target_uuid = proposal_hash
        fact.object_class = bep.object_class
        fact.location = bep.estimated_location
        fact.convergence_time = time.time() - proposal_info['start_time']
        fact.accepted = (result == ConsensusResult.ACCEPTED)
        fact.original_bep = bep
        
        if fact.accepted:
            fact.supporting_uavs = [
                str(vid) for vid, (vote, _) in proposal_info['votes'].items() 
                if vote == 'YES'
            ]
        else:
            fact.supporting_uavs = [
                str(vid) for vid, (vote, _) in proposal_info['votes'].items() 
                if vote == 'NO'
            ]
        
        self.certificate_pub.publish(fact)
        
        self.node.get_logger().info(
            f"🎉 Consensus REACHED for {proposal_hash[:8]}: "
            f"Proposal {'ACCEPTED' if fact.accepted else 'REJECTED'}."
        )
        
        msg_size = len(serialize_message(fact))
        self.node.report_event(
            'certificate', 
            f"Result:{'Accepted' if fact.accepted else 'Rejected'}", 
            size_bytes=msg_size
        )

    def handle_certificate(self, fact: SemanticFact):
        """处理收到的证书"""
        if fact.target_uuid in self.decided_targets:
            return
        
        self.decided_targets[fact.target_uuid] = fact
        
        self.node.get_logger().info(
            f"📜 Certificate received: Proposal for {fact.object_class} was "
            f"{'ACCEPTED' if fact.accepted else 'REJECTED'}."
        )
        
        # 信誉管理员更新信誉
        if self.node.is_reputation_manager:
            self._update_reputations_after_consensus(fact.original_bep, fact)

    def _update_reputations_after_consensus(self, bep: Bep, fact: SemanticFact):
        """
        共识达成后更新信誉
        核心修复: 区分提案者和投票者，分别处理
        """
        ground_truth = self._get_ground_truth(bep.object_class)
        if not ground_truth:
            self.node.get_logger().warn(
                f"No ground truth for {bep.object_class}, skipping rep update."
            )
            return
        
        # 判断提案是否正确
        loc_error = math.sqrt(
            (bep.estimated_location.x - ground_truth['location']['x'])**2 + 
            (bep.estimated_location.y - ground_truth['location']['y'])**2
        )
        proposal_was_correct = (bep.object_class == ground_truth['class']) and (loc_error < 2.5)
        
        proposal_hash = self._hash_bep(bep)
        voters_in_this_round = self.node.vote_ledger.get(proposal_hash, {})
        
        if not voters_in_this_round:
            self.node.get_logger().warn(
                f"No votes in ledger for {proposal_hash[:8]}. Cannot update reputations."
            )
            return
        
        # ============ 修复1: 单独处理提案者的信誉 ============
        proposer_id = int(bep.header.frame_id)
        
        if proposal_was_correct:
            # 发起了正确的提案，奖励
            self.node.update_reputation_after_vote(proposer_id, True)
            self.node.get_logger().info(
                f"✅ Proposer {proposer_id} rewarded for correct proposal"
            )
        else:
            # 发起了错误的提案，严重惩罚
            self.node.update_reputation_after_vote(proposer_id, False)
            self.node.get_logger().warn(
                f"❌ Proposer {proposer_id} punished for incorrect proposal"
            )
        # ====================================================
        
        # ============ 修复2: 处理投票者的信誉 ============
        for voter_id, vote in voters_in_this_round.items():
            # 跳过提案者自己 (已经在上面处理过了)
            if voter_id == proposer_id:
                continue
            
            # 投票者的信誉基于是否正确验证了提案
            correct_vote = 'YES' if proposal_was_correct else 'NO'
            behavior_was_correct = (vote == correct_vote)
            
            self.node.update_reputation_after_vote(voter_id, behavior_was_correct)
        # ==============================================
        
        # 清理已处理的投票记录
        if proposal_hash in self.node.vote_ledger:
            del self.node.vote_ledger[proposal_hash]
        
        self.node.get_logger().info(
            f"📊 Reputations updated. Proposal correct: {proposal_was_correct}. "
            f"Consensus: {'ACCEPT' if fact.accepted else 'REJECT'}"
        )

    def _get_ground_truth(self, object_class: str):
        """获取目标的ground truth"""
        ground_truths = {
            'tank': {'class': 'tank', 'location': {'x': 15.0, 'y': 15.0, 'z': 0.5}},
            'truck': {'class': 'truck', 'location': {'x': -10.0, 'y': 8.0, 'z': 0.75}},
            'supply': {'class': 'supply', 'location': {'x': 5.0, 'y': -8.0, 'z': 0.5}},
            'radar': {'class': 'radar', 'location': {'x': -12.0, 'y': -10.0, 'z': 1.0}},
            'infantry': {'class': 'infantry', 'location': {'x': 0.0, 'y': 12.0, 'z': 0.3}}
        }
        return ground_truths.get(object_class)

    def check_timeouts(self):
        """检查提案超时"""
        current_time = time.time()
        for proposal_hash, info in list(self.my_proposals.items()):
            if info['phase'] == ConsensusPhase.VOTING and \
               (current_time - info['start_time']) > self.proposal_timeout:
                self.node.get_logger().warn(f"Proposal {proposal_hash} timed out.")
                info['phase'] = ConsensusPhase.IDLE

    def _check_target_sanity(self, bep: Bep) -> bool:
        """检查提案的基本合理性"""
        loc = bep.estimated_location
        bounds = self.known_target_bounds
        
        return (
            bounds['x_min'] <= loc.x <= bounds['x_max'] and
            bounds['y_min'] <= loc.y <= bounds['y_max'] and
            bounds['z_min'] <= loc.z <= bounds['z_max'] and
            bep.object_class in self.known_classes
        )