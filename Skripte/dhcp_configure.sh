#!/bin/bash

# This script is tested on Ubuntu-Server. If you use another OS, adjustments might be necessary, e.g for swap. 

C='\033[0;94m'
NC='\033[0m'

sudo swapoff -a
sudo rm -f /swap.img

cd /home/user
sudo apt-get update && sudo apt upgrade -y
sudo apt install mc termshark kea lnav -y

echo "alias ipbc='ip -br -c a'" >> /home/user/.bashrc
source ~/.bashrc

sudo apt install qemu-guest-agent -y
sudo systemctl start qemu-guest-agent
sudo systemctl status qemu-guest-agent

echo "Enter the (sudo) password of the DHCP-server user for askpass script:"
read password
touch askpass_script.sh
echo "#!/bin/bash
echo '"$password"'" > askpass_script.sh
chmod +x /home/user/askpass_script.sh
chmod 700 /home/user/askpass_script.sh

echo "Enter the number of the PVE node:"
read node_nr
cd /home/user/.ssh
touch config
echo "Host u$node_nr
  HostName 192.168.10.1$node_nr
  User user" > config
ssh-keygen -t ed25519 -f id_ed25519 -N ""

cd ..
echo "alias u$node_nr='ssh u$node_nr'">> .bashrc
source ~/.bashrc

echo -e "${C}dhcp_configure.sh executed successfully!${NC}"

sudo reboot
