#!/bin/bash

provider=$1
first_router=$2
last_router=$3

C='\033[0;94m'
G='\033[0;32m'
L='\033[38;5;135m'
R='\033[91m'
NC='\033[0m'

if [ -z "$provider" ] || [ -z "$first_router" ] || [ -z "$last_router" ]; then
    echo -e "${R}Error: At least one variable empty!${NC}"
    exit 1
fi

if [[ $(df -T / | awk 'NR==2 {print $2}') == "zfs" ]]
	then
		sudo mkdir /var/lib/vz/dump
        for i in $(seq $first_router $last_router); do  
			vmid=${provider}0${provider}0$(printf '%02d' $i)
			echo -e "${C}Backing up router ${vmid}${NC}"
    		sudo vzdump ${provider}0${provider}00$i --dumpdir /var/lib/vz/dump --mode snapshot --compress 0
			sleep 5
    	done
	else
		sudo mkdir /var/lib/pve/local-btrfs/dump
		for i in $(seq $first_router $last_router); do 
			vmid=${provider}0${provider}0$(printf '%02d' $i)
			echo -e "${C}Backing up router ${vmid}${NC}"
			sudo vzdump ${provider}0${provider}00$i --dumpdir /var/lib/pve/local-btrfs/dump --mode snapshot --compress 0
			sleep 5
    	done
fi  

if [[ $first_router == $last_router ]]; then
	echo -e "${G}Backup of router ${L}p${provider}r${first_router}v${G} executed successfully!${NC}"
else
	echo -e "${G}Backups of routers ${L}p${provider}r${first_router}v${G} to ${L}p${provider}r${last_router}v${G} executed successfully!${NC}"
fi
