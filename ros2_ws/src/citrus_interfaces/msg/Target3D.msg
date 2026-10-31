# detection_index is local to this image, not a persistent tracking ID.
uint32 detection_index
citrus_interfaces/Detection2D detection
bool depth_valid
string status
# Metres in color optical frame; NaN coordinates when depth_valid is false.
geometry_msgs/Point position
