std_msgs/Header header
uint8 mode                       # 0=unknown, 1=idle, 2=standing, 3=walking, 4=lowlevel, 5=damping, 6=emergency
uint32[] error_codes
float32[29] motor_temperatures   # Celsius per motor
float32[4] foot_forces           # N per foot contact sensor
string mode_name                 # Human-readable mode string
