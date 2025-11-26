string target_uuid
string object_class
geometry_msgs/Point location
# The main voters who reached a consensus
string[] supporting_uavs 
float64 convergence_time
#  True represents acceptance, and false represents rejection. Whether it's acceptance or rejection, it represents a consensus
bool accepted 
ebsc_interfaces/Bep original_bep