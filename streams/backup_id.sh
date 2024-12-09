#!/bin/bash

vm_id=$1

C='\033[0;94m'
G='\033[0;32m'
L='\033[38;5;135m'
R='\033[91m'
NC='\033[0m'

if [ -z "$vm_id" ]; then
    echo -e "${R}Error: VM-ID was left empty!${NC}"
    exit 1
fi

echo -e "${C}Backing up VM $vm_id${NC}"

if [[ $(df -T / | awk 'NR==2 {print $2}') == "zfs" ]]; then
	sudo mkdir /var/lib/vz/dump
    	sudo vzdump $vm_id --dumpdir /var/lib/vz/dump --mode snapshot --compress 0
else
	sudo mkdir /var/lib/pve/local-btrfs/dump
        sudo vzdump $vm_id --dumpdir /var/lib/pve/local-btrfs/dump --mode snapshot --compress 0
fi  

echo -e "${G}Backup of VM ${L}$vm_id${G} executed successfully!${NC}"
