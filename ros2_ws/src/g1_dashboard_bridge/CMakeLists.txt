cmake_minimum_required(VERSION 3.8)
project(g1_dashboard_bridge)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(g1_dashboard_msgs REQUIRED)

# Optional: full Unitree integration. Set -DUSE_UNITREE_HG=ON and ensure
# the unitree_hg package is available in the workspace.
option(USE_UNITREE_HG "Enable unitree_hg integration for real robot control" OFF)

if(USE_UNITREE_HG)
  find_package(unitree_hg REQUIRED)
  add_compile_definitions(USE_UNITREE_HG)
  message(STATUS "Building with unitree_hg support")
else()
  message(STATUS "Building in standalone mode (no unitree_hg)")
endif()

# Bridge library
add_library(bridge_lib
  src/safety_monitor.cpp
)
target_include_directories(bridge_lib PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
ament_target_dependencies(bridge_lib
  rclcpp
  g1_dashboard_msgs
)

# Bridge node executable
add_executable(g1_dashboard_bridge_node
  src/bridge_node.cpp
)
target_link_libraries(g1_dashboard_bridge_node bridge_lib)
ament_target_dependencies(g1_dashboard_bridge_node
  rclcpp
  sensor_msgs
  std_msgs
  geometry_msgs
  tf2_ros
  g1_dashboard_msgs
)
if(USE_UNITREE_HG)
  ament_target_dependencies(g1_dashboard_bridge_node unitree_hg)
endif()

install(TARGETS
  bridge_lib
  g1_dashboard_bridge_node
  DESTINATION lib/${PROJECT_NAME}
)
install(DIRECTORY include/ DESTINATION include)
install(DIRECTORY config/ DESTINATION share/${PROJECT_NAME}/config)
install(DIRECTORY launch/ DESTINATION share/${PROJECT_NAME}/launch)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  find_package(ament_cmake_gtest REQUIRED)
  ament_lint_auto_find_test_dependencies()

  ament_add_gtest(test_safety_monitor test/test_safety_monitor.cpp)
  target_link_libraries(test_safety_monitor bridge_lib)

  ament_add_gtest(test_joint_limits test/test_joint_limits.cpp)
  target_link_libraries(test_joint_limits bridge_lib)
endif()

ament_package()
