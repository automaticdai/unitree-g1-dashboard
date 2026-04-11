cmake_minimum_required(VERSION 3.8)
project(g1_dashboard_bridge)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(g1_dashboard_msgs REQUIRED)

# Bridge node (placeholder — implementation in Phase 2)
# add_executable(g1_dashboard_bridge_node
#   src/bridge_node.cpp
#   src/safety_monitor.cpp
#   src/joint_command_handler.cpp
#   src/tf_broadcaster.cpp
# )
# ament_target_dependencies(g1_dashboard_bridge_node
#   rclcpp sensor_msgs std_msgs geometry_msgs tf2_ros g1_dashboard_msgs
# )
# install(TARGETS g1_dashboard_bridge_node DESTINATION lib/${PROJECT_NAME})

install(DIRECTORY config/ DESTINATION share/${PROJECT_NAME}/config)
install(DIRECTORY launch/ DESTINATION share/${PROJECT_NAME}/launch)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
