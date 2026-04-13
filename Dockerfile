FROM osrf/ros:humble-desktop

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-pyside6.qtcore \
    python3-pyside6.qtgui \
    python3-pyside6.qtwidgets \
    python3-pyside6.qtopenglwidgets \
    python3-opencv \
    ros-humble-cv-bridge \
    ros-humble-sensor-msgs-py \
    libxcb-xinerama0 \
    libxkbcommon-x11-0 \
    libegl1 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
    PyOpenGL PyOpenGL-accelerate \
    pyqtgraph \
    numpy

WORKDIR /workspace
COPY ros2_ws /workspace/ros2_ws

RUN bash -c "source /opt/ros/humble/setup.bash && \
    cd /workspace/ros2_ws && \
    colcon build --symlink-install"

# Source overlays on shell start
RUN echo 'source /opt/ros/humble/setup.bash' >> /etc/bash.bashrc && \
    echo 'source /workspace/ros2_ws/install/setup.bash' >> /etc/bash.bashrc

ENV QT_X11_NO_MITSHM=1
CMD ["bash", "-lc", "ros2 run g1_dashboard dashboard"]
