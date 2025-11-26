import rclpy
from .ebsc_agent import EBSCAgent

def main(args=None):
    rclpy.init(args=args)
    ebsc_agent = EBSCAgent()
    try:
        rclpy.spin(ebsc_agent)
    except KeyboardInterrupt:
        ebsc_agent.get_logger().info("UAV node interrupted by user.")
    finally:
        ebsc_agent.destroy_node()

if __name__ == '__main__':
    main()