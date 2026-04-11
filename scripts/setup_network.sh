#!/bin/bash
# Configure the network interface for Unitree G1 robot communication.
# The G1 robot uses 192.168.123.161 by default.

set -e

INTERFACE="${1:-enp3s0}"
HOST_IP="192.168.123.99"
SUBNET="24"

echo "Configuring interface $INTERFACE for Unitree G1 communication..."
sudo ip addr add ${HOST_IP}/${SUBNET} dev ${INTERFACE} 2>/dev/null || \
    echo "Address ${HOST_IP}/${SUBNET} already assigned to ${INTERFACE}"
sudo ip link set ${INTERFACE} up

echo "Verifying robot connectivity..."
if ping -c 1 -W 2 192.168.123.161 > /dev/null 2>&1; then
    echo "Robot reachable at 192.168.123.161"
else
    echo "WARNING: Robot not reachable at 192.168.123.161"
    echo "Check cable connection and robot power."
fi

echo ""
echo "Set these environment variables before launching:"
echo "  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp"
echo "  export CYCLONEDDS_URI='<CycloneDDS><Domain><General>"
echo "    <NetworkInterfaceAddress>${INTERFACE}</NetworkInterfaceAddress>"
echo "  </General></Domain></CycloneDDS>'"
