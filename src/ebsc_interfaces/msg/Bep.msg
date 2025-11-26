# Bep.msg (Belief-Evidence Package)

std_msgs/Header header

# Belief (The claim being made)
string object_class
float64 confidence_score
geometry_msgs/Point estimated_location

# Evidence (The proof to back the claim)
# DEPRECATED: We no longer use feature_vector for validation
float32[] feature_vector 
# NEW: This is the cryptographic proof from the TEE/Truth Oracle
string crypto_proof

# Contextual Metadata
geometry_msgs/Pose uav_pose_at_perception