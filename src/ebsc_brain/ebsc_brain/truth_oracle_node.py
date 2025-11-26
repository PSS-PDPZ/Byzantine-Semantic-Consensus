import rclpy
from rclpy.node import Node
from ebsc_interfaces.srv import VerifyProof
import json

class TruthOracle(Node):
    """
    Simulates a TEE as a centralized "Truth Oracle".
    NEW: It has a static, built-in knowledge of the ground truth to avoid race conditions.
    """
    def __init__(self):
        super().__init__('truth_oracle')
        
        # 核心改动：内置一份地面实况地图，与 agent 和 world 文件保持一致
        self.ground_truth_targets = {
            'tank': {'x': 15.0, 'y': 15.0},
            'truck': {'x': -10.0, 'y': 8.0},
            'supply': {'x': 5.0, 'y': -8.0},
            'radar': {'x': -12.0, 'y': -10.0},
            'infantry': {'x': 0.0, 'y': 12.0}
        }
        
        # 创建验证服务
        self.verify_srv = self.create_service(
            VerifyProof,
            'verify_proof',
            self.verify_proof_callback)
            
        self.get_logger().info("✅ Truth Oracle is running with static ground truth map.")

    def verify_proof_callback(self, request, response):
        """
        Service callback to verify a claim's truthfulness against the built-in ground truth map.
        """
        bep = request.bep_proposal
        claim_str = bep.crypto_proof

        try:
            claim = json.loads(claim_str)
            proposer_id = claim['proposer_id']
            claimed_class = claim['object_class']
            claimed_loc = claim['location']

            # 检查声明的类别是否存在于我们的地图中
            if claimed_class not in self.ground_truth_targets:
                self.get_logger().warn(f"❌ Claim from UAV {proposer_id} for unknown class '{claimed_class}' rejected.")
                response.is_valid = False
                return response

            # 获取该类别目标的真实位置
            gt_loc = self.ground_truth_targets[claimed_class]
            
            # 计算声明位置与真实位置的距离
            dist = ((gt_loc['x'] - claimed_loc['x'])**2 + 
                    (gt_loc['y'] - claimed_loc['y'])**2)**0.5
            
            # 如果距离在误差范围内，则认为声明为真
            if dist < 2.5: # 允许 2.5m 的误差容忍度
                self.get_logger().info(f"✅ Proof from UAV {proposer_id} for '{claimed_class}' is VALID (error: {dist:.2f}m).")
                response.is_valid = True
            else:
                self.get_logger().warn(f"❌ Proof from UAV {proposer_id} for '{claimed_class}' is a FALSE claim. "
                                     f"Claimed loc: ({claimed_loc['x']},{claimed_loc['y']}), "
                                     f"GT loc: ({gt_loc['x']},{gt_loc['y']}), Distance: {dist:.2f}m.")
                response.is_valid = False

        except (json.JSONDecodeError, KeyError) as e:
            self.get_logger().error(f"Invalid proof format from UAV {bep.header.frame_id}. Error: {e}. Content: '{claim_str}'")
            response.is_valid = False
            
        return response

def main(args=None):
    rclpy.init(args=args)
    oracle_node = TruthOracle()
    try:
        rclpy.spin(oracle_node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            oracle_node.destroy_node()
            rclpy.shutdown()

if __name__ == '__main__':
    main()