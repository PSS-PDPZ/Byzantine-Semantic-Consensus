string target_uuid
string object_class
geometry_msgs/Point location
# 达成共识的主要投票者
string[] supporting_uavs 
float64 convergence_time
#  true代表接受，false代表拒绝   不管是接受还是拒绝，都是一种共识
bool accepted 
ebsc_interfaces/Bep original_bep