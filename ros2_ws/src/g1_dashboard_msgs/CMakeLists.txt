cmake_minimum_required(VERSION 3.8)
project(g1_dashboard_msgs)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/JointCommand.msg"
  "msg/RobotState.msg"
  "msg/SafetyStatus.msg"
  "srv/EmergencyStop.srv"
  "srv/SetControlMode.srv"
  DEPENDENCIES std_msgs
)

ament_package()
